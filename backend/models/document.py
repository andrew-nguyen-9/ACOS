from __future__ import annotations

from sqlalchemy import String, Text, Integer, CheckConstraint, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, generate_uuid, utcnow


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "file_type IN ('pdf','docx','txt','md','json','github_repo')",
            name="ck_document_file_type",
        ),
        CheckConstraint(
            "source_type IN ('resume','cover_letter','job_description','github','claude_export','answer_bank','other')",
            name="ck_document_source_type",
        ),
        CheckConstraint(
            "ingestion_status IN ('pending','processing','complete','failed','skipped')",
            name="ck_document_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    ingestion_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
    processed_at: Mapped[str | None] = mapped_column(String(32), nullable=True)

    logs: Mapped[list[IngestionLog]] = relationship(
        "IngestionLog",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class IngestionLog(Base):
    __tablename__ = "ingestion_logs"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('parse','normalize','extract_entities','embed','link_graph')",
            name="ck_ingestion_stage",
        ),
        CheckConstraint(
            "status IN ('success','failure','skipped')",
            name="ck_ingestion_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)

    document: Mapped[Document] = relationship("Document", back_populates="logs")
