import pytest
from backend.services.optimization.applier import Applier, ApprovalRequired
from backend.repositories.optimization import (
    OptimizationProposalRepository, OptimizationLogRepository,
)
from backend.repositories.system_config import SystemConfigRepository


def _make(session, **overrides):
    repo = OptimizationProposalRepository(session)
    base = dict(
        target_engine="ats", target_parameter="ats_keyword_weight",
        current_value="0.35", proposed_value="0.30",
        rationale="r mentions interview", expected_impact="interview rate up",
        confidence_level="strong_inference", risk_level="low",
    )
    base.update(overrides)
    p = repo.create(**base); session.commit()
    return p


def test_apply_requires_approval(test_session):
    p = _make(test_session)
    applier = Applier(test_session)
    with pytest.raises(ApprovalRequired):
        applier.apply(p.id)            # still pending → refused


def test_full_approve_apply_revert_cycle(test_session):
    cfg = SystemConfigRepository(test_session)
    cfg.set_value("ats_keyword_weight", "0.35"); test_session.commit()
    p = _make(test_session)
    applier = Applier(test_session)

    applier.approve(p.id); test_session.commit()
    assert OptimizationProposalRepository(test_session).get(p.id).status == "approved"

    log = applier.apply(p.id); test_session.commit()
    assert log.action == "applied"
    assert log.old_value == "0.35" and log.new_value == "0.30"
    assert cfg.get_value("ats_keyword_weight") == "0.30"

    rev = applier.revert(p.id); test_session.commit()
    assert rev.action == "reverted"
    assert cfg.get_value("ats_keyword_weight") == "0.35"   # restored
    assert OptimizationProposalRepository(test_session).get(p.id).status == "reverted"
    # Audit trail has both entries.
    logs = OptimizationLogRepository(test_session).list_for_proposal(p.id)
    assert {l.action for l in logs} == {"applied", "reverted"}


def test_reject_blocks_apply(test_session):
    p = _make(test_session)
    applier = Applier(test_session)
    applier.reject(p.id); test_session.commit()
    with pytest.raises(ApprovalRequired):
        applier.apply(p.id)


def test_revert_without_apply_raises(test_session):
    p = _make(test_session)
    applier = Applier(test_session)
    applier.approve(p.id); test_session.commit()
    with pytest.raises(ValueError):
        applier.revert(p.id)
