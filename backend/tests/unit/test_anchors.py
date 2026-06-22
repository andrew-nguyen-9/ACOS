"""Success anchoring (Phase 11.3).

High-performing resume strategies (templates) are pinned as anchors that the
selector always considers, immune to recency-only drift. The headline guarantee:
flooding many recent low-success applications must not evict a prior high-success
anchor from the selection.
"""
from __future__ import annotations

from backend.repositories.application import ApplicationRepository
from backend.services.learning import anchors
from backend.services.learning.ranker import OutcomeRanker


def _record(session, signal_type, template, n=1):
    app_repo = ApplicationRepository(session)
    ranker = OutcomeRanker(session)
    for _ in range(n):
        app = app_repo.create(company="C", position="P")
        ranker.record_outcome(
            application_id=app.id, signal_type=signal_type, template_used=template
        )


def test_no_signals_returns_empty(test_session):
    assert anchors.select_anchors(test_session) == []


def test_selects_high_success_template(test_session):
    _record(test_session, "offer", "consulting_narrative", n=3)
    _record(test_session, "rejected", "pm_executive", n=3)

    result = anchors.select_anchors(test_session)

    names = [a["template_name"] for a in result]
    assert "consulting_narrative" in names
    assert result[0]["template_name"] == "consulting_narrative"


def test_eviction_resistance(test_session):
    # One proven historical winner...
    _record(test_session, "offer", "consulting_narrative", n=2)
    # ...then a flood of recent low-success applications on another template.
    _record(test_session, "rejected", "pm_executive", n=50)
    _record(test_session, "no_response", "pm_executive", n=50)

    result = anchors.select_anchors(test_session)
    names = [a["template_name"] for a in result]

    assert "consulting_narrative" in names, "high-success anchor was evicted by recent flood"


def test_caps_at_max_count(test_session):
    for i, tmpl in enumerate(["a", "b", "c", "d", "e"]):
        # descending success so all are plausible anchors
        _record(test_session, "offer", tmpl, n=2)

    result = anchors.select_anchors(test_session, top_n=3)
    assert len(result) <= 3


def test_zero_success_not_anchored(test_session):
    _record(test_session, "no_response", "deadweight", n=5)
    result = anchors.select_anchors(test_session)
    assert all(a["template_name"] != "deadweight" for a in result)
