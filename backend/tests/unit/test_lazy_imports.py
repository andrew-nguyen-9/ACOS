"""Phase 12.3 — cold-start lazy-import gate.

The server bind path (`import backend.main` + `create_app()`) must NOT
transitively import the heavy deps (chromadb pulls numpy/onnxruntime/otel;
rank_bm25 pulls numpy). They load on first use only.

The `sys.modules` assertions run in a FRESH interpreter (subprocess) because
other tests in this process may have already imported chromadb/numpy — a
same-process check would be meaningless.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

# Child imports the app, asserts the heavy deps are absent, then exercises a
# Chroma path and asserts chromadb is now present. Prints OK on success.
_CHILD = r"""
import sys, tempfile
import backend.main
backend.main.create_app()

leaked = [m for m in ("chromadb", "numpy", "rank_bm25") if m in sys.modules]
assert not leaked, f"heavy deps leaked onto the bind path: {leaked}"

# First use of Chroma imports it once.
from backend.rag.chroma_client import get_chroma_manager
mgr = get_chroma_manager(tempfile.mkdtemp())
mgr.get_or_create_collection("lazy_import_probe")
assert "chromadb" in sys.modules, "Chroma use did not trigger its import"

print("OK")
"""


def test_server_bind_does_not_import_heavy_deps() -> None:
    """Fresh-interpreter gate: bind path clean, Chroma loads only on first use."""
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
        env={**os.environ, "PYTHONPATH": str(_REPO_ROOT)},
    )
    assert proc.returncode == 0, f"child failed:\n{proc.stdout}\n{proc.stderr}"
    assert "OK" in proc.stdout, f"unexpected child output:\n{proc.stdout}\n{proc.stderr}"


def test_get_chroma_manager_memoizes_per_path(tmp_path) -> None:
    """One PersistentClient per process: repeated calls reuse the same manager."""
    from backend.rag.chroma_client import get_chroma_manager

    path = str(tmp_path / "chroma")
    a = get_chroma_manager(path)
    b = get_chroma_manager(path)
    assert a is b
