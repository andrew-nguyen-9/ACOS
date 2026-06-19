from __future__ import annotations

import logging

from backend.services.rag.service import RAGService

logger = logging.getLogger(__name__)

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

    def chat(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
    ) -> dict:
        history = conversation_history or []
        intent = _detect_intent(message)
        history_text = _format_history(history)
        query = f"{history_text}\nUser: {message}".strip() if history_text else message
        rag_result = self._rag.query(query, intent=intent)
        evidence = rag_result.get("evidence", [])
        citations = [
            {
                "source": e["source"],
                "text": e["text"][:150],
                "confidence": e["confidence"],
                "similarity": e.get("similarity_score", 0.0),
            }
            for e in evidence[:5]
        ]
        return {
            "response": rag_result["response"],
            "intent": intent,
            "confidence": rag_result.get("confidence_summary", "no_evidence"),
            "citations": citations,
            "evidence_count": len(evidence),
        }
