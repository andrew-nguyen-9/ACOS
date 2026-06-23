"""15.1 — prioritize rows carry confidence + evidence + a deterministic top_pick.

The job-prioritization surface (ADR-012) ranks and explains; every row must carry
its ADR-006 confidence and the evidence it derived from, and the "top pick"
emphasis must be withheld from low-n (weak_inference) rows so the user is never
nudged hard on thin evidence.
"""
from __future__ import annotations

from backend.services.strategy.application_strategy import (
    ApplicationStrategyEngine,
    _mark_top_pick,
)


def test_rows_carry_confidence_and_evidence(test_session) -> None:
    engine = ApplicationStrategyEngine(test_session)
    jd = (
        "Senior Data Analyst. Strong Python and SQL required. Build ETL, "
        "maintain Tableau dashboards, define KPIs for executive stakeholders."
    )
    rows = engine.prioritize([{"job_id": "j1", "jd_text": jd}])

    assert len(rows) == 1
    row = rows[0]
    for key in (
        "confidence",
        "missing_critical_skills",
        "risk_factors",
        "explanation",
        "top_pick",
    ):
        assert key in row, f"missing enriched field: {key}"
    # Empty profile → no outcome signals → low-n estimate, never asserted as verified.
    assert row["confidence"] == "weak_inference"


def test_results_are_server_ranked_descending(test_session) -> None:
    engine = ApplicationStrategyEngine(test_session)
    jobs = [
        {"job_id": "low", "jd_text": "We need someone. Generic role with vague duties here."},
        {"job_id": "high", "jd_text": "Python SQL Python SQL data analyst KPI Tableau ETL pipeline."},
    ]
    rows = engine.prioritize(jobs)
    scores = [r["fit_score"] for r in rows]
    assert scores == sorted(scores, reverse=True)


def test_top_pick_withheld_from_weak_inference() -> None:
    rows = [
        {"fit_score": 80.0, "confidence": "weak_inference", "priority": "prioritize"},
        {"fit_score": 60.0, "confidence": "weak_inference", "priority": "tailor"},
    ]
    _mark_top_pick(rows)
    assert all(r["top_pick"] is False for r in rows)


def test_top_pick_marks_best_eligible_row() -> None:
    rows = [
        {"fit_score": 90.0, "confidence": "weak_inference", "priority": "prioritize"},
        {"fit_score": 78.0, "confidence": "strong_inference", "priority": "tailor"},
        {"fit_score": 50.0, "confidence": "verified", "priority": "bridge"},
    ]
    _mark_top_pick(rows)
    # The 90 row is weak → skipped; the 78 strong/tailor row is the top pick;
    # the 50 verified row is non-weak but a "bridge", not apply-worthy → not picked.
    assert rows[0]["top_pick"] is False
    assert rows[1]["top_pick"] is True
    assert rows[2]["top_pick"] is False
