# services/vs-engine/tests/test_selection.py
import pytest


class TestSelectFromDistribution:
    def _make_dist(self):
        from distribution import Item, DiscreteDist
        items = [
            Item(text="best", p=0.5),
            Item(text="second", p=0.3),
            Item(text="third", p=0.2),
        ]
        return DiscreteDist(items, trace={"model": "test"})

    def test_argmax_returns_highest(self):
        from selection import select_from_distribution
        dist = self._make_dist()
        result = select_from_distribution(dist, strategy="argmax")
        assert result.text == "best"

    def test_sample_returns_valid_item(self):
        from selection import select_from_distribution
        dist = self._make_dist()
        result = select_from_distribution(dist, strategy="sample")
        assert result.text in ("best", "second", "third")

    def test_human_selection_by_index(self):
        from selection import select_from_distribution
        dist = self._make_dist()
        result = select_from_distribution(dist, strategy="human", human_selection_index=2)
        assert result.text == "third"

    def test_human_missing_index_raises(self):
        from selection import select_from_distribution
        dist = self._make_dist()
        with pytest.raises(ValueError, match="human_selection_index"):
            select_from_distribution(dist, strategy="human")

    def test_human_index_out_of_bounds_raises(self):
        from selection import select_from_distribution
        dist = self._make_dist()
        with pytest.raises(ValueError, match="out of range"):
            select_from_distribution(dist, strategy="human", human_selection_index=5)

    def test_unknown_strategy_raises(self):
        from selection import select_from_distribution
        dist = self._make_dist()
        with pytest.raises(ValueError, match="Unknown strategy"):
            select_from_distribution(dist, strategy="magic")
