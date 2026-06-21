from __future__ import annotations

import pytest

from backend.services.intelligence.self_corrector import SelfCorrector


@pytest.fixture
def corrector() -> SelfCorrector:
    return SelfCorrector(max_chars=175)


def _b(text: str, confidence: str = "verified", score: float = 0.5, **extra) -> dict:
    return {"bullet_text": text, "confidence": confidence, "score": score, **extra}


def test_long_bullet_compressed_within_limit(corrector: SelfCorrector) -> None:
    long = "Led " + "the cross-functional initiative across many teams " * 6  # >175
    result = corrector.correct([_b(long)])
    assert len(result.bullets[0]["bullet_text"]) <= 175
    assert any("compress" in c.lower() or "length" in c.lower() for c in result.corrections)


def test_clean_bullets_unchanged(corrector: SelfCorrector) -> None:
    clean = _b("Led migration reducing latency by 40%")
    result = corrector.correct([clean])
    assert result.bullets[0]["bullet_text"] == "Led migration reducing latency by 40%"
    assert result.requires_approval is False


def test_weak_inference_sets_requires_approval(corrector: SelfCorrector) -> None:
    result = corrector.correct([_b("Possibly led a team", confidence="weak_inference")])
    assert result.requires_approval is True


def test_exact_duplicate_deduped_keeping_higher_score(corrector: SelfCorrector) -> None:
    dup_low = _b("Built the data pipeline", score=0.3, evidence_id="a")
    dup_high = _b("Built the data pipeline", score=0.9, evidence_id="b")
    result = corrector.correct([dup_low, dup_high])
    assert len(result.bullets) == 1
    assert result.bullets[0]["evidence_id"] == "b"  # higher score kept


def test_near_duplicate_deduped(corrector: SelfCorrector) -> None:
    a = _b("Led python data pipeline reducing latency", score=0.9, evidence_id="a")
    b = _b("Led python data pipeline reducing latency time", score=0.5, evidence_id="b")
    result = corrector.correct([a, b])
    assert len(result.bullets) == 1
    assert result.bullets[0]["evidence_id"] == "a"


def test_hallucinated_skill_flagged(corrector: SelfCorrector) -> None:
    # bullet claims Kubernetes but it's not in the allowed evidence skills
    result = corrector.correct(
        [_b("Deployed services on Kubernetes")],
        allowed_skills=["Python", "SQL"],
    )
    assert any("kubernetes" in f.lower() for f in result.hallucination_flags)


def test_no_hallucination_when_skill_allowed(corrector: SelfCorrector) -> None:
    result = corrector.correct(
        [_b("Built Python services")],
        allowed_skills=["Python"],
    )
    assert result.hallucination_flags == []


def test_hallucination_check_skipped_without_allowed_skills(corrector: SelfCorrector) -> None:
    result = corrector.correct([_b("Deployed services on Kubernetes")])
    assert result.hallucination_flags == []
