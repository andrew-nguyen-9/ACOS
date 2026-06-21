from __future__ import annotations

from backend.services.intelligence.index_preprocessor import IndexPreprocessor


def test_bullet_is_normalized_and_chunked() -> None:
    p = IndexPreprocessor()
    # compound bullet with an alias → normalized + split into chunks
    chunks = p.preprocess("Built ML models; shipped to production")
    assert len(chunks) == 2
    assert "machine learning" in chunks[0].lower()


def test_project_text_gets_skill_expansion() -> None:
    p = IndexPreprocessor()
    chunks = p.preprocess("Built a Tableau dashboard", is_project=True)
    assert any("[skills:" in c for c in chunks)


def test_non_project_not_expanded() -> None:
    p = IndexPreprocessor()
    chunks = p.preprocess("Built a Tableau dashboard", is_project=False)
    assert all("[skills:" not in c for c in chunks)


def test_empty_returns_empty() -> None:
    p = IndexPreprocessor()
    assert p.preprocess("") == []
