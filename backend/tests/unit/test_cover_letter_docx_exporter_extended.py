from __future__ import annotations

import pytest
from backend.services.cover_letter.docx_exporter import CoverLetterDOCXExporter


def test_export_returns_bytes():
    exporter = CoverLetterDOCXExporter()
    result = exporter.export("Dear Hiring Manager,\n\nI am excited to apply.", "SWE", "Acme")
    assert isinstance(result, bytes)
    assert result[:2] == b"PK"


def test_export_empty_text_returns_bytes():
    exporter = CoverLetterDOCXExporter()
    result = exporter.export("", "Dev", "Corp")
    assert isinstance(result, bytes)


def test_export_multiline_text():
    exporter = CoverLetterDOCXExporter()
    text = "Line one.\n\nLine two.\n\nSincerely,"
    result = exporter.export(text, "PM", "StartupCo")
    assert isinstance(result, bytes)
    assert len(result) > 500  # sanity: non-trivial DOCX file


def test_export_never_raises_on_bad_input():
    exporter = CoverLetterDOCXExporter()
    # Force the outer try to fail by passing a non-str
    result = exporter.export(None, "x", "y")  # type: ignore[arg-type]
    # Should return b"" via double-fallback
    assert isinstance(result, bytes)
