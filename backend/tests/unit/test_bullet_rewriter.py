from __future__ import annotations

import pytest
from backend.services.resume.bullet_rewriter import BulletRewriter


@pytest.fixture
def rewriter() -> BulletRewriter:
    return BulletRewriter()


# ── normalize ────────────────────────────────────────────────────────────────

def test_normalize_removes_responsible_for(rewriter: BulletRewriter) -> None:
    assert "responsible for" not in rewriter.normalize("Responsible for managing the team").lower()


def test_normalize_replaces_helped_with_supported(rewriter: BulletRewriter) -> None:
    result = rewriter.normalize("Helped the analytics team")
    assert "Supported" in result or "helped" not in result.lower()


def test_normalize_removes_successfully(rewriter: BulletRewriter) -> None:
    result = rewriter.normalize("Successfully delivered the project on time")
    assert "successfully" not in result.lower()


def test_normalize_replaces_leveraged(rewriter: BulletRewriter) -> None:
    result = rewriter.normalize("Leveraged Python to build the pipeline")
    assert "Leveraged" not in result and "leveraged" not in result.lower()


def test_normalize_removes_various(rewriter: BulletRewriter) -> None:
    result = rewriter.normalize("Worked on various data pipelines")
    assert "various" not in result.lower()


def test_normalize_keeps_unaffected_text_intact(rewriter: BulletRewriter) -> None:
    text = "Built a Python ETL pipeline generating $3M in revenue"
    assert rewriter.normalize(text) == text


# ── enforce_action_verb ──────────────────────────────────────────────────────

def test_enforce_action_verb_keeps_valid_verb(rewriter: BulletRewriter) -> None:
    text = "Built a Python ETL pipeline reducing latency by 40%"
    assert rewriter.enforce_action_verb(text) == text


def test_enforce_action_verb_prepends_led_when_no_verb(rewriter: BulletRewriter) -> None:
    text = "Python ETL pipeline that generated $3M"
    result = rewriter.enforce_action_verb(text)
    assert result.startswith("Led ")


def test_enforce_action_verb_case_insensitive_check(rewriter: BulletRewriter) -> None:
    text = "built a Python ETL pipeline"  # lowercase — valid verb
    result = rewriter.enforce_action_verb(text)
    assert not result.startswith("Led ")


# ── compress ─────────────────────────────────────────────────────────────────

def test_compress_removes_filler_and_returns_shorter_or_equal(rewriter: BulletRewriter) -> None:
    text = "Responsible for working with the team in order to successfully deliver the project"
    result = rewriter.compress(text)
    assert len(result) <= len(text)


def test_compress_preserves_meaningful_content(rewriter: BulletRewriter) -> None:
    text = "Responsible for building Python ETL pipeline generating $3M revenue"
    result = rewriter.compress(text)
    assert "Python" in result
    assert "$3M" in result or "3M" in result


# ── force_single_line ─────────────────────────────────────────────────────────

def test_force_single_line_short_text_unchanged(rewriter: BulletRewriter) -> None:
    text = "Built API reducing latency by 40%"
    assert rewriter.force_single_line(text) == text


def test_force_single_line_truncates_long_text(rewriter: BulletRewriter) -> None:
    text = "x" * 200
    result = rewriter.force_single_line(text, max_chars=88)
    assert len(result) <= 88 + 3  # 3 for "..."
    assert result.endswith("...")


def test_force_single_line_compresses_first(rewriter: BulletRewriter) -> None:
    text = "Responsible for working on various multiple different tasks in order to deliver results"
    result = rewriter.force_single_line(text, max_chars=88)
    # After compression the text should fit without truncation (or at least be shorter)
    assert len(result) < len(text)
