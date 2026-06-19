from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class PromptLoader:
    def load(self, name: str) -> dict[str, Any]:
        path = _PROMPTS_DIR / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        with path.open() as f:
            data = yaml.safe_load(f)
        return {
            "version": data.get("version", "1.0"),
            "system": data.get("system", ""),
            "user_template": data.get("user_template", ""),
        }
