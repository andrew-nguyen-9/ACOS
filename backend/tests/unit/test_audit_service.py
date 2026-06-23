"""Phase 16.3 (ADR-016) — audit hash-chain integrity + tamper detection."""
from __future__ import annotations

import json

import pytest

from backend.models.audit import AuditLog
from backend.services import audit
from backend.services.tenancy import ensure_tenant, set_session_tenant


def test_record_builds_a_verifiable_chain(test_session):
    audit.record(test_session, "generation", {"kind": "resume"})
    audit.record(test_session, "retrieval", {"intent": "x"})
    audit.record(test_session, "ats_score", {"overall_score": 80})
    assert audit.verify_chain(test_session) is True

    rows = test_session.query(AuditLog).order_by(AuditLog.id).all()
    assert [r.op_type for r in rows] == ["generation", "retrieval", "ats_score"]
    assert rows[0].prev_hash == audit.GENESIS
    assert rows[1].prev_hash == rows[0].row_hash  # chained


def test_editing_a_past_row_breaks_the_chain(test_session):
    audit.record(test_session, "generation", {"a": 1})
    audit.record(test_session, "retrieval", {"b": 2})
    first = test_session.query(AuditLog).order_by(AuditLog.id).first()
    first.metadata_json = json.dumps({"a": 999})  # tamper
    test_session.flush()
    assert audit.verify_chain(test_session) is False


def test_deleting_a_row_breaks_the_chain(test_session):
    audit.record(test_session, "generation", {"a": 1})
    audit.record(test_session, "retrieval", {"b": 2})
    audit.record(test_session, "ats_score", {"c": 3})
    middle = test_session.query(AuditLog).order_by(AuditLog.id).all()[1]
    test_session.delete(middle)
    test_session.flush()
    assert audit.verify_chain(test_session) is False


def test_bodies_are_never_stored(test_session):
    body = "the full secret prompt body that must not be logged"
    audit.record(test_session, "generation", {"prompt_digest": audit.digest(body)})
    row = test_session.query(AuditLog).first()
    assert body not in row.metadata_json
    assert audit.digest(body) in row.metadata_json


def test_unknown_op_type_rejected(test_session):
    with pytest.raises(ValueError):
        audit.record(test_session, "not-an-op", {})


def test_chains_are_per_tenant(test_session):
    ensure_tenant(test_session, "t1")
    ensure_tenant(test_session, "t2")
    set_session_tenant(test_session, "t1")
    audit.record(test_session, "generation", {"who": "t1"})
    set_session_tenant(test_session, "t2")
    audit.record(test_session, "generation", {"who": "t2"})
    # Each tenant's chain starts at GENESIS independently and verifies on its own.
    assert audit.verify_chain(test_session, tenant_id="t2") is True
    set_session_tenant(test_session, "t1")
    assert audit.verify_chain(test_session, tenant_id="t1") is True


def test_verify_all_chains_flags_broken(test_session):
    ensure_tenant(test_session, "t1")
    set_session_tenant(test_session, "t1")
    audit.record(test_session, "generation", {"a": 1})
    audit.record(test_session, "retrieval", {"b": 2})
    row = test_session.query(AuditLog).order_by(AuditLog.id).first()
    row.row_hash = "deadbeef" * 8  # corrupt
    test_session.flush()
    assert "t1" in audit.verify_all_chains(test_session)
