from __future__ import annotations

import yaml
from sqlalchemy.orm import Session

from backend.repositories.optimization import PromptVersionRepository
from backend.services.prompt_loader import PromptLoader


def _next_minor(version: str) -> str:
    """'1.0' -> '1.1', '1.9' -> '1.10', '2' -> '2.1'."""
    parts = version.split(".")
    if len(parts) == 1:
        return f"{parts[0]}.1"
    major, minor = parts[0], parts[1]
    return f"{major}.{int(minor) + 1}"


def _highest(versions: list) -> str | None:
    if not versions:
        return None
    def key(v):
        parts = v.version.split(".")
        return tuple(int(p) if p.isdigit() else 0 for p in parts)
    return max(versions, key=key).version


class PromptEvolver:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = PromptVersionRepository(session)
        self._loader = PromptLoader()

    def seed_from_disk(self, prompt_name: str):
        data = self._loader.load(prompt_name)
        version = str(data.get("version", "1.0"))
        existing = [v for v in self._repo.list_for_prompt(prompt_name) if v.version == version]
        if existing:
            return existing[0]
        content = yaml.safe_dump(
            {"version": version, "system": data["system"], "user_template": data["user_template"]},
            sort_keys=False,
        )
        has_active = self._repo.get_active(prompt_name) is not None
        v = self._repo.create(
            prompt_name=prompt_name, version=version,
            content_yaml=content, is_active=not has_active,
        )
        return v

    def create_variant(self, prompt_name: str, content_yaml: str, change_rationale: str):
        versions = self._repo.list_for_prompt(prompt_name)
        prior = _highest(versions)
        new_version = _next_minor(prior) if prior else "1.1"
        return self._repo.create(
            prompt_name=prompt_name, version=new_version,
            content_yaml=content_yaml, is_active=False,
            parent_version=prior, change_rationale=change_rationale,
        )

    def activate(self, version_id: str):
        return self._repo.activate(version_id)

    def get_active_content(self, prompt_name: str) -> str | None:
        active = self._repo.get_active(prompt_name)
        return active.content_yaml if active else None
