"""15.3 — KG-grounded answer evaluation.

An interview answer score is backed by which knowledge-graph nodes the answer did
and did not cover (ADR-006) — never a bare "7/10". Low coverage yields an honest
low score; with no graph, the eval is honestly weak, not a fabricated number.
"""
from __future__ import annotations

from backend.services.knowledge_graph.service import KnowledgeGraphService


def test_evaluate_answer_grounds_in_graph(test_session) -> None:
    svc = KnowledgeGraphService(test_session)
    py = svc.get_or_create_node("skill", "s-python", "Python", {})
    sql = svc.get_or_create_node("skill", "s-sql", "SQL", {})
    etl = svc.get_or_create_node("experience", "e-etl", "Built ETL pipelines", {})
    test_session.flush()

    res = svc.evaluate_answer("I used Python to build ETL pipelines for analytics.")

    assert res["expected_count"] == 3
    assert py.id in res["covered_node_ids"]
    assert etl.id in res["covered_node_ids"]
    assert sql.id in res["missing_node_ids"]  # SQL never mentioned
    assert 0 < res["coverage"] < 1
    assert any("Python" in lbl for lbl in res["matched_labels"])
    assert res["confidence"] == "strong_inference"  # >=3 grounding nodes


def test_evaluate_answer_with_no_graph_is_honest(test_session) -> None:
    svc = KnowledgeGraphService(test_session)
    res = svc.evaluate_answer("A generic answer with no grounding.")
    assert res["coverage"] == 0.0
    assert res["expected_count"] == 0
    # No graph to ground against → honestly weak, never a fabricated score.
    assert res["confidence"] == "weak_inference"


def test_evaluate_answer_scoped_to_expected_nodes(test_session) -> None:
    svc = KnowledgeGraphService(test_session)
    py = svc.get_or_create_node("skill", "s-python", "Python", {})
    svc.get_or_create_node("skill", "s-go", "Golang", {})
    test_session.flush()

    # Only Python is "expected" for this question — Golang is out of scope.
    res = svc.evaluate_answer("Python is my primary language.", expected_node_ids=[py.id])
    assert res["expected_count"] == 1
    assert res["coverage"] == 1.0
