"""Phase 14.1 — reproducibility guarantee.

The honest claim (CLAUDE.md #1): given the *whole tuple* — seed + inputs +
prompt-version + model — generation is reproducible. These tests pin all four:
inputs/prompt/model are fixed by the stubs, the seed is passed explicitly. LLM
byte-stability itself is Ollama-side (seed + low temp); here we prove the app
(a) threads the seed to the model boundary and (b) the surrounding pipeline adds
no nondeterminism, and that ATS scoring is reproducible for fixed input.
"""
from __future__ import annotations

import copy
import json
from unittest.mock import MagicMock

import pytest

from backend.services.ats.scorer import ATSScorer
from backend.services.ollama_client import Operation, build_options
from backend.services.resume.generator import ResumeGenerator

_LLM_CONTENT = json.dumps(
    {
        "experiences": [
            {
                "title": "Data Engineer",
                "company": "Acme Corp",
                "dates": "2022–2024",
                "bullets": [
                    {"text": "Built Python ETL pipeline", "evidence_id": "b1", "confidence": "verified"}
                ],
            }
        ],
        "skills": ["Python", "ETL"],
        "projects": [],
        "education": [],
    }
)


class _SeedRecordingOllama:
    """Deterministic LLM stub that records the seed kwarg it was called with."""

    def __init__(self) -> None:
        self.seen_seed: object = "UNSET"

    def is_available(self) -> bool:
        return True

    def generate(self, *args, seed=None, **kwargs) -> str:
        self.seen_seed = seed
        return _LLM_CONTENT


def _selector():
    sel = MagicMock()
    sel.select.return_value = [
        {
            "bullet_text": "Built Python ETL pipeline reducing processing time by 40%",
            "evidence_id": "b1",
            "experience_id": "exp1",
            "company": "Acme Corp",
            "title": "Data Engineer",
            "dates": "2022-01–2024-01",
            "confidence": "verified",
        }
    ]
    return sel


def _kw():
    ext = MagicMock()
    ext.extract.return_value = {
        "required_skills": ["Python", "ETL"],
        "preferred_skills": [],
        "keywords": ["data pipeline", "Python"],
        "industry": "technology",
        "seniority_level": "senior",
    }
    return ext


def _loader():
    loader = MagicMock()
    loader.load.return_value = {
        "version": "1.0",
        "system": "Generate resume",
        "user_template": "JD: {job_description}\nTemplate: {template_name}\nKeywords: {keywords}\nEvidence: {evidence_json}",
    }
    return loader


def _strip_volatile(content: dict) -> dict:
    """Remove storage-assigned ids — those are not generated *content*."""
    c = copy.deepcopy(content)
    ctx = c.get("_resume_context")
    if isinstance(ctx, dict):
        ctx.pop("resume_id", None)
    return c


def _make_gen(ollama, session):
    ats = MagicMock()
    ats.score.return_value = {"overall_score": 85, "explanation": "x"}
    return ResumeGenerator(_selector(), _kw(), ats, ollama, _loader(), session)


def test_build_options_threads_seed():
    assert build_options(Operation.RESUME, seed=1209)["seed"] == 1209
    # absent when unset — never silently injects a default seed
    assert "seed" not in build_options(Operation.RESUME)


def test_resume_generator_threads_seed_to_llm(test_session):
    ollama = _SeedRecordingOllama()
    gen = _make_gen(ollama, test_session)
    gen.generate("Python data engineering role at Acme", "software", seed=1209)
    # seed reaches both the content LLM and the ATS scorer — the whole tuple
    assert ollama.seen_seed == 1209
    assert gen._ats_scorer.score.call_args.kwargs["seed"] == 1209


def test_seeded_resume_generation_is_byte_stable(test_session):
    g1 = _make_gen(_SeedRecordingOllama(), test_session).generate(
        "Python data engineering role at Acme", "software",
        company="Acme", job_title="Data Engineer", seed=1209,
    )
    g2 = _make_gen(_SeedRecordingOllama(), test_session).generate(
        "Python data engineering role at Acme", "software",
        company="Acme", job_title="Data Engineer", seed=1209,
    )
    a = json.dumps(_strip_volatile(g1["content_json"]), sort_keys=True)
    b = json.dumps(_strip_volatile(g2["content_json"]), sort_keys=True)
    assert a == b


def test_ats_keyword_score_reproducible():
    """ATS keyword path is pure → identical score for fixed input, every run."""
    scorer = ATSScorer(ollama_client=None, prompt_loader=None)
    kw = {"required_skills": ["Python", "ETL"], "keywords": ["sql", "airflow"]}
    resume = "Built Python ETL pipelines with SQL and Airflow."
    r1 = scorer.score(resume, "jd", kw)
    r2 = scorer.score(resume, "jd", kw)
    assert r1 == r2
