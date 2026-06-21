# Resume Engine Specification

**Version:** 1.0
**Updated:** 2026-06-20

---

## Goal

Generate ATS-safe resumes that:
- Match the approved template exactly
- Remain one page
- Maximize candidate impact
- Preserve readability
- Produce deterministic output

---

## Pipeline (Phase 8.1+)

```
EvidenceSelector.select()         → raw_bullets (RAG + reranker, top_k=20–25)
        ↓
BulletScorer.score_many()         → scored_bullets (composite 0.0–∞, see weights)
        ↓
ContentSelector.select()          → (selected_bullets, excluded_bullets)
        ↓
BulletRewriter.normalize/compress → rewritten_bullets (filler removed, verbs enforced)
        ↓
ResumeGenerator._build_content()  → content_json (LLM or rule-based)
        ↓
LayoutEngine.estimate_resume()    → LayoutResult (total_lines, remaining, fits)
        ↓
  ┌─ if overflow: remove weakest bullet → re-estimate (loop)
  └─ if space: add next best bullet → re-estimate (loop)
        ↓
ResumeValidator.validate()        → ValidationResult (errors + warnings)
        ↓
Persist Resume + emit ResumeContext
```

---

## Scoring Weights

| Dimension | Weight | Signal |
|-----------|--------|--------|
| Impact | 0.35 | $, %, revenue, growth, saved, reduced, increased, generated |
| Quantification | 0.25 | Any digit in bullet |
| Keyword relevance | 0.20 | JD keyword overlap |
| Leadership | 0.10 | led, managed, recruited, built, directed, owned |
| Uniqueness | 0.10 | Penalizes bullets similar to already-selected ones |

---

## Layout Parameters

| Parameter | Value |
|-----------|-------|
| Max lines | 60 |
| Preferred fill | 58–60 lines |
| Minimum lines | 55 |
| Bullet char width | 88 chars/line |
| Continuation indent | 92 chars/line |
| Position header | 2 lines |
| Section header | 1 line |

### Section Density Rules

| Section | Bullets |
|---------|---------|
| Current role | 5–6 |
| Previous role | 2–4 |
| Projects | 2–3 per project |
| Activities | 1–2 per activity |
| Additional | 2 (skills + interests) |

---

## Bullet Rules

- **Format:** Start with action verb (see allowed list below)
- **Length:** 1 line preferred, 2 lines allowed, 3+ lines **forbidden**
- **Quantification:** Preferred; include metrics, %, $, headcount, dates
- **Forbidden phrases:** "Responsible for", "Worked on", "Helped with", "Participated in", "Assisted with"

### Allowed Action Verbs

Built, Led, Developed, Created, Designed, Automated, Generated, Implemented, Scaled,
Optimized, Improved, Reduced, Analyzed, Architected, Managed, Directed, Partnered,
Deployed, Delivered, Launched, Streamlined, Accelerated, Drove, Established, Expanded,
Championed, Pioneered, Mentored, Evaluated, Integrated, Overhauled, Spearheaded

---

## Validation Gates

**Errors (block export):**
1. Resume exceeds 60-line page limit
2. Any bullet ≥ 3 lines (> 176 chars at 88 chars/line)
3. Any bullet does not start with allowed action verb

**Warnings (non-blocking):**
4. < 30% of bullets are quantified
5. Any role has > 6 bullets (current) or > 4 bullets (previous)
6. Any bullet starts with a forbidden phrase

---

## ATS Requirements

**Forbidden:** Tables, text boxes, floating objects, images, icons, columns, headers/footers with content.

**Allowed:** Paragraphs, runs, tab stops, indentation, bold, italic, underline.

---

## True Page Measurement (Phase 8.2)

Phase 8.1 uses line estimation (heuristic). Phase 8.2 will implement:
1. Generate DOCX
2. Convert DOCX → PDF (via `libreoffice --headless`)
3. Read PDF page count (via `pypdf`)
4. Measure remaining space
5. Expand/compress until `page_count == 1` and `remaining_space <= threshold`

---

## Template Fidelity

| Element | Spec |
|---------|------|
| Font | Times New Roman |
| Name size | 14pt |
| Section header size | 11pt |
| Body size | 10pt |
| Margins | 0.5" all sides |
| Bullet style | Unicode • with hanging indent (NOT Word List Bullet style) |
| Date alignment | Right-aligned via tab stop |
| Company/location | Left-aligned |

---

## Definition of Success

A recruiter should not be able to distinguish between a manually written resume and a generated one without inspecting the underlying source document.
