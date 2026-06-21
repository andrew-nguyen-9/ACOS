# Architecture Decisions Log

Running log of non-ADR decisions made during development.
For formal ADRs see `docs/adr/`.

---

## 2026-06-20 — Phase 8.1: Scoring weights

**Decision:** 5-dimension scoring: impact×0.35, quantification×0.25, keyword×0.20, leadership×0.10, uniqueness×0.10.
**Why:** Matches Resume Engine Spec v1.0 (provided by Andrew). Weights reflect recruiter priorities: impact is most signal-dense, uniqueness prevents bullet repetition across experiences.
**How to apply:** `BulletScorer.score()` in `backend/services/resume/bullet_scorer.py`.

## 2026-06-20 — Phase 8.1: Line-based layout estimation

**Decision:** Layout uses line estimation (60 lines max, 88 chars/line for bullets) not char count.
**Why:** Lines map directly to page rendering; char count doesn't account for visual density. Matches user's `layout-engine.py` reference.
**How to apply:** `LayoutEngine` in `backend/services/resume/layout_engine.py`.

## 2026-06-20 — Phase 8.1: PDF page validation deferred

**Decision:** True PDF page count validation (DOCX→PDF→measure) is Phase 8.2.
**Why:** Requires `libreoffice`/`unoconv` as a runtime sidecar dep — incompatible with PyInstaller bundling strategy for Phase 7 release. Line estimation is sufficient for Phase 8.1.
**How to apply:** Add `# Phase 8.2: replace with PDF page count` comment where relevant.

## 2026-06-20 — Phase 8.1: No schema change for ResumeContext

**Decision:** `ResumeContext` is in-memory; `Resume.content_json` stores selected bullets; CL route reconstructs context from `resume_id`.
**Why:** YAGNI — avoids a migration for data that can be derived.
**How to apply:** `backend/services/resume/resume_context.py` + route logic in `cover_letter.py`.

## 2026-06-20 — Phase 8.1: BulletRewriter is non-destructive

**Decision:** `BulletRewriter` returns new strings; original bullets preserved in DB.
**Why:** Content re-use across future applications requires pristine originals; rewriting is view-layer logic.
**How to apply:** Call rewriter only during content assembly, not at ingestion time.
