from __future__ import annotations

import logging

from backend.observability import log_operation
from backend.services.ollama_client import Operation
from backend.services.rag import lexical
from backend.services.tokens import count_tokens

logger = logging.getLogger(__name__)

# intent → doc_type partitions queried (values are doc_type metadata, == legacy
# collection names; the consolidated retriever filters acos_documents by where-$in).
_INTENT_DOCTYPES: dict[str, list[str]] = {
    "resume_help": ["acos_experiences", "acos_projects", "acos_skills", "acos_resumes"],
    "cover_letter_help": ["acos_cover_letters", "acos_experiences", "acos_projects"],
    "interview_prep": ["acos_answers", "acos_questions", "acos_experiences", "acos_projects"],
    "job_fit_analysis": ["acos_job_descriptions", "acos_skills", "acos_experiences", "acos_projects"],
    "knowledge_lookup": ["acos_experiences", "acos_projects", "acos_answers", "acos_github", "acos_claude_exports"],
    "career_advice": [
        "acos_experiences", "acos_projects", "acos_skills", "acos_resumes",
        "acos_cover_letters", "acos_questions", "acos_answers",
        "acos_job_descriptions", "acos_github", "acos_claude_exports",
    ],
}

_CONFIDENCE_PRIORITY: dict[str, int] = {"verified": 3, "strong_inference": 2, "weak_inference": 1}

# Hard token cap on retrieved context before prompt assembly. Prompt-eval over
# this dominates TTFT (12.5), so the budget — not a fixed item count — is the lever.
CONTEXT_TOKEN_BUDGET = 1500


def _prune_context_parts(parts: list[str], budget: int = CONTEXT_TOKEN_BUDGET) -> list[str]:
    """Keep highest-ranked parts whose cumulative token cost stays within budget.

    ``parts`` is rerank order (best first). The first part is always kept so a
    single oversized top hit never yields empty context; once adding a part would
    exceed the budget, that part and the entire tail are dropped.
    """
    kept: list[str] = []
    used = 0
    for i, part in enumerate(parts):
        cost = count_tokens(part)
        if i > 0 and used + cost > budget:
            break
        kept.append(part)
        used += cost
    return kept

# Shared by query() and the 12.4 streaming route so both produce the same answer.
RAG_MODEL = "qwen3:8b"
RAG_EMBED_MODEL = "nomic-embed-text"
RAG_SYSTEM = (
    "You are a career assistant. Answer only from the provided evidence. Never invent facts."
)
# [FIXED SYSTEM PREFIX] = RAG_SYSTEM, [FIXED INSTRUCTIONS] = RAG_INSTRUCTIONS,
# [DYNAMIC RAG CONTEXT] last. Keep RAG_INSTRUCTIONS byte-stable so Ollama reuses
# the system-prefix KV cache across calls (12.5 prefix-stability).
RAG_INSTRUCTIONS = (
    "Answer the question using only the evidence below. Cite the confidence level "
    "of each claim. If the evidence is insufficient, say so plainly.\n\n"
)


class RAGService:
    def __init__(
        self, retriever, reranker, ollama_client, fallback=None,
        embed_model: str = RAG_EMBED_MODEL, session=None,
    ) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self._ollama = ollama_client
        # Optional KeywordFallback (SQLite) used when the vector store is down.
        self._fallback = fallback
        self._embed_model = embed_model
        # Optional sync Session for the FTS5 lexical leg (12.7). When set, hybrid
        # retrieval unions dense (Chroma) + lexical (FTS5); None → dense-only.
        self._session = session

    def build_prompt(self, query: str, intent: str = "knowledge_lookup") -> tuple[str | None, dict]:
        """Run retrieval and assemble the LLM prompt without generating.

        Returns ``(prompt, base)``. ``prompt`` is ``None`` when generation should
        be skipped (keyword fallback or Ollama unavailable) — then ``base``
        already carries a usable ``response``. When ``prompt`` is set, ``base``
        has an empty ``response`` for the caller to fill (sync ``generate`` or the
        12.4 streaming path), so streamed and non-streamed answers share one prompt.
        """
        doc_types = _INTENT_DOCTYPES.get(intent, _INTENT_DOCTYPES["knowledge_lookup"])

        degraded_reason: str | None = None
        try:
            raw_results = self._retriever.retrieve(query, doc_types)
        except Exception as exc:
            raw_results = []
            degraded_reason = f"vector store error: {exc}"

        # Lexical leg (12.7): union FTS5 BM25 keyword recall with the dense
        # candidates. Defensive — a lexical failure must not sink dense results;
        # if Chroma also failed, lexical hits still beat the LIKE-scan fallback.
        if self._session is not None:
            try:
                from backend.services.tenancy import get_session_tenant

                lex = lexical.search(
                    self._session, query, doc_types, k=10,
                    tenant_id=get_session_tenant(self._session),
                )
                raw_results = lexical.fuse(raw_results, lex)
            except Exception as exc:
                logger.warning("build_prompt: lexical leg failed: %s", exc)

        # Degrade to keyword fallback when the vector store errored or returned
        # nothing and a fallback is wired.
        if not raw_results and self._fallback is not None:
            fb_evidence = self._fallback.search(query)
            if fb_evidence:
                reason = degraded_reason or "vector store unavailable or empty; keyword fallback"
                return None, self._fallback_response(fb_evidence, reason)

        ranked = self._reranker.rerank(query, raw_results)

        context_parts = []
        for r in ranked:
            conf = r["metadata"].get("confidence_level", "strong_inference")
            context_parts.append(f"[{conf}] {r['text']}")
        context = "\n\n".join(_prune_context_parts(context_parts))

        evidence = [
            {
                "text": r["text"][:300],
                "source": r["collection"],
                "entity_id": r["metadata"].get("entity_id", r["id"]),
                "confidence": r["metadata"].get("confidence_level", "strong_inference"),
                "similarity_score": round(r["semantic_score"], 4),
            }
            for r in ranked
        ]

        conf_summary = self._summarize_confidence(ranked)
        log_operation("rag_retrieve", intent=intent, evidence=len(evidence))

        # 12.7 fix-1: Chroma may have errored while the FTS5 lexical leg still
        # returned hits — the query succeeds but is degraded (dense retrieval is
        # down). Report that honestly instead of a hardcoded healthy flag.
        degraded = degraded_reason is not None
        degraded_extra = {"degraded_reason": degraded_reason} if degraded else {}

        if not self._ollama or not self._ollama.is_available():
            return None, {
                "response": context[:500] if context else "No relevant context found.",
                "evidence": evidence,
                "confidence_summary": conf_summary,
                "degraded": degraded,
                **degraded_extra,
            }

        # Fixed instructions first, dynamic context last (prefix-cache stability).
        prompt = f"{RAG_INSTRUCTIONS}Question: {query}\n\nEvidence:\n{context}"
        return prompt, {
            "response": "",
            "evidence": evidence,
            "confidence_summary": conf_summary,
            "degraded": degraded,
            **degraded_extra,
        }

    def query(self, query: str, intent: str = "knowledge_lookup") -> dict:
        prompt, base = self.build_prompt(query, intent)
        if prompt is None:
            return base
        # Retrieval already embedded the query; evict the embedder before the
        # generator loads so the two models don't co-reside (16GB starvation).
        self._ollama.unload(self._embed_model)  # type: ignore[union-attr]
        base["response"] = self._ollama.generate(  # type: ignore[union-attr]
            model=RAG_MODEL,
            prompt=prompt,
            temperature=0.3,
            system=RAG_SYSTEM,
            operation=Operation.CHAT,
            prompt_tokens=count_tokens(prompt),
        )
        return base

    def _fallback_response(self, evidence: list[dict], reason: str) -> dict:
        """Assemble a degraded result from SQLite keyword-fallback evidence."""
        conf_summary = max(
            (e.get("confidence", "weak_inference") for e in evidence[:5]),
            key=lambda c: _CONFIDENCE_PRIORITY.get(c, 0),
            default="no_evidence",
        )
        context = "\n\n".join(e["text"] for e in evidence[:15])
        log_operation("rag_fallback", evidence=len(evidence), reason=reason)
        return {
            "response": context[:500] if context else "No relevant context found.",
            "evidence": evidence,
            "confidence_summary": conf_summary,
            "degraded": True,
            "degraded_reason": reason,
        }

    def _summarize_confidence(self, results: list[dict]) -> str:
        if not results:
            return "no_evidence"
        levels = [r["metadata"].get("confidence_level", "strong_inference") for r in results[:5]]
        best = max(levels, key=lambda c: _CONFIDENCE_PRIORITY.get(c, 0))
        return best
