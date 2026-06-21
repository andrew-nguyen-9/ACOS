# Current Sprint

**Phase:** 8.1 — Resume + Cover Letter Engine Revamp
**Branch:** feat/phase-8-1-engine-revamp
**Status:** In progress
**Started:** 2026-06-20

## Objectives

1. Agent context activation (Context7 active; Ponytail/Caveman not installed — use auto-memory)
2. Resume engine: BulletScorer → ContentSelector → LayoutEngine → BulletRewriter → ResumeValidator
3. Resume Generator wired to full pipeline; emits `ResumeContext`
4. Cover letter engine: accept `ResumeContext`, elaborate rather than repeat
5. Cross-document `ConsistencyValidator`
6. Routes updated: `resume_context` in response; `resume_id` accepted by CL generate

## Scoring Weights (revised from spec v1.0)

| Dimension | Weight |
|-----------|--------|
| Impact | 0.35 |
| Quantification | 0.25 |
| Keyword relevance | 0.20 |
| Leadership | 0.10 |
| Uniqueness | 0.10 |

## Layout Parameters

- Max lines per page: **60**
- Bullet character width: **88** chars/line
- Continuation indent width: **92** chars/line
- Preferred fill: 58–60 lines

## Active Plan

`docs/superpowers/plans/2026-06-20-phase-8-1-engine-revamp.md`

## Completed Phases

Phase 0–8 complete (see `docs/08_ROADMAP.md`).
Repository cleanup + navigation docs added in `561e274`.
