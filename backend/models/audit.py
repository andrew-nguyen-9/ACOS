"""Phase 16.3 (ADR-016) — tamper-evident audit log.

Append-only, hash-chained: each row stores ``prev_hash`` and
``row_hash = H(prev_hash ‖ canonical(row))``. Editing or deleting any past row
breaks the chain from that point — detectable by ``verify_chain`` (ADR-016 §1).
Honest scope: tamper-*evident*, not tamper-*proof* — the owner can still delete the
DB; we detect it, we don't prevent it.

Content-light (ADR-016 §2): only op type + digests/metadata, never prompt/response
bodies (privacy + size; respects ADR-015 — no decrypted plaintext in the log).
Tenant-scoped, so each profile has its own independent chain.
"""
from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, utcnow
from backend.models.tenant import TenantScopedMixin


class AuditLog(TenantScopedMixin, Base):
    __tablename__ = "audit_log"

    # Monotonic integer = chain order. Per-tenant chains (auto-scoped selects).
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    op_type: Mapped[str] = mapped_column(String(20), nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # JSON of digests + metadata (model, prompt_version, confidence). No bodies.
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)
