from __future__ import annotations

from backend.services.tokens import count_tokens


def test_empty_is_zero() -> None:
    assert count_tokens("") == 0


def test_scales_with_length() -> None:
    # ~4 chars/token budgeting heuristic (or tiktoken if installed): longer text,
    # more tokens, monotonic.
    short = count_tokens("hello world")
    long = count_tokens("hello world " * 100)
    assert long > short
    assert short >= 1


def test_budget_is_in_reasonable_range() -> None:
    # 400 chars -> ~100 tokens under the cl100k/heuristic budget (never wildly off).
    n = count_tokens("x" * 400)
    assert 50 <= n <= 200
