from __future__ import annotations

from sqlalchemy import String, Text, Float, CheckConstraint, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, generate_uuid, utcnow
from backend.models.tenant import TenantScopedMixin


class KnowledgeGraphNode(TenantScopedMixin, Base):
    __tablename__ = "knowledge_graph_nodes"
    __table_args__ = (
        CheckConstraint(
            "node_type IN ('experience','skill','project','company','application','document','answer')",
            name="ck_kg_node_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    node_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    properties: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)

    outgoing_edges: Mapped[list[KnowledgeGraphEdge]] = relationship(
        "KnowledgeGraphEdge",
        foreign_keys="KnowledgeGraphEdge.from_node_id",
        back_populates="from_node",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list[KnowledgeGraphEdge]] = relationship(
        "KnowledgeGraphEdge",
        foreign_keys="KnowledgeGraphEdge.to_node_id",
        back_populates="to_node",
        cascade="all, delete-orphan",
    )


class KnowledgeGraphEdge(TenantScopedMixin, Base):
    __tablename__ = "knowledge_graph_edges"
    __table_args__ = (
        CheckConstraint(
            "edge_type IN ('has_skill','uses_technology','worked_at','produced','evidenced_by','applied_to','answered_for','resulted_in','related_to')",
            name="ck_kg_edge_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_uuid)
    from_node_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("knowledge_graph_nodes.id", ondelete="CASCADE"), nullable=False
    )
    to_node_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("knowledge_graph_nodes.id", ondelete="CASCADE"), nullable=False
    )
    edge_type: Mapped[str] = mapped_column(String(30), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    properties: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(String(32), default=utcnow)

    from_node: Mapped[KnowledgeGraphNode] = relationship(
        "KnowledgeGraphNode",
        foreign_keys="[KnowledgeGraphEdge.from_node_id]",
        back_populates="outgoing_edges",
    )
    to_node: Mapped[KnowledgeGraphNode] = relationship(
        "KnowledgeGraphNode",
        foreign_keys="[KnowledgeGraphEdge.to_node_id]",
        back_populates="incoming_edges",
    )
