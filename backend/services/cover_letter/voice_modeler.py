from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.resume import WritingProfileRepository

logger = logging.getLogger(__name__)

_DEFAULT_PROFILE = {
    "tone_descriptors": ["professional", "confident", "results-oriented"],
    "structure_patterns": ["hook → value proposition → evidence → call to action"],
    "vocabulary_patterns": {
        "formal_phrases": ["I am excited to", "I bring", "I have demonstrated"],
        "transition_words": ["furthermore", "additionally", "building on this"],
        "avoid": ["I feel", "I think", "I believe"],
    },
    "sample_sentences": [
        "I bring a proven track record of delivering measurable outcomes.",
        "My experience in [field] has equipped me to drive results from day one.",
    ],
}


class VoiceModeler:
    def __init__(self, ollama_client: Any, prompt_loader: Any, session: Session) -> None:
        self._ollama = ollama_client
        self._loader = prompt_loader
        self._profile_repo = WritingProfileRepository(session)

    def learn(self, source_texts: list[str]) -> dict:
        """
        Extract writing profile from cover letter texts and persist to database.

        Args:
            source_texts: List of cover letter texts to analyze.

        Returns:
            Dictionary with keys: profile_id, tone_descriptors, structure_patterns,
            vocabulary_patterns, sample_sentences.
        """
        profile_data = self._extract_profile(source_texts)
        profile = self._profile_repo.create(
            tone_descriptors=profile_data["tone_descriptors"],
            structure_patterns=profile_data["structure_patterns"],
            vocabulary_patterns=profile_data["vocabulary_patterns"],
            sample_sentences=profile_data["sample_sentences"],
            source_doc_ids=[],
        )
        return {
            "profile_id": profile.id,
            **profile_data,
        }

    def get_or_create_default(self) -> dict:
        """
        Get the latest WritingProfile or return default profile.

        Returns:
            Dictionary with keys: profile_id (or None), tone_descriptors,
            structure_patterns, vocabulary_patterns, sample_sentences.
        """
        existing = self._profile_repo.get_latest()
        if existing:
            return {
                "profile_id": existing.id,
                "tone_descriptors": existing.tone_descriptors,
                "structure_patterns": existing.structure_patterns,
                "vocabulary_patterns": existing.vocabulary_patterns,
                "sample_sentences": existing.sample_sentences,
            }
        return {"profile_id": None, **_DEFAULT_PROFILE}

    def _extract_profile(self, source_texts: list[str]) -> dict:
        """
        Extract profile data via LLM or use defaults if offline.

        Args:
            source_texts: List of cover letter texts to analyze.

        Returns:
            Dictionary with tone_descriptors, structure_patterns,
            vocabulary_patterns, and sample_sentences.
        """
        if not self._ollama or not self._ollama.is_available():
            return dict(_DEFAULT_PROFILE)
        try:
            prompt_data = self._loader.load("cover_letter/learn_voice")
            combined = "\n\n---\n\n".join(source_texts[:5])[:6000]
            user = prompt_data["user_template"].format(cover_letter_texts=combined)
            raw = self._ollama.generate(
                model="qwen3:8b",
                prompt=user,
                temperature=0.1,
                system=prompt_data["system"],
            )
            data = json.loads(raw)
            return {
                "tone_descriptors": data.get("tone_descriptors", []),
                "structure_patterns": data.get("structure_patterns", []),
                "vocabulary_patterns": data.get("vocabulary_patterns", {}),
                "sample_sentences": data.get("sample_sentences", []),
            }
        except Exception as exc:
            logger.warning("voice_modeler: extraction failed, using defaults: %s", exc)
            return dict(_DEFAULT_PROFILE)
