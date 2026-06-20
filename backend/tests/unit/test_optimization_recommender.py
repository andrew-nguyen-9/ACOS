# backend/tests/unit/test_optimization_recommender.py
from backend.services.optimization.recommender import Recommender
from backend.repositories.optimization import OptimizationProposalRepository
from backend.repositories.outcome import OutcomeSignalRepository
from backend.services.learning.ranker import _SIGNAL_WEIGHTS
from backend.models.application import Application


def _seed(session, rows):
    repo = OutcomeSignalRepository(session)
    app = Application(company="C", position="P"); session.add(app); session.flush()
    for st, ats, tpl, ind in rows:
        repo.create(application_id=app.id, signal_type=st,
                    signal_weight=_SIGNAL_WEIGHTS[st], ats_score=ats,
                    template_used=tpl, industry=ind)
    session.commit()


def test_template_proposal_created(test_session):
    # Template B clearly outperforms A on interview rate, both have >=5 samples.
    rows = []
    rows += [("no_response", 40, "A", "fintech")] * 5     # A: 0% interview
    rows += [("interview", 80, "B", "ai")] * 5            # B: 100% interview
    _seed(test_session, rows)

    rec = Recommender(test_session)
    created = rec.generate_proposals(min_sample_size=5)
    test_session.commit()

    repo = OptimizationProposalRepository(test_session)
    pending = repo.list_by_status("pending")
    assert any(p.target_parameter == "default_template" and p.proposed_value == "B"
               for p in pending)
    # All created proposals are pending and explainable.
    for p in created:
        assert p.status == "pending"
        assert p.rationale and p.expected_impact
        assert p.confidence_level in {"verified", "strong_inference", "weak_inference"}


def test_no_proposals_when_insufficient_data(test_session):
    _seed(test_session, [("interview", 80, "A", "ai")])  # only 1 signal
    rec = Recommender(test_session)
    created = rec.generate_proposals(min_sample_size=5)
    assert created == []


def test_ats_proposal_passes_guardrail(test_session):
    # Low ATS-outcome correlation + enough samples → ATS recalibration proposal.
    rows = [("interview", 10, "A", "ai")] * 3 + [("no_response", 95, "A", "ai")] * 3
    _seed(test_session, rows)
    rec = Recommender(test_session)
    created = rec.generate_proposals(min_sample_size=5)
    ats = [p for p in created if p.target_engine == "ats"]
    # If created, the rationale mentions interview (guardrail-compliant).
    for p in ats:
        assert "interview" in (p.rationale + p.expected_impact).lower()
