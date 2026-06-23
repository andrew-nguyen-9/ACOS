# Phase 13.5 — Onboarding Doc-Upload + Cold-Start Surfacing — Design

**Date:** 2026-06-23
**Branch:** `feat/phase-13-surfacing-onboarding-packaging`
**Status:** Approved design → implementation

## Goal

Let a new user build their profile during first-run by uploading documents, and surface
what the existing ingestion build produced (skills + Career-Voice) with honest confidence
labelling. The step is fully **skippable** — a user with nothing to upload still completes
onboarding.

## Reality check (why this scope, not the prompt's literal scope)

The build prompt assumes a "Backend cold-start (12.3)" intelligence engine. It does not
exist: commit `943cc62` ("Phase 12.3") was the **sidecar-warmup skeleton**
(`useBackendReady` + `AppShell` gate), not an onboarding-intelligence service. Grounded in
the actual backend:

| Building block | Reality | Decision |
|---|---|---|
| Validated upload + build | `POST /ingest` → background job (parse → skill entities into KG with `confidence` → RAG index), SSE at `/ingest/{job}/stream` | **Reuse as-is** (satisfies the secure-upload trap) |
| Skill graph | `KnowledgeGraphNodeRepository.get_by_type("skill")`; each node `properties.confidence` | Read it |
| Career-Voice | `VoiceModeler.get_or_create_default()` → latest `WritingProfile`, else `_DEFAULT_PROFILE` with `profile_id=None` | Surface it; `profile_id is None` ⇒ **synthetic** |
| Synthetic *skill* templates | **Do not exist** | **Do not build** (ponytail rung 1; CLAUDE.md #1 — never fabricate user history). Skip = empty skills. |
| ATS baseline | `/resume/analyze-ats` scores a resume **against a target JD**; no JD at onboarding | **Omit from onboarding summary** |
| Experience graph | Experiences are RAG docs, not structured nodes | Surface as a **document count**, not a graph |

Both forks confirmed with the user: *Honest minimal* cold-start, *Omit ATS*.

## Architecture

### Backend — one thin read route

`GET /onboarding/summary` (new, in a small `backend/api/v1/routes/onboarding.py`), reading
existing services only — no new engine, no writes:

```jsonc
{
  "skills": [{ "label": "Python", "confidence": "weak_inference" }, ...],
  "documents": { "count": 3 },               // completed Document rows
  "career_voice": {
    "tone_descriptors": ["professional", ...],
    "structure_patterns": [...],
    "sample_sentences": [...],
    "synthetic": true                          // profile_id is None ⇒ default template
  }
}
```

- **skills**: `KnowledgeGraphNodeRepository.get_by_type("skill")` → `{label, properties.confidence or "weak_inference"}`. Empty list when nothing ingested.
- **documents.count**: `len(DocumentRepository.get_by_status("complete"))`. No new repo method.
- **career_voice**: `VoiceModeler.get_or_create_default()`; `synthetic = profile_id is None`. (We do not expose `vocabulary_patterns` to the wizard — not needed for surfacing.)

Dependency wiring follows the existing route pattern (session dependency, service
construction). `VoiceModeler` needs an ollama client + prompt loader to *learn*, but
`get_or_create_default()` only reads the repo / returns the constant — construct it with the
same deps the cover-letter route already uses.

### Frontend — extend the wizard `profile` step

`FirstRunWizard.tsx` keeps its `welcome → ollama → profile → done` machine. The `profile`
step gains an upload sub-section above the existing model/GitHub fields:

1. File input (`accept=".txt,.md,.markdown,.pdf,.docx"`, multiple) → on select, each file
   `POST /ingest` (multipart) → collect `job_id`s.
2. Per-job SSE progress via `/ingest/{job_id}/stream` (reuse existing stream helper if
   present; else a minimal `EventSource`). Show queued/processing/complete/failed per file.
3. When all jobs reach a terminal state → `GET /onboarding/summary` → render:
   - **Skills**: chips with `ConfidenceBadge level={confidence}`. Empty → `EmptyState`
     ("No skills yet — upload a resume or skip").
   - **Career-Voice**: tone descriptors + a sample sentence; when `synthetic`, a clear
     **"Synthetic — starter template, not from your writing"** label (amber, mirrors the
     `weak_inference` treatment).
   - **Documents**: "Built from N document(s)".
4. **Skip / Continue**: existing "Finish Setup" still calls `finishSetup()` regardless of
   upload state. A "Skip upload" affordance is simply not uploading — the summary section is
   optional and never blocks `finishSetup`.

New FE files:
- `frontend/src/services/ingestion.ts` — `ingestDocument(file): Promise<{job_id}>` (raw
  `fetch` with `FormData`; **not** `apiFetch`, which hard-codes `Content-Type: application/json`
  and would break the multipart boundary), `getOnboardingSummary()` via `apiFetch`, and a
  small `streamIngestStatus(jobId, onUpdate)` over `EventSource` (or poll `GET /ingest/{id}`).
- `frontend/src/components/onboarding/UploadStep.tsx` — the upload + summary UI, kept out of
  the wizard file to keep `FirstRunWizard.tsx` focused.
- `frontend/src/types/onboarding.ts` — `OnboardingSummary` type.

Polling vs SSE: prefer **poll `GET /ingest/{id}` every ~800ms until terminal** — simpler than
wiring `EventSource` lifecycle into a wizard, and ingestion is short. `// ponytail: poll, swap
to SSE if a large-file build makes the poll feel slow`.

## Data flow

```
user picks files
  → POST /ingest (×N)         [existing, validated]
  → poll GET /ingest/{id}     until complete/failed (×N)
  → GET /onboarding/summary   [new thin read]
  → render skills (ConfidenceBadge) + Career-Voice (synthetic label) + doc count
  → Finish Setup (unchanged finishSetup)  ← always reachable
```

## Error handling

- Upload rejected by backend (400 bad ext / 422 too large): show the file's error inline,
  other files proceed. No crash.
- A job ends `failed`: mark that file failed, continue; summary still renders from whatever
  completed.
- `GET /onboarding/summary` fails: show a non-blocking notice; Finish Setup still works.
- Backend unreachable: upload sub-section degrades to a disabled state with a message; the
  rest of the wizard (model/GitHub/finish) is unaffected.

## Testing

**Backend** (`backend/tests/unit/test_onboarding_route.py`):
- summary with seeded KG skills + complete docs → correct skills/confidence + count.
- no writing profile → `career_voice.synthetic is True` and tone descriptors == defaults.
- existing writing profile → `synthetic is False`.
- empty DB → `skills == []`, `count == 0`, synthetic voice (skippable path is valid).

**Frontend** (vitest, `UploadStep.test.tsx` + service):
- selecting a file POSTs to `/ingest` (mock fetch asserts multipart + endpoint).
- summary renders skills with confidence badges; a `synthetic` career-voice shows the
  Synthetic label; non-synthetic does not.
- skip path: render wizard, never upload, Finish Setup still calls `completeOnboarding`.
- upload error (422) renders inline without blocking Finish Setup.

**E2E** (`onboarding` spec, self-mocked backend): upload → summary surfaces → finish; and a
pure-skip run completes. Perf gate: no long-tasks / 60fps on the wizard (consistent with the
phase's FE gate).

## Out of scope (explicit)

- No synthetic skill/experience fabrication (no cold-start engine).
- No ATS at onboarding (needs a JD target).
- No new ingestion engine, parser, or scoring.
- Writing-profile *learning* from uploads stays where it is (cover-letter flow); onboarding
  only *surfaces* the current/default voice.

## Definition of done

Upload → skill/Career-Voice/doc-count surfaced with honest confidence labels, secure reused
upload path, fully skippable, vitest + backend tests green, perf gate passed, one commit.
