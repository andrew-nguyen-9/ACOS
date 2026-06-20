from backend.services.learning.ranker import OutcomeRanker
from backend.services.optimization.evaluator import Evaluator, STRONG_SIGNALS
from backend.repositories.outcome import OutcomeSignalRepository


def _seed(session, rows):
    """rows: list of (signal_type, ats_score, template, industry)."""
    ranker = OutcomeRanker(session)
    # OutcomeRanker.record_outcome requires a real application FK; insert signals directly.
    repo = OutcomeSignalRepository(session)
    from backend.services.learning.ranker import _SIGNAL_WEIGHTS
    # Create a dummy application to satisfy the FK.
    from backend.models.application import Application
    app = Application(company="C", position="P")
    session.add(app); session.flush()
    for st, ats, tpl, ind in rows:
        repo.create(application_id=app.id, signal_type=st,
                    signal_weight=_SIGNAL_WEIGHTS[st], ats_score=ats,
                    template_used=tpl, industry=ind)
    session.commit()


def test_interview_rate(test_session):
    _seed(test_session, [
        ("interview", 80, "A", "fintech"),
        ("no_response", 40, "A", "fintech"),
        ("offer", 90, "B", "ai"),
        ("rejected", 30, "B", "ai"),
    ])
    ev = Evaluator(test_session)
    r = ev.interview_rate()
    assert r["total"] == 4
    assert r["interviews"] == 2           # interview + offer are strong
    assert abs(r["interview_rate"] - 0.5) < 1e-9


def test_template_effectiveness_has_interview_rate(test_session):
    _seed(test_session, [
        ("interview", 80, "A", "fintech"),
        ("no_response", 40, "A", "fintech"),
        ("offer", 90, "B", "ai"),
    ])
    ev = Evaluator(test_session)
    rows = {r["template_name"]: r for r in ev.template_effectiveness()}
    assert abs(rows["A"]["interview_rate"] - 0.5) < 1e-9
    assert abs(rows["B"]["interview_rate"] - 1.0) < 1e-9


def test_ats_correlation_runs(test_session):
    _seed(test_session, [
        ("interview", 80, "A", "fintech"),
        ("no_response", 30, "A", "fintech"),
        ("offer", 95, "B", "ai"),
        ("rejected", 20, "B", "ai"),
    ])
    ev = Evaluator(test_session)
    out = ev.ats_outcome_correlation()
    assert -1.0 <= out["correlation"] <= 1.0
    assert "buckets" in out


def test_industry_effectiveness(test_session):
    _seed(test_session, [
        ("interview", 80, "A", "fintech"),
        ("no_response", 40, "A", "fintech"),
        ("offer", 90, "B", "ai"),
    ])
    ev = Evaluator(test_session)
    by_ind = {r["industry"]: r for r in ev.industry_effectiveness()}
    assert abs(by_ind["fintech"]["interview_rate"] - 0.5) < 1e-9
    assert by_ind["ai"]["sample_size"] == 1


def test_empty_is_safe(test_session):
    ev = Evaluator(test_session)
    assert ev.interview_rate() == {"interview_rate": 0.0, "total": 0, "interviews": 0}
    assert ev.ats_outcome_correlation()["correlation"] == 0.0
