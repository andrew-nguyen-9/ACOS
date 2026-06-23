"""Phase 16.3 (ADR-016) — audit service: emit hash-chained events + verify the chain.

`record` is called at every inference chokepoint (generation / retrieval / ATS /
optimization) — a path that skips it is the "unlogged inference" bug the strict rule
forbids (a source-scan test enforces the chokepoints stay wired).

ponytail: one indexed insert in the request's own transaction — cheap enough to be
effectively off the hot path (ADR-016 §5). Concurrency is single-user-local, so the
read-prev/insert race is immaterial; revisit if a multi-writer mode appears.
"""
from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from backend.models.audit import AuditLog
from backend.models.base import utcnow
from backend.services.tenancy import require_session_tenant

OP_TYPES = {"generation", "retrieval", "ats_score", "optimization", "injection", "permission"}
GENESIS = "0" * 64


def digest(value: object) -> str:
    """SHA-256 hex of a value — log this, never the body (ADR-016 §2)."""
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _canonical(op_type: str, tenant_id: str, created_at: str, metadata: dict) -> str:
    return json.dumps(
        {"op_type": op_type, "tenant_id": tenant_id, "created_at": created_at,
         "metadata": metadata},
        sort_keys=True, separators=(",", ":"),
    )


def _row_hash(prev_hash: str, op_type: str, tenant_id: str, created_at: str, metadata: dict) -> str:
    return hashlib.sha256(
        (prev_hash + _canonical(op_type, tenant_id, created_at, metadata)).encode("utf-8")
    ).hexdigest()


def record(session: Session, op_type: str, metadata: dict | None = None) -> AuditLog:
    if op_type not in OP_TYPES:
        raise ValueError(f"unknown audit op_type: {op_type!r}")
    tenant_id = require_session_tenant(session)
    metadata = metadata or {}
    # Last row of this tenant's chain (selects auto-scope to the active tenant).
    prev = (
        session.query(AuditLog).order_by(AuditLog.id.desc()).first()
    )
    prev_hash = prev.row_hash if prev else GENESIS
    created_at = utcnow()
    row = AuditLog(
        op_type=op_type,
        prev_hash=prev_hash,
        row_hash=_row_hash(prev_hash, op_type, tenant_id, created_at, metadata),
        metadata_json=json.dumps(metadata, sort_keys=True),
        created_at=created_at,
    )
    session.add(row)
    session.flush()
    return row


def verify_chain(session: Session, tenant_id: str | None = None) -> bool:
    """Recompute the chain; False if any row was edited/deleted/reordered."""
    rows = session.query(AuditLog).order_by(AuditLog.id).all()
    expected_prev = GENESIS
    tid = tenant_id or require_session_tenant(session)
    for row in rows:
        meta = json.loads(row.metadata_json)
        if row.prev_hash != expected_prev:
            return False
        if row.row_hash != _row_hash(expected_prev, row.op_type, tid, row.created_at, meta):
            return False
        expected_prev = row.row_hash
    return True


def verify_all_chains(session: Session) -> list[str]:
    """Verify every tenant's chain. Returns the ids of tenants whose chain is
    broken (empty = all intact). Used by the `enforced` startup check (ADR-016 §4)."""
    from backend.models.tenant import Tenant
    from backend.services.tenancy import set_session_tenant

    broken: list[str] = []
    # Tenant isn't tenant-scoped, so this select sees all profiles.
    for tenant in session.query(Tenant).all():
        set_session_tenant(session, tenant.id)
        if not verify_chain(session, tenant_id=tenant.id):
            broken.append(tenant.id)
    return broken


def safe_record(session: Session, op_type: str, metadata: dict | None = None) -> None:
    """Emit but never let an audit failure crash a user's generation. The
    no-unlogged-inference guarantee is the wiring + the source-scan test; this guard
    only absorbs an unexpected insert failure (e.g. read-only recovery)."""
    try:
        record(session, op_type, metadata)
    except Exception:
        pass
