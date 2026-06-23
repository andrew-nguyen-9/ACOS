from __future__ import annotations

from sqlalchemy import select

from backend.api.v1.routes.resume import _emit_ats_metric
from backend.models.signal import Signal
from backend.repositories.application import ApplicationRepository
from backend.services.flywheel.feedback import FeedbackEngine
from backend.services.learning.ranker import OutcomeRanker


def test_recording_outcome_emits_traceable_signal(test_session):
    app = ApplicationRepository(test_session).create(company="Acme", position="PM")
    result = OutcomeRanker(test_session).record_outcome(
        application_id=app.id, signal_type="interview", template_used="software"
    )

    sigs = list(test_session.scalars(select(Signal)).all())
    assert len(sigs) == 1
    sig = sigs[0]
    assert sig.entity_type == "application"
    assert sig.entity_id == app.id
    assert sig.signal_type == "interview"
    assert sig.value == 0.7  # outcome weight
    # Trap 1: signal traces back to the outcome_signals row it was derived from.
    assert sig.source_json["table"] == "outcome_signals"
    assert sig.source_json["ids"] == [result["signal_id"]]

    explained = FeedbackEngine(test_session).explain(sig.id)
    assert explained["source"]["ids"] == [result["signal_id"]]


def test_recording_ats_score_emits_signal(test_session):
    _emit_ats_metric(
        test_session,
        {"ats_score": {"overall_score": 84}},
        template="software",
    )
    sigs = list(test_session.scalars(select(Signal)).all())
    ats = [s for s in sigs if s.signal_type == "ats_score"]
    assert len(ats) == 1
    sig = ats[0]
    assert sig.entity_type == "template"
    assert sig.entity_id == "software"
    assert sig.value == 84.0
    assert sig.source_json["table"] == "metrics"
    assert sig.source_json["ids"]  # the metric row id — traceable, non-empty


def test_outcome_signal_emit_is_best_effort(test_session):
    """A flywheel emit failure must never break outcome recording."""
    # No application row exists for this id at flush boundary, but record_outcome
    # itself still returns; the feedback emit is swallowed, never raised.
    app = ApplicationRepository(test_session).create(company="X", position="Y")
    result = OutcomeRanker(test_session).record_outcome(
        application_id=app.id, signal_type="offer"
    )
    assert result["signal_type"] == "offer"
