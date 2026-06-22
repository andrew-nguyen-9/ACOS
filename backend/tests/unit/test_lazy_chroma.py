"""Lazy-Chroma startup guard (Phase 11.3).

Importing the chroma client module — and transitively `backend.main` — must not
pull in `chromadb` (and its heavy deps: numpy, onnxruntime, opentelemetry, grpc).
The import is deferred until a ChromaManager actually touches a collection.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _fresh(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=_REPO_ROOT
    )


def test_import_chroma_client_does_not_import_chromadb():
    proc = _fresh(
        "import sys; import backend.rag.chroma_client;"
        "assert 'chromadb' not in sys.modules, 'chromadb imported eagerly';"
        "print('OK')"
    )
    assert proc.returncode == 0, proc.stderr


def test_import_backend_main_does_not_import_chromadb():
    proc = _fresh(
        "import sys; import backend.main; backend.main.create_app();"
        "assert 'chromadb' not in sys.modules, 'chromadb imported at startup';"
        "print('OK')"
    )
    assert proc.returncode == 0, proc.stderr


def test_chroma_manager_still_works_after_lazy_import(tmp_path):
    from backend.rag.chroma_client import ChromaManager

    mgr = ChromaManager(path=str(tmp_path / "chroma"))
    # Constructing the manager is cheap; the client materializes on first use.
    assert mgr.count("acos_documents") == 0
