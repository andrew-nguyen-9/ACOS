"""Phase 12.11 Skill ROI Engine — golden, confidence, explainability, determinism.

ROI is effect-size (mean outcome when a skill is used minus the global mean) over
12.10 signals — NOT a model (plan §3). Every figure carries n + a confidence level
(ADR-006); low-n skills are weak_inference and excluded from `recommended`.
"""
from __future__ import annotations

import pytest

from backend.services.flywheel.feedback import FeedbackEngine
from backend.services.flywheel.skill_roi import rank_skills


# (application_id, outcome signal_type, ladder weight)
_OUTCOMES = [
    ("app1", "interview", 0.7),
    ("app2", "offer", 1.0),
    ("app3", "rejected", 0.1),
    ("app4", "interview", 0.7),
    ("app5", "phone_screen", 0.4),
    ("app6", "final_round", 0.85),
    ("app7", "no_response", 0.0),
]
# skill -> applications that used it
_SKILL_USE = {
    "python": ["app1", "app2", "app3", "app4", "app5", "app6"],  # n=6 -> strong
    "rust": ["app1", "app7"],                                     # n=2 -> weak
    "sql": ["app3"],                                              # n=1 -> weak
}


def _seed(session, tenant_id: str | None = None) -> None:
    eng = FeedbackEngine(session)
    for app_id, stype, weight in _OUTCOMES:
        eng.record_signal(
            entity_type="application", entity_id=app_id, signal_type=stype,
            value=weight, source={"table": "outcome_signals", "ids": [f"os-{app_id}"]},
            tenant_id=tenant_id,
        )
    for skill, apps in _SKILL_USE.items():
        for app_id in apps:
            eng.record_signal(
                entity_type="skill", entity_id=skill, signal_type="skill_used",
                value=1.0, source={"table": "resumes", "ids": [app_id]},
                tenant_id=tenant_id,
            )


def test_golden_ranking_with_confidence(test_session):
    """Fixed signal set -> exact ROI ranking + sample-size-driven confidence."""
    _seed(test_session)
    out = rank_skills(test_session, metric="interview_lift", min_n=5)

    # global mean = (0.7+1.0+0.1+0.7+0.4+0.85+0.0)/7 = 0.535714
    # python apps mean = (0.7+1.0+0.1+0.7+0.4+0.85)/6 = 0.625 -> roi 0.0893
    # rust = (0.7+0.0)/2 = 0.35 -> roi -0.1857 ; sql = 0.1 -> roi -0.4357
    by_skill = {s["skill"]: s for s in out["skills"]}

    assert by_skill["python"]["roi"] == 0.0893
    assert by_skill["python"]["n"] == 6
    assert by_skill["python"]["confidence"] == "strong_inference"

    assert by_skill["rust"]["roi"] == -0.1857
    assert by_skill["rust"]["n"] == 2
    assert by_skill["rust"]["confidence"] == "weak_inference"

    assert by_skill["sql"]["confidence"] == "weak_inference"

    # ranked by roi descending
    assert [s["skill"] for s in out["skills"]] == ["python", "rust", "sql"]


def test_low_sample_skills_excluded_from_recommended(test_session):
    """Acceptance: weak_inference (low-n) skills never reach `recommended`."""
    _seed(test_session)
    out = rank_skills(test_session, metric="interview_lift", min_n=5)
    assert out["recommended"] == ["python"]  # only strong + positive ROI
    assert "rust" not in out["recommended"]
    assert "sql" not in out["recommended"]


def test_roi_is_explainable(test_session):
    """Acceptance: every ROI lists its contributing signal ids — no orphan ROI."""
    _seed(test_session)
    out = rank_skills(test_session, metric="interview_lift", min_n=5)
    python = next(s for s in out["skills"] if s["skill"] == "python")
    ids = python["contributing_signal_ids"]
    # 6 skill_used + 6 outcome signals contributed
    assert len(ids) == 12
    # all are real signal ids resolvable via explain()
    eng = FeedbackEngine(test_session)
    assert all(eng.explain(sid) is not None for sid in ids)


def test_deterministic_on_fixed_signal_set(test_session):
    """Trap 3: identical seeded state -> byte-identical ranking, stable ties."""
    _seed(test_session)
    a = rank_skills(test_session, metric="interview_lift", min_n=5)
    b = rank_skills(test_session, metric="interview_lift", min_n=5)
    assert a == b


def test_offer_probability_metric(test_session):
    """offer_probability scores 1.0 only for offer/accepted outcomes."""
    _seed(test_session)
    out = rank_skills(test_session, metric="offer_probability", min_n=5)
    by_skill = {s["skill"]: s for s in out["skills"]}
    # global offer rate = 1/7 = 0.142857 ; python = 1/6 = 0.166667 -> roi 0.0238
    assert by_skill["python"]["roi"] == 0.0238


def test_tenant_scoped_reads(test_session):
    """tenant_id filters the signal set (12.14 forward-compat)."""
    _seed(test_session, tenant_id="t1")
    _seed(test_session, tenant_id="t2")
    out = rank_skills(test_session, tenant_id="t1", metric="interview_lift", min_n=5)
    # python n must be 6 (t1 only), not 12 (both tenants)
    python = next(s for s in out["skills"] if s["skill"] == "python")
    assert python["n"] == 6


def test_ats_delta_metric(test_session):
    """ats_delta correlates skills with per-application ATS scores (0-100 scale)."""
    eng = FeedbackEngine(test_session)
    eng.record_signal(entity_type="application", entity_id="a1", signal_type="ats_score",
                      value=80.0, source={"table": "resumes", "ids": ["r1"]})
    eng.record_signal(entity_type="application", entity_id="a2", signal_type="ats_score",
                      value=60.0, source={"table": "resumes", "ids": ["r2"]})
    for app in ("a1", "a2"):
        eng.record_signal(entity_type="skill", entity_id="python", signal_type="skill_used",
                          value=1.0, source={"table": "resumes", "ids": [app]})
    eng.record_signal(entity_type="skill", entity_id="rust", signal_type="skill_used",
                      value=1.0, source={"table": "resumes", "ids": ["a2"]})
    out = rank_skills(test_session, metric="ats_delta", min_n=2)
    by = {s["skill"]: s for s in out["skills"]}
    # global mean = (80+60)/2 = 70 ; python = 70 -> roi 0.0 ; rust = 60 -> roi -10.0
    assert by["python"]["roi"] == 0.0
    assert by["rust"]["roi"] == -10.0


def test_unknown_metric_rejected(test_session):
    _seed(test_session)
    with pytest.raises(ValueError, match="metric"):
        rank_skills(test_session, metric="bogus")


def test_empty_signals_returns_empty(test_session):
    out = rank_skills(test_session, metric="interview_lift")
    assert out["skills"] == []
    assert out["recommended"] == []


def test_emit_skill_signals_links_skills_and_ats_to_application(test_session):
    """Thin write-path emit: real skills + ATS, source-linked to the application."""
    from backend.api.v1.routes.resume import _emit_skill_signals
    from backend.models.signal import Signal

    result = {
        "resume_id": "r1",
        "content_json": {"skills": ["Python", "SQL", ""]},  # blank skipped
        "ats_score": {"overall_score": 77.0},
    }
    _emit_skill_signals(test_session, result, "appX")

    sigs = test_session.query(Signal).all()
    skill_sigs = [s for s in sigs if s.entity_type == "skill"]
    assert {s.entity_id for s in skill_sigs} == {"Python", "SQL"}
    assert all(s.source_json["ids"][0] == "appX" for s in skill_sigs)  # join key first
    ats = [s for s in sigs if s.entity_type == "application" and s.signal_type == "ats_score"]
    assert ats[0].value == 77.0
    assert ats[0].entity_id == "appX"


def test_emit_skill_signals_noop_without_application(test_session):
    """No application id = no join key = nothing emitted (don't fabricate)."""
    from backend.api.v1.routes.resume import _emit_skill_signals
    from backend.models.signal import Signal

    _emit_skill_signals(test_session, {"content_json": {"skills": ["Python"]}}, None)
    assert test_session.query(Signal).count() == 0
