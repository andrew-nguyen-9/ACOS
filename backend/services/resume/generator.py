from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.repositories.resume import ResumeRepository
from backend.services.resume.templates import get_template

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "qwen3:8b"
_VALID_CONFIDENCE = {"verified", "strong_inference", "weak_inference"}


def _normalize_confidence(content: dict) -> dict:
    for exp in content.get("experiences", []):
        for bullet in exp.get("bullets", []):
            if isinstance(bullet, dict):
                if bullet.get("confidence") not in _VALID_CONFIDENCE:
                    bullet["confidence"] = "weak_inference"  # conservative fallback
    return content


class ResumeGenerator:
    def __init__(
        self,
        evidence_selector: Any,
        keyword_extractor: Any,
        ats_scorer: Any,
        ollama_client: Any,
        prompt_loader: Any,
        session: Session,
    ) -> None:
        self._selector = evidence_selector
        self._kw_extractor = keyword_extractor
        self._ats_scorer = ats_scorer
        self._ollama = ollama_client
        self._loader = prompt_loader
        self._resume_repo = ResumeRepository(session)

    def generate(
        self,
        job_description: str,
        template_name: str,
        application_id: str | None = None,
    ) -> dict:
        # Step 1: validate template (propagate ValueError for unknown names)
        template = get_template(template_name)

        # Step 2: extract keywords
        keywords: dict = self._kw_extractor.extract(job_description)

        # Step 3: select evidence bullets
        max_bullets: int = template.get("max_experience_bullets", 4) * 3
        evidence: list[dict] = self._selector.select(
            job_description, keywords, max_bullets=max_bullets
        )

        # Step 4: count weak inferences
        weak_count: int = sum(
            1 for e in evidence if e.get("confidence") == "weak_inference"
        )

        # Step 5: build content via LLM or rule-based fallback
        content_json: dict = self._build_content(
            job_description, template_name, keywords, evidence
        )

        # Step 6: score against ATS
        resume_text: str = self._content_to_text(content_json)
        ats_score: dict = self._ats_scorer.score(resume_text, job_description, keywords)

        # Step 7: persist to DB
        try:
            resume = self._resume_repo.create(
                name=f"Resume — {keywords.get('industry', 'general')} ({template_name})",
                application_id=application_id,
                content_json=content_json,
                ats_score=float(ats_score["overall_score"]),
                page_count=1,
                is_master=False,
            )
        except IntegrityError as exc:
            raise ValueError(f"Invalid application_id: {application_id}") from exc

        return {
            "resume_id": resume.id,
            "content_json": content_json,
            "ats_score": ats_score,
            "weak_inference_count": weak_count,
            "requires_approval": weak_count > 0,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_content(
        self,
        job_description: str,
        template_name: str,
        keywords: dict,
        evidence: list[dict],
    ) -> dict:
        if self._ollama and self._ollama.is_available():
            return self._llm_build(job_description, template_name, keywords, evidence)
        return self._rule_based_build(template_name, evidence)

    def _llm_build(
        self,
        job_description: str,
        template_name: str,
        keywords: dict,
        evidence: list[dict],
    ) -> dict:
        try:
            prompt_data: dict = self._loader.load("resume/generate")
            evidence_json = json.dumps(
                [
                    {
                        "text": e["bullet_text"],
                        "confidence": e["confidence"],
                        "evidence_id": e["evidence_id"],
                        "company": e["company"],
                        "title": e["title"],
                        "dates": e["dates"],
                    }
                    for e in evidence
                ],
                indent=2,
            )
            user_prompt: str = prompt_data["user_template"].format(
                job_description=job_description[:2000],
                job_title="",
                company="",
                industry=keywords.get("industry", ""),
                template_name=template_name,
                keywords=", ".join(
                    keywords.get("required_skills", []) + keywords.get("keywords", [])
                ),
                evidence_json=evidence_json,
            )
            raw: str = self._ollama.generate(
                model=_DEFAULT_MODEL,
                prompt=user_prompt,
                temperature=0.2,
                system=prompt_data["system"],
            )
            content: dict = json.loads(raw)
            return _normalize_confidence(content)
        except Exception as exc:
            logger.warning(
                "resume_generator: LLM build failed (%s), using rule-based fallback",
                exc,
            )
            return self._rule_based_build(template_name, evidence)

    def _rule_based_build(
        self, template_name: str, evidence: list[dict]
    ) -> dict:
        by_exp: dict[str, dict] = {}
        for e in evidence:
            key = e.get("experience_id") or e["evidence_id"]
            if key not in by_exp:
                by_exp[key] = {
                    "title": e.get("title", ""),
                    "company": e.get("company", ""),
                    "dates": e.get("dates", ""),
                    "bullets": [],
                }
            by_exp[key]["bullets"].append(
                {
                    "text": e["bullet_text"],
                    "evidence_id": e["evidence_id"],
                    "confidence": e["confidence"],
                }
            )
        return {
            "summary": "",
            "experiences": list(by_exp.values()),
            "skills": [],
            "projects": [],
            "education": [],
        }

    def _content_to_text(self, content_json: dict) -> str:
        parts: list[str] = [content_json.get("summary", "")]
        for exp in content_json.get("experiences", []):
            parts.append(f"{exp.get('title', '')} at {exp.get('company', '')}")
            for bullet in exp.get("bullets", []):
                text = bullet.get("text", "") if isinstance(bullet, dict) else str(bullet)
                parts.append(text)
        parts.extend(str(s) for s in content_json.get("skills", []))
        return "\n".join(p for p in parts if p)
