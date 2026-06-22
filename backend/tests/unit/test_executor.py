"""Phase 11.4 — approval-gated executor: approve, snapshot-first, run, audit."""
from __future__ import annotations

import json

import pytest

from backend.models.maintenance import MaintenanceAudit, MaintenanceSuggestion
from backend.repositories.system_config import SystemConfigRepository
from backend.services.maintenance.executor import MaintenanceExecutor, NotApprovedError
from backend.services.prompts.registry import PromptRegistry


class _SpySnapshotter:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def __call__(self) -> str:
        self.calls += 1
        if self.fail:
            raise RuntimeError("snapshot boom")
        return "snap-abc"


class _FakeIndexer:
    def __init__(self):
        self.calls = []

    def index_all(self, session, only_changed=False):
        self.calls.append(only_changed)
        return 7


def _make(session, type_, payload, status="suggested"):
    row = MaintenanceSuggestion(type=type_, reason="t", payload_json=json.dumps(payload), status=status)
    session.add(row)
    session.flush()
    return row


def test_approve_moves_to_approved_and_audits(test_session):
    s = _make(test_session, "model_switch", {"to_model": "x"})
    out = MaintenanceExecutor(test_session).approve(s.id)
    assert out.status == "approved"
    events = [a.event for a in test_session.query(MaintenanceAudit).all()]
    assert "approved" in events


def test_dismiss_moves_to_dismissed(test_session):
    s = _make(test_session, "reindex", {"only_changed": False})
    out = MaintenanceExecutor(test_session).dismiss(s.id)
    assert out.status == "dismissed"


def test_execute_snapshots_first_then_runs_model_switch(test_session):
    cfg = SystemConfigRepository(test_session)
    cfg.set_value("default_model", "qwen3:8b")
    s = _make(test_session, "model_switch", {"to_model": "qwen3:4b"})
    snap = _SpySnapshotter()
    exe = MaintenanceExecutor(test_session, snapshotter=snap)
    exe.approve(s.id)

    out = exe.execute(s.id)

    assert snap.calls == 1
    assert out.status == "executed"
    assert out.snapshot_id == "snap-abc"
    assert out.executed_at is not None
    assert cfg.get_value("default_model") == "qwen3:4b"
    assert json.loads(out.result_json)["default_model"] == "qwen3:4b"
    events = [a.event for a in test_session.query(MaintenanceAudit).all()]
    assert "executed" in events


def test_execute_prompt_rollback_runs_bound_action(test_session):
    reg = PromptRegistry(test_session)
    reg.deploy("resume_bullet", "v1")
    reg.deploy("resume_bullet", "v2")  # v2 active
    s = _make(test_session, "prompt_rollback", {"prompt_name": "resume_bullet", "to_version": "v1"})
    exe = MaintenanceExecutor(test_session, snapshotter=_SpySnapshotter())
    exe.approve(s.id)
    exe.execute(s.id)
    assert reg.active("resume_bullet").version == "v1"


def test_execute_reindex_requires_indexer(test_session):
    s = _make(test_session, "reindex", {"only_changed": False})
    exe = MaintenanceExecutor(test_session, snapshotter=_SpySnapshotter())
    exe.approve(s.id)
    with pytest.raises(RuntimeError):
        exe.execute(s.id)


def test_execute_reindex_with_indexer_runs_index_all(test_session):
    s = _make(test_session, "reindex", {"only_changed": False})
    idx = _FakeIndexer()
    exe = MaintenanceExecutor(test_session, snapshotter=_SpySnapshotter(), indexer=idx)
    exe.approve(s.id)
    out = exe.execute(s.id)
    assert idx.calls == [False]
    assert json.loads(out.result_json)["reembedded"] == 7


def test_snapshot_failure_aborts_before_action(test_session):
    cfg = SystemConfigRepository(test_session)
    cfg.set_value("default_model", "qwen3:8b")
    s = _make(test_session, "model_switch", {"to_model": "qwen3:4b"})
    exe = MaintenanceExecutor(test_session, snapshotter=_SpySnapshotter(fail=True))
    exe.approve(s.id)

    with pytest.raises(RuntimeError):
        exe.execute(s.id)

    # Action never ran; suggestion marked failed; audited.
    assert cfg.get_value("default_model") == "qwen3:8b"
    refreshed = test_session.get(MaintenanceSuggestion, s.id)
    assert refreshed.status == "failed"
    events = [a.event for a in test_session.query(MaintenanceAudit).all()]
    assert "failed" in events


def test_failure_record_survives_request_rollback(test_session):
    # The failure status + audit must be committed independently, so a caller
    # whose request session rolls back (on the re-raised exception) still keeps
    # the record. Simulate that rollback after execute() raises.
    s = _make(test_session, "model_switch", {"to_model": "x"})
    exe = MaintenanceExecutor(test_session, snapshotter=_SpySnapshotter(fail=True))
    exe.approve(s.id)
    with pytest.raises(RuntimeError):
        exe.execute(s.id)
    test_session.rollback()  # what get_session does on the propagated exception
    assert test_session.get(MaintenanceSuggestion, s.id).status == "failed"
    assert any(a.event == "failed" for a in test_session.query(MaintenanceAudit).all())
