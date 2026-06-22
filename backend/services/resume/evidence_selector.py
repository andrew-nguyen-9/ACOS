from __future__ import annotations

from typing import Any

_EXPERIENCE_COLLECTIONS = ["acos_experiences", "acos_projects", "acos_skills"]


class EvidenceSelector:
    # duck-typed: concrete types are RAGRetriever and Reranker from backend/rag/
    def __init__(self, rag_retriever: Any, reranker: Any) -> None:
        self._retriever = rag_retriever
        self._reranker = reranker

    def select(
        self, job_description: str, keywords: dict, max_bullets: int = 8
    ) -> list[dict]:
        # keywords reserved for future JD-keyword-boosted filtering; currently unused
        raw = self._retriever.retrieve(
            query=job_description,
            doc_types=_EXPERIENCE_COLLECTIONS,
            top_k=20,
        )
        ranked = self._reranker.rerank(
            query=job_description,
            results=raw,
            final_k=max_bullets,
        )
        return [self._to_bullet(r) for r in ranked[:max_bullets]]

    def _to_bullet(self, result: dict) -> dict:
        meta = result["metadata"]
        return {
            "bullet_text": result["text"],
            "evidence_id": result["id"],
            "experience_id": meta.get("experience_id", ""),
            "company": meta.get("company", ""),
            "title": meta.get("title", ""),
            "dates": f"{meta.get('start_date', '')}–{meta.get('end_date', 'Present')}",
            "confidence": meta.get("confidence_level", "strong_inference"),
        }
