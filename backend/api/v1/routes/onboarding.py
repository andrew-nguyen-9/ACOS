"""Phase 13.5 — onboarding cold-start summary (read-only surfacing).

Surfaces what the existing ingestion build produced — extracted skills (with their
confidence), a document count, and the current Career-Voice (writing-style) profile —
so the first-run wizard can show the user their freshly-built profile.

Read-only. No synthetic skills are fabricated here (CLAUDE.md #1): skills come only
from real uploads. The only template fill is the default Career-Voice, which is flagged
``synthetic`` so it is never presented as the user's own writing.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.database import get_async_session
from backend.repositories.document import DocumentRepository
from backend.repositories.knowledge_graph import KnowledgeGraphNodeRepository
from backend.services.cover_letter.voice_modeler import VoiceModeler

router = APIRouter(tags=["onboarding"])


@router.get("/onboarding/summary")
async def onboarding_summary(session: AsyncSession = Depends(get_async_session)) -> dict:
    def _impl(s: Session) -> dict:
        nodes = KnowledgeGraphNodeRepository(s).get_by_type("skill")
        skills = [
            {
                "label": n.label,
                "confidence": (n.properties or {}).get("confidence", "weak_inference"),
            }
            for n in nodes
        ]

        count = len(DocumentRepository(s).get_by_status("complete"))

        # get_or_create_default only reads the repo / returns the default constant —
        # ollama + loader are unused on this path, so None is fine.
        voice = VoiceModeler(None, None, s).get_or_create_default()
        career_voice = {
            "tone_descriptors": voice["tone_descriptors"],
            "structure_patterns": voice["structure_patterns"],
            "sample_sentences": voice["sample_sentences"],
            "synthetic": voice["profile_id"] is None,
        }

        return {
            "skills": skills,
            "documents": {"count": count},
            "career_voice": career_voice,
        }

    return await session.run_sync(_impl)
