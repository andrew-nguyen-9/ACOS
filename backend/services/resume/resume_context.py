from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResumeContext:
    """In-memory bridge carrying resume selection decisions to the cover letter pipeline.

    Serializes to/from dict so it can be embedded in Resume.content_json without a migration.
    """

    resume_id: str
    job_title: str
    company: str
    keywords: list[str] = field(default_factory=list)
    selected_bullets: list[dict] = field(default_factory=list)
    excluded_bullets: list[dict] = field(default_factory=list)
    selection_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "resume_id": self.resume_id,
            "job_title": self.job_title,
            "company": self.company,
            "keywords": self.keywords,
            "selected_bullets": self.selected_bullets,
            "excluded_bullets": self.excluded_bullets,
            "selection_scores": self.selection_scores,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResumeContext":
        return cls(
            resume_id=data["resume_id"],
            job_title=data["job_title"],
            company=data["company"],
            keywords=data.get("keywords", []),
            selected_bullets=data.get("selected_bullets", []),
            excluded_bullets=data.get("excluded_bullets", []),
            selection_scores=data.get("selection_scores", {}),
        )
