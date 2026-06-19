from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest
from backend.services.resume.generator import ResumeGenerator, _normalize_confidence


# ---------- _normalize_confidence ----------

def test_normalize_confidence_leaves_valid_unchanged():
    content = {
        "experiences": [
            {"bullets": [{"text": "did X", "confidence": "verified"}]}
        ]
    }
    result = _normalize_confidence(content)
    assert result["experiences"][0]["bullets"][0]["confidence"] == "verified"


def test_normalize_confidence_fixes_invalid():
    content = {
        "experiences": [
            {"bullets": [{"text": "did X", "confidence": "made_up"}]}
        ]
    }
    result = _normalize_confidence(content)
    assert result["experiences"][0]["bullets"][0]["confidence"] == "weak_inference"


def test_normalize_confidence_skips_non_dict_bullets():
    content = {"experiences": [{"bullets": ["plain string bullet"]}]}
    result = _normalize_confidence(content)
    assert result["experiences"][0]["bullets"][0] == "plain string bullet"


# ---------- _content_to_text ----------

@pytest.fixture
def base_generator(test_session):
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Built ETL pipeline", "evidence_id": "b1", "experience_id": "e1",
         "company": "Acme", "title": "SWE", "dates": "2022–2024", "confidence": "verified"}
    ]
    kw = MagicMock()
    kw.extract.return_value = {
        "required_skills": ["Python"], "keywords": ["ETL"], "industry": "tech",
        "seniority_level": "senior", "preferred_skills": [],
    }
    scorer = MagicMock()
    scorer.score.return_value = {
        "overall_score": 80, "keyword_score": 85, "skill_score": 80,
        "experience_score": 75, "industry_score": 85,
        "matched_keywords": ["Python"], "missing_keywords": [],
        "explanation": "Good match.",
    }
    ollama = MagicMock()
    ollama.is_available.return_value = True
    loader = MagicMock()
    loader.load.return_value = {
        "system": "Generate resume JSON",
        "user_template": (
            "JD: {job_description}\nTemplate: {template_name}\n"
            "Keywords: {keywords}\nEvidence: {evidence_json}\n"
            "Title: {job_title}\nCompany: {company}\nIndustry: {industry}"
        ),
    }
    return ResumeGenerator(sel, kw, scorer, ollama, loader, test_session)


def test_llm_build_success(base_generator):
    content = {
        "experiences": [
            {"title": "SWE", "company": "Acme", "dates": "2022–2024",
             "bullets": [{"text": "Built ETL", "evidence_id": "b1", "confidence": "verified"}]}
        ],
        "skills": ["Python"], "projects": [], "education": [],
    }
    base_generator._ollama.generate.return_value = json.dumps(content)
    result = base_generator.generate("Python engineer role", "software")
    assert result["ats_score"]["overall_score"] == 80
    assert result["weak_inference_count"] == 0
    assert result["requires_approval"] is False


def test_llm_build_json_decode_falls_back_to_rule_based(base_generator):
    base_generator._ollama.generate.return_value = "not valid json {{{"
    result = base_generator.generate("Python engineer role", "software")
    # Rule-based still builds a result from evidence
    assert "resume_id" in result
    assert len(result["content_json"]["experiences"]) == 1


def test_llm_build_exception_falls_back_to_rule_based(base_generator):
    base_generator._ollama.generate.side_effect = RuntimeError("model unavailable")
    result = base_generator.generate("Python engineer role", "software")
    assert "resume_id" in result


def test_generate_when_ollama_unavailable_uses_rule_based(test_session):
    sel = MagicMock()
    sel.select.return_value = [
        {"bullet_text": "Designed API", "evidence_id": "b2", "experience_id": "e2",
         "company": "Corp", "title": "Eng", "dates": "2020–2022", "confidence": "strong_inference"}
    ]
    kw = MagicMock()
    kw.extract.return_value = {
        "required_skills": [], "keywords": [], "industry": "finance",
        "seniority_level": "mid", "preferred_skills": [],
    }
    scorer = MagicMock()
    scorer.score.return_value = {
        "overall_score": 60, "keyword_score": 60, "skill_score": 60,
        "experience_score": 60, "industry_score": 60,
        "matched_keywords": [], "missing_keywords": [], "explanation": "",
    }
    ollama = MagicMock()
    ollama.is_available.return_value = False
    loader = MagicMock()
    gen = ResumeGenerator(sel, kw, scorer, ollama, loader, test_session)
    result = gen.generate("Finance role", "consulting")
    assert result["content_json"]["experiences"][0]["company"] == "Corp"


def test_content_to_text_handles_dict_and_string_bullets(base_generator):
    content = {
        "experiences": [
            {"title": "SWE", "company": "Acme", "dates": "2022–2024",
             "bullets": [
                 {"text": "Built ETL", "confidence": "verified"},
                 "plain string bullet",
             ]},
        ],
        "skills": ["Python", "SQL"],
    }
    text = base_generator._content_to_text(content)
    assert "Built ETL" in text
    assert "plain string bullet" in text
    assert "Python" in text


def test_rule_based_build_groups_by_experience(base_generator):
    evidence = [
        {"bullet_text": "Did A", "evidence_id": "b1", "experience_id": "e1",
         "company": "Acme", "title": "SWE", "dates": "2022–2024", "confidence": "verified"},
        {"bullet_text": "Did B", "evidence_id": "b2", "experience_id": "e1",
         "company": "Acme", "title": "SWE", "dates": "2022–2024", "confidence": "verified"},
        {"bullet_text": "Did C", "evidence_id": "b3", "experience_id": "e2",
         "company": "Corp", "title": "PM", "dates": "2020–2022", "confidence": "verified"},
    ]
    result = base_generator._rule_based_build("software", evidence)
    assert len(result["experiences"]) == 2
    e1_bullets = [e for e in result["experiences"] if e["company"] == "Acme"][0]["bullets"]
    assert len(e1_bullets) == 2


def test_generate_invalid_application_id_raises(base_generator):
    base_generator._ollama.generate.return_value = json.dumps({
        "experiences": [], "skills": [], "projects": [], "education": []
    })
    with pytest.raises(ValueError, match="Invalid application_id"):
        base_generator.generate("Python role", "software", application_id="nonexistent-uuid")
