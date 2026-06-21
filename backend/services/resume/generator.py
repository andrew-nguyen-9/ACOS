from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.observability import log_operation
from backend.repositories.resume import ResumeRepository
from backend.services.resume.bullet_rewriter import BulletRewriter
from backend.services.resume.bullet_scorer import BulletScorer
from backend.services.resume.content_selector import ContentSelector
from backend.services.resume.layout_engine import LayoutEngine
from backend.services.resume.resume_context import ResumeContext
from backend.services.resume.templates import get_template
from backend.services.resume.validator import ResumeValidator

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "qwen3:8b"
_VALID_CONFIDENCE = {"verified", "strong_inference", "weak_inference"}
_MAX_LAYOUT_ITERATIONS = 20


def _normalize_confidence(content: dict) -> dict:
    for exp in content.get("experiences", []):
        for bullet in exp.get("bullets", []):
            if isinstance(bullet, dict):
                if bullet.get("confidence") not in _VALID_CONFIDENCE:
                    bullet["confidence"] = "weak_inference"
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
        *,
        bullet_scorer: BulletScorer | None = None,
        content_selector: ContentSelector | None = None,
        bullet_rewriter: BulletRewriter | None = None,
        layout_engine: LayoutEngine | None = None,
        validator: ResumeValidator | None = None,
    ) -> None:
        self._selector = evidence_selector
        self._kw_extractor = keyword_extractor
        self._ats_scorer = ats_scorer
        self._ollama = ollama_client
        self._loader = prompt_loader
        self._resume_repo = ResumeRepository(session)

        self._bullet_scorer = bullet_scorer or BulletScorer()
        self._content_selector = content_selector or ContentSelector()
        self._bullet_rewriter = bullet_rewriter or BulletRewriter()
        self._layout_engine = layout_engine or LayoutEngine()
        self._validator = validator or ResumeValidator()

    def generate(
        self,
        job_description: str,
        template_name: str,
        application_id: str | None = None,
        company: str = "",
        job_title: str = "",
    ) -> dict:
        # Step 1: validate template
        template = get_template(template_name)

        # Step 2: extract keywords
        keywords: dict = self._kw_extractor.extract(job_description)
        kw_list: list[str] = keywords.get("required_skills", []) + keywords.get("keywords", [])

        # Step 3: select evidence (wider pool for scoring)
        max_bullets: int = template.get("max_experience_bullets", 4) * 3
        raw_evidence: list[dict] = self._selector.select(
            job_description, keywords, max_bullets=max_bullets * 2
        )

        # Step 4: score → rank → select (density-aware) → rewrite
        scored: list[dict] = self._bullet_scorer.score_many(raw_evidence, kw_list)
        selected, excluded = self._content_selector.select(scored, max_bullets=max_bullets)
        rewritten: list[dict] = [
            {**b, "bullet_text": self._bullet_rewriter.compress(b["bullet_text"])}
            for b in selected
        ]

        # Step 5: count weak inferences from selected set
        weak_count: int = sum(
            1 for e in rewritten if e.get("confidence") == "weak_inference"
        )

        # Step 6: build content via LLM or rule-based
        content_json: dict = self._build_content(
            job_description, template_name, keywords, rewritten,
            company=company, job_title=job_title,
        )

        # Step 7: layout optimization (shrink to fit page)
        content_json, excluded = self._optimize_layout(content_json, excluded)

        # Step 8: validate
        estimated_lines = self._layout_engine.estimate_resume(
            {"experiences": content_json.get("experiences", [])}
        ).total_lines
        content_json["_estimated_lines"] = estimated_lines
        validation = self._validator.validate(content_json)

        # Step 9: ATS score
        resume_text: str = self._content_to_text(content_json)
        ats_score: dict = self._ats_scorer.score(resume_text, job_description, keywords)

        # Step 10: persist
        try:
            resume = self._resume_repo.create(
                name=f"Resume — {job_title or keywords.get('industry', 'general')} ({template_name})",
                application_id=application_id,
                content_json=content_json,
                ats_score=float(ats_score["overall_score"]),
                page_count=1,
                is_master=False,
            )
        except IntegrityError as exc:
            raise ValueError(f"Invalid application_id: {application_id}") from exc

        # Step 11: build context for cover letter pipeline
        resume_context = ResumeContext(
            resume_id=resume.id,
            job_title=job_title,
            company=company,
            keywords=kw_list,
            selected_bullets=selected,
            excluded_bullets=excluded,
            selection_scores={
                b.get("evidence_id", ""): b.get("score", 0.0) for b in selected
            },
        )

        bullet_count = sum(
            len(exp.get("bullets", [])) for exp in content_json.get("experiences", [])
        )
        log_operation(
            "resume_generate",
            resume_id=resume.id,
            template=template_name,
            bullets=bullet_count,
            weak=weak_count,
        )
        return {
            "resume_id": resume.id,
            "content_json": content_json,
            "ats_score": ats_score,
            "weak_inference_count": weak_count,
            "requires_approval": weak_count > 0,
            "resume_context": resume_context.to_dict(),
            "validation": {
                "valid": validation.valid,
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
        }

    # ── Layout optimization ──────────────────────────────────────────────────

    def _optimize_layout(
        self,
        content_json: dict,
        excluded: list[dict],
    ) -> tuple[dict, list[dict]]:
        """Shrink content to fit within MAX_PAGE_LINES by trimming weakest bullets."""
        for _ in range(_MAX_LAYOUT_ITERATIONS):
            result = self._layout_engine.estimate_resume(
                {"experiences": content_json.get("experiences", [])}
            )
            if result.fits:
                break
            experiences = content_json.get("experiences", [])
            if not experiences:
                break
            # Remove the last bullet from the role with the most bullets
            target = max(experiences, key=lambda e: len(e.get("bullets", [])))
            bullets = target.get("bullets", [])
            if not bullets:
                break
            bullets.pop()
        return content_json, excluded

    # ── Content builders ─────────────────────────────────────────────────────

    def _build_content(
        self,
        job_description: str,
        template_name: str,
        keywords: dict,
        evidence: list[dict],
        company: str = "",
        job_title: str = "",
    ) -> dict:
        if self._ollama and self._ollama.is_available():
            return self._llm_build(
                job_description, template_name, keywords, evidence,
                company=company, job_title=job_title,
            )
        return self._rule_based_build(template_name, evidence)

    def _llm_build(
        self,
        job_description: str,
        template_name: str,
        keywords: dict,
        evidence: list[dict],
        company: str = "",
        job_title: str = "",
    ) -> dict:
        try:
            prompt_data: dict = self._loader.load("resume/generate")
            evidence_json = json.dumps(
                [
                    {
                        "text": e["bullet_text"],
                        "confidence": e["confidence"],
                        "evidence_id": e["evidence_id"],
                        "company": e.get("company", ""),
                        "title": e.get("title", ""),
                        "dates": e.get("dates", ""),
                    }
                    for e in evidence
                ],
                indent=2,
            )
            user_prompt: str = prompt_data["user_template"].format(
                job_description=job_description[:2000],
                job_title=job_title,
                company=company,
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
                "resume_generator: LLM build failed (%s), using rule-based fallback", exc
            )
            return self._rule_based_build(template_name, evidence)

    def _rule_based_build(self, template_name: str, evidence: list[dict]) -> dict:
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
            "experiences": list(by_exp.values()),
            "skills": [],
            "projects": [],
            "education": [],
        }

    def _content_to_text(self, content_json: dict) -> str:
        parts: list[str] = []
        for exp in content_json.get("experiences", []):
            parts.append(f"{exp.get('title', '')} at {exp.get('company', '')}")
            for bullet in exp.get("bullets", []):
                text = bullet.get("text", "") if isinstance(bullet, dict) else str(bullet)
                parts.append(text)
        parts.extend(str(s) for s in content_json.get("skills", []))
        return "\n".join(p for p in parts if p)
