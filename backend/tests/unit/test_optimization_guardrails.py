import pytest
from backend.services.optimization.guardrails import validate_proposal, GuardrailViolation


def _valid(**overrides):
    base = dict(
        target_engine="ats", target_parameter="ats_keyword_weight",
        proposed_value="0.40",
        rationale="Higher keyword weight correlates with more interviews in fintech.",
        expected_impact="+8% interview rate for fintech roles",
        confidence_level="strong_inference", risk_level="low",
    )
    base.update(overrides)
    return base


def test_valid_proposal_passes():
    validate_proposal(_valid())  # no raise


def test_missing_rationale_rejected():
    with pytest.raises(GuardrailViolation):
        validate_proposal(_valid(rationale=""))


def test_bad_confidence_rejected():
    with pytest.raises(GuardrailViolation):
        validate_proposal(_valid(confidence_level="guess"))


def test_bad_engine_rejected():
    with pytest.raises(GuardrailViolation):
        validate_proposal(_valid(target_engine="database"))


def test_ats_score_only_optimization_rejected():
    with pytest.raises(GuardrailViolation):
        validate_proposal(_valid(
            rationale="This raises the ATS score.",
            expected_impact="ATS score improves by 15 points",
        ))


def test_ats_change_justified_by_interviews_passes():
    validate_proposal(_valid(
        rationale="Raises ATS score AND historically lifts interview callbacks.",
        expected_impact="ATS score up; interview rate +6%",
    ))  # no raise — mentions interview


def test_high_risk_weak_confidence_rejected():
    with pytest.raises(GuardrailViolation):
        validate_proposal(_valid(risk_level="high", confidence_level="weak_inference"))
