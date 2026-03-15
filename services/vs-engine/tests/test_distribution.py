# Copyright 2024 CHATS-lab (ported to DHG AI Factory)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for distribution.py — Item, DiscreteDist, repair_weight, postprocess_responses."""

import math
import pytest

from distribution import Item, DiscreteDist, repair_weight, postprocess_responses


# ---------------------------------------------------------------------------
# TestRepairWeight — 10 tests
# ---------------------------------------------------------------------------

class TestRepairWeight:
    def test_normal_float_passes_through(self):
        value, repairs = repair_weight(0.25)
        assert math.isclose(value, 0.25)
        assert repairs == []

    def test_percentage_string_converted(self):
        value, repairs = repair_weight("45%")
        assert math.isclose(value, 0.45)
        assert "percentage" in repairs

    def test_negative_clamped_to_zero(self):
        value, repairs = repair_weight(-0.3)
        assert value == 0.0
        assert "negative" in repairs

    def test_nan_returns_zero(self):
        value, repairs = repair_weight(float("nan"))
        assert value == 0.0
        assert "invalid" in repairs

    def test_inf_returns_zero(self):
        value, repairs = repair_weight(float("inf"))
        assert value == 0.0
        assert "invalid" in repairs

    def test_string_float_parsed(self):
        value, repairs = repair_weight("0.3")
        assert math.isclose(value, 0.3)
        assert repairs == []

    def test_unparseable_string_returns_zero(self):
        value, repairs = repair_weight("not_a_number")
        assert value == 0.0
        assert "invalid" in repairs

    def test_greater_than_one_clipped(self):
        value, repairs = repair_weight(1.5)
        assert value == 1.0
        assert "clip>1" in repairs

    def test_zero_passes_through(self):
        value, repairs = repair_weight(0.0)
        assert value == 0.0
        assert repairs == []

    def test_none_returns_zero(self):
        value, repairs = repair_weight(None)
        assert value == 0.0
        assert "invalid" in repairs


# ---------------------------------------------------------------------------
# TestItem — 4 tests
# ---------------------------------------------------------------------------

class TestItem:
    def test_create_valid_item(self):
        item = Item(text="hello", p=0.5)
        assert item.text == "hello"
        assert item.p == 0.5
        assert item.meta == {}

    def test_invalid_probability_raises(self):
        with pytest.raises(ValueError):
            Item(text="hello", p=1.5)

    def test_negative_probability_raises(self):
        with pytest.raises(ValueError):
            Item(text="hello", p=-0.1)

    def test_repr_truncates_long_text(self):
        item = Item(text="x" * 100, p=0.5)
        r = repr(item)
        assert "..." in r


# ---------------------------------------------------------------------------
# TestDiscreteDist — 12 tests
# ---------------------------------------------------------------------------

class TestDiscreteDist:
    def _two_item_dist(self):
        items = [Item(text="a", p=0.7), Item(text="b", p=0.3)]
        return DiscreteDist(items=items)

    def test_create_valid_distribution(self):
        dist = self._two_item_dist()
        assert len(list(dist)) == 2

    def test_probabilities_must_sum_to_one(self):
        items = [Item(text="a", p=0.5), Item(text="b", p=0.3)]
        with pytest.raises(ValueError):
            DiscreteDist(items=items)

    def test_must_be_sorted_descending(self):
        # [0.3, 0.7] is ascending — should raise
        items = [Item(text="a", p=0.3), Item(text="b", p=0.7)]
        with pytest.raises(ValueError):
            DiscreteDist(items=items)

    def test_argmax_returns_first(self):
        dist = self._two_item_dist()
        best = dist.argmax()
        assert best.text == "a"
        assert best.p == 0.7

    def test_argmax_empty_raises(self):
        # Build via internal bypass then call argmax
        dist = object.__new__(DiscreteDist)
        dist._items = []
        dist._trace = {}
        with pytest.raises(ValueError):
            dist.argmax()

    def test_sample_returns_valid_item(self):
        dist = self._two_item_dist()
        result = dist.sample(seed=42)
        assert result.text in {"a", "b"}

    def test_sample_deterministic_with_seed(self):
        dist = self._two_item_dist()
        results = [dist.sample(seed=99) for _ in range(10)]
        texts = {r.text for r in results}
        assert len(texts) == 1  # same seed → same item every time

    def test_filter_items_renormalizes(self):
        items = [Item(text="a", p=0.6), Item(text="b", p=0.3), Item(text="c", p=0.1)]
        dist = DiscreteDist(items=items)
        filtered = dist.filter_items(min_p=0.3)
        total = sum(i.p for i in filtered)
        assert math.isclose(total, 1.0, abs_tol=1e-9)

    def test_filter_all_raises(self):
        dist = self._two_item_dist()
        with pytest.raises(ValueError):
            dist.filter_items(min_p=0.99)

    def test_single_item_wrong_probability_raises(self):
        # Single item must have p=1.0 to sum to 1.0
        items = [Item(text="a", p=0.5)]
        with pytest.raises(ValueError):
            DiscreteDist(items=items)

    def test_sample_empty_raises(self):
        dist = object.__new__(DiscreteDist)
        dist._items = []
        dist._trace = {}
        with pytest.raises(ValueError):
            dist.sample(seed=1)

    def test_to_dict_and_back(self):
        dist = self._two_item_dist()
        d = dist.to_dict()
        restored = DiscreteDist.from_dict(d)
        assert len(list(restored)) == 2
        assert math.isclose(restored.argmax().p, 0.7)


# ---------------------------------------------------------------------------
# TestPostprocessResponses — 6 tests
# ---------------------------------------------------------------------------

class TestPostprocessResponses:
    def _make_response(self, content, probability):
        return {"response": content, "probability": probability}

    def test_normal_responses_produce_valid_dist(self):
        responses = [
            self._make_response("Response A", 0.50),
            self._make_response("Response B", 0.30),
            self._make_response("Response C", 0.20),
        ]
        items, trace = postprocess_responses(
            parsed_responses=responses,
            min_probability=0.05,
            min_k_survivors=1,
            weight_mode="probability",
        )
        assert len(items) == 3
        total = sum(i.p for i in items)
        assert math.isclose(total, 1.0, abs_tol=1e-9)
        # Sorted descending
        probs = [i.p for i in items]
        assert probs == sorted(probs, reverse=True)

    def test_malformed_weights_get_repaired(self):
        responses = [
            self._make_response("Response A", "45%"),
            self._make_response("Response B", -0.1),
            self._make_response("Response C", 0.3),
        ]
        items, trace = postprocess_responses(
            parsed_responses=responses,
            min_probability=0.0,
            min_k_survivors=1,
            weight_mode="probability",
        )
        # At least 2 items should survive after repair (the -0.1 becomes 0.0 and
        # may be filtered, but "45%" and "0.3" repair cleanly)
        assert len(items) >= 2

    def test_min_probability_filters_junk(self):
        responses = [
            self._make_response("Response A", 0.50),
            self._make_response("Response B", 0.30),
            self._make_response("Response C", 0.15),
            self._make_response("Response D", 0.05),  # below threshold after normalize
        ]
        items, trace = postprocess_responses(
            parsed_responses=responses,
            min_probability=0.10,
            min_k_survivors=1,
            weight_mode="probability",
        )
        # Response D (0.05) should be filtered — 3 survivors
        assert len(items) == 3

    def test_tau_relaxation_preserves_min_k(self):
        # All weights are very small — after normalizing they'd all be ~equal
        # but min_probability might cut them. min_k_survivors=2 prevents full elimination.
        responses = [
            self._make_response("Response A", 0.001),
            self._make_response("Response B", 0.001),
            self._make_response("Response C", 0.001),
        ]
        items, trace = postprocess_responses(
            parsed_responses=responses,
            min_probability=0.50,  # very high threshold — would kill everything
            min_k_survivors=2,
            weight_mode="probability",
        )
        assert len(items) >= 2

    def test_all_zero_weights_produce_uniform(self):
        responses = [
            self._make_response("Response A", 0.0),
            self._make_response("Response B", 0.0),
            self._make_response("Response C", 0.0),
        ]
        items, trace = postprocess_responses(
            parsed_responses=responses,
            min_probability=0.0,
            min_k_survivors=1,
            weight_mode="probability",
        )
        assert len(items) == 3
        for item in items:
            assert math.isclose(item.p, 1 / 3, abs_tol=1e-9)

    def test_empty_input_returns_empty(self):
        items, trace = postprocess_responses(
            parsed_responses=[],
            min_probability=0.05,
            min_k_survivors=1,
            weight_mode="probability",
        )
        assert items == []
        assert isinstance(trace, dict)
