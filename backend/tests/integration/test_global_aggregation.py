"""Phase 12.15 — cross-tenant aggregation: abstractions only, k-respected, no re-id."""
from __future__ import annotations

from backend.services.flywheel.anonymization import assert_no_reidentification
from backend.services.flywheel.feedback import FeedbackEngine
from backend.services.flywheel.global_patterns import aggregate_skill_roi, refresh_global_patterns
from backend.models.global_pattern import GlobalPattern
from backend.services.tenancy import ensure_tenant, set_session_tenant


def _seed_python_winner(session, tenant_id: str) -> None:
    """python is a strong positive-ROI skill for this tenant (n>=5)."""
    ensure_tenant(session, tenant_id)
    set_session_tenant(session, tenant_id)
    eng = FeedbackEngine(session)
    outcomes = [("a1", "interview", 0.7), ("a2", "offer", 1.0), ("a3", "rejected", 0.1),
                ("a4", "interview", 0.7), ("a5", "phone_screen", 0.4),
                ("a6", "final_round", 0.85), ("a7", "no_response", 0.0)]
    for app, stype, w in outcomes:
        eng.record_signal(entity_type="application", entity_id=app, signal_type=stype,
                          value=w, source={"table": "outcome_signals", "ids": [f"os-{app}"]})
    for app in [o[0] for o in outcomes[:6]]:
        eng.record_signal(entity_type="skill", entity_id="python", signal_type="skill_used",
                          value=1.0, source={"table": "resumes", "ids": [app]})


def test_aggregate_respects_k_anonymity(test_session):
    # 6 tenants all show python winning in technology -> k satisfied
    industries = {f"t{i}": "technology" for i in range(6)}
    for t in industries:
        _seed_python_winner(test_session, t)

    patterns = aggregate_skill_roi(test_session, industries, metric="interview_lift")
    python = [p for p in patterns if p["key"] == "python"]
    assert python and python[0]["tenant_count"] == 6
    assert python[0]["industry"] == "technology"
    assert_no_reidentification(patterns)            # aggregate-only, no leak


def test_below_k_cohort_is_suppressed(test_session):
    # only 3 tenants -> below k=5 -> nothing emitted
    industries = {f"t{i}": "technology" for i in range(3)}
    for t in industries:
        _seed_python_winner(test_session, t)
    patterns = aggregate_skill_roi(test_session, industries, metric="interview_lift")
    assert patterns == []


def test_refresh_persists_content_free_rows(test_session):
    industries = {f"t{i}": "technology" for i in range(5)}
    for t in industries:
        _seed_python_winner(test_session, t)
    n = refresh_global_patterns(test_session, industries, metric="interview_lift")
    assert n >= 1
    rows = test_session.query(GlobalPattern).all()
    assert all(r.key == "python" for r in rows if r.pattern_type == "skill_roi")
    # content-free: the row exposes only abstract columns (no tenant_id attribute)
    assert not hasattr(rows[0], "tenant_id")
