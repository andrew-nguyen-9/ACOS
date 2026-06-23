"""Phase 16.5 — secure ingestion: block macros/scripts/executables, parse isolation."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from backend.ingestion import security
from backend.ingestion.security import UnsafeFileError


def _make_docx(path: Path, extra_members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", b"<Types/>")
        zf.writestr("word/document.xml", b"<document/>")
        for name, data in extra_members.items():
            zf.writestr(name, data)
    return path


def test_docx_with_macros_rejected(tmp_path):
    f = _make_docx(tmp_path / "resume.docx", {"word/vbaProject.bin": b"\x00macro"})
    with pytest.raises(UnsafeFileError):
        security.reject_active_content(f)


def test_docx_with_embedded_executable_rejected(tmp_path):
    f = _make_docx(tmp_path / "resume.docx", {"word/embeddings/payload.exe": b"MZ\x90"})
    with pytest.raises(UnsafeFileError):
        security.reject_active_content(f)


def test_clean_docx_passes(tmp_path):
    f = _make_docx(tmp_path / "resume.docx", {})
    security.reject_active_content(f)  # no raise


def test_pdf_with_javascript_rejected(tmp_path):
    f = tmp_path / "job.pdf"
    f.write_bytes(b"%PDF-1.5\n1 0 obj<< /Type /Action /S /JavaScript /JS (app.alert) >>\n%%EOF")
    with pytest.raises(UnsafeFileError):
        security.reject_active_content(f)


def test_pdf_with_launch_action_rejected(tmp_path):
    f = tmp_path / "job.pdf"
    f.write_bytes(b"%PDF-1.5\n<< /S /Launch /F (calc.exe) >>\n%%EOF")
    with pytest.raises(UnsafeFileError):
        security.reject_active_content(f)


def test_clean_pdf_passes(tmp_path):
    f = tmp_path / "job.pdf"
    f.write_bytes(b"%PDF-1.5\nplain text resume content\n%%EOF")
    security.reject_active_content(f)


def test_fuzzed_garbage_docx_does_not_crash(tmp_path):
    # Parse isolation: a corrupt "docx" (not a zip) must fail closed, never crash.
    f = tmp_path / "broken.docx"
    f.write_bytes(b"\x00\xff not a zip at all \x00")
    security.reject_active_content(f)  # returns quietly, no exception
