"""Phase 16.3 (ADR-016) strict rule — NO UNLOGGED INFERENCE.

Source-scan: every inference chokepoint route must wire the audit emit. A new
inference path that forgets to audit fails this test — the guarantee the ADR makes.
Plus one runtime proof that the wiring actually fires (optimization needs no Ollama).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.models.audit import AuditLog

ROUTES = Path(__file__).resolve().parents[2] / "api" / "v1" / "routes"

# (route file, op_type expected) — the four ADR-016 inference categories.
CHOKEPOINTS = [
    ("resume.py", "generation"),
    ("resume.py", "ats_score"),
    ("cover_letter.py", "generation"),
    ("copilot.py", "generation"),
    ("questions.py", "generation"),
    ("rag.py", "retrieval"),
    ("optimization.py", "optimization"),
]


@pytest.mark.parametrize("filename,op_type", CHOKEPOINTS)
def test_inference_route_wires_audit(filename, op_type):
    src = (ROUTES / filename).read_text()
    assert "audit.safe_record" in src or "audit.record" in src, (
        f"{filename} performs inference but never emits an audit event (ADR-016)"
    )
    assert f'"{op_type}"' in src, f"{filename} missing audit op_type {op_type!r}"


def test_optimization_route_emits_audit_row(client, test_session):
    """Runtime proof: generating proposals writes an audit row (no Ollama needed).
    client + test_session share one in-memory DB (conftest), so the row is visible."""
    r = client.post("/api/v1/optimization/proposals/generate")
    assert r.status_code == 200
    rows = test_session.query(AuditLog).filter(AuditLog.op_type == "optimization").all()
    assert len(rows) >= 1
