from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models.knowledge_graph import KnowledgeGraphEdge, KnowledgeGraphNode
from backend.repositories.knowledge_graph import (
    KnowledgeGraphEdgeRepository,
    KnowledgeGraphNodeRepository,
)


class KnowledgeGraphService:
    def __init__(self, session: Session) -> None:
        self._nodes = KnowledgeGraphNodeRepository(session)
        self._edges = KnowledgeGraphEdgeRepository(session)
        self._session = session

    def get_or_create_node(
        self, node_type: str, entity_id: str, label: str, properties: dict
    ) -> KnowledgeGraphNode:
        existing = self._nodes.get_by_entity(entity_id, node_type)
        if existing:
            return existing
        return self._nodes.create(
            node_type=node_type,
            entity_id=entity_id,
            label=label,
            properties=properties,
        )

    def upsert_node(
        self, node_type: str, entity_id: str, label: str, properties: dict
    ) -> KnowledgeGraphNode:
        existing = self._nodes.get_by_entity(entity_id, node_type)
        if existing:
            existing.label = label
            existing.properties = properties
            self._session.flush()
            self._session.refresh(existing)
            return existing
        return self._nodes.create(
            node_type=node_type,
            entity_id=entity_id,
            label=label,
            properties=properties,
        )

    def add_edge(
        self,
        from_node_id: str,
        to_node_id: str,
        edge_type: str,
        weight: float = 1.0,
        properties: dict | None = None,
    ) -> KnowledgeGraphEdge:
        return self._edges.create(
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            edge_type=edge_type,
            weight=weight,
            properties=properties or {},
        )

    def get_neighbors(
        self, node_id: str, edge_type: str | None = None
    ) -> list[KnowledgeGraphNode]:
        edges = self._edges.get_edges_from(node_id)
        if edge_type is not None:
            edges = [e for e in edges if e.edge_type == edge_type]
        neighbor_ids = [e.to_node_id for e in edges]
        return [n for n in (self._nodes.get(nid) for nid in neighbor_ids) if n is not None]
