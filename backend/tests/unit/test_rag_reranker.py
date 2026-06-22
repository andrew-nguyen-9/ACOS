from unittest.mock import MagicMock
import pytest
from backend.rag.reranker import Reranker


def _make_result(id_, text, semantic_score, confidence="verified", lexical_score=0.0):
    return {
        "id": id_,
        "text": text,
        "metadata": {"confidence_level": confidence},
        "semantic_score": semantic_score,
        "lexical_score": lexical_score,
        "collection": "acos_skills",
    }


def test_reranker_fuses_lexical_score():
    """The lexical leg is now FTS5: rerank fuses a carried lexical_score instead
    of computing in-set rank_bm25 over the candidate texts."""
    reranker = Reranker()
    results = [
        _make_result("dense_only", "alpha", 0.6, "verified", lexical_score=0.0),
        _make_result("lexical_hit", "alpha", 0.6, "verified", lexical_score=1.0),
    ]
    ranked = reranker.rerank("alpha", results)
    assert ranked[0]["id"] == "lexical_hit"


def test_reranker_handles_missing_lexical_score():
    """Candidates without a lexical_score (dense-only paths) must not crash."""
    reranker = Reranker()
    results = [{
        "id": "x", "text": "Python", "metadata": {"confidence_level": "verified"},
        "semantic_score": 0.7, "collection": "acos_skills",
    }]
    ranked = reranker.rerank("Python", results)
    assert ranked[0]["id"] == "x"


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
