from __future__ import annotations

from backend.services.intelligence.project_skill_mapper import ProjectSkillMapper


def test_appends_detected_skills() -> None:
    m = ProjectSkillMapper()
    out = m.expand("Built a Tableau dashboard for supply chain metrics")
    assert "[skills:" in out
    assert "Tableau" in out


def test_no_skills_returns_unchanged() -> None:
    m = ProjectSkillMapper()
    text = "Organized the annual team offsite retreat"
    assert m.expand(text) == text


def test_detection_is_case_insensitive() -> None:
    m = ProjectSkillMapper()
    out = m.expand("wrote python scripts using fastapi")
    assert "Python" in out
    assert "FastAPI" in out


def test_skills_deduped_and_original_text_preserved() -> None:
    m = ProjectSkillMapper()
    text = "Used Python; refactored Python services"
    out = m.expand(text)
    assert out.startswith(text)
    # exactly one Python in the appended skill list (deduped)
    appended = out.split("[skills:")[1]
    assert appended.lower().count("python") == 1
