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

"""selection.py — Selection strategy dispatch for Verbalized Sampling.

Supports three strategies:
  - argmax:  Return the highest-probability item deterministically.
  - sample:  Draw one item proportional to probability.
  - human:   Return the item at the caller-specified index (0-based).
"""

from typing import Optional

from distribution import DiscreteDist, Item


def select_from_distribution(
    dist: DiscreteDist,
    strategy: str = "argmax",
    human_selection_index: Optional[int] = None,
) -> Item:
    """Select one Item from a DiscreteDist using the specified strategy.

    Args:
        dist:                   A validated DiscreteDist (sorted descending, sums to 1.0).
        strategy:               One of 'argmax', 'sample', or 'human'.
        human_selection_index:  Required when strategy is 'human'. Zero-based index
                                into the distribution (items are sorted descending by p).

    Returns:
        The selected Item.

    Raises:
        ValueError: For 'human' strategy when index is missing or out of range.
        ValueError: For any unknown strategy value.
    """
    if strategy == "argmax":
        return dist.argmax()

    if strategy == "sample":
        return dist.sample()

    if strategy == "human":
        if human_selection_index is None:
            raise ValueError(
                "human_selection_index is required when strategy is 'human'"
            )
        if human_selection_index < 0 or human_selection_index >= len(dist):
            raise ValueError(
                f"human_selection_index {human_selection_index} out of range "
                f"for distribution with {len(dist)} items"
            )
        return dist[human_selection_index]

    raise ValueError(
        f"Unknown strategy: {strategy!r}. Use 'argmax', 'sample', or 'human'."
    )
