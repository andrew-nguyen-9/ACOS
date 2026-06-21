from __future__ import annotations

from pathlib import Path

from backend.services.profile.contact_loader import load_contact

_SAMPLE = """# Contact & Links

- Name: Andrew Nguyen
- Location: Chicago, IL 60611
- Email: andrew.nguyen.9@icloud.com
- Phone: (281) 787-9811
- LinkedIn: https://www.linkedin.com/in/andrew-t-nguyen/  (display: linkedin.com/in/andrew-t-nguyen)
- GitHub: https://github.com/andrew-nguyen-9  (display: github.com/andrew-nguyen-9)
"""


def _write(tmp_path: Path) -> Path:
    p = tmp_path / "contact.md"
    p.write_text(_SAMPLE)
    return p


def test_parses_core_fields(tmp_path: Path) -> None:
    c = load_contact(_write(tmp_path))
    assert c["name"] == "Andrew Nguyen"
    assert c["location"] == "Chicago, IL 60611"
    assert c["email"] == "andrew.nguyen.9@icloud.com"
    assert c["phone"] == "(281) 787-9811"


def test_prefers_display_form_for_links(tmp_path: Path) -> None:
    c = load_contact(_write(tmp_path))
    assert c["linkedin"] == "linkedin.com/in/andrew-t-nguyen"
    assert c["github"] == "github.com/andrew-nguyen-9"


def test_missing_file_returns_empty_dict(tmp_path: Path) -> None:
    assert load_contact(tmp_path / "nope.md") == {}
