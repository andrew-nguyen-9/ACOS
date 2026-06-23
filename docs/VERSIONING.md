# Versioning & Reproducibility (Phase 14.1)

One coherent answer to "what exactly is this build, and can I reproduce its output?"
This consolidates pieces that already existed (Alembic, `PromptVersion` prompt-lock
[ADR-010], model keep_alive/build [12.5], updater + prompt rollback [13.9]) into a
single surface. It does **not** rebuild any of them.

## App version — one home

The app semantic version lives in **`frontend/src-tauri/tauri.conf.json` → `version`**.
That is canonical: it ships in the DMG and drives the updater's `{{current_version}}`.
`backend/config.py` `app_version` **mirrors** it (the Python sidecar can't read the
Tauri config across the bundle boundary at runtime). They are kept in lock-step by
`test_app_version_single_source` — the suite fails if they drift, so there is no second
place to silently bump.

To release a new version: bump `tauri.conf.json` `version` **and** `config.py`
`app_version` together (the test enforces it).

## Version endpoint — `GET /api/v1/health/version`

Returns the reproducibility tuple for the running build:

```json
{
  "app_version": "0.1.0",
  "model": { "generator": "qwen3:8b", "embedder": "nomic-embed-text" },
  "prompt_versions": [ { "prompt_name": "resume/generate", "version": "2.0" } ],
  "migration_head": "b2c3d4e5f6a7"
}
```

- **`prompt_versions`** — the active (`is_active=True`) `PromptVersion` rows. Empty
  until a prompt has been promoted (ADR-010); that's honest, not an error.
- **`migration_head`** — the Alembic **script-directory** head, not the DB's stamped
  rev. The app provisions schema via `Base.metadata.create_all` (`database.py`), so
  `alembic_version` is never stamped at runtime; the meaningful "what schema does this
  build expect" answer is the head the migration scripts define. Memoized (can't change
  at runtime).

## Determinism — the honest guarantee

Generation is reproducible **only when the whole tuple is pinned**: `seed` + inputs +
prompt-version + model. Fix all four and you get the same output; let any one float and
you don't.

- **`seed`** threads `config → OllamaClient.generate/generate_stream → build_options`
  (Ollama `options.seed`) and through `ResumeGenerator.generate(..., seed=...)`. Unset
  by default — never silently injected, so normal generation stays free-running.
- **Scope (no overclaim, CLAUDE.md #1):** the LLM is byte-stable **Ollama-side** for a
  fixed `(seed, prompt, model build, options)` tuple with low/zero temperature on the
  same hardware (per Ollama docs — `seed` + `temperature: 0`). The app's job is to
  *thread the seed and add no nondeterminism of its own*; it does not (and cannot)
  guarantee determinism across different model builds or hardware.
- **ATS scoring** is reproducible for fixed input on the keyword path (pure regex
  match); the LLM path inherits the seed scope above.

Tests: `backend/tests/unit/test_reproducibility.py` (seed threaded to the model
boundary, seeded resume content byte-stable, ATS keyword score reproducible),
`backend/tests/integration/test_health_version.py` (endpoint + single-source guard).

## Migration spine

Alembic migrations round-trip `base → head → base` cleanly
(`test_migration_roundtrip.py`); the single head is reported by the version endpoint.
Rollback story (prompt + updater) is unchanged from 13.9.

## Release verification (DMG + cold-start)

The on-hardware install + first-run-wizard + cold-start check lives in
[`PACKAGING.md`](./PACKAGING.md#release-verification-run-on-the-release-machine) —
owed from 13.8, pending a real release machine.
