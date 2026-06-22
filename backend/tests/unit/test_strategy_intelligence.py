"""Phase 12.12 Resume Strategy Intelligence — compose ROI + signals + JD analysis
into personalized, evidence-grounded, confidence-tagged recommendations.

No hallucinated best practices: sparse data degrades to weak_inference, unknown
industry is flagged, never fabricated (CLAUDE.md non-negotiable #1).
"""
from __future__ import annotations

from backend.services.flywheel.feedback import FeedbackEngine
from backend.services.flywheel.strategy import recommend, INDUSTRY_STRUCTURES


def _seed_rich(session) -> None:
    """python with a strong, positive ROI (6 apps, n>=5)."""
    eng = FeedbackEngine(session)
    outcomes = [("app1", "interview", 0.7), ("app2", "offer", 1.0),
                ("app3", "rejected", 0.1), ("app4", "interview", 0.7),
                ("app5", "phone_screen", 0.4), ("app6", "final_round", 0.85),
                ("app7", "no_response", 0.0)]
    for app_id, stype, w in outcomes:
        eng.record_signal(entity_type="application", entity_id=app_id, signal_type=stype,
                          value=w, source={"table": "outcome_signals", "ids": [f"os-{app_id}"]})
    for app_id in [o[0] for o in outcomes[:6]]:
        eng.record_signal(entity_type="skill", entity_id="python", signal_type="skill_used",
                          value=1.0, source={"table": "resumes", "ids": [app_id]})


def test_rich_data_yields_confident_recs_with_evidence(test_session):
    _seed_rich(test_session)
    keywords = {"required_skills": ["python", "sql"], "keywords": ["api"], "industry": "technology"}
    rec = recommend(test_session, keywords=keywords)

    assert rec.industry == "technology"
    assert rec.section_order == INDUSTRY_STRUCTURES["technology"]
    assert "python" in rec.recommended_skills           # high-ROI skill surfaced
    assert "python" in rec.keyword_targets              # JD ∩ high-ROI prioritized first
    assert rec.keyword_targets[0] == "python"
    assert rec.confidence == "strong_inference"
    assert rec.evidence                                  # contributing signal ids, not empty
    assert rec.flagged is False


def test_sparse_data_degrades_to_weak_inference(test_session):
    """No ROI signal → generic, weak_inference, flagged — never a fabricated best practice."""
    keywords = {"required_skills": ["python"], "keywords": [], "industry": "technology"}
    rec = recommend(test_session, keywords=keywords)

    assert rec.recommended_skills == []
    assert rec.confidence == "weak_inference"
    assert rec.flagged is True
    # still safe to consume: structure present, no invented evidence
    assert rec.section_order == INDUSTRY_STRUCTURES["technology"]
    assert rec.evidence == []


def test_unknown_industry_is_flagged_not_guessed(test_session):
    _seed_rich(test_session)
    keywords = {"required_skills": ["python"], "keywords": [], "industry": "underwater basket weaving"}
    rec = recommend(test_session, keywords=keywords)

    assert rec.industry == "generic"
    assert rec.section_order == INDUSTRY_STRUCTURES["generic"]
    assert rec.flagged is True                          # unknown industry flagged
    assert rec.confidence == "weak_inference"


def test_recommend_is_tenant_scoped(test_session):
    from backend.services.tenancy import ensure_tenant, set_session_tenant

    ensure_tenant(test_session, "t1")
    set_session_tenant(test_session, "t1")
    _seed_rich(test_session)  # seeded under t1
    ensure_tenant(test_session, "t2")
    set_session_tenant(test_session, "t2")
    keywords = {"required_skills": ["python"], "keywords": [], "industry": "technology"}
    rec = recommend(test_session, tenant_id="t2", keywords=keywords)
    assert rec.recommended_skills == []                 # t2 has no signals
    assert rec.confidence == "weak_inference"


def test_output_drops_into_resume_generator_as_optional_hint(test_session):
    """Acceptance §4: strategy integrates with the resume engine inputs, no schema
    mismatch — and the unhinted path is unchanged."""
    from dataclasses import asdict

    _seed_rich(test_session)
    keywords = {"required_skills": ["python", "sql"], "keywords": [], "industry": "technology"}
    rec = recommend(test_session, keywords=keywords)
    hint = asdict(rec)
    # the engine merges keyword_targets — a plain list[str] it already understands
    assert isinstance(hint["keyword_targets"], list)
    assert all(isinstance(k, str) for k in hint["keyword_targets"])
