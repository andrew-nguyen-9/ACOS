from __future__ import annotations

import pytest
from backend.services.cover_letter.consistency_validator import ConsistencyValidator, ConsistencyResult


@pytest.fixture
def cv() -> ConsistencyValidator:
    return ConsistencyValidator()


def _context(companies: list[str] | None = None, years: list[str] | None = None) -> dict:
    bullets = []
    if companies is None:
        companies = ["Acme Corp"]
    for c in companies:
        bullets.append({"company": c, "dates": "2022–2024", "bullet_text": "Built API"})
    for yr in (years or []):
        bullets.append({"company": "OtherCo", "dates": yr, "bullet_text": "Led team"})
    return {"selected_bullets": bullets}


# ── Return type ──────────────────────────────────────────────────────────────

def test_returns_consistency_result(cv: ConsistencyValidator) -> None:
    result = cv.validate("Dear Hiring Manager, I worked at Acme Corp.", _context())
    assert isinstance(result, ConsistencyResult)
    assert isinstance(result.warnings, list)
    assert isinstance(result.consistent, bool)


# ── Company reference check ──────────────────────────────────────────────────

def test_no_warning_when_company_referenced(cv: ConsistencyValidator) -> None:
    text = "I am excited to join Acme Corp and contribute to the mission."
    result = cv.validate(text, _context(companies=["Acme Corp"]))
    company_warns = [w for w in result.warnings if "company" in w.lower()]
    assert not company_warns


def test_warning_when_no_resume_company_referenced(cv: ConsistencyValidator) -> None:
    text = "I am excited about this opportunity and have strong Python skills."
    result = cv.validate(text, _context(companies=["Acme Corp", "Beta Inc"]))
    assert any("company" in w.lower() or "reference" in w.lower() for w in result.warnings)


def test_empty_companies_no_company_warning(cv: ConsistencyValidator) -> None:
    result = cv.validate("Any text here.", _context(companies=[]))
    company_warns = [w for w in result.warnings if "company" in w.lower()]
    assert not company_warns


# ── Year consistency check ────────────────────────────────────────────────────

def test_no_warning_when_year_in_range(cv: ConsistencyValidator) -> None:
    text = "In 2023 I built a Python ETL pipeline at Acme Corp."
    result = cv.validate(text, _context(companies=["Acme Corp"], years=["2022–2024"]))
    year_warns = [w for w in result.warnings if "year" in w.lower() or "date" in w.lower()]
    assert not year_warns


def test_warning_when_year_outside_range(cv: ConsistencyValidator) -> None:
    text = "In 2010 I built a Python ETL pipeline at Acme Corp."
    result = cv.validate(text, _context(companies=["Acme Corp"], years=["2022–2024"]))
    assert any("year" in w.lower() or "2010" in w or "date" in w.lower() for w in result.warnings)


# ── Consistency flag ─────────────────────────────────────────────────────────

def test_consistent_when_no_warnings(cv: ConsistencyValidator) -> None:
    text = "I worked at Acme Corp in 2023 building ETL pipelines."
    result = cv.validate(text, _context(companies=["Acme Corp"], years=["2022–2024"]))
    assert result.consistent


def test_empty_context_no_warnings(cv: ConsistencyValidator) -> None:
    result = cv.validate("Any text.", {"selected_bullets": []})
    assert result.consistent
