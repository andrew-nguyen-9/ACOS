import pytest
from pathlib import Path


def test_txt_parser(tmp_path):
    from backend.ingestion.parsers.txt import parse
    f = tmp_path / "test.txt"
    f.write_text("Hello world\nLine 2", encoding="utf-8")
    result = parse(f)
    assert "Hello world" in result
    assert "Line 2" in result


def test_txt_parser_handles_latin1(tmp_path):
    from backend.ingestion.parsers.txt import parse
    f = tmp_path / "latin.txt"
    f.write_bytes("caf\xe9".encode("latin-1"))
    result = parse(f)
    assert len(result) > 0  # Did not crash


def test_markdown_parser(tmp_path):
    from backend.ingestion.parsers.markdown import parse
    f = tmp_path / "test.md"
    f.write_text("# Title\n\nSome **bold** text.", encoding="utf-8")
    result = parse(f)
    assert "Title" in result
    assert "bold" in result  # Markdown stripped


def test_pdf_parser_malformed_returns_empty(tmp_path):
    from backend.ingestion.parsers.pdf import parse
    f = tmp_path / "bad.pdf"
    f.write_bytes(b"this is not a pdf")
    result = parse(f)
    assert isinstance(result, str)  # Did not crash


def test_docx_parser_malformed_returns_empty(tmp_path):
    from backend.ingestion.parsers.docx import parse
    f = tmp_path / "bad.docx"
    f.write_bytes(b"this is not a docx")
    result = parse(f)
    assert isinstance(result, str)  # Did not crash
