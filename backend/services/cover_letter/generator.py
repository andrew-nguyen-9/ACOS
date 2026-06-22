from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.services.cover_letter.consistency_validator import ConsistencyValidator

logger = logging.getLogger(__name__)

_DEFAULT_LLM_MODEL = "qwen3:8b"

LENGTH_TARGETS: dict[str, int] = {
    "short": 100,
    "medium": 250,
    "long": 400,
    "full": 600,
}


def tone_descriptor(tone: float) -> str:
    """Map a 0..1 tone dial (Phase 11.9, RCL-003) to a prompt tone band.

    0 = Traditional, 1 = Bold. Clamped, so out-of-range slider values are safe.
    """
    t = 0.0 if tone < 0 else 1.0 if tone > 1 else tone
    if t < 1 / 3:
        return "formal, traditional, measured"
    if t < 2 / 3:
        return "balanced, professional, confident"
    return "bold, dynamic, assertive"


class CoverLetterGenerator:
    def __init__(
        self,
        evidence_selector: Any,
        voice_modeler: Any,
        ollama_client: Any,
        prompt_loader: Any,
        *,
        consistency_validator: ConsistencyValidator | None = None,
    ) -> None:
        self._selector = evidence_selector
        self._voice = voice_modeler
        self._ollama = ollama_client
        self._loader = prompt_loader
        self._consistency = consistency_validator or ConsistencyValidator()

    def generate(
        self,
        job_description: str,
        company: str,
        job_title: str,
        length_target: str,
        resume_context: dict | None = None,
        tone: float | None = None,
    ) -> dict:
        """Generate a cover letter for the given job.

        Args:
            job_description: Full text of the job description.
            company: Name of the company.
            job_title: Title of the role being applied for.
            length_target: One of "short", "medium", "long", "full".
            resume_context: Optional dict from ResumeContext.to_dict(). When provided,
                the LLM is instructed to elaborate on selected bullets rather than repeat them.

        Returns:
            Dict with keys: text, word_count, length_target, requires_approval,
            consistency (ConsistencyResult dict).

        Raises:
            ValueError: If length_target is not a valid variant.
        """
        if length_target not in LENGTH_TARGETS:
            raise ValueError(
                f"Invalid length_target '{length_target}'. Valid: {list(LENGTH_TARGETS)}"
            )

        target_words = LENGTH_TARGETS[length_target]
        profile = self._voice.get_or_create_default()

        if resume_context is not None:
            evidence = resume_context.get("selected_bullets", [])
            excluded = resume_context.get("excluded_bullets", [])
        else:
            evidence = self._selector.select(job_description, {}, max_bullets=6)
            excluded = []

        weak_count = sum(1 for e in evidence if e.get("confidence") == "weak_inference")

        if self._ollama and self._ollama.is_available():
            text = self._llm_generate(
                job_description, company, job_title, length_target, target_words,
                profile, evidence, excluded, tone,
            )
        else:
            text = self._template_generate(company, job_title, evidence, target_words)

        consistency = self._consistency.validate(text, {"selected_bullets": evidence})

        return {
            "text": text,
            "word_count": len(text.split()),
            "length_target": length_target,
            "requires_approval": weak_count > 0,
            "consistency": {
                "consistent": consistency.consistent,
                "warnings": consistency.warnings,
            },
        }

    def _llm_generate(
        self,
        job_description: str,
        company: str,
        job_title: str,
        length_target: str,
        target_words: int,
        profile: dict,
        evidence: list[dict],
        excluded: list[dict],
        tone: float | None = None,
    ) -> str:
        try:
            prompt_data = self._loader.load("cover_letter/generate")
            evidence_json = json.dumps(
                [
                    {
                        "text": e.get("bullet_text", ""),
                        "company": e.get("company", ""),
                        "title": e.get("title", ""),
                        "confidence": e.get("confidence", "verified"),
                    }
                    for e in evidence
                ],
                indent=2,
            )
            excluded_json = json.dumps(
                [
                    {"text": e.get("bullet_text", ""), "company": e.get("company", "")}
                    for e in excluded[:6]
                ],
                indent=2,
            )
            descriptors = list(profile.get("tone_descriptors", []))
            # RCL-003: the tone dial overrides the learned voice's tone band.
            if tone is not None:
                descriptors = [tone_descriptor(tone), *descriptors]
            user = prompt_data["user_template"].format(
                job_description=job_description[:2000],
                company=company,
                job_title=job_title,
                industry="",
                length_target=target_words,
                tone_descriptors=", ".join(descriptors),
                vocabulary_patterns=json.dumps(profile.get("vocabulary_patterns", {})),
                sample_sentences="\n".join(profile.get("sample_sentences", [])),
                evidence_json=evidence_json,
                keywords="",
                selected_bullets_json=evidence_json,
                excluded_bullets_json=excluded_json,
            )
            return self._ollama.generate(
                model=_DEFAULT_LLM_MODEL,
                prompt=user,
                temperature=0.3,
                system=prompt_data["system"],
            )
        except Exception as exc:
            logger.warning("cl_generator: LLM failed, falling back to template: %s", exc)
            return self._template_generate(company, job_title, evidence, target_words)

    def _template_generate(
        self,
        company: str,
        job_title: str,
        evidence: list[dict],
        target_words: int,
    ) -> str:
        lines: list[str] = [
            "Dear Hiring Manager,",
            "",
            f"I am writing to express my strong interest in the {job_title} position at {company}.",
            "",
        ]
        for e in evidence[:3]:
            bullet = e.get("bullet_text", "")
            title = e.get("title", "a professional")
            stripped = re.sub(
                r"^(led|built|improved|designed|managed|created|developed|implemented)\s+",
                "",
                bullet.lower(),
                flags=re.IGNORECASE,
            )
            lines.append(f"In my previous role as {title}, I {stripped}.")
        lines += [
            "",
            (
                "I look forward to the opportunity to discuss how my experience "
                "aligns with your team's needs."
            ),
            "",
            "Sincerely,",
        ]
        return "\n".join(lines)
