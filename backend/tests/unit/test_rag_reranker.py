from unittest.mock import MagicMock
import pytest
from backend.rag.reranker import Reranker


def _make_result(id_, text, semantic_score, confidence="verified"):
    return {
        "id": id_,
        "text": text,
        "metadata": {"confidence_level": confidence},
        "semantic_score": semantic_score,
        "collection": "acos_skills",
    }


def test_reranker_sorts_by_combined_score():
    reranker = Reranker()
    results = [
        _make_result("a", "Python programming language", 0.9, "verified"),
        _make_result("b", "SQL database queries", 0.5, "weak_inference"),
        _make_result("c", "FastAPI web framework", 0.7, "strong_inference"),
    ]
    ranked = reranker.rerank("Python", results)
    assert ranked[0]["id"] == "a"  # highest semantic * verified multiplier


def test_reranker_confidence_multiplier_applied():
    reranker = Reranker()
    # Same semantic score, different confidence — verified should rank higher
    results = [
        _make_result("weak", "Python", 0.8, "weak_inference"),
        _make_result("verified", "Python", 0.8, "verified"),
    ]
    ranked = reranker.rerank("Python", results)
    assert ranked[0]["id"] == "verified"


def test_reranker_final_k_limits_results():
    reranker = Reranker()
    results = [_make_result(str(i), f"doc {i}", 0.5) for i in range(20)]
    ranked = reranker.rerank("doc", results, final_k=5)
    assert len(ranked) == 5


def test_reranker_combined_score_in_results():
    reranker = Reranker()
    results = [_make_result("x", "Python", 0.6, "strong_inference")]
    ranked = reranker.rerank("Python", results)
    assert "combined_score" in ranked[0]
