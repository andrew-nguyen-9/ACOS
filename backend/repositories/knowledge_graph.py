from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.knowledge_graph import KnowledgeGraphEdge, KnowledgeGraphNode
from backend.repositories.base import BaseRepository


class KnowledgeGraphNodeRepository(BaseRepository[KnowledgeGraphNode]):
    def __init__(self, session: Session) -> None:
        super().__init__(KnowledgeGraphNode, session)

    def get_by_entity(self, entity_id: str, node_type: str) -> KnowledgeGraphNode | None:
        stmt = select(KnowledgeGraphNode).where(
            KnowledgeGraphNode.entity_id == entity_id,
            KnowledgeGraphNode.node_type == node_type,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_type(self, node_type: str) -> list[KnowledgeGraphNode]:
        stmt = select(KnowledgeGraphNode).where(KnowledgeGraphNode.node_type == node_type)
        return list(self.session.execute(stmt).scalars().all())


class KnowledgeGraphEdgeRepository(BaseRepository[KnowledgeGraphEdge]):
    def __init__(self, session: Session) -> None:
        super().__init__(KnowledgeGraphEdge, session)

    def get_edges_from(self, from_node_id: str) -> list[KnowledgeGraphEdge]:
        stmt = select(KnowledgeGraphEdge).where(
            KnowledgeGraphEdge.from_node_id == from_node_id
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_edges_between(self, from_id: str, to_id: str) -> list[KnowledgeGraphEdge]:
        stmt = select(KnowledgeGraphEdge).where(
            KnowledgeGraphEdge.from_node_id == from_id,
            KnowledgeGraphEdge.to_node_id == to_id,
        )
        return list(self.session.execute(stmt).scalars().all())
