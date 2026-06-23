"""Phase 18.5 (ADR-020/011) — update check: notify-only, data-free, pluggable."""
from __future__ import annotations

from pathlib import Path

from backend.services import update_check
from backend.services.update_check import check

SRC = Path(update_check.__file__)


def test_update_available_when_remote_newer():
    s = check("0.1.0", {"version": "0.2.0", "url": "https://dl.test/acos-0.2.0.dmg"})
    assert s.update_available is True
    assert s.latest_version == "0.2.0"
    assert s.download_url == "https://dl.test/acos-0.2.0.dmg"  # user clicks; not auto-fetched


def test_no_update_when_equal_or_older():
    assert check("0.2.0", {"version": "0.2.0"}).update_available is False
    assert check("0.3.0", {"version": "0.2.0"}).update_available is False


def test_semver_compare_handles_v_prefix_and_segments():
    assert check("v1.0.0", {"version": "v1.0.1"}).update_available is True
    assert check("1.2.0", {"version": "1.10.0"}).update_available is True  # 10 > 2


def test_no_url_when_no_update():
    assert check("1.0.0", {"version": "1.0.0", "url": "x"}).download_url is None


def test_module_imports_nothing_network_or_process():
    """Behavioral guarantee: the check can't fetch or install — it imports no network
    or process module (it only compares the manifest the caller already fetched)."""
    import ast

    tree = ast.parse(SRC.read_text())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"httpx", "requests", "urllib", "socket", "aiohttp", "subprocess", "os"}
    assert not (imported & forbidden), f"update check must not import {imported & forbidden}"
