"""Prompt version registry (Phase 11.2).

Governs prompt versioning on top of the existing ``PromptVersion`` table:
immutable deployed artifacts, a single active version per name, and atomic
rollback. Content is never UPDATEd — every deploy INSERTs a new version, so a
deployed version's stored artifact can never change.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models.optimization import PromptVersion
from backend.repositories.optimization import PromptVersionRepository


class PromptImmutableError(Exception):
    """Raised on any attempt to overwrite an already-deployed version."""


class PromptRegistry:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = PromptVersionRepository(session)

    def deploy(
        self,
        name: str,
        content: str,
        *,
        version: str | None = None,
        rationale: str | None = None,
    ) -> PromptVersion:
        """Deploy `content` as the next version of `name` and make it active.

        Passing an explicit `version` that already exists raises — deployed
        artifacts are immutable.
        """
        existing = self._repo.list_for_prompt(name)
        if version is not None and any(v.version == version for v in existing):
            raise PromptImmutableError(
                f"{name} {version} already exists; deployed versions are immutable"
            )
        new_version = version or f"v{len(existing) + 1}"
        parent = existing[-1].version if existing else None
        row = self._repo.create(
            prompt_name=name,
            version=new_version,
            content_yaml=content,
            is_active=False,
            parent_version=parent,
            change_rationale=rationale,
        )
        self._repo.activate(row.id)
        return row

    def active(self, name: str) -> PromptVersion | None:
        return self._repo.get_active(name)

    def get(self, name: str, version: str) -> PromptVersion:
        for row in self._repo.list_for_prompt(name):
            if row.version == version:
                return row
        raise KeyError(f"{name} {version} not found")

    def rollback(self, name: str, to_version: str) -> PromptVersion:
        target = self.get(name, to_version)  # raises KeyError if unknown
        return self._repo.activate(target.id)

    def list_versions(self, name: str) -> list[str]:
        return [row.version for row in self._repo.list_for_prompt(name)]
