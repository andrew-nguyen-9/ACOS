from __future__ import annotations

from backend.services.intelligence.project_skill_mapper import ProjectSkillMapper
from backend.services.intelligence.semantic_chunker import SemanticChunker
from backend.services.intelligence.skill_normalizer import SkillNormalizer


class IndexPreprocessor:
    """Compose the index-time text transforms: normalize → expand → chunk.

    Apply before embedding so synonyms cluster, projects surface their skills,
    and compound bullets embed as atomic clauses.
    """

    def __init__(self) -> None:
        self._normalizer = SkillNormalizer()
        self._mapper = ProjectSkillMapper()
        self._chunker = SemanticChunker()

    def preprocess(self, text: str, is_project: bool = False) -> list[str]:
        text = self._normalizer.normalize(text)
        if is_project:
            text = self._mapper.expand(text)
        return self._chunker.chunk(text)
