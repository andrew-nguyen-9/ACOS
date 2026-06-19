from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import get_session
from backend.services.ats.keyword_extractor import KeywordExtractor
from backend.services.ats.scorer import ATSScorer
from backend.services.ollama_client import OllamaClient
from backend.services.prompt_loader import PromptLoader

router = APIRouter(tags=["resume"])


class ATSRequest(BaseModel):
    resume_text: str
    job_description: str


@router.post("/resume/analyze-ats")
def analyze_ats(
    body: ATSRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    settings = get_settings()
    ollama = OllamaClient(base_url=settings.ollama_base_url)
    loader = PromptLoader()
    extractor = KeywordExtractor(ollama, loader)
    scorer = ATSScorer(ollama, loader)

    keywords = extractor.extract(body.job_description)
    score = scorer.score(body.resume_text, body.job_description, keywords)
    return {"keywords": keywords, "ats_score": score}
