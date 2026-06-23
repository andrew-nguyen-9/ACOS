# Known Issues

> **Historical (Phase 8.1 era).** The entries below were filed during the resume/cover-letter
> engine revamp and predate Phases 9–13. Several were addressed by later phases (8.2 layout
> work, 10 intelligence layer, 13 surfacing). They are kept for traceability; verify against
> current code before acting. Live decisions/regressions are tracked in `docs/DECISIONS.md` and
> the phase plans, not here.

| ID | Area | Description | Priority | Status |
|----|------|-------------|----------|--------|
| KI-001 | Layout | Line estimation is heuristic (88 chars/line). True measurement requires DOCX→PDF (Phase 8.2). | Medium | Open |
| KI-002 | Scoring | Uniqueness score is intra-session only (detects duplicate bullets in current resume, not across applications). | Low | Open |
| KI-003 | Voice | VoiceModeler learns from past cover letters only; bullet writing style not incorporated. | Medium | Phase 8.2 |
| KI-004 | Renderer | `_render_education`, `_render_projects`, `_render_activities`, `_render_additional` are stubs in initial `ResumeRenderer`. | High | Phase 8.1 (Task 8) |
| KI-005 | Bullet | `BulletRewriter.force_single_line` truncates with `...` — may produce invalid bullet text. Use compression first. | Low | Open |
