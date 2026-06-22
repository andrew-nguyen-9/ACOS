from __future__ import annotations

from typing import Any

from backend.services.rag import lexical

_EXPERIENCE_COLLECTIONS = ["acos_experiences", "acos_projects", "acos_skills"]


class EvidenceSelector:
    # duck-typed: concrete types are RAGRetriever and Reranker from backend/rag/
    def __init__(self, rag_retriever: Any, reranker: Any, session: Any = None) -> None:
        self._retriever = rag_retriever
        self._reranker = reranker
        # Optional sync Session for the FTS5 lexical leg (12.7); None → dense-only.
        self._session = session

    def select(
        self, job_description: str, keywords: dict, max_bullets: int = 8
    ) -> list[dict]:
        # keywords reserved for future JD-keyword-boosted filtering; currently unused
        raw = self._retriever.retrieve(
            query=job_description,
            doc_types=_EXPERIENCE_COLLECTIONS,
            top_k=20,
        )
        # Union the FTS5 lexical leg so keyword-matched experience text the dense
        # leg missed still reaches selection (mirrors RAGService.build_prompt).
        if self._session is not None:
            from backend.services.tenancy import get_session_tenant

            lex = lexical.search(
                self._session, job_description, _EXPERIENCE_COLLECTIONS, k=20,
                tenant_id=get_session_tenant(self._session),
            )
            raw = lexical.fuse(raw, lex)
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
