import pytest
import tempfile
import os

from backend.rag.chroma_client import ChromaManager
from backend.rag.collections import CollectionName, ALL_COLLECTION_NAMES


@pytest.fixture
def chroma(tmp_path):
    return ChromaManager(path=str(tmp_path / "chroma"))


def test_health_check_returns_true(chroma):
    assert chroma.health_check() is True


def test_init_all_collections_creates_all(chroma):
    chroma.init_all_collections()
    for name in ALL_COLLECTION_NAMES:
        col = chroma.get_or_create_collection(name)
        assert col is not None


def test_add_and_query(chroma):
    chroma.add(
        collection=CollectionName.EXPERIENCES,
        ids=["exp-001"],
        documents=["Built a Python ETL pipeline for data analytics."],
        embeddings=[[0.1] * 768],
        metadatas=[{"confidence_level": "verified", "company": "Secretariat"}],
    )
    results = chroma.query(
        collection=CollectionName.EXPERIENCES,
        query_embeddings=[[0.1] * 768],
        n_results=1,
    )
    assert results["ids"][0] == ["exp-001"]


def test_upsert_updates_existing(chroma):
    chroma.add(
        collection=CollectionName.EXPERIENCES,
        ids=["exp-001"],
        documents=["Original text"],
        embeddings=[[0.1] * 768],
        metadatas=[{"confidence_level": "verified"}],
    )
    chroma.upsert(
        collection=CollectionName.EXPERIENCES,
        ids=["exp-001"],
        documents=["Updated text"],
        embeddings=[[0.2] * 768],
        metadatas=[{"confidence_level": "strong_inference"}],
    )
    assert chroma.count(CollectionName.EXPERIENCES) == 1


def test_count_returns_correct_number(chroma):
    assert chroma.count(CollectionName.PROJECTS) == 0
    chroma.add(
        collection=CollectionName.PROJECTS,
        ids=["proj-001", "proj-002"],
        documents=["Project A", "Project B"],
        embeddings=[[0.1] * 768, [0.2] * 768],
        metadatas=[{"source": "github"}, {"source": "manual"}],
    )
    assert chroma.count(CollectionName.PROJECTS) == 2


def test_delete_removes_document(chroma):
    chroma.add(
        collection=CollectionName.SKILLS,
        ids=["skill-001"],
        documents=["Python programming"],
        embeddings=[[0.5] * 768],
        metadatas=[{"category": "programming"}],
    )
    chroma.delete(collection=CollectionName.SKILLS, ids=["skill-001"])
    assert chroma.count(CollectionName.SKILLS) == 0


def test_query_with_where_filter(chroma):
    chroma.add(
        collection=CollectionName.EXPERIENCES,
        ids=["exp-a", "exp-b"],
        documents=["Verified bullet", "Weak bullet"],
        embeddings=[[0.1] * 768, [0.9] * 768],
        metadatas=[
            {"confidence_level": "verified"},
            {"confidence_level": "weak_inference"},
        ],
    )
    results = chroma.query(
        collection=CollectionName.EXPERIENCES,
        query_embeddings=[[0.1] * 768],
        n_results=2,
        where={"confidence_level": "verified"},
    )
    assert "exp-a" in results["ids"][0]
    assert "exp-b" not in results["ids"][0]
