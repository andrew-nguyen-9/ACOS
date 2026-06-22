"""Maintenance executor (Phase 11.4) — the single, approval-gated chokepoint.

Only ``execute`` runs a bound action, and only when status == 'approved'. Every
execution takes a snapshot *first* (an auto restore point) so the action is
reversible, then runs the action bound to the suggestion type and records an
audit entry with the result. If the pre-action snapshot fails, the action never
runs (fail-safe).

# ponytail: snapshotter + indexer are injected. Defaults build the real snapshot
# (filesystem-level, no chromadb import) and require the caller to pass an indexer
# for reindex/embedding_refresh (which need Chroma + an embedder).
"""
from __future__ import annotations

import json
from typing import Callable

from sqlalchemy.orm import Session

from backend.models.maintenance import MaintenanceAudit, MaintenanceSuggestion
from backend.repositories.system_config import SystemConfigRepository
from backend.services.prompts.registry import PromptRegistry


class NotApprovedError(Exception):
    """Raised when execute() is called on a suggestion that is not approved."""


class MaintenanceExecutor:
    def __init__(
        self,
        session: Session,
        *,
        snapshotter: Callable[[], str] | None = None,
        indexer=None,
    ) -> None:
        self._session = session
        self._snapshotter = snapshotter or self._default_snapshotter
        self._indexer = indexer

    # --- state transitions ------------------------------------------------
    def approve(self, suggestion_id: str) -> MaintenanceSuggestion:
        s = self._require(suggestion_id)
        if s.status != "suggested":
            raise ValueError(f"cannot approve suggestion in status {s.status!r}")
        s.status = "approved"
        self._flush_audit(s, "approved")
        return s

    def dismiss(self, suggestion_id: str) -> MaintenanceSuggestion:
        s = self._require(suggestion_id)
        s.status = "dismissed"
        self._flush_audit(s, "dismissed")
        return s

    def execute(self, suggestion_id: str) -> MaintenanceSuggestion:
        s = self._require(suggestion_id)
        if s.status != "approved":
            raise NotApprovedError(
                f"suggestion {suggestion_id} is {s.status!r}, not 'approved' — refusing to run"
            )

        # Snapshot FIRST. If this fails, the action must not run.
        try:
            s.snapshot_id = self._snapshotter()
        except Exception as exc:
            self._fail(s, f"pre-execute snapshot failed: {exc}")
            raise

        try:
            result = self._run_action(s)
        except Exception as exc:
            self._fail(s, f"action failed: {exc}")
            raise

        s.status = "executed"
        s.executed_at = _now()
        s.result_json = json.dumps(result)
        self._flush_audit(s, "executed", result)
        return s

    # --- bound actions ----------------------------------------------------
    def _run_action(self, s: MaintenanceSuggestion) -> dict:
        payload = json.loads(s.payload_json or "{}")
        if s.type in ("reindex", "embedding_refresh"):
            if self._indexer is None:
                raise RuntimeError(f"{s.type} requires an indexer")
            count = self._indexer.index_all(
                self._session, only_changed=bool(payload.get("only_changed", False))
            )
            return {"reembedded": count}
        if s.type == "prompt_rollback":
            row = PromptRegistry(self._session).rollback(
                payload["prompt_name"], payload["to_version"]
            )
            return {"active_version": row.version}
        if s.type == "model_switch":
            repo = SystemConfigRepository(self._session)
            previous = repo.get_value("default_model")
            repo.set_value("default_model", payload["to_model"])
            return {"default_model": payload["to_model"], "previous": previous}
        raise ValueError(f"unknown suggestion type: {s.type!r}")  # pragma: no cover

    # --- helpers ----------------------------------------------------------
    def _require(self, suggestion_id: str) -> MaintenanceSuggestion:
        s = self._session.get(MaintenanceSuggestion, suggestion_id)
        if s is None:
            raise ValueError(f"suggestion {suggestion_id} not found")
        return s

    def _fail(self, s: MaintenanceSuggestion, reason: str) -> None:
        s.status = "failed"
        s.result_json = json.dumps({"error": reason})
        self._flush_audit(s, "failed", {"error": reason})
        # Persist the failure record independently of the caller's request
        # transaction: execute() re-raises after this, and the request session
        # would otherwise roll back the audit trail, leaving the suggestion stuck
        # at 'approved' with no record of what failed.
        self._session.commit()

    def _flush_audit(self, s: MaintenanceSuggestion, event: str, detail: dict | None = None) -> None:
        self._session.add(
            MaintenanceAudit(
                suggestion_id=s.id,
                event=event,
                detail_json=json.dumps(detail) if detail is not None else None,
            )
        )
        self._session.flush()

    def _default_snapshotter(self) -> str:
        from pathlib import Path

        from backend.config import get_settings
        from backend.services.backup.snapshot import snapshot

        settings = get_settings()
        meta = snapshot(
            self._session,
            full=False,
            backups_dir=Path(settings.db_path).parent / "backups",
            db_path=settings.db_path,
            chroma_path=settings.chroma_db_path,
            app_version=settings.app_version,
        )
        return meta.id


def _now() -> str:
    from backend.models.base import utcnow

    return utcnow()
