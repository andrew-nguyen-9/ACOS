"""Phase 13.10 (8c) — global-aggregation demo: a synthetic >=5-profile fixture that
exercises the k-anonymity path end-to-end (ADR-009 / 12.15 / 13.3).

Test-only and in-memory: it seeds synthetic tenants on the test session and never
writes real profiles or touches the dev DB. Demonstrates that a skill shared by >=5
tenants is EMITTED (k-anonymous) while the same skill shared by <5 is SUPPRESSED.
"""
from __future__ import annotations

from backend.services.flywheel.anonymization import K_ANONYMITY, assert_no_reidentification
from backend.services.flywheel.feedback import FeedbackEngine
from backend.services.flywheel.global_patterns import aggregate_skill_roi
from backend.services.tenancy import ensure_tenant

# A high-ROI outcome ladder + a skill ("python") used across the successful apps, so
# every seeded tenant independently ranks "python" with a positive interview_lift.
_OUTCOMES = [
    ("app1", "interview", 0.7), ("app2", "offer", 1.0), ("app3", "rejected", 0.1),
    ("app4", "interview", 0.7), ("app5", "final_round", 0.85), ("app6", "no_response", 0.0),
]
_PY_APPS = ["app1", "app2", "app3", "app4", "app5"]  # n=5 -> strong per tenant


def _seed_tenant(session, tenant_id: str) -> None:
    ensure_tenant(session, tenant_id)
    eng = FeedbackEngine(session)
    for app_id, stype, weight in _OUTCOMES:
        eng.record_signal(
            entity_type="application", entity_id=app_id, signal_type=stype, value=weight,
            source={"table": "outcome_signals", "ids": [f"{tenant_id}-os-{app_id}"]},
            tenant_id=tenant_id,
        )
    for app_id in _PY_APPS:
        # source ids MUST be the application ids — that's the skill→outcome join key.
        eng.record_signal(
            entity_type="skill", entity_id="python", signal_type="skill_used", value=1.0,
            source={"table": "resumes", "ids": [app_id]}, tenant_id=tenant_id,
        )


def _industries(n: int) -> dict[str, str]:
    tenants = {f"t{i}": "software" for i in range(n)}
    return tenants


def test_five_profiles_emit_k_anonymous_pattern(test_session):
    industries = _industries(K_ANONYMITY)  # exactly 5
    for t in industries:
        _seed_tenant(test_session, t)
    test_session.flush()

    patterns = aggregate_skill_roi(test_session, industries, metric="interview_lift")

    python = next((p for p in patterns if p["key"] == "python" and p["industry"] == "software"), None)
    assert python is not None, "a skill shared by 5 tenants must clear the k-anonymity gate"
    assert python["tenant_count"] == K_ANONYMITY
    assert python["confidence"] == "strong_inference"
    # the gate must not leak anything re-identifying (ids, raw rows, embeddings)
    assert_no_reidentification(patterns)
    assert set(python.keys()) <= {
        "pattern_type", "industry", "key", "value", "metric", "tenant_count", "confidence",
    }


def test_four_profiles_are_suppressed(test_session):
    industries = _industries(K_ANONYMITY - 1)  # 4 -> below threshold
    for t in industries:
        _seed_tenant(test_session, t)
    test_session.flush()

    patterns = aggregate_skill_roi(test_session, industries, metric="interview_lift")
    assert all(p["key"] != "python" for p in patterns), (
        "a skill shared by only 4 tenants must be suppressed (k<5, ADR-009)"
    )
