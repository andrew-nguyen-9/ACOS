import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String


def generate_uuid() -> str:
    return uuid.uuid4().hex


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[str] = mapped_column(
        String(32),
        default=utcnow,
    )
    updated_at: Mapped[str] = mapped_column(
        String(32),
        default=utcnow,
        onupdate=utcnow,
    )
