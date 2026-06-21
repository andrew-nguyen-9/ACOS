from __future__ import annotations

import json
from backend.services.resume.resume_context import ResumeContext


def _sample_context() -> ResumeContext:
    return ResumeContext(
        resume_id="abc123",
        job_title="Software Engineer",
        company="Acme Corp",
        keywords=["Python", "ETL", "AWS"],
        selected_bullets=[
            {"bullet_text": "Built ETL pipeline reducing latency by 40%", "score": 0.85},
        ],
        excluded_bullets=[
            {"bullet_text": "Helped with documentation", "score": 0.2},
        ],
        selection_scores={"bullet_0": 0.85},
    )


def test_resume_context_constructs() -> None:
    ctx = _sample_context()
    assert ctx.resume_id == "abc123"
    assert ctx.job_title == "Software Engineer"
    assert ctx.company == "Acme Corp"
    assert len(ctx.keywords) == 3
    assert len(ctx.selected_bullets) == 1
    assert len(ctx.excluded_bullets) == 1


def test_resume_context_to_dict() -> None:
    ctx = _sample_context()
    d = ctx.to_dict()
    assert isinstance(d, dict)
    assert d["resume_id"] == "abc123"
    assert d["keywords"] == ["Python", "ETL", "AWS"]
    assert "selected_bullets" in d
    assert "excluded_bullets" in d


def test_resume_context_to_dict_is_json_serializable() -> None:
    ctx = _sample_context()
    json_str = json.dumps(ctx.to_dict())
    assert "ETL" in json_str


def test_resume_context_from_dict_roundtrip() -> None:
    ctx = _sample_context()
    d = ctx.to_dict()
    ctx2 = ResumeContext.from_dict(d)
    assert ctx2.resume_id == ctx.resume_id
    assert ctx2.keywords == ctx.keywords
    assert ctx2.selected_bullets == ctx.selected_bullets


def test_resume_context_defaults() -> None:
    ctx = ResumeContext(resume_id="id1", job_title="PM", company="Acme")
    assert ctx.keywords == []
    assert ctx.selected_bullets == []
    assert ctx.excluded_bullets == []
    assert ctx.selection_scores == {}
