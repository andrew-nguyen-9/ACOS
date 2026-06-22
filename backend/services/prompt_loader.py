from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _shape(data: dict, version: str) -> dict[str, Any]:
    return {
        "version": version,
        "system": data.get("system", ""),
        "user_template": data.get("user_template", ""),
    }


class PromptLoader:
    """Resolve prompt content.

    With a session, the prompt **registry** is authoritative: ``load(name)``
    returns the active deployed version, ``load(name, version=...)`` pins one.
    Prompts never deployed to the registry (and the no-session path used by
    existing callers) fall back to the on-disk ``prompts/<name>.yaml``.
    """

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def load(self, name: str, version: str | None = None) -> dict[str, Any]:
        if self._session is not None:
            # Imported lazily to keep module load light and avoid cycles.
            from backend.services.prompts.registry import PromptRegistry

            registry = PromptRegistry(self._session)
            row = registry.get(name, version) if version else registry.active(name)
            if row is not None:
                data = yaml.safe_load(row.content_yaml) or {}
                return _shape(data, row.version)

        path = _PROMPTS_DIR / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        with path.open() as f:
            data = yaml.safe_load(f) or {}
        return _shape(data, data.get("version", "1.0"))
