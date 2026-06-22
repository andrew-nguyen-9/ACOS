"""Phase 11.4 — maintenance advisor maps health/drift signals to suggestions.

The advisor only *suggests* (persists rows with status 'suggested' + an audit
entry). It never runs anything — execution is the executor's job (test_no_autoexec).
"""
from __future__ import annotations

import json

from backend.models.maintenance import MaintenanceAudit, MaintenanceSuggestion
from backend.services.maintenance.advisor import MaintenanceAdvisor
from backend.services.observability.metrics import MetricsStore
from backend.services.prompts.registry import PromptRegistry
from backend.repositories.system_config import SystemConfigRepository


def _drift_down(session, kind, high, low, n=5):
    """Seed a metric series that drifts downward (baseline high → current low)."""
    store = MetricsStore(session)
    for _ in range(n):
        store.record(kind, high)
    for _ in range(n):
        store.record(kind, low)


def test_healthy_inputs_produce_no_suggestions(test_session):
    # No metrics, no recorded embedding model, no system_status → nothing to do.
    out = MaintenanceAdvisor(test_session).suggest()
    assert out == []


def test_retrieval_quality_drift_suggests_reindex(test_session):
    _drift_down(test_session, "retrieval_quality", 0.9, 0.4)
    out = MaintenanceAdvisor(test_session).suggest()
    types = {s.type for s in out}
    assert "reindex" in types
    reindex = next(s for s in out if s.type == "reindex")
    assert reindex.status == "suggested"
    assert json.loads(reindex.payload_json)["only_changed"] is False


def test_embedding_stale_suggests_embedding_refresh(test_session):
    SystemConfigRepository(test_session).set_value("embedding_model", "old-embedder")
    out = MaintenanceAdvisor(test_session).suggest(embedding_model="nomic-embed-text")
    refresh = next(s for s in out if s.type == "embedding_refresh")
    assert json.loads(refresh.payload_json)["only_changed"] is True


def test_prompt_perf_drift_suggests_rollback_to_parent(test_session):
    reg = PromptRegistry(test_session)
    reg.deploy("resume_bullet", "v1 content")
    reg.deploy("resume_bullet", "v2 content")  # active, parent=v1
    _drift_down(test_session, "prompt_perf", 0.9, 0.4)

    out = MaintenanceAdvisor(test_session).suggest()
    rollback = next(s for s in out if s.type == "prompt_rollback")
    payload = json.loads(rollback.payload_json)
    assert payload["prompt_name"] == "resume_bullet"
    assert payload["to_version"] == "v1"


def test_prompt_perf_drift_without_rollback_target_skips(test_session):
    # Only a single version exists → no parent to roll back to → no suggestion.
    PromptRegistry(test_session).deploy("resume_bullet", "v1 content")
    _drift_down(test_session, "prompt_perf", 0.9, 0.4)
    out = MaintenanceAdvisor(test_session).suggest()
    assert "prompt_rollback" not in {s.type for s in out}


def test_conversion_drift_with_fallback_suggests_model_switch(test_session):
    SystemConfigRepository(test_session).set_value("fallback_model", "qwen3:4b")
    _drift_down(test_session, "interview_conversion", 0.6, 0.2)
    out = MaintenanceAdvisor(test_session).suggest()
    switch = next(s for s in out if s.type == "model_switch")
    assert json.loads(switch.payload_json)["to_model"] == "qwen3:4b"


def test_conversion_drift_without_fallback_skips_model_switch(test_session):
    _drift_down(test_session, "interview_conversion", 0.6, 0.2)
    out = MaintenanceAdvisor(test_session).suggest()
    assert "model_switch" not in {s.type for s in out}


def test_degraded_chroma_status_suggests_reindex(test_session):
    out = MaintenanceAdvisor(test_session).suggest(
        system_status={"db": "ok", "chroma": "down", "ollama": "ok", "embedding": "ok"}
    )
    assert "reindex" in {s.type for s in out}


def test_suggesting_writes_audit_entries(test_session):
    _drift_down(test_session, "retrieval_quality", 0.9, 0.4)
    MaintenanceAdvisor(test_session).suggest()
    audits = test_session.query(MaintenanceAudit).all()
    assert any(a.event == "suggested" for a in audits)


def test_does_not_duplicate_open_suggestion_of_same_type(test_session):
    _drift_down(test_session, "retrieval_quality", 0.9, 0.4)
    advisor = MaintenanceAdvisor(test_session)
    first = advisor.suggest()
    assert any(s.type == "reindex" for s in first)
    second = advisor.suggest()  # same open reindex still pending
    assert "reindex" not in {s.type for s in second}
    # Only one open reindex row total.
    open_reindex = (
        test_session.query(MaintenanceSuggestion)
        .filter(MaintenanceSuggestion.type == "reindex")
        .all()
    )
    assert len(open_reindex) == 1
