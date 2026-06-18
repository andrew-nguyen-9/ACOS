import pytest
from backend.repositories.knowledge_graph import (
    KnowledgeGraphNodeRepository,
    KnowledgeGraphEdgeRepository,
)
from backend.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge


def _make_node(session, node_type="skill", label="Python", entity_id=None):
    import uuid
    repo = KnowledgeGraphNodeRepository(session)
    return repo.create(
        node_type=node_type,
        entity_id=entity_id or uuid.uuid4().hex,
        label=label,
        properties={},
    )


def test_get_by_entity_id(test_session):
    node = _make_node(test_session)
    repo = KnowledgeGraphNodeRepository(test_session)
    found = repo.get_by_entity(node.entity_id, node.node_type)
    assert found is not None
    assert found.id == node.id


def test_get_by_entity_returns_none_for_unknown(test_session):
    repo = KnowledgeGraphNodeRepository(test_session)
    assert repo.get_by_entity("nonexistent", "skill") is None


def test_get_by_type(test_session):
    _make_node(test_session, node_type="skill", label="Python")
    _make_node(test_session, node_type="skill", label="SQL")
    _make_node(test_session, node_type="project", label="ACOS")
    repo = KnowledgeGraphNodeRepository(test_session)
    skills = repo.get_by_type("skill")
    assert len(skills) == 2


def test_edge_get_edges_from(test_session):
    n1 = _make_node(test_session, node_type="experience", label="Exp1")
    n2 = _make_node(test_session, node_type="skill", label="Python")
    edge_repo = KnowledgeGraphEdgeRepository(test_session)
    edge_repo.create(
        from_node_id=n1.id, to_node_id=n2.id, edge_type="has_skill", weight=1.0, properties={}
    )
    edges = edge_repo.get_edges_from(n1.id)
    assert len(edges) == 1
    assert edges[0].to_node_id == n2.id


def test_edge_get_edges_between(test_session):
    n1 = _make_node(test_session, node_type="experience", label="E1")
    n2 = _make_node(test_session, node_type="skill", label="S1")
    edge_repo = KnowledgeGraphEdgeRepository(test_session)
    edge_repo.create(
        from_node_id=n1.id, to_node_id=n2.id, edge_type="has_skill", weight=1.0, properties={}
    )
    found = edge_repo.get_edges_between(n1.id, n2.id)
    assert len(found) == 1
    assert found[0].edge_type == "has_skill"
