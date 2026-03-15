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
"""Tests for TTCTEvaluator (Torrance Tests of Creative Thinking)."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestTTCTScoring:

    def test_compute_composite_score(self):
        from evaluators.ttct import compute_composite_score
        scores = {"fluency": 4, "flexibility": 3, "originality": 5, "elaboration": 3}
        composite = compute_composite_score(scores)
        expected = (4 * 0.25 + 3 * 0.25 + 5 * 0.25 + 3 * 0.25)
        assert abs(composite - expected) < 1e-6

    def test_composite_max_score(self):
        from evaluators.ttct import compute_composite_score
        scores = {"fluency": 5, "flexibility": 5, "originality": 5, "elaboration": 5}
        assert compute_composite_score(scores) == 5.0

    def test_composite_min_score(self):
        from evaluators.ttct import compute_composite_score
        scores = {"fluency": 1, "flexibility": 1, "originality": 1, "elaboration": 1}
        assert compute_composite_score(scores) == 1.0

    def test_parse_judge_response_valid(self):
        from evaluators.ttct import parse_judge_response
        raw = {
            "fluency": {"score": 4, "justification": "Good fluency"},
            "flexibility": {"score": 3, "justification": "Moderate flexibility"},
            "originality": {"score": 5, "justification": "Very original"},
            "elaboration": {"score": 3, "justification": "Some detail"},
        }
        result = parse_judge_response(raw)
        assert result["fluency"] == 4
        assert result["flexibility"] == 3
        assert result["originality"] == 5
        assert result["elaboration"] == 3
        assert "composite" in result

    def test_parse_judge_response_missing_field_raises(self):
        from evaluators.ttct import parse_judge_response
        raw = {"fluency": {"score": 4, "justification": "OK"}}
        with pytest.raises(KeyError):
            parse_judge_response(raw)

    def test_build_evaluation_prompt_contains_rubrics(self):
        from evaluators.ttct import build_evaluation_prompt
        prompt = build_evaluation_prompt("Original prompt", "Response text")
        assert "Fluency" in prompt or "FLUENCY" in prompt
        assert "Flexibility" in prompt or "FLEXIBILITY" in prompt
        assert "Originality" in prompt or "ORIGINALITY" in prompt
        assert "Elaboration" in prompt or "ELABORATION" in prompt
        assert "1-5" in prompt or "1 to 5" in prompt
