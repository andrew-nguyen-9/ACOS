from __future__ import annotations

import logging
import math

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

_CONFIDENCE_MULTIPLIER: dict[str, float] = {
    "verified": 1.2,
    "strong_inference": 1.0,
    "weak_inference": 0.6,
}


class Reranker:
    def rerank(
        self,
        query: str,
        results: list[dict],
        bm25_weight: float = 0.3,
        semantic_weight: float = 0.7,
        final_k: int = 15,
    ) -> list[dict]:
        if not results:
            return []

        corpus = [r["text"].lower().split() for r in results]
        bm25 = BM25Okapi(corpus)
        query_tokens = query.lower().split()
        bm25_scores = bm25.get_scores(query_tokens)

        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
        norm_bm25 = [s / max_bm25 for s in bm25_scores]

        scored: list[dict] = []
        for i, result in enumerate(results):
            confidence = result["metadata"].get("confidence_level", "strong_inference")
            multiplier = _CONFIDENCE_MULTIPLIER.get(confidence, 1.0)

            outcome_weight = result["metadata"].get("outcome_signal_weight", 0.0)
            outcome_boost = 1.0 + math.log1p(float(outcome_weight))

            combined = (
                (result["semantic_score"] * semantic_weight + norm_bm25[i] * bm25_weight)
                * multiplier
                * outcome_boost
            )
            scored.append({**result, "combined_score": combined})

        scored.sort(key=lambda r: r["combined_score"], reverse=True)

        # Deduplicate by entity_id if present; otherwise use result id
        seen: set[str] = set()
        deduped: list[dict] = []
        for r in scored:
            entity_id = r["metadata"].get("entity_id", r["id"])
            if entity_id not in seen:
                seen.add(entity_id)
                deduped.append(r)

        return deduped[:final_k]
