"""Snapshot / regression tests.

These tests lock structural invariants of the core output schemas.  They use
the rule-based / template fallback paths (Ollama unavailable) so results are
deterministic and do not require a live LLM.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.services.ats.scorer import ATSScorer
from backend.services.prompt_loader import PromptLoader

# ── Prompt integrity ──────────────────────────────────────────────────────────

_PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "backend" / "prompts"

ALL_PROMPT_YAML = [
    "extract_entities",
    "copilot/chat",
    "resume/extract_keywords",
    "resume/generate",
    "resume/score_ats",
    "cover_letter/learn_voice",
    "cover_letter/generate",
    "questions/generate",
    "questions/answer",
]


@pytest.mark.parametrize("prompt_name", ALL_PROMPT_YAML)
def test_all_prompts_have_required_keys(prompt_name: str) -> None:
    """Every prompt YAML must contain version, system, and user_template."""
    loader = PromptLoader()
    data = loader.load(prompt_name)
    assert "version" in data, f"{prompt_name}: missing 'version'"
    assert "system" in data, f"{prompt_name}: missing 'system'"
    assert "user_template" in data, f"{prompt_name}: missing 'user_template'"


@pytest.mark.parametrize("prompt_name", ALL_PROMPT_YAML)
def test_all_prompts_have_non_empty_values(prompt_name: str) -> None:
    """No prompt field may be empty — catches accidental blank YAML values."""
    loader = PromptLoader()
    data = loader.load(prompt_name)
    for key in ("system", "user_template"):
        assert data[key] and data[key].strip(), (
            f"{prompt_name}: '{key}' is empty"
        )


# ── ATS keyword scoring stability ─────────────────────────────────────────────

_ATS_KEYWORDS: dict = {
    "keywords": ["Python", "SQL", "ETL", "data pipeline"],
    "required_skills": ["Python"],
}

_ATS_RESUME = "Experienced Python developer with SQL expertise and ETL data pipeline skills."

ATS_SCORE_KEYS = {
    "overall_score",
    "keyword_score",
    "skill_score",
    "experience_score",
    "industry_score",
    "matched_keywords",
    "missing_keywords",
    "explanation",
}


def _offline_scorer() -> ATSScorer:
    """Return an ATSScorer whose Ollama client reports unavailable."""
    ollama = MagicMock()
    ollama.is_available.return_value = False
    return ATSScorer(ollama_client=ollama, prompt_loader=MagicMock())


def test_ats_keyword_score_schema() -> None:
    """Keyword-fallback score always returns the expected key set."""
    scorer = _offline_scorer()
    result = scorer.score(_ATS_RESUME, "Python SQL ETL role", _ATS_KEYWORDS)
    assert set(result.keys()) >= ATS_SCORE_KEYS


def test_ats_keyword_score_range() -> None:
    """All numeric scores must be clamped to [0, 100]."""
    scorer = _offline_scorer()
    result = scorer.score(_ATS_RESUME, "Python SQL ETL role", _ATS_KEYWORDS)
    for key in ("overall_score", "keyword_score", "skill_score", "experience_score", "industry_score"):
        val = result[key]
        assert isinstance(val, int), f"{key} must be int, got {type(val)}"
        assert 0 <= val <= 100, f"{key}={val} out of range"


def test_ats_keyword_score_is_deterministic() -> None:
    """Same input must produce identical output on every call."""
    scorer = _offline_scorer()
    r1 = scorer.score(_ATS_RESUME, "Python SQL ETL role", _ATS_KEYWORDS)
    r2 = scorer.score(_ATS_RESUME, "Python SQL ETL role", _ATS_KEYWORDS)
    assert r1 == r2


def test_ats_keyword_score_all_match() -> None:
    """Resume containing all keywords yields overall_score of 100."""
    scorer = _offline_scorer()
    keywords = {"keywords": ["python", "sql"], "required_skills": []}
    result = scorer.score("python sql", "role", keywords)
    assert result["overall_score"] == 100
    assert len(result["missing_keywords"]) == 0


def test_ats_keyword_score_no_match() -> None:
    """Resume missing all keywords yields overall_score of 0."""
    scorer = _offline_scorer()
    keywords = {"keywords": ["cobol", "fortran"], "required_skills": []}
    result = scorer.score("python java", "role", keywords)
    assert result["overall_score"] == 0
    assert len(result["matched_keywords"]) == 0


# ── Cover letter template fallback structure ───────────────────────────────────

def test_cover_letter_template_fallback_schema() -> None:
    """Template fallback (Ollama offline) returns the correct key set."""
    from backend.services.cover_letter.generator import CoverLetterGenerator

    ollama = MagicMock()
    ollama.is_available.return_value = False

    selector = MagicMock()
    selector.select.return_value = [
        {"text": "Built Python ETL pipeline", "confidence": "verified"},
    ]

    voice = MagicMock()
    voice.get_or_create_default.return_value = {"writing_style": "professional"}

    gen = CoverLetterGenerator(
        evidence_selector=selector,
        voice_modeler=voice,
        ollama_client=ollama,
        prompt_loader=MagicMock(),
    )
    result = gen.generate(
        job_description="Python data engineer role",
        company="Acme Corp",
        job_title="Data Engineer",
        length_target="short",
    )

    assert set(result.keys()) >= {"text", "word_count", "length_target", "requires_approval"}
    assert isinstance(result["text"], str) and result["text"]
    assert result["length_target"] == "short"
    assert isinstance(result["word_count"], int) and result["word_count"] > 0


def test_cover_letter_invalid_length_target_raises() -> None:
    """Invalid length_target raises ValueError before any I/O."""
    from backend.services.cover_letter.generator import CoverLetterGenerator

    gen = CoverLetterGenerator(
        evidence_selector=MagicMock(),
        voice_modeler=MagicMock(),
        ollama_client=MagicMock(),
        prompt_loader=MagicMock(),
    )
    with pytest.raises(ValueError, match="Invalid length_target"):
        gen.generate("jd", "Acme", "Engineer", length_target="HUGE")
