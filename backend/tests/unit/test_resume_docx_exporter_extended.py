from __future__ import annotations

import pytest
from backend.services.resume.docx_exporter import ResumeDOCXExporter

_SAMPLE_CONTENT = {
    "experiences": [
        {
            "title": "SWE", "company": "Acme", "dates": "2022–2024",
            "bullets": [
                {"text": "Built ETL pipeline reducing costs by 40%", "confidence": "verified"},
                {"text": "Possibly managed a team of 3", "confidence": "weak_inference"},
                "Legacy string bullet",
            ],
        }
    ],
    "skills": ["Python", "SQL", "dbt"],
    "projects": [
        {"name": "ACOS", "description": "Career OS", "tech": "Python, React"},
    ],
    "education": [],
}


def test_export_returns_bytes():
    exporter = ResumeDOCXExporter()
    result = exporter.export(_SAMPLE_CONTENT, "software")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_export_returns_valid_docx_magic_bytes():
    exporter = ResumeDOCXExporter()
    result = exporter.export(_SAMPLE_CONTENT, "software")
    # DOCX is a ZIP file — starts with PK magic bytes
    assert result[:2] == b"PK"


def test_export_empty_content_still_returns_bytes():
    exporter = ResumeDOCXExporter()
    result = exporter.export({}, "software")
    assert isinstance(result, bytes)
    assert result[:2] == b"PK"


def test_export_with_weak_bullet_does_not_raise():
    exporter = ResumeDOCXExporter()
    content = {
        "experiences": [
            {"title": "Mgr", "company": "Co", "dates": "2020–2022",
             "bullets": [{"text": "Possibly led team", "confidence": "weak_inference"}]}
        ],
        "skills": [], "projects": [],
    }
    result = exporter.export(content, "consulting")
    assert isinstance(result, bytes)


def test_export_skills_section():
    exporter = ResumeDOCXExporter()
    result = exporter.export({"experiences": [], "skills": ["Python", "Go"], "projects": []}, "software")
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_export_projects_section():
    exporter = ResumeDOCXExporter()
    content = {
        "experiences": [],
        "skills": [],
        "projects": [{"name": "MyProj", "description": "Cool tool", "tech": "Rust"}],
    }
    result = exporter.export(content, "software")
    assert isinstance(result, bytes)


def test_export_handles_malformed_content_gracefully():
    exporter = ResumeDOCXExporter()
    # Pass a non-dict to trigger the except branch
    result = exporter.export(None, "software")  # type: ignore[arg-type]
    assert isinstance(result, bytes)
