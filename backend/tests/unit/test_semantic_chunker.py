from __future__ import annotations

from backend.services.intelligence.semantic_chunker import SemanticChunker


def test_splits_compound_bullet_on_semicolons() -> None:
    c = SemanticChunker()
    chunks = c.chunk("Led the migration effort; achieved 40% latency cut; resulting in higher retention")
    assert len(chunks) == 3


def test_single_sentence_returns_one_chunk() -> None:
    c = SemanticChunker()
    text = "Built a data pipeline that reduced processing time by 30%"
    assert c.chunk(text) == [text]


def test_splits_on_sentence_boundary() -> None:
    c = SemanticChunker()
    chunks = c.chunk("Designed the system architecture. Mentored three junior engineers.")
    assert len(chunks) == 2


def test_empty_text_returns_empty() -> None:
    c = SemanticChunker()
    assert c.chunk("") == []
    assert c.chunk("   ") == []


def test_drops_trivial_fragments() -> None:
    # trailing tiny fragment below min length is discarded
    c = SemanticChunker(min_chunk_len=10)
    chunks = c.chunk("Led a cross-functional redesign initiative; ok")
    assert all(len(ch) >= 10 for ch in chunks)
    assert len(chunks) == 1


def test_chunks_are_stripped() -> None:
    c = SemanticChunker()
    chunks = c.chunk("  Led the team  ;  shipped the product on schedule  ")
    assert chunks == ["Led the team", "shipped the product on schedule"]
