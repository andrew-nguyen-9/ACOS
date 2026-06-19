from __future__ import annotations

import pytest
from backend.repositories.application import ApplicationRepository
from backend.services.learning.ranker import OutcomeRanker


def _make_app(session, company="Acme", position="Engineer"):
    return ApplicationRepository(session).create(company=company, position=position)


def test_record_outcome_valid_signal(test_session):
    app = _make_app(test_session)
    ranker = OutcomeRanker(test_session)
    result = ranker.record_outcome(
        application_id=app.id, signal_type="interview", template_used="software"
    )
    assert result["signal_type"] == "interview"
    assert result["signal_weight"] == 0.7
    assert result["application_id"] == app.id
    assert "signal_id" in result


def test_record_outcome_all_weight_values(test_session):
    expected = {
        "no_response": 0.0, "rejected": 0.1, "phone_screen": 0.4,
        "interview": 0.7, "final_round": 0.85, "offer": 1.0, "accepted": 1.0,
    }
    ranker = OutcomeRanker(test_session)
    for signal_type, weight in expected.items():
        app = _make_app(test_session, company=signal_type, position="P")
        result = ranker.record_outcome(application_id=app.id, signal_type=signal_type)
        assert result["signal_weight"] == weight, f"Wrong weight for {signal_type}"


def test_record_outcome_invalid_signal_type(test_session):
    app = _make_app(test_session)
    ranker = OutcomeRanker(test_session)
    with pytest.raises(ValueError, match="Invalid signal_type"):
        ranker.record_outcome(application_id=app.id, signal_type="hired")


def test_get_template_rankings_empty(test_session):
    ranker = OutcomeRanker(test_session)
    assert ranker.get_template_rankings() == []


def test_get_template_rankings_sorted_descending(test_session):
    ranker = OutcomeRanker(test_session)
    app1 = _make_app(test_session, company="A")
    app2 = _make_app(test_session, company="B")
    ranker.record_outcome(app1.id, "offer", template_used="software")
    ranker.record_outcome(app2.id, "rejected", template_used="ai")
    rankings = ranker.get_template_rankings()
    assert len(rankings) == 2
    assert rankings[0]["template_name"] == "software"
    assert rankings[0]["score"] == 1.0
    assert rankings[1]["template_name"] == "ai"
    assert rankings[1]["score"] == 0.1


def test_get_template_rankings_averages_multiple_signals(test_session):
    ranker = OutcomeRanker(test_session)
    app1 = _make_app(test_session, company="A")
    app2 = _make_app(test_session, company="B")
    ranker.record_outcome(app1.id, "offer", template_used="software")   # weight 1.0
    ranker.record_outcome(app2.id, "rejected", template_used="software")  # weight 0.1
    rankings = ranker.get_template_rankings()
    assert rankings[0]["score"] == pytest.approx(0.55, abs=1e-3)
    assert rankings[0]["signal_count"] == 2


def test_get_template_rankings_includes_signal_types(test_session):
    ranker = OutcomeRanker(test_session)
    app = _make_app(test_session)
    ranker.record_outcome(app.id, "interview", template_used="consulting")
    rankings = ranker.get_template_rankings()
    assert "interview" in rankings[0]["signal_types"]


def test_ats_vs_outcome_no_data(test_session):
    ranker = OutcomeRanker(test_session)
    result = ranker.get_ats_vs_outcome_correlation()
    assert result["total_signals"] == 0
    assert all(b["count"] == 0 for b in result["buckets"])


def test_ats_vs_outcome_correct_bucket_assignment(test_session):
    ranker = OutcomeRanker(test_session)
    app1 = _make_app(test_session, company="A")
    app2 = _make_app(test_session, company="B")
    app3 = _make_app(test_session, company="C")
    ranker.record_outcome(app1.id, "offer", ats_score=85.0)   # 80-100 bucket
    ranker.record_outcome(app2.id, "rejected", ats_score=30.0)  # 20-40 bucket
    ranker.record_outcome(app3.id, "interview", ats_score=55.0)  # 40-60 bucket
    result = ranker.get_ats_vs_outcome_correlation()
    assert result["total_signals"] == 3
    bucket_map = {b["range"]: b for b in result["buckets"]}
    assert bucket_map["80-100"]["count"] == 1
    assert bucket_map["80-100"]["outcome_rate"] == 1.0
    assert bucket_map["20-40"]["count"] == 1
    assert bucket_map["20-40"]["outcome_rate"] == pytest.approx(0.1)
    assert bucket_map["0-20"]["count"] == 0
