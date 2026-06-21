from __future__ import annotations

import pytest

from backend.services.intelligence.multi_vector_retriever import MultiVectorRetriever


class _FakeRetriever:
    """Records queries it receives; returns canned results per call."""

    def __init__(self, results_by_call: list[list[dict]] | None = None) -> None:
        self.queries: list[str] = []
        self._results_by_call = results_by_call or []
        self._call = 0

    def retrieve(self, query: str, collections: list[str], top_k: int = 10) -> list[dict]:
        self.queries.append(query)
        if self._call < len(self._results_by_call):
            out = self._results_by_call[self._call]
        else:
            out = []
        self._call += 1
        return out


def _r(doc_id: str, text: str, score: float, exp_id: str = "") -> dict:
    return {
        "id": doc_id,
        "text": text,
        "metadata": {"experience_id": exp_id, "company": "", "title": "", "confidence_level": "verified"},
        "semantic_score": score,
        "collection": "acos_experiences",
    }


UQ = {
    "role_type": "product_management",
    "seniority": "senior",
    "required_skills": ["SQL", "roadmapping"],
    "preferred_skills": ["Python"],
    "must_have_keywords": ["cross-functional", "stakeholder"],
}


def test_issues_one_query_per_nonempty_vector() -> None:
    fake = _FakeRetriever()
    mvr = MultiVectorRetriever(fake)

    mvr.retrieve(UQ)

    # skills, keywords, role vectors → 3 queries
    assert len(fake.queries) == 3


def test_empty_query_returns_empty() -> None:
    fake = _FakeRetriever()
    mvr = MultiVectorRetriever(fake)

    empty_uq = {"role_type": "", "required_skills": [], "preferred_skills": [], "must_have_keywords": []}
    assert mvr.retrieve(empty_uq) == []


def test_merges_and_dedups_by_id() -> None:
    fake = _FakeRetriever([
        [_r("a", "alpha", 0.9), _r("b", "beta", 0.8)],
        [_r("b", "beta", 0.85)],   # duplicate id b
        [_r("c", "gamma", 0.7)],
    ])
    mvr = MultiVectorRetriever(fake)

    results = mvr.retrieve(UQ)

    ids = {r["evidence_id"] for r in results}
    assert ids == {"a", "b", "c"}


def test_mmr_demotes_near_duplicate_in_favor_of_diverse() -> None:
    # A and B are near-identical; C is diverse with lower relevance.
    fake = _FakeRetriever([
        [
            _r("A", "led python data pipeline reducing latency", 0.90, "e1"),
            _r("B", "led python data pipeline reducing latency time", 0.88, "e1"),
            _r("C", "managed stakeholder roadmap and kpis", 0.60, "e2"),
        ],
        [], [],
    ])
    mvr = MultiVectorRetriever(fake, mmr_lambda=0.5)

    results = mvr.retrieve(UQ)
    order = [r["evidence_id"] for r in results]

    assert order[0] == "A"               # highest relevance first
    assert order.index("C") < order.index("B")  # diverse C beats near-dup B


def test_respects_max_results() -> None:
    fake = _FakeRetriever([
        [_r(str(i), f"text {i}", 0.9 - i * 0.05, f"e{i}") for i in range(10)],
        [], [],
    ])
    mvr = MultiVectorRetriever(fake)

    results = mvr.retrieve(UQ, max_results=3)

    assert len(results) == 3


def test_returns_bullet_shape() -> None:
    fake = _FakeRetriever([[_r("a", "alpha", 0.9, "e1")], [], []])
    mvr = MultiVectorRetriever(fake)

    results = mvr.retrieve(UQ)

    b = results[0]
    assert b["bullet_text"] == "alpha"
    assert b["evidence_id"] == "a"
    assert b["experience_id"] == "e1"
    assert "confidence" in b
