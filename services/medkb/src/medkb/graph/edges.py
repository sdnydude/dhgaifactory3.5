from __future__ import annotations

from typing import Literal


def should_grade(state: dict) -> Literal["grade_docs", "generate"]:
    strategy = state["config"]["strategy"]
    if strategy == "regular":
        return "generate"
    return "grade_docs"


def should_rewrite(state: dict) -> Literal["rewrite_query", "generate"]:
    grade = state.get("doc_grade", "good")
    retries = state.get("rewrite_count", 0)
    max_retries = state["config"].get("max_retries", 2)
    if grade == "good":
        return "generate"
    if retries < max_retries:
        return "rewrite_query"
    return "generate"


def should_check_grounded(state: dict) -> Literal["check_grounded", "format_cite"]:
    if state["config"]["strategy"] in ("regular", "crag"):
        return "format_cite"
    return "check_grounded"


def should_regenerate(state: dict) -> Literal["regenerate", "format_cite"]:
    if state.get("regenerated", False):
        return "format_cite"
    threshold = state["config"].get("groundedness_threshold", 0.8)
    if state.get("groundedness_score", 1.0) < threshold:
        return "regenerate"
    return "format_cite"
