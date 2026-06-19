from __future__ import annotations

import io
import logging
from docx import Document  # type: ignore[name-defined]
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

logger = logging.getLogger(__name__)

_WEAK_MARKER = "⚠ [REVIEW REQUIRED]"


class ResumeDOCXExporter:
    def export(self, content_json: dict, template_name: str) -> bytes:
        """
        Export resume content to DOCX bytes.

        Args:
            content_json: Resume content dictionary with summary, experiences, skills, projects, education
            template_name: Template name (currently unused, reserved for future use)

        Returns:
            DOCX file as bytes. Never raises exceptions; returns minimal DOCX with error message on failure.
        """
        try:
            doc = Document()  # type: ignore[operator]
            self._set_margins(doc)
            self._add_experiences(doc, content_json.get("experiences", []))
            self._add_skills(doc, content_json.get("skills", []))
            self._add_projects(doc, content_json.get("projects", []))
            buffer = io.BytesIO()
            doc.save(buffer)
            return buffer.getvalue()
        except Exception as exc:
            logger.error("docx_exporter: failed to generate DOCX: %s", exc)
            doc = Document()  # type: ignore[operator]
            doc.add_paragraph("Resume generation error. Please try again.")
            buffer = io.BytesIO()
            doc.save(buffer)
            return buffer.getvalue()

    def _set_margins(self, doc: object) -> None:
        """Set document margins to 36pt (top/bottom) and 54pt (left/right)."""
        for section in doc.sections:  # type: ignore[attr-defined]
            section.top_margin = Pt(36)
            section.bottom_margin = Pt(36)
            section.left_margin = Pt(54)
            section.right_margin = Pt(54)

    def _add_experiences(self, doc: object, experiences: list[dict]) -> None:
        """Add experiences section with title, company, dates, and bullets."""
        if not experiences:
            return
        doc.add_heading("Experience", level=2)  # type: ignore[attr-defined]
        for exp in experiences:
            p = doc.add_paragraph()  # type: ignore[attr-defined]
            run = p.add_run(f"{exp.get('title', '')} — {exp.get('company', '')}")  # type: ignore[attr-defined]
            run.bold = True
            p.add_run(f"  {exp.get('dates', '')}")  # type: ignore[attr-defined]
            for bullet in exp.get("bullets", []):
                if isinstance(bullet, dict):
                    text = bullet.get("text", "")
                    confidence = bullet.get("confidence", "verified")
                else:
                    text = str(bullet)
                    confidence = "verified"
                bullet_para = doc.add_paragraph(style="List Bullet")  # type: ignore[attr-defined]
                if confidence == "weak_inference":
                    run = bullet_para.add_run(f"{_WEAK_MARKER} {text}")  # type: ignore[attr-defined]
                    run.font.color.rgb = RGBColor(0xFF, 0x80, 0x00)
                else:
                    bullet_para.add_run(text)  # type: ignore[attr-defined]

    def _add_skills(self, doc: object, skills: list[str]) -> None:
        """Add skills section as bullet-separated list."""
        if not skills:
            return
        doc.add_heading("Skills", level=2)  # type: ignore[attr-defined]
        doc.add_paragraph(" · ".join(skills))  # type: ignore[attr-defined]

    def _add_projects(self, doc: object, projects: list[dict]) -> None:
        """Add projects section with name, description, and tech stack."""
        if not projects:
            return
        doc.add_heading("Projects", level=2)  # type: ignore[attr-defined]
        for proj in projects:
            p = doc.add_paragraph()  # type: ignore[attr-defined]
            run = p.add_run(proj.get("name", ""))  # type: ignore[attr-defined]
            run.bold = True
            desc = proj.get("description", "")
            tech = proj.get("tech", "")
            if desc:
                p.add_run(f" — {desc}")  # type: ignore[attr-defined]
            if tech:
                p.add_run(f" [{tech}]")  # type: ignore[attr-defined]
