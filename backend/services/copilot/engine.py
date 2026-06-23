from __future__ import annotations

from backend.observability import log_operation
from backend.services.rag.service import RAGService

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "resume_help": ["resume", "cv", "bullet", "template", "one-page", "tailor"],
    "cover_letter_help": ["cover letter", "cover_letter", "covering letter"],
    "interview_prep": ["interview", "behavioral", "technical", "whiteboard", "question", "prep"],
    "job_fit_analysis": ["fit", "match", "job", "jd", "requirement", "skill gap", "qualify"],
    "career_advice": ["career", "advice", "next step", "growth", "path", "pivot", "transition"],
}


def _detect_intent(message: str) -> str:
    lower = message.lower()
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return intent
    return "knowledge_lookup"


def _format_history(history: list[dict]) -> str:
    if not history:
        return ""
    lines = []
    for turn in history[-5:]:  # limit context to last 5 turns
        role = turn.get("role", "user").capitalize()
        content = turn.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


class CopilotEngine:
    def __init__(self, rag_service: RAGService) -> None:
        self._rag = rag_service

    def _route(self, message: str, conversation_history: list[dict] | None) -> tuple[str, str]:
        history = conversation_history or []
        intent = _detect_intent(message)
        history_text = _format_history(history)
        query = f"{history_text}\nUser: {message}".strip() if history_text else message
        return intent, query

    def _assemble(self, intent: str, rag_base: dict) -> dict:
        evidence = rag_base.get("evidence", [])
        citations = [
            {
                "source": e.get("source", ""),
                "text": e.get("text", "")[:150],
                "confidence": e.get("confidence", "strong_inference"),
                "similarity": e.get("similarity_score", 0.0),
            }
            for e in evidence[:5]
        ]
        return {
            "response": rag_base.get("response", ""),
            "intent": intent,
            "confidence": rag_base.get("confidence_summary", "no_evidence"),
            "citations": citations,
            "evidence_count": len(evidence),
        }

    def chat(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
    ) -> dict:
        intent, query = self._route(message, conversation_history)
        result = self._assemble(intent, self._rag.query(query, intent=intent))
        log_operation("copilot_chat", intent=intent, citations=len(result["citations"]))
        return result

    def prepare(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
    ) -> tuple[str | None, dict]:
        """Streaming-path counterpart of chat(): retrieval + prompt, no generation.

        Returns ``(prompt, result)``. ``prompt`` is ``None`` when RAG already has a
        usable response (fallback / degraded); otherwise ``result["response"]`` is
        empty for the streaming route to fill from token deltas.
        """
        intent, query = self._route(message, conversation_history)
        prompt, base = self._rag.build_prompt(query, intent=intent)
        return prompt, self._assemble(intent, base)
