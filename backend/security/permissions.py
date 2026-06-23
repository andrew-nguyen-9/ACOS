"""Phase 16.6 (ADR-018) — capability-manifest permission model.

Every service module declares a manifest: which tenant-scoped resources it may
touch (`data_access`), which operations it may invoke (`actions`), and its
`boundaries` (network/filesystem). Enforcement is **default-closed** — a call
outside the manifest raises and is audited (ADR-016). The manifest is the single
source of truth; there are no implicit grants.

Honest scope (ADR-018): this governs *trusted internal* modules — it formalizes the
`docs/07` boundary and is real + tested today. It is NOT a sandbox for untrusted
third-party code; that runtime engine stays deferred (v2). The schema is shaped so
that engine can attach later without a redesign.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class PermissionManifest:
    name: str
    data_access: frozenset[str] = field(default_factory=frozenset)
    actions: frozenset[str] = field(default_factory=frozenset)
    # Boundaries default to nothing — local-first, least-privilege (ADR-018 §1).
    boundaries: frozenset[str] = field(default_factory=frozenset)


class PermissionDenied(RuntimeError):
    """A module attempted an access outside its declared manifest (default-closed)."""


# Registry of the existing internal service modules' manifests. Adding a module
# here documents AND enforces its boundary. Least-privilege: list only what's used.
_REGISTRY: dict[str, PermissionManifest] = {
    "optimization": PermissionManifest(
        name="optimization",
        data_access=frozenset({"signals", "optimization_proposals", "generation_logs", "metrics"}),
        actions=frozenset({"optimization", "recommend"}),
    ),
    "flywheel": PermissionManifest(
        name="flywheel",
        data_access=frozenset({"signals", "global_patterns"}),
        actions=frozenset({"record_signal", "rollup"}),
    ),
    "rag": PermissionManifest(
        name="rag",
        data_access=frozenset({"documents", "experiences", "projects"}),
        actions=frozenset({"retrieval"}),
    ),
}


def register(manifest: PermissionManifest) -> None:
    _REGISTRY[manifest.name] = manifest


def get_manifest(name: str) -> Optional[PermissionManifest]:
    return _REGISTRY.get(name)


def _deny(module: str, what: str, session: Session | None) -> None:
    if session is not None:
        from backend.services import audit

        audit.safe_record(session, "permission", {
            "module": module, "denied": what, "reason": "outside manifest (default-closed)",
        })
    raise PermissionDenied(f"module {module!r} denied {what} — not in its capability manifest")


def require(
    module: str,
    *,
    resource: str | None = None,
    action: str | None = None,
    session: Session | None = None,
) -> None:
    """Enforce a module's manifest at an access boundary. Default-closed: an unknown
    module, or an unlisted resource/action, is denied (and audited)."""
    manifest = _REGISTRY.get(module)
    if manifest is None:
        _deny(module, "unregistered-module", session)
        return
    if resource is not None and resource not in manifest.data_access:
        _deny(module, f"data_access:{resource}", session)
    if action is not None and action not in manifest.actions:
        _deny(module, f"action:{action}", session)
