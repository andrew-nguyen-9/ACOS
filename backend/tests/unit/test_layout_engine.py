from __future__ import annotations

import pytest
from backend.services.resume.layout_engine import LayoutEngine, LayoutResult


@pytest.fixture
def engine() -> LayoutEngine:
    return LayoutEngine()


# ── Line estimation ──────────────────────────────────────────────────────────

def test_short_bullet_is_one_line(engine: LayoutEngine) -> None:
    # 50 chars < 88
    assert engine.estimate_bullet_lines("Led team to 40% cost reduction via Python") == 1


def test_exactly_88_chars_is_one_line(engine: LayoutEngine) -> None:
    assert engine.estimate_bullet_lines("x" * 88) == 1


def test_89_chars_is_two_lines(engine: LayoutEngine) -> None:
    assert engine.estimate_bullet_lines("x" * 89) == 2


def test_176_chars_is_two_lines(engine: LayoutEngine) -> None:
    assert engine.estimate_bullet_lines("x" * 176) == 2


def test_177_chars_is_three_lines(engine: LayoutEngine) -> None:
    assert engine.estimate_bullet_lines("x" * 177) == 3


def test_empty_bullet_is_one_line(engine: LayoutEngine) -> None:
    assert engine.estimate_bullet_lines("") == 1


# ── Role line estimation ─────────────────────────────────────────────────────

def test_role_with_no_bullets(engine: LayoutEngine) -> None:
    role = {"bullets": []}
    # 2 lines for position header even with no bullets
    assert engine.estimate_role_lines(role) == 2


def test_role_with_two_short_bullets(engine: LayoutEngine) -> None:
    role = {"bullets": [{"text": "Short bullet A"}, {"text": "Short bullet B"}]}
    # 2 (header) + 1 + 1 = 4
    assert engine.estimate_role_lines(role) == 4


def test_role_with_long_bullet(engine: LayoutEngine) -> None:
    role = {"bullets": [{"text": "x" * 89}]}
    # 2 (header) + 2 (wrapping bullet) = 4
    assert engine.estimate_role_lines(role) == 4


# ── Resume total estimation ──────────────────────────────────────────────────

def test_estimate_resume_returns_layout_result(engine: LayoutEngine) -> None:
    resume = {"experiences": [], "header_lines": 3}
    result = engine.estimate_resume(resume)
    assert isinstance(result, LayoutResult)
    assert result.total_lines >= 0
    assert isinstance(result.fits, bool)


def test_empty_resume_fits(engine: LayoutEngine) -> None:
    resume = {"experiences": [], "header_lines": 3}
    result = engine.estimate_resume(resume)
    assert result.fits


def test_too_many_lines_does_not_fit(engine: LayoutEngine) -> None:
    # A resume with 25 roles of 3 short bullets each: 25*(2+3) = 125 lines
    roles = [{"bullets": [{"text": "Short"}, {"text": "Short"}, {"text": "Short"}]} for _ in range(25)]
    resume = {"experiences": roles, "header_lines": 3}
    result = engine.estimate_resume(resume)
    assert not result.fits


def test_overflow_amount_zero_when_fits(engine: LayoutEngine) -> None:
    resume = {"experiences": [], "header_lines": 3}
    assert engine.overflow_amount(resume) == 0


def test_overflow_amount_positive_when_over(engine: LayoutEngine) -> None:
    roles = [{"bullets": [{"text": "Short"}] * 5} for _ in range(15)]
    resume = {"experiences": roles, "header_lines": 3}
    assert engine.overflow_amount(resume) > 0


def test_remaining_lines_decreases_with_content(engine: LayoutEngine) -> None:
    empty = engine.estimate_resume({"experiences": [], "header_lines": 3})
    one_role = engine.estimate_resume({
        "experiences": [{"bullets": [{"text": "Bullet A"}, {"text": "Bullet B"}]}],
        "header_lines": 3,
    })
    assert one_role.remaining_lines < empty.remaining_lines
