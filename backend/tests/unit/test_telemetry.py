"""Phase 18.3 — local-only aggregate telemetry: no PII, no outbound, low-n suppressed."""
from __future__ import annotations

from pathlib import Path

from backend.models.application import Application
from backend.models.outcome import OutcomeSignal
from backend.services import audit
from backend.services.observability import telemetry
from backend.services.observability.metrics import MetricsStore
from backend.services.tenancy import require_session_tenant

TELEMETRY_SRC = Path(telemetry.__file__)


def _outcome(session, signal_type):
    tid = require_session_tenant(session)
    app = Application(company="C", position="P", tenant_id=tid)
    session.add(app)
    session.flush()
    session.add(OutcomeSignal(
        application_id=app.id, signal_type=signal_type, signal_weight=1.0, tenant_id=tid,
    ))


def test_usage_counts_from_audit(test_session):
    audit.record(test_session, "generation", {})
    audit.record(test_session, "generation", {})
    audit.record(test_session, "retrieval", {})
    agg = telemetry.local_aggregates(test_session)
    assert agg["usage_counts"]["generation"] == 2
    assert agg["usage_counts"]["retrieval"] == 1


def test_perf_summary_is_means_only(test_session):
    MetricsStore(test_session).record("ats_score", 80.0, {"template": "x"})
    MetricsStore(test_session).record("ats_score", 90.0, {"template": "y"})
    agg = telemetry.local_aggregates(test_session)
    assert agg["perf"]["ats_score"]["mean"] == 85.0
    assert agg["perf"]["ats_score"]["n"] == 2


def test_success_rate_suppressed_below_k(test_session):
    for _ in range(3):  # below _MIN_N
        _outcome(test_session, "offer")
    test_session.flush()
    agg = telemetry.local_aggregates(test_session)
    assert agg["success"]["suppressed"] is True
    assert agg["success"]["rate"] is None


def test_success_rate_computed_above_k(test_session):
    for st in ["offer", "interview", "rejected", "no_response", "phone_screen", "rejected"]:
        _outcome(test_session, st)
    test_session.flush()
    agg = telemetry.local_aggregates(test_session)
    assert agg["success"]["suppressed"] is False
    assert agg["success"]["rate"] == round(3 / 6, 3)  # offer+interview+phone_screen


def test_payload_has_no_pii_keys(test_session):
    audit.record(test_session, "generation", {})
    agg = telemetry.local_aggregates(test_session)
    flat = str(agg).lower()
    for pii in ["email", "name", "company", "resume", "body", "content"]:
        assert pii not in flat


def test_no_network_imports_in_telemetry():
    src = TELEMETRY_SRC.read_text()
    for net in ["httpx", "requests", "urllib", "socket", "aiohttp"]:
        assert net not in src, f"telemetry must not do network I/O ({net})"
