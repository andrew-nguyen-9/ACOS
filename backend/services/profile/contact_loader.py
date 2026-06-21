from __future__ import annotations

import re
from pathlib import Path

# Matches "- Key: value" bullet lines in contact.md
_LINE = re.compile(r"^-\s*([A-Za-z]+)\s*:\s*(.+?)\s*$")
# Pulls the parenthetical "(display: X)" form when present
_DISPLAY = re.compile(r"\(display:\s*(.+?)\s*\)")

_FIELDS = {"name", "location", "email", "phone", "linkedin", "github"}

# repo_root/.static_files/profile/contact.md  (this file is backend/services/profile/)
_DEFAULT_CONTACT_PATH = Path(__file__).parents[3] / ".static_files" / "profile" / "contact.md"


def default_contact_path() -> Path:
    return _DEFAULT_CONTACT_PATH


def load_contact(path: str | Path) -> dict:
    """Parse contact.md into a header dict for DOCX export.

    Returns keys: name, location, email, phone, linkedin, github.
    For link fields, prefers the human-readable "(display: ...)" form.
    Missing file → empty dict (export degrades gracefully).
    """
    p = Path(path)
    if not p.exists():
        return {}

    out: dict[str, str] = {}
    for line in p.read_text().splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        key, value = m.group(1).lower(), m.group(2)
        if key not in _FIELDS:
            continue
        display = _DISPLAY.search(value)
        out[key] = display.group(1) if display else value
    return out
