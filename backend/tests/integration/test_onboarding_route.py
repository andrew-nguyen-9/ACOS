"""Phase 13.5 — onboarding cold-start summary (read-only surfacing)."""
from __future__ import annotations

from backend.repositories.document import DocumentRepository
from backend.repositories.resume import WritingProfileRepository
from backend.services.knowledge_graph.service import KnowledgeGraphService


def _seed_skill(session, name: str, confidence: str) -> None:
    kg = KnowledgeGraphService(session)
    kg.get_or_create_node("skill", name.lower(), name, {"confidence": confidence})


def _seed_complete_doc(session, filename: str) -> None:
    DocumentRepository(session).create(
        filename=filename,
        original_path=f"/tmp/{filename}",
        file_type="pdf",
        file_size_bytes=100,
        checksum_sha256=filename,  # unique-enough for the test
        source_type="other",
        ingestion_status="complete",
        metadata_json={},
    )


def test_summary_surfaces_skills_docs_and_synthetic_voice(client, test_session):
    _seed_skill(test_session, "Python", "strong_inference")
    _seed_skill(test_session, "SQL", "weak_inference")
    _seed_complete_doc(test_session, "resume.pdf")
    _seed_complete_doc(test_session, "experience.pdf")
    test_session.flush()

    resp = client.get("/api/v1/onboarding/summary")
    assert resp.status_code == 200
    data = resp.json()

    labels = {s["label"]: s["confidence"] for s in data["skills"]}
    assert labels == {"Python": "strong_inference", "SQL": "weak_inference"}
    assert data["documents"]["count"] == 2

    # No WritingProfile built → default template → must be flagged synthetic.
    assert data["career_voice"]["synthetic"] is True
    assert data["career_voice"]["tone_descriptors"]  # non-empty default


def test_summary_marks_real_voice_not_synthetic(client, test_session):
    WritingProfileRepository(test_session).create(
        tone_descriptors=["analytical"],
        structure_patterns=["p"],
        vocabulary_patterns={},
        sample_sentences=["s"],
        source_doc_ids=[],
    )
    test_session.flush()

    resp = client.get("/api/v1/onboarding/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["career_voice"]["synthetic"] is False
    assert data["career_voice"]["tone_descriptors"] == ["analytical"]


def test_summary_empty_db_is_skippable_state(client):
    """A user who uploads nothing still gets a valid, completable summary."""
    resp = client.get("/api/v1/onboarding/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["skills"] == []
    assert data["documents"]["count"] == 0
    assert data["career_voice"]["synthetic"] is True  # default voice, clearly labeled
