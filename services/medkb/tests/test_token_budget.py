import pytest
from medkb.token_budget import TokenBudget, BudgetExceeded


def test_budget_tracks_usage():
    budget = TokenBudget(max_tokens=1000)
    budget.record(node="retrieve", tokens_in=200, tokens_out=0)
    assert budget.tokens_used == 200
    assert budget.remaining == 800


def test_budget_raises_when_exceeded():
    budget = TokenBudget(max_tokens=100)
    budget.record(node="retrieve", tokens_in=80, tokens_out=0)
    with pytest.raises(BudgetExceeded) as exc_info:
        budget.check(node="generate", estimated_tokens=50)
    assert exc_info.value.truncated_at_node == "generate"
    assert exc_info.value.tokens_used == 80


def test_budget_allows_within_limit():
    budget = TokenBudget(max_tokens=1000)
    budget.record(node="retrieve", tokens_in=200, tokens_out=0)
    budget.check(node="generate", estimated_tokens=500)


def test_budget_to_dict():
    budget = TokenBudget(max_tokens=1000)
    budget.record(node="retrieve", tokens_in=200, tokens_out=50)
    d = budget.to_dict()
    assert d["tokens_used"] == 250
    assert d["budget_exceeded"] is False
    assert d["max_tokens"] == 1000
