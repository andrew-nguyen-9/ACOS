# ADR-006: Evidence-Based Confidence System for All Generated Content

**Status:** Accepted  
**Date:** 2026-06-18  
**Deciders:** Andrew Nguyen

---

## Context

AI-generated career content carries a hallucination risk. Specifically:
- Generated resumes may invent metrics ("increased revenue by 40%")
- Generated cover letters may invent projects or responsibilities
- Generated Q&A answers may attribute fake achievements

In a legal consulting context where the user has deep experience validating evidence,
this is not acceptable. Every generated statement must be traceable to a source.

---

## Decision

Every generated text unit (bullet, sentence, claim) receives an explicit confidence level:

| Level | Definition | Usage |
|-------|-----------|-------|
| `verified` | Direct evidence exists in a source document | Use freely |
| `strong_inference` | Multiple supporting records exist; no direct evidence | Use with citation |
| `weak_inference` | Model-generated assumption; no supporting records | Flag for user review before use |

Rules:
1. Prompts MUST instruct the model to assign confidence to each statement
2. Weak inference content is visually flagged in the UI (yellow highlight)
3. Weak inference content cannot be exported to DOCX without user confirmation
4. The evidence panel shows source documents for every non-weak statement
5. `generation_logs` records the confidence distribution of every generation

---

## Consequences

**Positive:**
- Eliminates hallucinated metrics, employers, dates, and certifications
- User can trust exported documents without manual review of every line
- Evidence panel provides transparency and builds trust
- Aligns with professional standards (litigation context)
- Differentiates ACOS from generic AI resume tools

**Negative:**
- More complex prompt engineering
- Structured output (JSON with confidence fields) constrains model creativity
- User must confirm weak-inference items before export — adds a step

**Mitigations:**
- The knowledge graph is well-populated with real evidence, reducing weak-inference rate
- UI makes confirmation flow fast (checkbox + single click)
- Weak inference is explicitly useful for "bridge" language (transitions, soft skills)

---

## Prohibited Content

The following may NEVER appear in generated output regardless of confidence:

- Invented metrics (`"increased revenue by X%"` — only real metrics from evidence)
- Invented employer names
- Invented certification names
- Invented project names
- Invented dates
- Composite fabrications (real employer + invented project)
