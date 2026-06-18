import pytest
from backend.repositories.document import DocumentRepository
from backend.models.document import Document


@pytest.fixture
def repo(test_session):
    return DocumentRepository(test_session)


def _make_doc(**kwargs) -> dict:
    defaults = {
        "filename": "resume.pdf",
        "original_path": "/docs/resume.pdf",
        "file_type": "pdf",
        "file_size_bytes": 1024,
        "source_type": "resume",
    }
    return {**defaults, **kwargs}


def test_create_document(repo):
    doc = repo.create(**_make_doc())
    assert doc.id is not None
    assert doc.ingestion_status == "pending"


def test_get_by_checksum_finds_existing(repo):
    repo.create(**_make_doc(checksum_sha256="abc123"))
    found = repo.get_by_checksum("abc123")
    assert found is not None
    assert found.checksum_sha256 == "abc123"


def test_get_by_checksum_returns_none_for_missing(repo):
    assert repo.get_by_checksum("notfound") is None


def test_get_by_status_filters_correctly(repo):
    repo.create(**_make_doc(filename="a.pdf", ingestion_status="complete"))
    repo.create(**_make_doc(filename="b.pdf", ingestion_status="pending"))
    results = repo.get_by_status("complete")
    assert len(results) == 1
    assert results[0].filename == "a.pdf"


def test_add_log_creates_ingestion_log(repo, test_session):
    doc = repo.create(**_make_doc())
    log = repo.add_log(
        document_id=doc.id,
        stage="parse",
        status="success",
        message="Parsed 3 pages",
        duration_ms=45,
    )
    assert log.id is not None
    assert log.document_id == doc.id
    assert log.stage == "parse"
    assert log.duration_ms == 45


def test_delete_document(repo):
    doc = repo.create(**_make_doc())
    assert repo.delete(doc.id) is True
    assert repo.get(doc.id) is None
