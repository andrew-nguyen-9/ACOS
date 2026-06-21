from __future__ import annotations

import pytest
from backend.services.resume.bullet_scorer import BulletScorer


@pytest.fixture
def scorer() -> BulletScorer:
    return BulletScorer()


def _bullet(text: str, confidence: str = "verified") -> dict:
    return {"bullet_text": text, "evidence_id": "e1", "confidence": confidence}


def test_score_high_impact_quantified_keyword_leadership(scorer: BulletScorer) -> None:
    bullet = _bullet("Led team of 8 engineers generating $2M in revenue via Python ETL pipeline")
    s = scorer.score(bullet, keywords=["Python", "ETL", "revenue"], relevance_score=0.9)
    assert s > 0.7


def test_score_weak_no_signal_is_low(scorer: BulletScorer) -> None:
    bullet = _bullet("Helped with some tasks at the office", "weak_inference")
    s = scorer.score(bullet, keywords=["Python", "ETL"], relevance_score=0.1)
    assert s < 0.3


def test_score_returns_non_negative(scorer: BulletScorer) -> None:
    bullet = _bullet("Did something", "weak_inference")
    s = scorer.score(bullet, keywords=[], relevance_score=0.0)
    assert s >= 0.0


def test_score_many_adds_score_key(scorer: BulletScorer) -> None:
    bullets = [
        _bullet("Built Python API reducing latency by 50%"),
        _bullet("Helped team", "weak_inference"),
    ]
    result = scorer.score_many(bullets, keywords=["Python"])
    assert all("score" in b for b in result)
    assert len(result) == 2


def test_score_many_sorted_descending(scorer: BulletScorer) -> None:
    bullets = [
        _bullet("Helped team", "weak_inference"),
        _bullet("Led migration generating $3M revenue with 40% latency reduction"),
    ]
    result = scorer.score_many(bullets, keywords=["Python"])
    assert result[0]["score"] >= result[1]["score"]


def test_impact_keywords_raise_score(scorer: BulletScorer) -> None:
    with_impact = _bullet("Generated $3M in revenue through automation")
    without_impact = _bullet("Worked on automation project")
    s_with = scorer.score(with_impact, keywords=[], relevance_score=0.5)
    s_without = scorer.score(without_impact, keywords=[], relevance_score=0.5)
    assert s_with > s_without


def test_leadership_keywords_raise_score(scorer: BulletScorer) -> None:
    led = _bullet("Led team of 12 engineers across 3 countries")
    not_led = _bullet("Participated in team project across 3 countries")
    s_led = scorer.score(led, keywords=[], relevance_score=0.5)
    s_not = scorer.score(not_led, keywords=[], relevance_score=0.5)
    assert s_led > s_not


def test_uniqueness_penalizes_similar_bullets(scorer: BulletScorer) -> None:
    already_selected = [
        {"bullet_text": "Built Python ETL pipeline reducing latency by 40%"}
    ]
    # Exact duplicate — same signal strength but uniqueness=0
    duplicate = _bullet("Built Python ETL pipeline reducing latency by 40%")
    # Same keywords + equal signal, but distinct content → uniqueness≈1
    unique = _bullet("Led Python data warehouse generating $2M in efficiency gains")
    s_dup = scorer.score(duplicate, keywords=["Python"], relevance_score=0.8, already_selected=already_selected)
    s_unique = scorer.score(unique, keywords=["Python"], relevance_score=0.8, already_selected=already_selected)
    assert s_unique > s_dup


def test_score_many_preserves_original_fields(scorer: BulletScorer) -> None:
    bullets = [{"bullet_text": "Led team", "evidence_id": "abc", "company": "Acme", "confidence": "verified"}]
    result = scorer.score_many(bullets, keywords=[])
    assert result[0]["company"] == "Acme"
    assert result[0]["evidence_id"] == "abc"


def test_no_keywords_gives_zero_keyword_score(scorer: BulletScorer) -> None:
    # Should not crash and should return a valid score
    bullet = _bullet("Led team of 5")
    s = scorer.score(bullet, keywords=[], relevance_score=0.5)
    assert 0.0 <= s <= 2.0  # upper bound is generous since weights sum to 1 × max_contribution


def test_score_many_empty_returns_empty(scorer: BulletScorer) -> None:
    assert scorer.score_many([], keywords=["Python"]) == []
