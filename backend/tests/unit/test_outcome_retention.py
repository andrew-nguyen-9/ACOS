"""OutcomeLearner applies retention weighting (Phase 11.3).

category_breakdown gains a `weighted_signal` aggregate: recency-decayed success
with a permanent floor. Recent successes weigh full; old successes decay toward
(but never below) the floor.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.repositories.application import ApplicationRepository
from backend.repositories.outcome import OutcomeSignalRepository
from backend.services.strategy.outcome_learner import OutcomeLearner

_POS = "data analyst sql pipeline"


def _signal(session, weight, age_days):
    app = ApplicationRepository(session).create(company="C", position="P")
    created = (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat(
        timespec="microseconds"
    )
    OutcomeSignalRepository(session).create(
        application_id=app.id,
        signal_type="interview",
        signal_weight=weight,
        position_type=_POS,
        created_at=created,
    )


def _entry(report):
    return report["category_breakdown"][0]


def test_weighted_signal_present(test_session):
    _signal(test_session, 0.7, age_days=0)
    report = OutcomeLearner(test_session).outcome_report()
    assert "weighted_signal" in _entry(report)


def test_recent_success_weighs_more_than_old(test_session):
    _signal(test_session, 0.7, age_days=0)
    _signal(test_session, 0.7, age_days=400)
    entry = _entry(OutcomeLearner(test_session).outcome_report())
    # Decay pulls the weighted mean below the raw average...
    assert entry["weighted_signal"] < entry["avg_signal_weight"]
    # ...but the floor keeps it strictly positive.
    assert entry["weighted_signal"] > 0.0


def test_old_winner_keeps_floor(test_session):
    # A single very old high-success signal never decays to zero.
    _signal(test_session, 0.9, age_days=100_000)
    entry = _entry(OutcomeLearner(test_session).outcome_report())
    assert entry["weighted_signal"] >= 0.25 * 0.9 - 1e-6
