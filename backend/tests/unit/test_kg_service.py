import uuid

import pytest

from backend.services.knowledge_graph.service import KnowledgeGraphService


def test_get_or_create_node_creates(test_session):
    svc = KnowledgeGraphService(test_session)
    eid = uuid.uuid4().hex
    node = svc.get_or_create_node("skill", eid, "Python", {})
    assert node.id is not None
    assert node.label == "Python"


def test_get_or_create_node_is_idempotent(test_session):
    svc = KnowledgeGraphService(test_session)
    eid = uuid.uuid4().hex
    n1 = svc.get_or_create_node("skill", eid, "Python", {})
    n2 = svc.get_or_create_node("skill", eid, "Python", {})
    assert n1.id == n2.id


def test_add_edge(test_session):
    svc = KnowledgeGraphService(test_session)
    exp = svc.get_or_create_node("experience", uuid.uuid4().hex, "Exp", {})
    skill = svc.get_or_create_node("skill", uuid.uuid4().hex, "Python", {})
    edge = svc.add_edge(exp.id, skill.id, "has_skill")
    assert edge.from_node_id == exp.id
    assert edge.to_node_id == skill.id


def test_get_neighbors(test_session):
    svc = KnowledgeGraphService(test_session)
    exp = svc.get_or_create_node("experience", uuid.uuid4().hex, "Exp", {})
    s1 = svc.get_or_create_node("skill", uuid.uuid4().hex, "Python", {})
    s2 = svc.get_or_create_node("skill", uuid.uuid4().hex, "SQL", {})
    svc.add_edge(exp.id, s1.id, "has_skill")
    svc.add_edge(exp.id, s2.id, "has_skill")
    neighbors = svc.get_neighbors(exp.id, edge_type="has_skill")
    assert len(neighbors) == 2


def test_upsert_node_updates_label(test_session):
    svc = KnowledgeGraphService(test_session)
    eid = uuid.uuid4().hex
    svc.get_or_create_node("skill", eid, "Old Label", {})
    updated = svc.upsert_node("skill", eid, "New Label", {"level": "senior"})
    assert updated.label == "New Label"
    assert updated.properties["level"] == "senior"
