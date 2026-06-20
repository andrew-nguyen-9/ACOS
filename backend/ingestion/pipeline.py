from __future__ import annotations

import importlib
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from backend.ingestion import security
from backend.ingestion.entity_extractor import EntityExtractor
from backend.ingestion.normalizer import normalize
from backend.models.document import Document
from backend.rag.indexer import RAGIndexer
from backend.repositories.document import DocumentRepository
from backend.services.knowledge_graph.service import KnowledgeGraphService

logger = logging.getLogger(__name__)

_PARSER_MAP: dict[str, str] = {
    ".txt": "backend.ingestion.parsers.txt",
    ".md": "backend.ingestion.parsers.markdown",
    ".markdown": "backend.ingestion.parsers.markdown",
    ".pdf": "backend.ingestion.parsers.pdf",
    ".docx": "backend.ingestion.parsers.docx",
}

# Map file suffix → file_type enum value (per Document CHECK constraint)
_FILE_TYPE_MAP: dict[str, str] = {
    ".txt": "txt",
    ".md": "md",
    ".markdown": "md",
    ".pdf": "pdf",
    ".docx": "docx",
}

_DEFAULT_ALLOWED = ["./static_files", "./.static_files", "./uploads"]


class IngestionPipeline:
    def __init__(
        self,
        session: Session,
        kg_service: KnowledgeGraphService,
        indexer: RAGIndexer,
        entity_extractor: EntityExtractor,
        allowed_dirs: list[str] | None = None,
    ) -> None:
        self._session = session
        self._kg = kg_service
        self._indexer = indexer
        self._extractor = entity_extractor
        self._doc_repo = DocumentRepository(session)
        self._allowed = allowed_dirs or _DEFAULT_ALLOWED

    def ingest(self, path: str) -> str:
        """Ingest a document at *path* and return its document ID.

        If a document with the same SHA-256 checksum already exists, returns
        the existing document's ID without re-processing.
        """
        validated = security.validate_path(path, self._allowed)
        security.validate_size(validated)
        checksum = security.compute_checksum(validated)

        existing = self._doc_repo.get_by_checksum(checksum)
        if existing:
            logger.info(
                "pipeline: duplicate document '%s' (id=%s)", path, existing.id
            )
            return existing.id

        suffix = validated.suffix.lower()
        module_name = _PARSER_MAP.get(suffix)
        if not module_name:
            raise ValueError(f"Unsupported file type: {suffix!r}")

        module = importlib.import_module(module_name)
        raw_text = module.parse(validated)
        text = normalize(raw_text)

        file_type = _FILE_TYPE_MAP[suffix]
        file_size = validated.stat().st_size

        doc = self._doc_repo.create(
            filename=validated.name,
            original_path=str(validated),
            file_type=file_type,
            file_size_bytes=file_size,
            checksum_sha256=checksum,
            source_type="other",
            ingestion_status="processing",
            metadata_json={"raw_text": text},
        )

        entities = self._extractor.extract(text, suffix.lstrip("."))
        self._store_entities(doc, entities)

        collection = (
            "acos_resumes"
            if "resume" in validated.name.lower()
            else "acos_experiences"
        )
        try:
            self._indexer.index_document(
                collection,
                doc.id,
                text[:2000],
                {
                    "document_id": doc.id,
                    "source_type": doc.source_type,
                    "confidence_level": "strong_inference",
                },
            )
        except Exception:
            logger.exception(
                "pipeline: ChromaDB indexing failed for doc '%s'; marking status=failed",
                doc.id,
            )
            doc.ingestion_status = "failed"
            self._session.flush()
            raise

        doc.ingestion_status = "complete"
        self._session.flush()
        return doc.id

    def _store_entities(self, doc: Document, entities: dict) -> None:
        doc_node = self._kg.get_or_create_node(
            "document", doc.id, doc.filename, {}
        )
        for skill in entities.get("skills", []):
            skill_node = self._kg.get_or_create_node(
                "skill",
                skill["name"].lower(),
                skill["name"],
                {"confidence": skill.get("confidence", "weak_inference")},
            )
            self._kg.add_edge(doc_node.id, skill_node.id, "evidenced_by")
