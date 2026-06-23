"""Phase 18.2 (ADR-020) — local feature flags + deterministic A/B.

No server (Q14): flags live in local config (system_config), and staged rollout /
A/B bucketing is a pure hash of (tenant_id ‖ flag_key) → a stable bucket in [0,1),
reproducible offline. A broken feature is killed by flipping its flag — rollback
without a rebuild. In-progress features default OFF.
"""
from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from backend.repositories.system_config import SystemConfigRepository

_FLAGS_KEY = "feature_flags"


def bucket(tenant_id: str, flag_key: str) -> float:
    """Deterministic [0,1) bucket — same (tenant, flag) → same value every run."""
    h = hashlib.sha256(f"{tenant_id}:{flag_key}".encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big") / 2**64


def _load(session: Session) -> dict:
    raw = SystemConfigRepository(session).get_value(_FLAGS_KEY)
    return json.loads(raw) if raw else {}


def set_flag(
    session: Session, key: str, *, enabled: bool | None = None, rollout: float | None = None
) -> None:
    flags = _load(session)
    entry = flags.get(key, {})
    if enabled is not None:
        entry["enabled"] = enabled
    if rollout is not None:
        entry["rollout"] = max(0.0, min(1.0, rollout))
    flags[key] = entry
    SystemConfigRepository(session).set_value(_FLAGS_KEY, json.dumps(flags))


def is_enabled(session: Session, key: str, tenant_id: str = "default") -> bool:
    """Default-off. An explicit ``enabled`` wins; otherwise a ``rollout`` fraction
    buckets the tenant deterministically. Unknown flag → off."""
    entry = _load(session).get(key)
    if not entry:
        return False
    if "enabled" in entry:
        return bool(entry["enabled"])
    rollout = entry.get("rollout")
    if rollout is None:
        return False
    return bucket(tenant_id, key) < rollout
