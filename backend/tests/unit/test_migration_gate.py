"""Phase 18.4 (ADR-020) strict rule — NO breaking schema change without a
down-migration. Every Alembic revision must define a real downgrade (not a stub),
so a tester can roll back to a prior build's head.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

VERSIONS = Path(__file__).resolve().parents[3] / "database" / "migrations" / "versions"


def _downgrade_body(path: Path) -> list[ast.stmt]:
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "downgrade":
            return node.body
    return []


MIGRATIONS = sorted(p for p in VERSIONS.glob("*.py") if not p.name.startswith("__"))


@pytest.mark.parametrize("path", MIGRATIONS, ids=lambda p: p.name)
def test_every_migration_has_a_real_downgrade(path):
    body = _downgrade_body(path)
    assert body, f"{path.name} has no downgrade()"
    # Reject a stub downgrade (just `pass`, or only a docstring) on a migration that
    # has substantive work — a breaking change must be reversible (ADR-020 §3).
    meaningful = [
        s for s in body
        if not (isinstance(s, ast.Pass))
        and not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
    ]
    assert meaningful, f"{path.name} downgrade is a stub — no rollback path"
