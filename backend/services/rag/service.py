from __future__ import annotations

import logging

from backend.observability import log_operation

logger = logging.getLogger(__name__)

_INTENT_COLLECTIONS: dict[str, list[str]] = {
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


class RAGService:
    def __init__(self, retriever, reranker, ollama_client) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self._ollama = ollama_client

    def query(self, query: str, intent: str = "knowledge_lookup") -> dict:
        collections = _INTENT_COLLECTIONS.get(intent, _INTENT_COLLECTIONS["knowledge_lookup"])
        raw_results = self._retriever.retrieve(query, collections)
        ranked = self._reranker.rerank(query, raw_results)

        context_parts = []
        for r in ranked:
            conf = r["metadata"].get("confidence_level", "strong_inference")
            context_parts.append(f"[{conf}] {r['text']}")
        context = "\n\n".join(context_parts[:15])

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

        if not self._ollama or not self._ollama.is_available():
            return {
                "response": context[:500] if context else "No relevant context found.",
                "evidence": evidence,
                "confidence_summary": conf_summary,
            }

        prompt = (
            f"Using the following evidence, answer the question: {query}\n\nEvidence:\n{context}"
        )
        response = self._ollama.generate(
            model="qwen3:8b",
            prompt=prompt,
            temperature=0.3,
            system="You are a career assistant. Answer only from the provided evidence. Never invent facts.",
        )
        return {
            "response": response,
            "evidence": evidence,
            "confidence_summary": conf_summary,
        }

    def _summarize_confidence(self, results: list[dict]) -> str:
        if not results:
            return "no_evidence"
        levels = [r["metadata"].get("confidence_level", "strong_inference") for r in results[:5]]
        best = max(levels, key=lambda c: _CONFIDENCE_PRIORITY.get(c, 0))
        return best
