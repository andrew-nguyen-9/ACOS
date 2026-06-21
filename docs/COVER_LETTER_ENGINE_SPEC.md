# Cover Letter Engine Specification

**Version:** 1.0
**Updated:** 2026-06-20

---

## Pipeline (Phase 8.1+)

```
ResumeContext (from resume/generate)
        ↓
CoverLetterGenerator.generate(resume_context=...)
        ↓
VoiceModeler.get_or_create_default()   → voice profile
        ↓
LLM prompt (selected_bullets + excluded_bullets + voice + JD + company + title)
        ↓
ConsistencyValidator.validate()        → ConsistencyResult
        ↓
Return: text, word_count, consistency_result
```

---

## Narrative Strategy

| Document | Question answered |
|----------|------------------|
| Resume | "What did the candidate accomplish?" |
| Cover letter | "Why do those accomplishments matter for THIS role?" |

**Rule:** The cover letter must NEVER copy a resume bullet verbatim. It elaborates on the WHY.

**Example:**
- Resume bullet: *Built a Python ETL platform that generated $3M+ in revenue.*
- Cover letter: *My experience building a Python ETL platform from MVP to production taught me how to identify high-leverage automation opportunities and drive measurable business outcomes.*

---

## Shared Data

Both resume and cover letter use `EvidenceSelector` → same ChromaDB RAG collections.
`ResumeContext` carries the selection decisions to the CL pipeline:
- `selected_bullets` — elaborate on these
- `excluded_bullets` — may reference if highly relevant
- `selection_scores` — why bullets were ranked
- `keywords` — from JD keyword extraction

---

## Length Targets

| Variant | Target words |
|---------|-------------|
| short | ~100 |
| medium | ~250 |
| long | ~400 |
| full | ~600 |

---

## Voice Modeling

Derived from past cover letters via `VoiceModeler.learn()`. Profile includes:
- `tone_descriptors` — e.g. ["professional", "confident", "results-oriented"]
- `structure_patterns` — e.g. ["hook → value proposition → evidence → call to action"]
- `vocabulary_patterns` — formal phrases, transition words, avoid list
- `sample_sentences` — representative sentences extracted from past letters

**Phase 8.2 extension:** Also derive voice from resume bullet style (action verb choices, quantification patterns).

---

## Consistency Checks

| Check | Type | Description |
|-------|------|-------------|
| Company reference | Warning | Cover letter must reference ≥1 resume company |
| Year consistency | Warning | Years in CL must appear in resume date ranges |

Warnings are non-blocking. Generation succeeds; implementer logs them.

---

## Definition of Success

The generated resume and cover letter should feel as though they were written together by the same person. A recruiter should see one coherent story — consistent accomplishments, voice, and positioning — without noticing any disconnect between the two documents.
