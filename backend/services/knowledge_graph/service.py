from __future__ import annotations

import re

from sqlalchemy.orm import Session

from backend.models.knowledge_graph import KnowledgeGraphEdge, KnowledgeGraphNode
from backend.repositories.knowledge_graph import (
    KnowledgeGraphEdgeRepository,
    KnowledgeGraphNodeRepository,
)

# 15.3 — node types the user's own evidence lives under; an answer is "grounded"
# when it references these. Companies/applications/documents are context, not claims.
_GROUNDING_NODE_TYPES = ("skill", "experience", "project")


def _tokenize(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-zA-Z0-9#+]{2,}", text)}


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

    def evaluate_answer(
        self, answer_text: str, expected_node_ids: list[str] | None = None
    ) -> dict:
        """15.3 — score an interview answer by its grounding in the graph.

        Coverage = fraction of the expected nodes whose label is referenced in
        the answer; the result names exactly which nodes were and weren't covered
        (ADR-006 — no bare score). Confidence reflects the evidence base: with
        fewer than 3 grounding nodes (or none) the score is honestly weak, never
        a fabricated certainty.
        """
        if expected_node_ids:
            nodes = [n for n in (self._nodes.get(i) for i in expected_node_ids) if n]
        else:
            nodes = [
                n for t in _GROUNDING_NODE_TYPES for n in self._nodes.get_by_type(t)
            ]
        answer_tokens = _tokenize(answer_text)
        covered: list[str] = []
        missing: list[str] = []
        matched_labels: list[str] = []
        for n in nodes:
            if _tokenize(n.label) & answer_tokens:
                covered.append(n.id)
                matched_labels.append(n.label)
            else:
                missing.append(n.id)
        total = len(nodes)
        coverage = round(len(covered) / total, 3) if total else 0.0
        # Heuristic grounding — never "verified"; thin evidence → weak.
        confidence = "strong_inference" if total >= 3 else "weak_inference"
        return {
            "coverage": coverage,
            "covered_node_ids": covered,
            "missing_node_ids": missing,
            "matched_labels": matched_labels,
            "expected_count": total,
            "confidence": confidence,
        }

    def get_neighbors(
        self, node_id: str, edge_type: str | None = None
    ) -> list[KnowledgeGraphNode]:
        edges = self._edges.get_edges_from(node_id)
        if edge_type is not None:
            edges = [e for e in edges if e.edge_type == edge_type]
        neighbor_ids = [e.to_node_id for e in edges]
        return [n for n in (self._nodes.get(nid) for nid in neighbor_ids) if n is not None]
