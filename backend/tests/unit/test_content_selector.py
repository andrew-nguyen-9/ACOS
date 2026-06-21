from __future__ import annotations

import pytest
from backend.services.resume.content_selector import ContentSelector


def _bullet(
    text: str,
    experience_id: str = "exp1",
    company: str = "Acme",
    is_current: bool = False,
    score: float = 0.5,
) -> dict:
    return {
        "bullet_text": text,
        "experience_id": experience_id,
        "company": company,
        "is_current": is_current,
        "score": score,
        "evidence_id": "e1",
        "confidence": "verified",
    }


@pytest.fixture
def selector() -> ContentSelector:
    return ContentSelector()


# ── Basic selection ──────────────────────────────────────────────────────────

def test_select_returns_two_lists(selector: ContentSelector) -> None:
    bullets = [_bullet(f"Bullet {i}", score=float(i)) for i in range(5)]
    selected, excluded = selector.select(bullets, max_bullets=3)
    assert len(selected) == 3
    assert len(excluded) == 2


def test_select_picks_highest_scored(selector: ContentSelector) -> None:
    bullets = [
        _bullet("Low", score=0.1),
        _bullet("High", score=0.9),
        _bullet("Mid", score=0.5),
    ]
    selected, _ = selector.select(bullets, max_bullets=1)
    assert selected[0]["bullet_text"] == "High"


def test_select_all_when_max_exceeds_pool(selector: ContentSelector) -> None:
    bullets = [_bullet(f"B{i}", score=float(i)) for i in range(3)]
    selected, excluded = selector.select(bullets, max_bullets=10)
    assert len(selected) == 3
    assert len(excluded) == 0


def test_select_empty_returns_empty(selector: ContentSelector) -> None:
    selected, excluded = selector.select([], max_bullets=5)
    assert selected == []
    assert excluded == []


# ── Section density rules ────────────────────────────────────────────────────

def test_current_role_capped_at_six(selector: ContentSelector) -> None:
    bullets = [_bullet(f"B{i}", experience_id="e1", is_current=True, score=1.0 - i * 0.01) for i in range(10)]
    selected, _ = selector.select(bullets, max_bullets=20)
    current_selected = [b for b in selected if b["experience_id"] == "e1"]
    assert len(current_selected) <= 6


def test_previous_role_capped_at_four(selector: ContentSelector) -> None:
    bullets = [_bullet(f"B{i}", experience_id="e2", is_current=False, score=1.0 - i * 0.01) for i in range(8)]
    selected, _ = selector.select(bullets, max_bullets=20)
    exp_selected = [b for b in selected if b["experience_id"] == "e2"]
    assert len(exp_selected) <= 4


def test_mix_current_and_previous_respects_caps(selector: ContentSelector) -> None:
    current = [_bullet(f"C{i}", experience_id="curr", is_current=True, score=0.9) for i in range(8)]
    previous = [_bullet(f"P{i}", experience_id="prev", is_current=False, score=0.8) for i in range(8)]
    selected, _ = selector.select(current + previous, max_bullets=20)
    curr_sel = [b for b in selected if b["experience_id"] == "curr"]
    prev_sel = [b for b in selected if b["experience_id"] == "prev"]
    assert len(curr_sel) <= 6
    assert len(prev_sel) <= 4


# ── Excluded bullets ─────────────────────────────────────────────────────────

def test_excluded_preserves_all_fields(selector: ContentSelector) -> None:
    bullets = [_bullet(f"B{i}", score=float(i)) for i in range(5)]
    _, excluded = selector.select(bullets, max_bullets=3)
    for b in excluded:
        assert "bullet_text" in b
        assert "evidence_id" in b


def test_excluded_bullets_are_not_in_selected(selector: ContentSelector) -> None:
    bullets = [_bullet(f"Bullet {i}", score=float(i)) for i in range(6)]
    selected, excluded = selector.select(bullets, max_bullets=3)
    selected_texts = {b["bullet_text"] for b in selected}
    for b in excluded:
        assert b["bullet_text"] not in selected_texts


def test_selection_plus_excluded_equals_total(selector: ContentSelector) -> None:
    bullets = [_bullet(f"B{i}", score=float(i)) for i in range(7)]
    selected, excluded = selector.select(bullets, max_bullets=4)
    assert len(selected) + len(excluded) == 7
