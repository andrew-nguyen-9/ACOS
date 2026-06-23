from __future__ import annotations

import logging
import math

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
        lexical_weight: float = 0.3,
        semantic_weight: float = 0.7,
        final_k: int = 15,
    ) -> list[dict]:
        if not results:
            return []

        # 12.7: lexical_score is carried on each candidate by the caller (FTS5
        # bm25, normalized to [0,1]); dense-only candidates default to 0.0. This
        # replaced the in-set rank_bm25 rescoring — FTS5 retrieves lexically over
        # the whole corpus, the reranker just fuses the two normalized scores.
        scored: list[dict] = []
        for result in results:
            confidence = result["metadata"].get("confidence_level", "strong_inference")
            multiplier = _CONFIDENCE_MULTIPLIER.get(confidence, 1.0)

            outcome_weight = result["metadata"].get("outcome_signal_weight", 0.0)
            outcome_boost = 1.0 + math.log1p(float(outcome_weight))

            lexical_score = float(result.get("lexical_score", 0.0))
            combined = (
                (result.get("semantic_score", 0.0) * semantic_weight + lexical_score * lexical_weight)
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
