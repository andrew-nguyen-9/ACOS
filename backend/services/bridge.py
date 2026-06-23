"""Phase 17.1 (ADR-019) — browser-extension ↔ backend pairing bridge.

One-time token pairing: the app (authenticated) generates a pairing token shown in
the wizard; the user pastes it into the extension once; the extension presents it on
every request. Unpaired requests are rejected (default-closed). The bridge is
app-gated by nature — the sidecar only runs while the Tauri app does (ADR-019 §2).

ponytail: a single active pairing stored in system_config (global key) — single-user
desktop app, so no table/per-extension registry. Re-pairing overwrites; unpair
clears. Bind a real table if multi-extension pairing ever matters.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets

from sqlalchemy.orm import Session

from backend.repositories.system_config import SystemConfigRepository

_PAIRING_KEY = "bridge_pairing"


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_pairing(session: Session, tenant_id: str) -> str:
    """Mint a pairing token bound to a tenant; store only its digest. Returns the
    raw token (shown once in the app)."""
    token = secrets.token_urlsafe(24)
    SystemConfigRepository(session).set_value(
        _PAIRING_KEY, json.dumps({"hash": _digest(token), "tenant_id": tenant_id})
    )
    return token


def resolve_pairing(session: Session, token: str | None) -> str | None:
    """Return the bound tenant for a valid pairing token, else None (default-closed)."""
    if not token:
        return None
    raw = SystemConfigRepository(session).get_value(_PAIRING_KEY)
    if not raw:
        return None
    data = json.loads(raw)
    if hmac.compare_digest(_digest(token), data.get("hash", "")):
        return data.get("tenant_id")
    return None


def is_paired(session: Session) -> bool:
    return bool(SystemConfigRepository(session).get_value(_PAIRING_KEY))


def unpair(session: Session) -> None:
    SystemConfigRepository(session).set_value(_PAIRING_KEY, "")
