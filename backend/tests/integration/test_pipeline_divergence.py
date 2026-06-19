from __future__ import annotations

from unittest.mock import MagicMock
import pytest
from backend.ingestion.pipeline import IngestionPipeline
from backend.repositories.document import DocumentRepository
from backend.services.knowledge_graph.service import KnowledgeGraphService


@pytest.fixture
def real_kg(test_session):
    return KnowledgeGraphService(test_session)


@pytest.fixture
def mock_extractor():
    ext = MagicMock()
    ext.extract.return_value = {
        "skills": [],
        "experiences": [],
        "projects": [],
    }
    return ext


def test_indexer_failure_sets_status_failed(tmp_path, test_session, real_kg, mock_extractor):
    """If ChromaDB indexing fails, the document must be saved as status='failed',
    not left as 'processing' (the divergence bug from pipeline.py TODO)."""
    f = tmp_path / "resume.txt"
    f.write_text("Experienced Python developer.")

    indexer = MagicMock()
    indexer.index_document.side_effect = RuntimeError("ChromaDB connection failed")

    pipeline = IngestionPipeline(
        session=test_session,
        kg_service=real_kg,
        indexer=indexer,
        entity_extractor=mock_extractor,
        allowed_dirs=[str(tmp_path)],
    )

    with pytest.raises(RuntimeError, match="ChromaDB connection failed"):
        pipeline.ingest(str(f))

    doc_repo = DocumentRepository(test_session)
    docs = doc_repo.list()
    assert len(docs) == 1
    assert docs[0].ingestion_status == "failed"
