# Copyright 2026 CHATS-lab / Digital Harmony Group
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
TTCTEvaluator — Torrance Tests of Creative Thinking scoring for VS Engine.

Ported from CHATS-lab analysis/evals/ (Apache 2.0).

Evaluates LLM responses across four TTCT dimensions:
  - Fluency:     quantity of distinct, relevant ideas
  - Flexibility: variety of conceptual categories covered
  - Originality: uniqueness and unexpectedness of ideas
  - Elaboration: depth, detail, and development of ideas

Each dimension is scored 1–5 by a judge LLM. A composite score is computed
as a weighted average of the four dimension scores.
"""

from __future__ import annotations

from typing import Dict

# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------

TTCT_WEIGHTS: Dict[str, float] = {
    "fluency": 0.25,
    "flexibility": 0.25,
    "originality": 0.25,
    "elaboration": 0.25,
}

_DIMENSIONS = list(TTCT_WEIGHTS.keys())

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def compute_composite_score(scores: Dict[str, float]) -> float:
    """Compute a weighted composite TTCT score from dimension scores.

    Args:
        scores: Mapping of dimension name to numeric score (1–5 scale).
                Must contain all four TTCT dimensions.

    Returns:
        Weighted composite score as a float on the 1–5 scale.
    """
    return sum(scores[dim] * TTCT_WEIGHTS[dim] for dim in _DIMENSIONS)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def parse_judge_response(raw: Dict[str, Dict]) -> Dict[str, float]:
    """Extract dimension scores from a structured judge response and add composite.

    The judge is expected to return a dict with one key per TTCT dimension.
    Each value must be a dict containing at least a ``"score"`` key.

    Args:
        raw: Structured judge output, e.g.::

            {
                "fluency":     {"score": 4, "justification": "..."},
                "flexibility": {"score": 3, "justification": "..."},
                "originality": {"score": 5, "justification": "..."},
                "elaboration": {"score": 3, "justification": "..."},
            }

    Returns:
        Dict with keys ``fluency``, ``flexibility``, ``originality``,
        ``elaboration`` (int scores) and ``composite`` (float).

    Raises:
        KeyError: If any required dimension is absent from ``raw``.
    """
    result: Dict[str, float] = {}
    for dim in _DIMENSIONS:
        result[dim] = raw[dim]["score"]  # KeyError propagates if dim missing
    result["composite"] = compute_composite_score(result)
    return result


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = """\
You are an expert evaluator applying the Torrance Tests of Creative Thinking (TTCT) \
framework to assess the creativity of an AI-generated response.

## Original Prompt
{original_prompt}

## Response to Evaluate
{response_text}

## Evaluation Task

Score the response on each of the four TTCT dimensions using a 1-5 scale \
(1 = very low, 5 = very high). Provide a brief justification for each score.

### Dimensions

**Fluency** (1-5)
The quantity of distinct, relevant, and meaningful ideas present in the response.
- 1: One idea or very few ideas, highly repetitive
- 3: Several ideas but limited range
- 5: Rich variety of distinct ideas, all relevant

**Flexibility** (1-5)
The variety of conceptual categories or approaches represented across ideas.
- 1: All ideas fall within a single category or perspective
- 3: Two or three different categories represented
- 5: Many diverse categories and perspectives explored

**Originality** (1-5)
The uniqueness, unexpectedness, and novelty of the ideas relative to typical responses.
- 1: Entirely conventional, predictable ideas
- 3: Some novel elements mixed with commonplace ideas
- 5: Strikingly original, rare, or surprising ideas throughout

**Elaboration** (1-5)
The depth, detail, and development of the ideas presented.
- 1: Ideas are bare, undeveloped, or superficial
- 3: Moderate detail; some ideas developed further than others
- 5: Ideas are richly detailed, well-developed, and thoroughly explained

## Output Format

Return ONLY valid JSON matching this schema exactly — no markdown fences, \
no commentary outside the JSON:

{{
  "fluency":     {{"score": <int 1-5>, "justification": "<string>"}},
  "flexibility": {{"score": <int 1-5>, "justification": "<string>"}},
  "originality": {{"score": <int 1-5>, "justification": "<string>"}},
  "elaboration": {{"score": <int 1-5>, "justification": "<string>"}}
}}
"""


def build_evaluation_prompt(original_prompt: str, response_text: str) -> str:
    """Build a full TTCT evaluation prompt for a judge LLM.

    The prompt instructs the judge to score the response on all four TTCT
    dimensions (Fluency, Flexibility, Originality, Elaboration) using a 1-5
    scale and return structured JSON.

    Args:
        original_prompt: The prompt that was given to the evaluated LLM.
        response_text:   The LLM response being evaluated.

    Returns:
        A complete prompt string ready to send to the judge model.
    """
    return _PROMPT_TEMPLATE.format(
        original_prompt=original_prompt,
        response_text=response_text,
    )
