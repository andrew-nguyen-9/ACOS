from __future__ import annotations

import pytest
from backend.services.resume.validator import ResumeValidator, ValidationResult


@pytest.fixture
def v() -> ResumeValidator:
    return ResumeValidator()


def _resume(experiences: list[dict] | None = None, total_lines: int = 50) -> dict:
    return {"experiences": experiences or [], "_estimated_lines": total_lines}


def _role(bullets: list[str], is_current: bool = False) -> dict:
    return {"is_current": is_current, "bullets": [{"text": b} for b in bullets]}


# ── Return type ──────────────────────────────────────────────────────────────

def test_validate_returns_validation_result(v: ResumeValidator) -> None:
    result = v.validate(_resume())
    assert isinstance(result, ValidationResult)
    assert isinstance(result.valid, bool)
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)


def test_empty_resume_is_valid(v: ResumeValidator) -> None:
    result = v.validate(_resume())
    assert result.valid


# ── Error: page overflow ─────────────────────────────────────────────────────

def test_error_when_over_60_lines(v: ResumeValidator) -> None:
    resume = _resume(total_lines=65)
    result = v.validate(resume)
    assert not result.valid
    assert any("line" in e.lower() or "page" in e.lower() for e in result.errors)


def test_no_error_at_exactly_60_lines(v: ResumeValidator) -> None:
    resume = _resume(total_lines=60)
    result = v.validate(resume)
    assert not any("line" in e.lower() or "page" in e.lower() for e in result.errors)


# ── Error: bullet too long (≥ 3 lines = > 176 chars) ────────────────────────

def test_error_when_bullet_exceeds_176_chars(v: ResumeValidator) -> None:
    long_bullet = "x" * 177
    resume = _resume(experiences=[_role([long_bullet])])
    result = v.validate(resume)
    assert not result.valid
    assert any("length" in e.lower() or "long" in e.lower() or "177" in e or "176" in e for e in result.errors)


def test_no_error_at_176_chars(v: ResumeValidator) -> None:
    bullet = "x" * 176
    resume = _resume(experiences=[_role([bullet])])
    result = v.validate(resume)
    long_errors = [e for e in result.errors if "length" in e.lower() or "long" in e.lower()]
    assert not long_errors


# ── Error: action verb enforcement ───────────────────────────────────────────

def test_error_when_bullet_lacks_action_verb(v: ResumeValidator) -> None:
    resume = _resume(experiences=[_role(["Python ETL pipeline that generated $3M"])])
    result = v.validate(resume)
    assert not result.valid
    assert any("verb" in e.lower() or "action" in e.lower() for e in result.errors)


def test_no_error_when_bullet_starts_with_action_verb(v: ResumeValidator) -> None:
    resume = _resume(experiences=[_role(["Built Python ETL pipeline generating $3M"])])
    result = v.validate(resume)
    verb_errors = [e for e in result.errors if "verb" in e.lower() or "action" in e.lower()]
    assert not verb_errors


# ── Warning: quantification ───────────────────────────────────────────────────

def test_warning_when_less_than_30_pct_bullets_quantified(v: ResumeValidator) -> None:
    # 1 of 5 is quantified → 20% < 30%
    bullets = [
        "Built API reducing latency by 40%",  # quantified
        "Led team meetings",
        "Developed documentation",
        "Managed stakeholder relations",
        "Deployed infrastructure updates",
    ]
    resume = _resume(experiences=[_role(bullets)])
    result = v.validate(resume)
    assert any("quantif" in w.lower() for w in result.warnings)


def test_no_warning_when_majority_quantified(v: ResumeValidator) -> None:
    bullets = [
        "Built API reducing latency by 40%",
        "Generated $2M in revenue through 3 new features",
        "Led team of 8 engineers to 30% efficiency gain",
    ]
    resume = _resume(experiences=[_role(bullets)])
    result = v.validate(resume)
    assert not any("quantif" in w.lower() for w in result.warnings)


# ── Warning: bullet count per role ───────────────────────────────────────────

def test_warning_when_current_role_exceeds_6_bullets(v: ResumeValidator) -> None:
    bullets = [f"Built feature {i} for 10% gain" for i in range(7)]
    resume = _resume(experiences=[_role(bullets, is_current=True)])
    result = v.validate(resume)
    assert any("bullet" in w.lower() or "role" in w.lower() for w in result.warnings)


def test_warning_when_previous_role_exceeds_4_bullets(v: ResumeValidator) -> None:
    bullets = [f"Built feature {i} for 10% gain" for i in range(5)]
    resume = _resume(experiences=[_role(bullets, is_current=False)])
    result = v.validate(resume)
    assert any("bullet" in w.lower() or "role" in w.lower() for w in result.warnings)
