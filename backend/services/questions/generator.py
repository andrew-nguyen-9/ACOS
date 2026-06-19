from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.question import AnswerRepository, QuestionRepository

logger = logging.getLogger(__name__)

_VALID_LENGTHS = {"short", "medium", "long"}
_VALID_CONFIDENCE = {"verified", "strong_inference", "weak_inference"}
_VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")

_FALLBACK_QUESTIONS = [
    {
        "question_template": "Tell me about your experience relevant to {{position}}.",
        "category": "behavioral",
    },
    {
        "question_template": "Why are you interested in the {{position}} role at {{company}}?",
        "category": "motivational",
    },
    {
        "question_template": "Describe a challenging situation in {{industry}} and how you handled it.",
        "category": "situational",
    },
    {
        "question_template": "What experience do you have with {{tech_stack}}?",
        "category": "technical",
    },
    {
        "question_template": "Where do you see yourself growing in the {{industry}} space?",
        "category": "motivational",
    },
]


def _interpolate(template: str, variables: dict[str, str]) -> str:
    """Replace {{var}} placeholders with values from variables dict."""
    def replace(m: re.Match) -> str:
        return variables.get(m.group(1), m.group(0))

    return _VARIABLE_PATTERN.sub(replace, template)


class QuestionGenerator:
    def __init__(
        self,
        ollama_client: Any,  # duck-typed OllamaClient
        prompt_loader: Any,  # duck-typed PromptLoader
        evidence_selector: Any,  # duck-typed EvidenceSelector
        session: Session,
    ) -> None:
        self._ollama = ollama_client
        self._loader = prompt_loader
        self._selector = evidence_selector
        self._session = session

    def generate_questions(
        self,
        job_description: str,
        company: str = "",
        position: str = "",
        industry: str = "",
        tech_stack: str = "",
        application_id: str | None = None,
    ) -> list[dict]:
        variables = {
            "company": company,
            "position": position,
            "industry": industry,
            "tech_stack": tech_stack,
        }
        raw = self._llm_generate_questions(job_description, variables)
        q_repo = QuestionRepository(self._session)
        results = []
        for item in raw:
            template = item.get("question_template", "")
            category = item.get("category", "behavioral")
            if category not in {
                "behavioral", "technical", "situational",
                "motivational", "cultural", "role_specific",
            }:
                category = "behavioral"
            detected_vars = _VARIABLE_PATTERN.findall(template)
            q = q_repo.create(
                question_template=template,
                category=category,
                length_target="medium",
                variables=detected_vars,
                source="generated",
                industry=industry or None,
            )
            results.append(
                {
                    "id": q.id,
                    "question_template": q.question_template,
                    "interpolated": _interpolate(q.question_template, variables),
                    "category": q.category,
                    "variables": q.variables,
                }
            )
        return results

    def generate_answer(
        self,
        question_id: str,
        variables: dict[str, str],
        application_id: str | None = None,
        length_target: str = "medium",
    ) -> dict:
        if length_target not in _VALID_LENGTHS:
            raise ValueError(f"Invalid length_target '{length_target}'")
        q_repo = QuestionRepository(self._session)
        a_repo = AnswerRepository(self._session)
        question = q_repo.get(question_id)
        if question is None:
            raise ValueError(f"Question not found: {question_id}")
        interpolated = _interpolate(question.question_template, variables)
        evidence = self._selector.select(interpolated, {}, max_bullets=6)
        answer_text, evidence_ids, confidence = self._llm_generate_answer(
            interpolated, evidence, length_target
        )
        answer = a_repo.create(
            question_id=question_id,
            application_id=application_id,
            original_answer=answer_text,
            confidence_level=confidence,
            evidence_ids=evidence_ids,
        )
        return {
            "answer_id": answer.id,
            "question_id": question_id,
            "interpolated_question": interpolated,
            "original_answer": answer.original_answer,
            "evidence_ids": answer.evidence_ids,
            "confidence_level": answer.confidence_level,
            "requires_approval": confidence == "weak_inference",
        }

    def edit_answer(
        self, answer_id: str, edited_text: str, diff_summary: str | None = None
    ) -> dict:
        a_repo = AnswerRepository(self._session)
        answer = a_repo.get(answer_id)
        if answer is None:
            raise ValueError(f"Answer not found: {answer_id}")
        answer.edited_answer = edited_text
        answer.diff_summary = diff_summary
        self._session.flush()
        self._session.refresh(answer)
        return {
            "answer_id": answer.id,
            "original_answer": answer.original_answer,
            "edited_answer": answer.edited_answer,
            "diff_summary": answer.diff_summary,
        }

    def _llm_generate_questions(
        self, job_description: str, variables: dict[str, str]
    ) -> list[dict]:
        if not self._ollama or not self._ollama.is_available():
            return _FALLBACK_QUESTIONS
        try:
            prompt_data = self._loader.load("questions/generate")
            user_prompt = prompt_data["user_template"].format(
                job_description=job_description,
                company=variables.get("company", ""),
                position=variables.get("position", ""),
                industry=variables.get("industry", ""),
                tech_stack=variables.get("tech_stack", ""),
            )
            raw = self._ollama.generate(
                model="qwen3:8b",
                prompt=user_prompt,
                system=prompt_data["system"],
                temperature=0.4,
            )
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                items = json.loads(match.group())
                if isinstance(items, list) and items:
                    return items
        except Exception:
            logger.exception("LLM question generation failed; using fallback")
        return _FALLBACK_QUESTIONS

    def _llm_generate_answer(
        self,
        question: str,
        evidence: list[dict],
        length_target: str,
    ) -> tuple[str, list[str], str]:
        evidence_ids = [
            e.get("evidence_id", "") for e in evidence if e.get("evidence_id")
        ]
        if not evidence:
            return (
                "Based on my professional background, I have relevant experience to address this question.",
                [],
                "weak_inference",
            )
        confidences = [e.get("confidence", "strong_inference") for e in evidence]
        if all(c == "verified" for c in confidences):
            overall_confidence = "verified"
        elif any(c in ("verified", "strong_inference") for c in confidences):
            overall_confidence = "strong_inference"
        else:
            overall_confidence = "weak_inference"

        if not self._ollama or not self._ollama.is_available():
            return self._template_answer(evidence, length_target), evidence_ids, overall_confidence

        evidence_text = "\n".join(
            f"- [{e.get('confidence', 'strong_inference')}] {e.get('bullet_text', '')}"
            for e in evidence[:8]
        )
        try:
            prompt_data = self._loader.load("questions/answer")
            user_prompt = prompt_data["user_template"].format(
                question=question,
                evidence=evidence_text,
                length_target=length_target,
            )
            raw = self._ollama.generate(
                model="qwen3:8b",
                prompt=user_prompt,
                system=prompt_data["system"],
                temperature=0.3,
            )
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                text = parsed.get("answer_text", "")
                conf = parsed.get("confidence_level", overall_confidence)
                if conf not in _VALID_CONFIDENCE:
                    conf = "weak_inference"
                if text:
                    return text, evidence_ids, conf
        except Exception:
            logger.exception("LLM answer generation failed; using template fallback")
        return self._template_answer(evidence, length_target), evidence_ids, overall_confidence

    def _template_answer(self, evidence: list[dict], length_target: str) -> str:
        bullets = [e.get("bullet_text", "") for e in evidence[:4] if e.get("bullet_text")]
        if not bullets:
            return "Based on my professional background, I have relevant experience in this area."
        if length_target == "short":
            return bullets[0]
        return "In my career, " + " Additionally, ".join(bullets[:3]) + "."
