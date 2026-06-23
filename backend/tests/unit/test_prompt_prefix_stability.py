from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.services.rag.service import RAG_INSTRUCTIONS, RAG_SYSTEM, RAGService


def _doc(text: str, ident: str) -> dict:
    return {
        "id": ident,
        "text": text,
        "collection": "acos_experiences",
        "semantic_score": 0.9,
        "metadata": {"confidence_level": "verified", "entity_id": ident},
    }


@pytest.fixture
def reranker() -> MagicMock:
    rr = MagicMock()
    rr.rerank.side_effect = lambda q, results, **kw: results
    return rr


@pytest.fixture
def ollama_up() -> MagicMock:
    o = MagicMock()
    o.is_available.return_value = True
    return o


def test_fixed_prefix_identical_across_different_context(reranker, ollama_up) -> None:
    """Two retrievals with different evidence share a byte-identical fixed prefix.

    Ollama reuses the system-prompt + fixed-instruction KV cache only when those
    bytes are stable; the dynamic evidence must come last.
    """
    retriever = MagicMock()
    retriever.retrieve.side_effect = [
        [_doc("Led Python migration at Acme.", "a1")],
        [_doc("Built a Rust pipeline at Globex saving 30%.", "b2")],
    ]
    svc = RAGService(retriever, reranker, ollama_up)

    p1, _ = svc.build_prompt("Tell me about my work", intent="knowledge_lookup")
    p2, _ = svc.build_prompt("Tell me about my work", intent="knowledge_lookup")

    assert p1 is not None and p2 is not None
    assert p1 != p2  # evidence differs
    assert p1.startswith(RAG_INSTRUCTIONS)
    assert p2.startswith(RAG_INSTRUCTIONS)
    # Everything up to (and including) the "Evidence:" marker is the fixed prefix.
    marker = "Evidence:\n"
    end = p1.index(marker) + len(marker)
    assert p1[:end] == p2[:end]


def test_system_prompt_is_constant() -> None:
    # The FIXED SYSTEM PREFIX is a module constant — trivially stable across calls.
    assert isinstance(RAG_SYSTEM, str) and RAG_SYSTEM


def test_embedder_unloaded_before_generate(reranker, ollama_up) -> None:
    """After retrieval (which embeds the query) the embedder is unloaded with
    keep_alive:0 *before* the generator runs — prevents 16GB starvation."""
    order: list[tuple[str, str]] = []
    ollama_up.unload.side_effect = lambda m: order.append(("unload", m))
    ollama_up.generate.side_effect = lambda **kw: order.append(("generate", kw["model"])) or "ans"

    retriever = MagicMock()
    retriever.retrieve.return_value = [_doc("Led Python migration at Acme.", "a1")]
    svc = RAGService(retriever, reranker, ollama_up, embed_model="nomic-embed-text")

    svc.query("Tell me about my work", intent="resume_help")

    assert order == [("unload", "nomic-embed-text"), ("generate", "qwen3:8b")]
