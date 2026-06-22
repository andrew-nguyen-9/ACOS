"""ResumeStrategySelector merges success anchors into candidates (Phase 11.3).

Anchors are *added* to the candidate set (not pinned to output) so a flood of
recent low-success applications on the detected template cannot evict a prior
high-success strategy from consideration.
"""
from __future__ import annotations

from backend.repositories.application import ApplicationRepository
from backend.services.learning.ranker import OutcomeRanker
from backend.services.strategy.resume_strategy_selector import ResumeStrategySelector

# A JD that the keyword detector maps to product_management (template pm_executive).
_PM_JD = (
    "Senior Product Manager owning roadmap and product strategy, partnering with "
    "stakeholders to drive product vision and prioritize the backlog. Product-led."
)


def _record(session, signal_type, template, n=1):
    app_repo = ApplicationRepository(session)
    ranker = OutcomeRanker(session)
    for _ in range(n):
        app = app_repo.create(company="C", position="P")
        ranker.record_outcome(
            application_id=app.id, signal_type=signal_type, template_used=template
        )


def test_recommend_works_without_outcomes(test_session):
    result = ResumeStrategySelector(test_session).recommend(_PM_JD)
    assert result["template_name"]
    assert result["anchored_candidates"] == []


def test_recommend_surfaces_high_success_anchor(test_session):
    _record(test_session, "offer", "consulting_narrative", n=3)
    result = ResumeStrategySelector(test_session).recommend(_PM_JD)
    names = [a["template_name"] for a in result["anchored_candidates"]]
    assert "consulting_narrative" in names


def test_anchor_survives_recent_low_success_flood(test_session):
    _record(test_session, "offer", "consulting_narrative", n=2)
    _record(test_session, "rejected", "pm_executive", n=60)
    result = ResumeStrategySelector(test_session).recommend(_PM_JD)
    names = [a["template_name"] for a in result["anchored_candidates"]]
    assert "consulting_narrative" in names, "anchor evicted by recent flood"
