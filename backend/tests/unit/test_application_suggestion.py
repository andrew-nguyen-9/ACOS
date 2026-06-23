"""15.2 — per-application Apply/Skip/Tailor suggestion composed from existing engines.

Recommend-only (ADR-012): the suggestion is information; every section carries its
confidence + evidence (ADR-006), and Tailor-First is the safe default on anything
short of a high-fit match.
"""
from __future__ import annotations

from backend.services.strategy.application_suggestion import (
    ApplicationSuggestionEngine,
    _RECOMMENDATION,
)


def test_suggestion_composes_all_sections(test_session) -> None:
    engine = ApplicationSuggestionEngine(test_session)
    jd = (
        "Senior Data Analyst. Python and SQL required. Build ETL pipelines, "
        "maintain Tableau dashboards, define KPIs for executive stakeholders."
    )
    s = engine.suggest(jd)
    for key in (
        "recommendation",
        "reason",
        "fit_score",
        "confidence",
        "missing_critical_skills",
        "resume_template",
        "resume_reason",
        "cover_letter_tone",
        "cover_letter_tone_descriptor",
        "interview_probability",
        "interview_sample_size",
        "interview_confidence",
        "interview_category",
    ):
        assert key in s, f"missing suggestion section: {key}"
    assert s["recommendation"] in ("apply", "tailor", "skip")
    # Empty profile → low-fit, low-n → never asserted as verified, never "apply".
    assert s["confidence"] == "weak_inference"
    assert s["recommendation"] != "apply"


def test_tailor_first_is_default_below_high_fit() -> None:
    # Trap 2: moderate / bridgeable fit recommends Tailor, not Apply.
    assert _RECOMMENDATION["prioritize"] == "apply"
    assert _RECOMMENDATION["tailor"] == "tailor"
    assert _RECOMMENDATION["bridge"] == "tailor"
    assert _RECOMMENDATION["skip"] == "skip"
