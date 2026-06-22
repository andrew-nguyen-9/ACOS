"""Phase 12.13 Adaptive Prompt Evolution — versioned, reversible, approval-gated.

No autonomous prod mutation: candidates are new inactive rows, promotion requires
explicit approval, every transition is audited, and rollback is one call. Builds on
the 11.2 PromptRegistry/PromptVersion — extends, never replaces.
"""
from __future__ import annotations

import pytest

from backend.repositories.optimization import OptimizationLogRepository, PromptVersionRepository
from backend.services.optimization.guardrails import GuardrailViolation
from backend.services.prompts.registry import PromptRegistry
from backend.services.flywheel.prompt_evolution import PromptEvolutionService


def _deploy_incumbent(session) -> None:
    PromptRegistry(session).deploy("resume/extract_keywords", "system: v1", version="v1")


def test_propose_creates_inactive_candidate_incumbent_unchanged(test_session):
    _deploy_incumbent(test_session)
    svc = PromptEvolutionService(test_session)
    cand = svc.propose(
        "resume/extract_keywords", "system: v2 better",
        signal_ids=["sig1", "sig2"], rationale="v1 underperforms on interview lift",
        expected_impact="raise interview conversion",
    )
    assert cand.is_active is False                    # incumbent untouched
    assert cand.version == "v2"
    assert cand.parent_version == "v1"
    # rationale links the motivating signals (explainability)
    assert "sig1" in cand.change_rationale and "sig2" in cand.change_rationale

    repo = PromptVersionRepository(test_session)
    assert repo.get_active("resume/extract_keywords").version == "v1"  # still v1


def test_propose_requires_linked_signals(test_session):
    _deploy_incumbent(test_session)
    svc = PromptEvolutionService(test_session)
    with pytest.raises(ValueError, match="signal"):
        svc.propose("resume/extract_keywords", "x", signal_ids=[],
                    rationale="r", expected_impact="i")


def test_propose_runs_optimization_guardrails(test_session):
    _deploy_incumbent(test_session)
    svc = PromptEvolutionService(test_session)
    # high risk + weak confidence is a guardrail violation (reused from optimization/)
    with pytest.raises(GuardrailViolation):
        svc.propose("resume/extract_keywords", "x", signal_ids=["s1"],
                    rationale="r", expected_impact="i",
                    confidence_level="weak_inference", risk_level="high")


def test_promote_requires_explicit_approval(test_session):
    _deploy_incumbent(test_session)
    svc = PromptEvolutionService(test_session)
    svc.propose("resume/extract_keywords", "system: v2", signal_ids=["s1"],
                rationale="r", expected_impact="i")
    with pytest.raises(ValueError, match="approv"):
        svc.promote("resume/extract_keywords", "v2", approved_by="")


def test_promote_with_approval_flips_pointer_and_audits(test_session):
    _deploy_incumbent(test_session)
    svc = PromptEvolutionService(test_session)
    svc.propose("resume/extract_keywords", "system: v2", signal_ids=["s1"],
                rationale="r", expected_impact="i")
    svc.promote("resume/extract_keywords", "v2", approved_by="andrew")

    repo = PromptVersionRepository(test_session)
    assert repo.get_active("resume/extract_keywords").version == "v2"  # pointer flipped
    logs = OptimizationLogRepository(test_session).list()
    applied = [l for l in logs if l.action == "applied" and l.target_parameter == "resume/extract_keywords"]
    assert applied and applied[-1].actor == "andrew"
    assert applied[-1].old_value == "v1" and applied[-1].new_value == "v2"


def test_rollback_restores_prior_active_in_one_call(test_session):
    _deploy_incumbent(test_session)
    svc = PromptEvolutionService(test_session)
    svc.propose("resume/extract_keywords", "system: v2", signal_ids=["s1"],
                rationale="r", expected_impact="i")
    svc.promote("resume/extract_keywords", "v2", approved_by="andrew")

    svc.rollback("resume/extract_keywords", approved_by="andrew")
    repo = PromptVersionRepository(test_session)
    assert repo.get_active("resume/extract_keywords").version == "v1"  # restored
    logs = OptimizationLogRepository(test_session).list()
    assert any(l.action == "reverted" and l.new_value == "v1" for l in logs)
