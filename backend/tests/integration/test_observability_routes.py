"""Integration: observability drift + metrics endpoints (Phase 11.2)."""
from __future__ import annotations

from backend.services.observability.metrics import MetricsStore


def test_drift_endpoint_reports_all_kinds(client):
    r = client.get("/api/v1/observability/drift")
    assert r.status_code == 200
    kinds = {m["kind"] for m in r.json()["metrics"]}
    assert "ats_score" in kinds
    for m in r.json()["metrics"]:
        assert "drifting" in m and "baseline" in m and "delta" in m


def test_metrics_endpoint_returns_recorded_series(client, test_session):
    MetricsStore(test_session).record("ats_score", 88.0, {"resume_id": "x"})
    test_session.commit()
    r = client.get("/api/v1/observability/metrics", params={"kind": "ats_score"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["series"][0]["value"] == 88.0
    assert body["series"][0]["meta"] == {"resume_id": "x"}
