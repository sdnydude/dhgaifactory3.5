# Copyright 2024 CHATS-lab
# Ported to DHG AI Factory — Digital Harmony Group
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

"""
distribution.py — Core probability distribution primitives for Verbalized Sampling.

Ported from CHATS-lab selection.py. Provides:
  - repair_weight:         Normalise/repair raw LLM weight values (str, float, %, NaN …)
  - Item:                  Frozen dataclass representing one scored candidate response
  - DiscreteDist:          Validated discrete probability distribution over Items
  - postprocess_responses: Steps 2-7 of the VS 10-step pipeline

Field naming: internal code uses compact names (Item.text, Item.p, Item.meta).
The main.py API layer maps these to public spec names (content, probability, metadata).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple

__all__ = [
    "repair_weight",
    "Item",
    "DiscreteDist",
    "postprocess_responses",
]

# ---------------------------------------------------------------------------
# repair_weight
# ---------------------------------------------------------------------------

def repair_weight(raw: Any) -> Tuple[float, List[str]]:
    """Coerce a raw LLM weight value to a valid float in [0, 1].

    Args:
        raw: The raw probability/weight value from the LLM response.
             May be a float, int, string (including "45%"), None, NaN, or Inf.

    Returns:
        (value, repairs) where:
          value   — float in [0.0, 1.0]
          repairs — list of repair tags applied (e.g. ["percentage"], ["negative"])
    """
    repairs: List[str] = []

    # --- Handle None ---
    if raw is None:
        return 0.0, ["invalid"]

    # --- Handle string inputs ---
    if isinstance(raw, str):
        s = raw.strip()
        if s.endswith("%"):
            try:
                value = float(s[:-1]) / 100.0
                repairs.append("percentage")
            except ValueError:
                return 0.0, ["invalid"]
        else:
            try:
                value = float(s)
            except ValueError:
                return 0.0, ["invalid"]
    else:
        # Numeric (float, int, …)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return 0.0, ["invalid"]

    # --- Reject NaN / Inf ---
    if math.isnan(value) or math.isinf(value):
        return 0.0, ["invalid"]

    # --- Clamp negative ---
    if value < 0.0:
        repairs.append("negative")
        value = 0.0

    # --- Clip > 1 ---
    if value > 1.0:
        repairs.append("clip>1")
        value = 1.0

    return value, repairs


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Item:
    """A single candidate response with its probability and optional metadata.

    Attributes:
        text: The response text content.
        p:    Probability in [0.0, 1.0].
        meta: Arbitrary metadata dict (defaults to empty dict).
    """

    text: str
    p: float
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (0.0 <= self.p <= 1.0):
            raise ValueError(
                f"Item probability must be in [0, 1], got {self.p!r}"
            )

    def __repr__(self) -> str:
        display = self.text if len(self.text) <= 40 else self.text[:37] + "..."
        return f"Item(text={display!r}, p={self.p:.4f})"

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "p": self.p, "meta": dict(self.meta)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Item":
        return cls(text=d["text"], p=d["p"], meta=d.get("meta", {}))


# ---------------------------------------------------------------------------
# DiscreteDist
# ---------------------------------------------------------------------------

_SUM_TOL = 1e-6  # tolerance for probability sum validation


class DiscreteDist:
    """A validated discrete probability distribution over Item objects.

    Invariants enforced at construction:
      1. Items are sorted in descending order of probability.
      2. Probabilities sum to 1.0 (within _SUM_TOL).

    Args:
        items: Sequence of Items. Must be sorted descending and sum to 1.0.
        trace: Optional metadata dict (audit trail, repair log, etc.).
    """

    def __init__(
        self,
        items: List[Item],
        trace: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._items: List[Item] = list(items)
        self._trace: Dict[str, Any] = trace or {}

        if self._items:
            # Validate descending order
            for i in range(len(self._items) - 1):
                if self._items[i].p < self._items[i + 1].p:
                    raise ValueError(
                        "DiscreteDist items must be sorted in descending order of probability. "
                        f"Item[{i}].p={self._items[i].p} < Item[{i+1}].p={self._items[i+1].p}"
                    )
            # Validate sum
            total = sum(it.p for it in self._items)
            if not math.isclose(total, 1.0, abs_tol=_SUM_TOL):
                raise ValueError(
                    f"DiscreteDist probabilities must sum to 1.0, got {total:.6f}"
                )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator[Item]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: int) -> Item:
        return self._items[index]

    def argmax(self) -> Item:
        """Return the Item with the highest probability.

        Raises:
            ValueError: If the distribution is empty.
        """
        if not self._items:
            raise ValueError("Cannot call argmax() on an empty distribution.")
        return self._items[0]

    def sample(self, seed: Optional[int] = None) -> Item:
        """Draw one Item proportional to probability.

        Args:
            seed: Optional RNG seed for deterministic sampling.

        Returns:
            A randomly selected Item.

        Raises:
            ValueError: If the distribution is empty.
        """
        if not self._items:
            raise ValueError("Cannot sample from an empty distribution.")

        rng = random.Random(seed)
        r = rng.random()
        cumulative = 0.0
        for item in self._items:
            cumulative += item.p
            if r <= cumulative:
                return item
        # Floating-point edge: return last item
        return self._items[-1]

    # ------------------------------------------------------------------
    # Transformations
    # ------------------------------------------------------------------

    def filter_items(self, min_p: float) -> List[Item]:
        """Return items with p >= min_p, renormalized to sum to 1.0.

        Args:
            min_p: Minimum probability threshold (inclusive).

        Returns:
            Renormalized list of Items sorted descending.

        Raises:
            ValueError: If no items meet the threshold.
        """
        survivors = [it for it in self._items if it.p >= min_p]
        if not survivors:
            raise ValueError(
                f"filter_items(min_p={min_p}) eliminated all items."
            )
        total = sum(it.p for it in survivors)
        renormed = [
            Item(text=it.text, p=it.p / total, meta=it.meta)
            for it in survivors
        ]
        renormed.sort(key=lambda x: x.p, reverse=True)
        return renormed

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [it.to_dict() for it in self._items],
            "trace": dict(self._trace),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DiscreteDist":
        items = [Item.from_dict(x) for x in d["items"]]
        trace = d.get("trace", {})
        return cls(items=items, trace=trace)


# ---------------------------------------------------------------------------
# postprocess_responses  — Steps 2-7 of the VS 10-step pipeline
# ---------------------------------------------------------------------------
# Step 1 (LLM call) and Steps 8-10 (selection / output) happen in main.py.
#
# Pipeline executed here:
#   Step 2 — Extract weights from parsed_responses dicts
#   Step 3 — Repair each weight via repair_weight()
#   Step 4 — Filter: remove items whose repaired weight is 0.0
#             (only if survivors remain; otherwise keep all for uniform)
#   Step 5 — Normalize to sum = 1.0 (uniform if all-zero)
#   Step 6 — Apply min_probability filter with tau relaxation (min_k_survivors)
#   Step 7 — Sort descending and return (items, trace)

def postprocess_responses(
    parsed_responses: List[Dict[str, Any]],
    min_probability: float,
    min_k_survivors: int,
    weight_mode: str,
) -> Tuple[List[Item], Dict[str, Any]]:
    """Convert raw parsed LLM responses into a sorted, normalized list of Items.

    Args:
        parsed_responses:  List of dicts with 'response' (text) and a weight
                           field (named by weight_mode, e.g. 'probability').
        min_probability:   Minimum probability threshold for Step 6 filtering.
        min_k_survivors:   Guarantee at least this many items survive (tau relaxation).
        weight_mode:       Key in each response dict that holds the weight value
                           (e.g. 'probability', 'confidence').

    Returns:
        (items, trace) where:
          items — List[Item] sorted descending, probabilities summing to 1.0.
                  Empty list if parsed_responses is empty.
          trace — Dict with audit info (repairs, normalization constant, etc.).
    """
    trace: Dict[str, Any] = {
        "n_input": len(parsed_responses),
        "weight_mode": weight_mode,
        "repairs": [],
        "n_zero_filtered": 0,
        "tau_relaxed": False,
        "normalization_constant": None,
    }

    # --- Guard: empty input ---
    if not parsed_responses:
        return [], trace

    # --- Step 2 + 3: Extract and repair weights ---
    texts: List[str] = []
    weights: List[float] = []
    all_repairs: List[Dict[str, Any]] = []

    for resp in parsed_responses:
        text = resp.get("response", "")
        raw_w = resp.get(weight_mode, 0.0)
        repaired_w, repair_tags = repair_weight(raw_w)

        texts.append(text)
        weights.append(repaired_w)
        if repair_tags:
            all_repairs.append({"text_prefix": text[:40], "tags": repair_tags})

    trace["repairs"] = all_repairs

    # --- Step 4: Filter zero weights (only if at least one non-zero survives) ---
    non_zero_mask = [w > 0.0 for w in weights]
    if any(non_zero_mask):
        filtered_texts = [t for t, nz in zip(texts, non_zero_mask) if nz]
        filtered_weights = [w for w, nz in zip(weights, non_zero_mask) if nz]
        n_filtered = len(texts) - len(filtered_texts)
        trace["n_zero_filtered"] = n_filtered
    else:
        # All zeros — keep all for uniform distribution
        filtered_texts = texts
        filtered_weights = weights
        trace["n_zero_filtered"] = 0

    # --- Step 5: Normalize ---
    total = sum(filtered_weights)
    if total == 0.0 or math.isclose(total, 0.0, abs_tol=1e-12):
        # Uniform
        n = len(filtered_texts)
        normalized = [1.0 / n] * n
    else:
        normalized = [w / total for w in filtered_weights]
    trace["normalization_constant"] = total

    # --- Step 6: Apply min_probability with tau relaxation ---
    # Sort by normalized probability descending to implement min_k_survivors correctly
    paired = sorted(zip(normalized, filtered_texts), key=lambda x: x[0], reverse=True)

    # Collect survivors above threshold
    survivors = [(p, t) for p, t in paired if p >= min_probability]

    # Tau relaxation: if too few survive, take top min_k_survivors regardless
    if len(survivors) < min_k_survivors:
        survivors = list(paired[:min_k_survivors])
        trace["tau_relaxed"] = True

    # Re-normalize survivors
    survivor_total = sum(p for p, _ in survivors)
    if math.isclose(survivor_total, 0.0, abs_tol=1e-12):
        n_surv = len(survivors)
        survivors = [(1.0 / n_surv, t) for _, t in survivors]
    else:
        survivors = [(p / survivor_total, t) for p, t in survivors]

    # --- Step 7: Sort descending and build Item list ---
    survivors.sort(key=lambda x: x[0], reverse=True)
    items = [Item(text=t, p=p) for p, t in survivors]

    return items, trace
