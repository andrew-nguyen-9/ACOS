"""Phase 14.2 — off-hot-path drift snapshot + versioned/confidence-tagged report."""
from __future__ import annotations

from backend.models.application import Application
from backend.models.outcome import OutcomeSignal
from backend.services.observability.metrics import MetricsStore
from backend.services.tenancy import require_session_tenant


def _seed_outcomes(session, signal_types: list[str]) -> None:
    tid = require_session_tenant(session)
    app = Application(company="Acme", position="Data Engineer", tenant_id=tid)
    session.add(app)
    session.flush()
    for st in signal_types:
        session.add(
            OutcomeSignal(
                application_id=app.id,
                signal_type=st,
                signal_weight=1.0,
                tenant_id=tid,
            )
        )
    session.commit()


def test_snapshot_records_versioned_success_rate(client, test_session):
    _seed_outcomes(test_session, ["interview", "offer", "rejected", "no_response"])

    r = client.post("/api/v1/observability/drift/snapshot")
    assert r.status_code == 200

    series = MetricsStore(test_session).series("success_rate")
    assert len(series) == 1
    assert series[0].value == 0.5
    # baseline is tied to the app version (14.1) — not a bare number
    assert "app_version" in series[0].meta_json


def test_snapshot_no_outcomes_records_nothing(client, test_session):
    r = client.post("/api/v1/observability/drift/snapshot")
    assert r.status_code == 200
    # No data → no fabricated sample (ADR-006 low-n honesty)
    assert MetricsStore(test_session).series("success_rate") == []


def test_drift_report_carries_confidence_and_baseline_version(client, test_session):
    store = MetricsStore(test_session)
    for v in [80.0, 82.0, 60.0, 58.0, 55.0]:  # ats_score sliding down
        store.record("ats_score", v, {"app_version": "0.1.0"})
    test_session.commit()

    body = client.get("/api/v1/observability/drift").json()
    ats = next(m for m in body["metrics"] if m["kind"] == "ats_score")
    assert ats["confidence"] in ("weak_inference", "strong_inference", "verified")
    assert ats["baseline_version"] == "0.1.0"


def test_drift_report_low_n_suppresses_confidence(client, test_session):
    MetricsStore(test_session).record("ats_score", 80.0, {"app_version": "0.1.0"})
    test_session.commit()
    body = client.get("/api/v1/observability/drift").json()
    ats = next(m for m in body["metrics"] if m["kind"] == "ats_score")
    # 1 sample: not drifting, no confident figure
    assert ats["drifting"] is False
    assert ats["confidence"] is None
