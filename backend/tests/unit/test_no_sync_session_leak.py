"""Phase 12.2 AC#2 — request paths must not use a sync Session.

Routes depend on ``get_async_session`` and do DB work via ``await session.run_sync``.
This guards against a regression that reintroduces the blocking sync ``get_session``
dependency or the module-level ``SessionLocal`` into an API module.
"""
import re
from pathlib import Path

_API_DIR = Path(__file__).resolve().parents[2] / "api"
_IMPORT_RE = re.compile(r"from\s+backend\.database\s+import\s+([^\n]+)")


def _banned_imports(path: Path) -> set[str]:
    found: set[str] = set()
    for line in _IMPORT_RE.findall(path.read_text()):
        names = {n.strip() for n in line.replace("(", "").replace(")", "").split(",")}
        found |= names & {"get_session", "SessionLocal"}
    return found


def test_api_routes_have_no_sync_session_dependency():
    offenders = {
        str(p.relative_to(_API_DIR.parent.parent)): banned
        for p in _API_DIR.rglob("*.py")
        if (banned := _banned_imports(p))
    }
    assert offenders == {}, f"sync Session leaked into request paths: {offenders}"
