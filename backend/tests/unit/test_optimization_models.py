import pytest
from backend.models.optimization import OptimizationProposal
from backend.repositories.optimization import OptimizationProposalRepository


def test_create_and_fetch_proposal(test_session):
    repo = OptimizationProposalRepository(test_session)
    p = repo.create(
        target_engine="ats",
        target_parameter="ats_keyword_weight",
        current_value="0.35",
        proposed_value="0.40",
        rationale="Keyword-heavy roles correlate with more interviews.",
        expected_impact="+8% interview rate for fintech roles",
        confidence_level="strong_inference",
        risk_level="low",
        evidence_json='{"sample_size": 12}',
    )
    test_session.commit()
    assert p.id and len(p.id) == 32
    assert p.status == "pending"          # default
    assert p.decided_at is None
    fetched = repo.get(p.id)
    assert fetched is not None
    assert fetched.target_engine == "ats"


def test_list_by_status(test_session):
    repo = OptimizationProposalRepository(test_session)
    repo.create(
        target_engine="resume", target_parameter="template", proposed_value="B",
        rationale="r", expected_impact="i", confidence_level="weak_inference",
        risk_level="low",
    )
    approved = repo.create(
        target_engine="rag", target_parameter="similarity_threshold", proposed_value="0.4",
        rationale="r", expected_impact="i", confidence_level="verified", risk_level="medium",
        status="approved",
    )
    test_session.commit()
    pending = repo.list_by_status("pending")
    assert len(pending) == 1
    assert repo.list_by_status("approved")[0].id == approved.id


def test_invalid_engine_rejected(test_session):
    repo = OptimizationProposalRepository(test_session)
    with pytest.raises(Exception):  # IntegrityError from CheckConstraint
        repo.create(
            target_engine="not_an_engine", target_parameter="x", proposed_value="y",
            rationale="r", expected_impact="i", confidence_level="verified", risk_level="low",
        )
