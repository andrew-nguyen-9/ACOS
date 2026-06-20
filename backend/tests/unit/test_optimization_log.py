from backend.repositories.optimization import (
    OptimizationProposalRepository,
    OptimizationLogRepository,
)


def _make_proposal(session):
    repo = OptimizationProposalRepository(session)
    p = repo.create(
        target_engine="ats", target_parameter="ats_keyword_weight",
        current_value="0.35", proposed_value="0.40",
        rationale="r", expected_impact="i",
        confidence_level="strong_inference", risk_level="low",
    )
    session.commit()
    return p


def test_log_records_apply(test_session):
    p = _make_proposal(test_session)
    log_repo = OptimizationLogRepository(test_session)
    entry = log_repo.create(
        proposal_id=p.id, action="applied",
        target_engine="ats", target_parameter="ats_keyword_weight",
        old_value="0.35", new_value="0.40",
    )
    test_session.commit()
    assert entry.actor == "user"            # default
    assert log_repo.list_for_proposal(p.id)[0].action == "applied"


def test_list_recent_orders_desc(test_session):
    p = _make_proposal(test_session)
    log_repo = OptimizationLogRepository(test_session)
    log_repo.create(proposal_id=p.id, action="applied",
                    target_engine="ats", target_parameter="w",
                    old_value="1", new_value="2")
    log_repo.create(proposal_id=p.id, action="reverted",
                    target_engine="ats", target_parameter="w",
                    old_value="2", new_value="1")
    test_session.commit()
    recent = log_repo.list_recent(limit=10)
    assert len(recent) == 2
    assert recent[0].action == "reverted"   # most recent first
