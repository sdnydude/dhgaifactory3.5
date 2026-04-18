from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceeded(Exception):
    def __init__(self, truncated_at_node: str, tokens_used: int, max_tokens: int):
        self.truncated_at_node = truncated_at_node
        self.tokens_used = tokens_used
        self.max_tokens = max_tokens
        super().__init__(
            f"Token budget exceeded at node '{truncated_at_node}': "
            f"{tokens_used}/{max_tokens}"
        )


@dataclass
class TokenBudget:
    max_tokens: int
    tokens_used: int = 0
    _breakdown: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens - self.tokens_used)

    def record(self, *, node: str, tokens_in: int, tokens_out: int) -> None:
        total = tokens_in + tokens_out
        self.tokens_used += total
        self._breakdown[node] = {"tokens_in": tokens_in, "tokens_out": tokens_out}

    def check(self, *, node: str, estimated_tokens: int) -> None:
        if self.tokens_used + estimated_tokens > self.max_tokens:
            raise BudgetExceeded(
                truncated_at_node=node,
                tokens_used=self.tokens_used,
                max_tokens=self.max_tokens,
            )

    def to_dict(self) -> dict:
        return {
            "tokens_used": self.tokens_used,
            "max_tokens": self.max_tokens,
            "budget_exceeded": self.tokens_used >= self.max_tokens,
            "breakdown": dict(self._breakdown),
        }
