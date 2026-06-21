from __future__ import annotations

import pytest

from backend.services.resume.bullet_scorer import BulletScorer


@pytest.fixture
def scorer() -> BulletScorer:
    return BulletScorer()


def _b(text: str, confidence: str = "verified", **extra: object) -> dict:
    return {"bullet_text": text, "confidence": confidence, **extra}


def test_higher_confidence_scores_higher(scorer: BulletScorer) -> None:
    verified = scorer.score_with_context(_b("reduced cost by 30%", "verified"), relevance=0.5)
    weak = scorer.score_with_context(_b("reduced cost by 30%", "weak_inference"), relevance=0.5)
    assert verified > weak


def test_higher_relevance_scores_higher(scorer: BulletScorer) -> None:
    high = scorer.score_with_context(_b("led team of 12"), relevance=0.9)
    low = scorer.score_with_context(_b("led team of 12"), relevance=0.1)
    assert high > low


def test_current_role_scores_higher_than_old(scorer: BulletScorer) -> None:
    current = scorer.score_with_context(_b("led team", is_current=True), relevance=0.5)
    old = scorer.score_with_context(_b("led team", is_current=False, years_ago=8), relevance=0.5)
    assert current > old


def test_uncovered_dimension_gets_coverage_bonus(scorer: BulletScorer) -> None:
    # impact already covered; a leadership bullet should out-score another impact bullet
    leadership = scorer.score_with_context(
        _b("led team of 12 engineers"), relevance=0.5, covered_dimensions={"impact"}
    )
    impact = scorer.score_with_context(
        _b("reduced cost by 30%"), relevance=0.5, covered_dimensions={"impact"}
    )
    assert leadership > impact


def test_score_in_unit_range(scorer: BulletScorer) -> None:
    s = scorer.score_with_context(
        _b("reduced cost by 30% leading team", "verified", is_current=True), relevance=1.0
    )
    assert 0.0 <= s <= 1.0


def test_unknown_confidence_treated_as_weak(scorer: BulletScorer) -> None:
    unknown = scorer.score_with_context(_b("did stuff", "bogus"), relevance=0.5)
    weak = scorer.score_with_context(_b("did stuff", "weak_inference"), relevance=0.5)
    assert unknown == weak
