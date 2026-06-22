"""Phase 11.4 headline safety invariant: nothing runs without explicit approval.

The executor is the single chokepoint — only ``execute`` runs a bound action,
and only when status == 'approved'. The advisor never executes. (CLAUDE.md global
rule + roadmap §37: no autonomous destructive actions.)
"""
from __future__ import annotations

import json

import pytest

from backend.models.maintenance import MaintenanceAudit, MaintenanceSuggestion
from backend.repositories.system_config import SystemConfigRepository
from backend.services.maintenance.advisor import MaintenanceAdvisor
from backend.services.maintenance.executor import MaintenanceExecutor, NotApprovedError
from backend.services.observability.metrics import MetricsStore


class _SpySnapshotter:
    def __init__(self):
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        return "snap-test"


def _make_suggestion(session, type_, payload, status="suggested"):
    row = MaintenanceSuggestion(type=type_, reason="t", payload_json=json.dumps(payload), status=status)
    session.add(row)
    session.flush()
    return row


def test_execute_on_unapproved_suggestion_raises_and_runs_nothing(test_session):
    cfg = SystemConfigRepository(test_session)
    cfg.set_value("default_model", "qwen3:8b")
    snap = _SpySnapshotter()
    s = _make_suggestion(test_session, "model_switch", {"to_model": "qwen3:4b"})  # status suggested

    exe = MaintenanceExecutor(test_session, snapshotter=snap)
    with pytest.raises(NotApprovedError):
        exe.execute(s.id)

    # No snapshot taken, no action run.
    assert snap.calls == 0
    assert cfg.get_value("default_model") == "qwen3:8b"


def test_execute_on_dismissed_suggestion_raises(test_session):
    s = _make_suggestion(test_session, "model_switch", {"to_model": "x"}, status="dismissed")
    with pytest.raises(NotApprovedError):
        MaintenanceExecutor(test_session, snapshotter=_SpySnapshotter()).execute(s.id)


def test_advisor_only_suggests_never_executes(test_session):
    cfg = SystemConfigRepository(test_session)
    cfg.set_value("default_model", "qwen3:8b")
    cfg.set_value("fallback_model", "qwen3:4b")
    store = MetricsStore(test_session)
    for _ in range(5):
        store.record("interview_conversion", 0.6)
    for _ in range(5):
        store.record("interview_conversion", 0.2)

    created = MaintenanceAdvisor(test_session).suggest()

    assert created  # produced something
    assert all(s.status == "suggested" for s in created)
    # Nothing executed: no side effect, no 'executed' audit.
    assert cfg.get_value("default_model") == "qwen3:8b"
    events = {a.event for a in test_session.query(MaintenanceAudit).all()}
    assert "executed" not in events
