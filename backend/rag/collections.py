"""ChromaDB collection topology.

Phase 12.6: the 10 physical collections collapse into ONE — ``acos_documents`` —
partitioned by a ``doc_type`` metadata field. Fewer collections = less disk I/O
and a single HNSW index per query (``where={"doc_type": {"$in": [...]}}``) instead
of looping ten indexes.

``doc_type`` values are the *legacy collection names* (e.g. ``acos_experiences``)
so intent→partition maps and stored ``source`` semantics carry over unchanged; the
only thing that moved is the physical partitioning.
"""
from enum import Enum

# The single physical collection holding all RAG vectors.
DOCUMENTS = "acos_documents"


class CollectionName(str, Enum):
    """Legacy collection names — retained as ``doc_type`` metadata values."""

    EXPERIENCES = "acos_experiences"
    PROJECTS = "acos_projects"
    SKILLS = "acos_skills"
    RESUMES = "acos_resumes"
    COVER_LETTERS = "acos_cover_letters"
    QUESTIONS = "acos_questions"
    ANSWERS = "acos_answers"
    JOB_DESCRIPTIONS = "acos_job_descriptions"
    GITHUB = "acos_github"
    CLAUDE_EXPORTS = "acos_claude_exports"


# Default doc_type for generic ingested documents that predate per-type tagging
# (and the catch-all the migration backfills onto untagged acos_documents rows).
DEFAULT_DOC_TYPE = CollectionName.EXPERIENCES.value

# Legacy collections the one-time migration re-homes into DOCUMENTS.
LEGACY_COLLECTION_NAMES: list[str] = [c.value for c in CollectionName]

# Only one physical collection now; cosine/HNSW unchanged.
COLLECTION_CONFIGS: dict[str, dict] = {DOCUMENTS: {"hnsw:space": "cosine"}}

ALL_COLLECTION_NAMES: list[str] = [DOCUMENTS]
