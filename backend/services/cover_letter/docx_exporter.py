from __future__ import annotations

import io
import logging

from docx import Document
from docx.shared import Pt

logger = logging.getLogger(__name__)


class CoverLetterDOCXExporter:
    """Exports cover letter text to a DOCX byte stream.

    The ``export`` method never raises; it always returns bytes.
    """

    def export(self, text: str, job_title: str, company: str) -> bytes:
        """Render *text* into a DOCX document and return raw bytes.

        Args:
            text: Plain-text cover letter content (newlines delimit paragraphs).
            job_title: Role title (available for future header use).
            company: Company name (available for future header use).

        Returns:
            Raw DOCX bytes; never raises.
        """
        try:
            doc = Document()
            for section in doc.sections:
                section.top_margin = Pt(72)
                section.bottom_margin = Pt(72)
                section.left_margin = Pt(72)
                section.right_margin = Pt(72)
            for line in text.split("\n"):
                doc.add_paragraph(line)
            buffer = io.BytesIO()
            doc.save(buffer)
            return buffer.getvalue()
        except Exception as exc:
            logger.error(
                "cl_docx_exporter: primary export failed for '%s' @ '%s': %s",
                job_title,
                company,
                exc,
            )
            # Minimal fallback — still never raises
            try:
                doc = Document()
                doc.add_paragraph(text)
                buffer = io.BytesIO()
                doc.save(buffer)
                return buffer.getvalue()
            except Exception as inner_exc:
                logger.error("cl_docx_exporter: fallback also failed: %s", inner_exc)
                return b""
