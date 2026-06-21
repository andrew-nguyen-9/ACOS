import json
from unittest.mock import MagicMock

import pytest

from backend.services.intelligence.self_corrector import SelfCorrector
from backend.services.resume.generator import ResumeGenerator
from backend.tests.unit.test_resume_generator import (  # noqa: F401
    mock_evidence_selector, mock_kw_extractor, mock_ats_scorer, mock_loader,
)


def _ollama_with_duplicate_bullets() -> MagicMock:
    client = MagicMock()
    client.is_available.return_value = True
    client.generate.return_value = json.dumps({
        "experiences": [{
            "title": "Engineer", "company": "Acme", "dates": "2022–2024",
            "bullets": [
                {"text": "Built the data pipeline", "evidence_id": "b1", "confidence": "verified"},
                {"text": "Built the data pipeline", "evidence_id": "b2", "confidence": "verified"},
            ],
        }],
        "skills": ["Python"], "projects": [], "education": [],
    })
    return client


def test_self_correction_dedups_content_bullets(
    mock_evidence_selector, mock_kw_extractor, mock_ats_scorer, mock_loader, test_session
):
    gen = ResumeGenerator(
        mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
        _ollama_with_duplicate_bullets(), mock_loader, test_session,
        self_corrector=SelfCorrector(),
    )
    result = gen.generate("Python role", "software")

    bullets = result["content_json"]["experiences"][0]["bullets"]
    assert len(bullets) == 1  # duplicate removed


def test_no_corrector_keeps_duplicates(
    mock_evidence_selector, mock_kw_extractor, mock_ats_scorer, mock_loader, test_session
):
    gen = ResumeGenerator(
        mock_evidence_selector, mock_kw_extractor, mock_ats_scorer,
        _ollama_with_duplicate_bullets(), mock_loader, test_session,
    )
    result = gen.generate("Python role", "software")

    bullets = result["content_json"]["experiences"][0]["bullets"]
    assert len(bullets) == 2  # duplicates untouched without corrector
