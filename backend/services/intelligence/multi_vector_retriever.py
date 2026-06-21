from __future__ import annotations

from typing import Any

_EXPERIENCE_COLLECTIONS = ["acos_experiences", "acos_projects", "acos_skills"]

# Human-readable role labels used to build the role query vector.
_ROLE_LABELS: dict[str, str] = {
    "product_management": "product management roadmap stakeholder strategy",
    "data_analytics": "data analytics dashboards insights metrics",
    "consulting": "consulting client engagement strategy delivery",
    "engineering": "software engineering systems architecture development",
    "tpm_solutions": "technical program management solutions delivery",
}


def _word_overlap(a: str, b: str) -> float:
    """Jaccard-style overlap of word sets; 0.0 (disjoint) … 1.0 (identical)."""
    wa, wb = set(a.lower().split()), set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


class MultiVectorRetriever:
    """Retrieve evidence using parallel query vectors, merged with MMR for diversity.

    Builds up to 3 query vectors from a QueryUnderstander result (skills,
    keywords, role), retrieves each, dedups, then reranks via Maximal Marginal
    Relevance so near-duplicate bullets don't crowd out diverse evidence.

    # ponytail: MMR similarity uses word-overlap, not embedding cosine —
    # upgrade to embedding similarity only if diversity quality falls short.
    """

    def __init__(
        self,
        rag_retriever: Any,
        *,
        mmr_lambda: float = 0.5,
        top_k_per_vector: int = 15,
        final_pool_size: int = 30,
    ) -> None:
        self._retriever = rag_retriever
        self._lambda = mmr_lambda
        self._top_k = top_k_per_vector
        self._pool = final_pool_size

    def retrieve(self, understood_query: dict, *, max_results: int | None = None) -> list[dict]:
        merged = self._merge(self._build_queries(understood_query))
        ranked = self._mmr(merged)
        limit = max_results if max_results is not None else self._pool
        return [self._to_bullet(r) for r in ranked[:limit]]

    # ── Query construction ─────────────────────────────────────────────────────

    def _build_queries(self, uq: dict) -> list[str]:
        skills = " ".join(uq.get("required_skills", []) + uq.get("preferred_skills", []))
        keywords = " ".join(uq.get("must_have_keywords", []))
        role = _ROLE_LABELS.get(uq.get("role_type", ""), uq.get("role_type", ""))
        return [q for q in (skills, keywords, role) if q.strip()]

    def _merge(self, queries: list[str]) -> list[dict]:
        """Retrieve for each query and dedup by id, keeping the highest semantic_score."""
        by_id: dict[str, dict] = {}
        for query in queries:
            for res in self._retriever.retrieve(
                query=query, collections=_EXPERIENCE_COLLECTIONS, top_k=self._top_k
            ):
                rid = res["id"]
                if rid not in by_id or res["semantic_score"] > by_id[rid]["semantic_score"]:
                    by_id[rid] = res
        return list(by_id.values())

    # ── MMR reranking ───────────────────────────────────────────────────────────

    def _mmr(self, candidates: list[dict]) -> list[dict]:
        if not candidates:
            return []
        remaining = sorted(candidates, key=lambda r: r["semantic_score"], reverse=True)
        selected: list[dict] = [remaining.pop(0)]  # seed with most relevant

        while remaining:
            best, best_score = None, float("-inf")
            for cand in remaining:
                max_sim = max(
                    _word_overlap(cand["text"], s["text"]) for s in selected
                )
                mmr = self._lambda * cand["semantic_score"] - (1 - self._lambda) * max_sim
                if mmr > best_score:
                    best, best_score = cand, mmr
            selected.append(best)
            remaining.remove(best)
        return selected

    # ── Output shaping ──────────────────────────────────────────────────────────

    def _to_bullet(self, result: dict) -> dict:
        meta = result.get("metadata", {})
        return {
            "bullet_text": result["text"],
            "evidence_id": result["id"],
            "experience_id": meta.get("experience_id", ""),
            "company": meta.get("company", ""),
            "title": meta.get("title", ""),
            "dates": f"{meta.get('start_date', '')}–{meta.get('end_date', 'Present')}",
            "confidence": meta.get("confidence_level", "strong_inference"),
            "relevance_score": result["semantic_score"],
        }
