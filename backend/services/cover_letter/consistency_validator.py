from __future__ import annotations

import re
from dataclasses import dataclass, field

_YEAR_PATTERN = re.compile(r"\b(20\d{2}|19\d{2})\b")


@dataclass
class ConsistencyResult:
    consistent: bool
    warnings: list[str] = field(default_factory=list)


class ConsistencyValidator:
    """Cross-document consistency checks between a cover letter and its resume context.

    All checks are non-blocking (warnings only). Generation always succeeds.
    """

    def validate(self, cl_text: str, resume_context: dict) -> ConsistencyResult:
        warnings: list[str] = []
        bullets = resume_context.get("selected_bullets", [])

        self._check_company_reference(cl_text, bullets, warnings)
        self._check_year_consistency(cl_text, bullets, warnings)

        return ConsistencyResult(consistent=len(warnings) == 0, warnings=warnings)

    def _check_company_reference(
        self,
        cl_text: str,
        bullets: list[dict],
        warnings: list[str],
    ) -> None:
        companies = {b.get("company", "").strip() for b in bullets if b.get("company")}
        if not companies:
            return
        cl_lower = cl_text.lower()
        if not any(c.lower() in cl_lower for c in companies):
            warnings.append(
                "Cover letter does not reference any company from the resume. "
                f"Expected at least one of: {', '.join(sorted(companies))}."
            )

    def _check_year_consistency(
        self,
        cl_text: str,
        bullets: list[dict],
        warnings: list[str],
    ) -> None:
        cl_years = {int(y) for y in _YEAR_PATTERN.findall(cl_text)}
        if not cl_years:
            return

        resume_years: set[int] = set()
        for b in bullets:
            for y in _YEAR_PATTERN.findall(b.get("dates", "")):
                resume_years.add(int(y))

        if not resume_years:
            return

        min_year = min(resume_years)
        max_year = max(resume_years)

        for year in cl_years:
            if not (min_year <= year <= max_year):
                warnings.append(
                    f"Cover letter references year {year}, which is outside "
                    f"the resume date range ({min_year}–{max_year})."
                )
