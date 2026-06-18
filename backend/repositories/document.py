from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.document import Document, IngestionLog
from backend.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, session: Session) -> None:
        super().__init__(Document, session)

    def get_by_checksum(self, checksum: str) -> Document | None:
        return self.session.scalars(
            select(Document).where(Document.checksum_sha256 == checksum)
        ).first()

    def get_by_status(self, status: str) -> list[Document]:
        return list(
            self.session.scalars(
                select(Document).where(Document.ingestion_status == status)
            ).all()
        )

    def add_log(
        self,
        document_id: str,
        stage: str,
        status: str,
        message: str | None = None,
        duration_ms: int | None = None,
    ) -> IngestionLog:
        log = IngestionLog(
            document_id=document_id,
            stage=stage,
            status=status,
            message=message,
            duration_ms=duration_ms,
        )
        self.session.add(log)
        self.session.flush()
        self.session.refresh(log)
        return log
