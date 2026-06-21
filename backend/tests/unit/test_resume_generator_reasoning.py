import json
from unittest.mock import MagicMock

import pytest

from backend.services.resume.generator import ResumeGenerator


def _two_bullet_selector() -> MagicMock:
    sel = MagicMock()
    sel.select.return_value = [
        {
            "bullet_text": "Built Python ETL pipeline reducing time by 40%",
            "evidence_id": "b1", "experience_id": "exp1", "company": "Acme",
            "title": "Engineer", "dates": "2022–2024", "confidence": "verified",
        },
        {
            "bullet_text": "Possibly led a small team",
            "evidence_id": "w1", "experience_id": "exp1", "company": "Acme",
            "title": "Engineer", "dates": "2022–2024", "confidence": "weak_inference",
        },
    ]
    return sel


@pytest.fixture
def deps(mock_kw_extractor, mock_ats_scorer, mock_ollama, mock_loader):  # noqa: F811
    return mock_kw_extractor, mock_ats_scorer, mock_ollama, mock_loader


# Re-use fixtures from the sibling test module
from backend.tests.unit.test_resume_generator import (  # noqa: E402
    mock_kw_extractor, mock_ats_scorer, mock_ollama, mock_loader,
)


def test_reasoning_filters_weak_bullet(deps, test_session):
    kw, ats, ollama, loader = deps
    reasoning = MagicMock()
    reasoning.reason.return_value = {"recommended_evidence_ids": ["b1"], "confidence": 0.8}

    gen = ResumeGenerator(
        _two_bullet_selector(), kw, ats, ollama, loader, test_session,
        reasoning_engine=reasoning,
    )
    result = gen.generate("Python role", "software")

    reasoning.reason.assert_called_once()
    # weak bullet w1 dropped by reasoning → no approval needed
    assert result["weak_inference_count"] == 0
    assert result["requires_approval"] is False


def test_no_reasoning_keeps_weak_bullet(deps, test_session):
    kw, ats, ollama, loader = deps
    gen = ResumeGenerator(_two_bullet_selector(), kw, ats, ollama, loader, test_session)

    result = gen.generate("Python role", "software")

    # without reasoning, weak bullet survives → approval required
    assert result["requires_approval"] is True


def test_empty_recommendation_keeps_all(deps, test_session):
    kw, ats, ollama, loader = deps
    reasoning = MagicMock()
    reasoning.reason.return_value = {"recommended_evidence_ids": [], "confidence": 0.0}

    gen = ResumeGenerator(
        _two_bullet_selector(), kw, ats, ollama, loader, test_session,
        reasoning_engine=reasoning,
    )
    result = gen.generate("Python role", "software")

    # empty recommendation = "no opinion" → weak bullet kept
    assert result["requires_approval"] is True
