"""Maintenance advisor (Phase 11.4) — turns health/drift signals into suggestions.

Suggest-only. Each call reads the current drift report, embedding state, and an
optional externally-probed ``system_status`` dict, then maps signals to inert
``MaintenanceSuggestion`` rows (status ``suggested``) plus an audit entry. It
never executes anything — only ``MaintenanceExecutor.execute`` runs an action,
and only after explicit approval (CLAUDE.md global rule: no autonomous actions).

# ponytail: one suggestion per type per run, and we skip a type that already has
# an open (suggested/approved) row — keeps `generate` idempotent without a job queue.
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.maintenance import MaintenanceAudit, MaintenanceSuggestion
from backend.repositories.optimization import PromptVersionRepository
from backend.repositories.system_config import SystemConfigRepository
from backend.services import integrity
from backend.services.observability.drift import DriftDetector

_OPEN = ("suggested", "approved")
_DEGRADED_STATES = {"degraded", "down"}


class MaintenanceAdvisor:
    def __init__(self, session: Session) -> None:
        self._session = session

    def suggest(
        self,
        *,
        system_status: dict | None = None,
        embedding_model: str | None = None,
    ) -> list[MaintenanceSuggestion]:
        embedding_model = embedding_model or get_settings().embedding_model
        drift = {r["kind"]: r for r in DriftDetector(self._session).report()}
        emb_state = integrity.embedding_status(self._session, embedding_model)

        # Collect candidate (type, reason, payload) tuples, then dedup by type.
        candidates: list[tuple[str, str, dict]] = []

        if emb_state == "stale":
            candidates.append((
                "embedding_refresh",
                f"Configured embedding model differs from the embedded corpus "
                f"(state={emb_state}); re-embed to align.",
                {"only_changed": True},
            ))

        if self._drifting(drift, "retrieval_quality"):
            candidates.append((
                "reindex",
                "Retrieval quality has drifted beyond threshold; rebuild the RAG index.",
                {"only_changed": False},
            ))

        if self._drifting(drift, "embedding_drift"):
            candidates.append((
                "embedding_refresh",
                "Embedding space has drifted; re-embed changed documents.",
                {"only_changed": True},
            ))

        if self._drifting(drift, "prompt_perf"):
            target = self._rollback_target()
            if target is not None:
                name, to_version = target
                candidates.append((
                    "prompt_rollback",
                    f"Prompt performance drifted; roll '{name}' back to {to_version}.",
                    {"prompt_name": name, "to_version": to_version},
                ))

        if self._drifting(drift, "interview_conversion") or self._drifting(drift, "ats_score"):
            fallback = SystemConfigRepository(self._session).get_value("fallback_model")
            if fallback:
                candidates.append((
                    "model_switch",
                    "Outcome metrics drifted; switch the generation model to the "
                    f"configured fallback ({fallback}).",
                    {"to_model": fallback},
                ))

        if system_status and system_status.get("chroma") in _DEGRADED_STATES:
            candidates.append((
                "reindex",
                f"Chroma subsystem is {system_status['chroma']}; rebuild the RAG index.",
                {"only_changed": False},
            ))

        return self._persist(candidates)

    def _drifting(self, drift: dict, kind: str) -> bool:
        row = drift.get(kind)
        return bool(row and row.get("drifting"))

    def _rollback_target(self) -> tuple[str, str] | None:
        """An active prompt that has a parent version to roll back to."""
        repo = PromptVersionRepository(self._session)
        # ponytail: scan active versions directly — no separate "active prompts" index.
        active = self._session.scalars(
            select(repo.model).where(repo.model.is_active.is_(True))
        ).all()
        for version in active:
            if version.parent_version:
                return version.prompt_name, version.parent_version
        return None

    def _open_types(self) -> set[str]:
        rows = self._session.scalars(
            select(MaintenanceSuggestion.type).where(
                MaintenanceSuggestion.status.in_(_OPEN)
            )
        ).all()
        return set(rows)

    def _persist(self, candidates: list[tuple[str, str, dict]]) -> list[MaintenanceSuggestion]:
        skip = self._open_types()
        created: list[MaintenanceSuggestion] = []
        seen: set[str] = set()
        for type_, reason, payload in candidates:
            if type_ in skip or type_ in seen:
                continue
            seen.add(type_)
            row = MaintenanceSuggestion(
                type=type_, reason=reason, payload_json=json.dumps(payload)
            )
            self._session.add(row)
            self._session.flush()
            self._session.add(
                MaintenanceAudit(suggestion_id=row.id, event="suggested", actor="advisor")
            )
            self._session.flush()
            created.append(row)
        return created
