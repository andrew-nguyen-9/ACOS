from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_LLM_MODEL = "qwen3:8b"

LENGTH_TARGETS: dict[str, int] = {
    "short": 100,
    "medium": 250,
    "long": 400,
    "full": 600,
}


class CoverLetterGenerator:
    def __init__(
        self,
        evidence_selector: Any,
        voice_modeler: Any,
        ollama_client: Any,
        prompt_loader: Any,
    ) -> None:
        self._selector = evidence_selector
        self._voice = voice_modeler
        self._ollama = ollama_client
        self._loader = prompt_loader

    def generate(
        self,
        job_description: str,
        company: str,
        job_title: str,
        length_target: str,
    ) -> dict:
        """Generate a cover letter for the given job.

        Args:
            job_description: Full text of the job description.
            company: Name of the company.
            job_title: Title of the role being applied for.
            length_target: One of "short", "medium", "long", "full".

        Returns:
            Dict with keys: text, word_count, length_target, requires_approval.

        Raises:
            ValueError: If length_target is not a valid variant.
        """
        if length_target not in LENGTH_TARGETS:
            raise ValueError(
                f"Invalid length_target '{length_target}'. Valid: {list(LENGTH_TARGETS)}"
            )

        target_words = LENGTH_TARGETS[length_target]
        profile = self._voice.get_or_create_default()
        evidence = self._selector.select(job_description, {}, max_bullets=6)
        weak_count = sum(1 for e in evidence if e.get("confidence") == "weak_inference")

        if self._ollama and self._ollama.is_available():
            text = self._llm_generate(
                job_description, company, job_title, length_target, target_words, profile, evidence
            )
        else:
            text = self._template_generate(company, job_title, evidence, target_words)

        return {
            "text": text,
            "word_count": len(text.split()),
            "length_target": length_target,
            "requires_approval": weak_count > 0,
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
    ) -> str:
        """Generate cover letter text via LLM; falls back to template on any error."""
        try:
            prompt_data = self._loader.load("cover_letter/generate")
            evidence_json = json.dumps(
                [
                    {
                        "text": e["bullet_text"],
                        "company": e["company"],
                        "title": e["title"],
                        "confidence": e["confidence"],
                    }
                    for e in evidence
                ],
                indent=2,
            )
            user = prompt_data["user_template"].format(
                job_description=job_description[:2000],
                company=company,
                job_title=job_title,
                industry="",
                length_target=target_words,
                tone_descriptors=", ".join(profile.get("tone_descriptors", [])),
                vocabulary_patterns=json.dumps(profile.get("vocabulary_patterns", {})),
                sample_sentences="\n".join(profile.get("sample_sentences", [])),
                evidence_json=evidence_json,
                keywords="",
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
        """Build a minimal cover letter from evidence bullets without LLM."""
        lines: list[str] = [
            "Dear Hiring Manager,",
            "",
            f"I am writing to express my strong interest in the {job_title} position at {company}.",
            "",
        ]
        for e in evidence[:3]:
            bullet = e.get("bullet_text", "")
            title = e.get("title", "a professional")
            lines.append(
                f"In my previous role as {title}, I {bullet.lower().lstrip('abcdefghijklmnopqrstuvwxyz '[:0])}."
            )
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
