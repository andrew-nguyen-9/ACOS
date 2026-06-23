"""Phase 12.6 AC5 — reranked context truncated to a hard token budget.

The old code capped context at a fixed COUNT (parts[:15]); the TTFT lever is a
cumulative TOKEN budget. Highest-ranked parts are kept; the tail is dropped once
the budget would be exceeded.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from backend.services.rag.service import (
    CONTEXT_TOKEN_BUDGET,
    RAGService,
    _prune_context_parts,
)
from backend.services.tokens import count_tokens


def test_prune_keeps_within_budget_and_drops_tail():
    # Each part ~600 tokens (2400 chars / 4). Budget 1500 → 2 parts fit, rest dropped.
    parts = [f"[verified] {'x' * 2400}" for _ in range(5)]
    kept = _prune_context_parts(parts, budget=1500)

    assert count_tokens("\n\n".join(kept)) <= 1500
    assert kept == parts[:2]  # highest-ranked retained, in order
    assert len(kept) < len(parts)  # tail genuinely dropped


def test_prune_always_keeps_top_ranked_even_if_oversized():
    # A single top part bigger than the whole budget must not yield empty context.
    huge = "[verified] " + "y" * (1500 * 4 + 4000)
    kept = _prune_context_parts([huge, "[strong] tail"], budget=1500)
    assert kept == [huge]


def test_prune_keeps_all_when_under_budget():
    parts = ["[verified] short a", "[strong] short b", "[weak] short c"]
    assert _prune_context_parts(parts, budget=1500) == parts


def test_build_prompt_context_respects_token_budget():
    """End-to-end: an oversized rerank set produces a prompt whose evidence block
    is within CONTEXT_TOKEN_BUDGET, dropping low-ranked tail items."""
    # 30 parts of ~400 tokens each (1600 chars) → far over 1500; must be truncated.
    ranked = [
        {
            "id": f"d{i}",
            "text": "z" * 1600,
            "collection": "acos_experiences",
            "semantic_score": 0.9 - i * 0.01,
            "metadata": {"confidence_level": "verified", "entity_id": f"e{i}"},
        }
        for i in range(30)
    ]
    retriever = MagicMock()
    retriever.retrieve.return_value = ranked
    reranker = MagicMock()
    reranker.rerank.side_effect = lambda q, results, **kw: results
    ollama = MagicMock()
    ollama.is_available.return_value = True

    svc = RAGService(retriever, reranker, ollama)
    prompt, _ = svc.build_prompt("tell me everything", intent="knowledge_lookup")

    assert prompt is not None
    context = prompt.split("Evidence:\n", 1)[1]
    assert count_tokens(context) <= CONTEXT_TOKEN_BUDGET
    # The first (highest-ranked) evidence text is present; some tail is gone.
    assert "z" * 1600 in context
    assert count_tokens(context) < count_tokens("\n\n".join("z" * 1600 for _ in range(30)))
