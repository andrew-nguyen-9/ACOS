from __future__ import annotations

import pytest
from backend.services.resume.bullet_quality import BulletQualityChecker, QualityViolation


@pytest.fixture
def checker() -> BulletQualityChecker:
    return BulletQualityChecker()


# ── PASSIVE_OPENER ────────────────────────────────────────────────────────────

def test_passive_opener_was_responsible_for(checker: BulletQualityChecker) -> None:
    v = checker.check("Was responsible for building the pipeline")
    codes = [x.code for x in v]
    assert "PASSIVE_OPENER" in codes


def test_passive_opener_was_tasked_with(checker: BulletQualityChecker) -> None:
    v = checker.check("Was tasked with managing the team")
    codes = [x.code for x in v]
    assert "PASSIVE_OPENER" in codes


def test_no_passive_opener_for_active_verb(checker: BulletQualityChecker) -> None:
    v = checker.check("Built a Python ETL pipeline generating $3M revenue")
    codes = [x.code for x in v]
    assert "PASSIVE_OPENER" not in codes


# ── HELPING_VERB ──────────────────────────────────────────────────────────────

def test_helping_verb_have(checker: BulletQualityChecker) -> None:
    v = checker.check("Have developed multiple analytics tools")
    codes = [x.code for x in v]
    assert "HELPING_VERB" in codes


def test_helping_verb_would(checker: BulletQualityChecker) -> None:
    v = checker.check("Would coordinate all data requests for clients")
    codes = [x.code for x in v]
    assert "HELPING_VERB" in codes


def test_no_helping_verb_mid_sentence(checker: BulletQualityChecker) -> None:
    v = checker.check("Built a tool that would normally take 10x longer")
    codes = [x.code for x in v]
    assert "HELPING_VERB" not in codes


# ── PRONOUN ───────────────────────────────────────────────────────────────────

def test_pronoun_I(checker: BulletQualityChecker) -> None:
    v = checker.check("I developed the analytics pipeline from scratch")
    codes = [x.code for x in v]
    assert "PRONOUN" in codes


def test_pronoun_my(checker: BulletQualityChecker) -> None:
    v = checker.check("Led my team through a complex data migration")
    codes = [x.code for x in v]
    assert "PRONOUN" in codes


def test_no_pronoun_third_party_their(checker: BulletQualityChecker) -> None:
    # "their" in "analyzed their records" — currently not flagged (correct)
    v = checker.check("Analyzed client transaction records to identify fraud")
    codes = [x.code for x in v]
    assert "PRONOUN" not in codes


# ── PASSIVE_VOICE (mid-sentence) ──────────────────────────────────────────────

def test_passive_voice_mid_sentence(checker: BulletQualityChecker) -> None:
    v = checker.check("Led a project where the data was processed nightly")
    codes = [x.code for x in v]
    assert "PASSIVE_VOICE" in codes


def test_no_passive_voice_active_sentence(checker: BulletQualityChecker) -> None:
    v = checker.check("Processed nightly data batches for 15+ clients")
    codes = [x.code for x in v]
    assert "PASSIVE_VOICE" not in codes


# ── WEAK_ADVERB ───────────────────────────────────────────────────────────────

def test_weak_adverb_effectively(checker: BulletQualityChecker) -> None:
    v = checker.check("Effectively managed a team of 5 analysts")
    codes = [x.code for x in v]
    assert "WEAK_ADVERB" in codes


def test_weak_adverb_successfully(checker: BulletQualityChecker) -> None:
    v = checker.check("Successfully delivered 30+ client engagements")
    codes = [x.code for x in v]
    assert "WEAK_ADVERB" in codes


def test_no_weak_adverb_in_clean_bullet(checker: BulletQualityChecker) -> None:
    v = checker.check("Delivered 30+ client engagements generating $3M revenue")
    codes = [x.code for x in v]
    assert "WEAK_ADVERB" not in codes


# ── NON_DESCRIPT ──────────────────────────────────────────────────────────────

def test_non_descript_worked_on(checker: BulletQualityChecker) -> None:
    v = checker.check("Led team that worked on ETL pipeline improvements")
    codes = [x.code for x in v]
    assert "NON_DESCRIPT" in codes


def test_non_descript_experience_with(checker: BulletQualityChecker) -> None:
    v = checker.check("Experience with Python and SQL for data analysis")
    codes = [x.code for x in v]
    assert "NON_DESCRIPT" in codes


# ── TOO_LONG ──────────────────────────────────────────────────────────────────

def test_too_long_over_176(checker: BulletQualityChecker) -> None:
    long = "Built " + "x" * 180
    v = checker.check(long)
    codes = [x.code for x in v]
    assert "TOO_LONG" in codes


def test_no_too_long_at_176(checker: BulletQualityChecker) -> None:
    exactly = "B" * 176
    v = checker.check(exactly)
    codes = [x.code for x in v]
    assert "TOO_LONG" not in codes


# ── NO_QUANTIFICATION ─────────────────────────────────────────────────────────

def test_no_quantification_suggestion(checker: BulletQualityChecker) -> None:
    v = checker.check("Developed analytics pipeline for client engagements")
    codes = [x.code for x in v]
    assert "NO_QUANTIFICATION" in codes


def test_quantified_bullet_no_suggestion(checker: BulletQualityChecker) -> None:
    v = checker.check("Developed analytics pipeline for 30+ client engagements")
    codes = [x.code for x in v]
    assert "NO_QUANTIFICATION" not in codes


# ── severity field ────────────────────────────────────────────────────────────

def test_passive_opener_is_error_severity(checker: BulletQualityChecker) -> None:
    v = checker.check("Was responsible for managing reporting workflows")
    passive = next(x for x in v if x.code == "PASSIVE_OPENER")
    assert passive.severity == "error"


def test_too_long_is_warning_severity(checker: BulletQualityChecker) -> None:
    v = checker.check("B" * 200)
    too_long = next(x for x in v if x.code == "TOO_LONG")
    assert too_long.severity == "warning"


def test_no_quantification_is_suggestion(checker: BulletQualityChecker) -> None:
    v = checker.check("Led analytics team building ETL pipeline")
    no_q = next(x for x in v if x.code == "NO_QUANTIFICATION")
    assert no_q.severity == "suggestion"


# ── summary ───────────────────────────────────────────────────────────────────

def test_summary_counts_violations(checker: BulletQualityChecker) -> None:
    bullets = [
        "I developed the pipeline from scratch",
        "Was responsible for managing reports",
        "Built ETL pipeline generating $3M revenue",
    ]
    counts = checker.summary(bullets)
    assert counts.get("PRONOUN", 0) >= 1
    assert counts.get("PASSIVE_OPENER", 0) >= 1


def test_clean_bullet_has_only_suggestion(checker: BulletQualityChecker) -> None:
    v = checker.check("Built Python ETL pipeline generating $3M across 150 client engagements")
    codes = [x.code for x in v]
    # Should have zero errors/warnings; only possible suggestion is VAGUE_JUDGMENT
    error_warning = [x for x in v if x.severity in ("error", "warning")]
    assert len(error_warning) == 0
