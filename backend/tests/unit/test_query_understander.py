from __future__ import annotations

import json

import pytest

from backend.services.intelligence.query_understander import QueryUnderstander


class _FakeOllama:
    """Stub Ollama client with controllable availability and response."""

    def __init__(self, available: bool = True, response: str = "") -> None:
        self._available = available
        self._response = response

    def is_available(self) -> bool:
        return self._available

    def generate(self, **kwargs: object) -> str:
        return self._response


class _FakeLoader:
    def load(self, name: str) -> dict:
        return {"system": "sys", "user_template": "JD: {job_description}"}


PM_JD = (
    "Senior Product Manager role. You will own the product roadmap, work cross-functionally "
    "with engineering and design, define KPIs, and drive stakeholder alignment. "
    "Required: SQL, A/B testing, roadmapping. Preferred: Python, machine learning."
)


@pytest.fixture
def loader() -> _FakeLoader:
    return _FakeLoader()


def test_llm_path_parses_structured_json(loader: _FakeLoader) -> None:
    response = json.dumps({
        "role_type": "product_management",
        "seniority": "senior",
        "required_skills": ["SQL", "A/B testing", "roadmapping"],
        "preferred_skills": ["Python", "machine learning"],
        "must_have_keywords": ["cross-functional", "stakeholder"],
    })
    ollama = _FakeOllama(available=True, response=response)
    qu = QueryUnderstander(ollama, loader)

    result = qu.understand(PM_JD)

    assert result["role_type"] == "product_management"
    assert result["seniority"] == "senior"
    assert "SQL" in result["required_skills"]


def test_llm_malformed_json_falls_back(loader: _FakeLoader) -> None:
    ollama = _FakeOllama(available=True, response="not json at all")
    qu = QueryUnderstander(ollama, loader)

    result = qu.understand(PM_JD)

    # Fallback still produces a usable structure
    assert "role_type" in result
    assert isinstance(result["required_skills"], list)


def test_fallback_used_when_ollama_unavailable(loader: _FakeLoader) -> None:
    ollama = _FakeOllama(available=False)
    qu = QueryUnderstander(ollama, loader)

    result = qu.understand(PM_JD)

    assert result["role_type"] == "product_management"


def test_fallback_classifies_consulting(loader: _FakeLoader) -> None:
    jd = "Management Consultant. Advise clients on strategy engagements and deliver client outcomes."
    qu = QueryUnderstander(_FakeOllama(available=False), loader)

    assert qu.understand(jd)["role_type"] == "consulting"


def test_fallback_keywords_are_non_hallucinatory(loader: _FakeLoader) -> None:
    """Every extracted keyword must appear in the source JD (no invention)."""
    qu = QueryUnderstander(_FakeOllama(available=False), loader)

    result = qu.understand(PM_JD)
    jd_lower = PM_JD.lower()

    for kw in result["required_skills"] + result["must_have_keywords"]:
        assert kw.lower() in jd_lower, f"hallucinated keyword: {kw}"


def test_fallback_detects_seniority(loader: _FakeLoader) -> None:
    qu = QueryUnderstander(_FakeOllama(available=False), loader)
    assert qu.understand(PM_JD)["seniority"] == "senior"

    junior_jd = "Junior Data Analyst. Entry-level role building dashboards in SQL and Tableau."
    assert qu.understand(junior_jd)["seniority"] == "junior"
