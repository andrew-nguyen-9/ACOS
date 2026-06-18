from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def real_kg(test_session):
    from backend.services.knowledge_graph.service import KnowledgeGraphService

    return KnowledgeGraphService(test_session)


@pytest.fixture
def mock_indexer():
    idx = MagicMock()
    return idx


@pytest.fixture
def mock_extractor():
    ext = MagicMock()
    ext.extract.return_value = {
        "skills": [{"name": "Python", "confidence": "strong_inference"}],
        "experiences": [],
        "projects": [],
    }
    return ext


def test_ingest_txt_file(tmp_path, test_session, real_kg, mock_indexer, mock_extractor):
    from backend.ingestion.pipeline import IngestionPipeline

    f = tmp_path / "resume.txt"
    f.write_text("Experienced Python developer with SQL expertise.")

    pipeline = IngestionPipeline(
        session=test_session,
        kg_service=real_kg,
        indexer=mock_indexer,
        entity_extractor=mock_extractor,
        allowed_dirs=[str(tmp_path)],
    )
    doc_id = pipeline.ingest(str(f))

    assert doc_id is not None
    mock_indexer.index_document.assert_called_once()


def test_ingest_duplicate_returns_same_id(
    tmp_path, test_session, real_kg, mock_indexer, mock_extractor
):
    from backend.ingestion.pipeline import IngestionPipeline

    f = tmp_path / "resume.txt"
    f.write_text("Unique text for dedup test.")

    pipeline = IngestionPipeline(
        session=test_session,
        kg_service=real_kg,
        indexer=mock_indexer,
        entity_extractor=mock_extractor,
        allowed_dirs=[str(tmp_path)],
    )
    id1 = pipeline.ingest(str(f))
    id2 = pipeline.ingest(str(f))

    assert id1 == id2
    # Indexer called only once — second ingest hits duplicate path
    assert mock_indexer.index_document.call_count == 1
