# Phase 12.3 — Cold-Start (Lazy Imports + Single-Worker + Sidecar Warmup)

**Track:** Velocity · **Depends on:** 12.0 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned · **Brief items:** PY-003, UI-002, Ollama rec #7

## 1. Context

The PyInstaller backend (`server_entry.py`, `acos-backend.spec`) imports heavy libs (Chroma,
embedder, ML deps) at module load, delaying the port-8000 bind. The Tauri shell waits for the
sidecar before showing UI. Goal: bind the HTTP server instantly, defer heavy imports to first use,
and show the UI with a skeleton while Python finishes booting.

## 2. Goals

- **Lazy imports**: ChromaDB, embedder, and any ML module imported *inside* the functions/routes that
  use them, not at top of module. Server binds before they load.
- **Single Uvicorn worker** pinned (`workers=1`) — avoid duplicating the process memory footprint.
- **Sidecar warmup**: Tauri renders the shell + skeleton immediately; frontend polls `/health` (already
  exists) and swaps skeleton → live when ready.

## 3. Non-goals (YAGNI)

- No Nuitka (that's a 12.9 spike).
- No lazy-loading of trivial stdlib imports — only the measurably heavy ones.

## 4. Acceptance criteria

- [ ] `import backend.main` (or server bind) no longer transitively imports chromadb/embedder (assert via `sys.modules` test).
- [ ] Cold-start median ≤ 400 ms (12.0 budget) — bench attached.
- [ ] First request that needs Chroma triggers its import once; subsequent requests reuse it (memoized).
- [ ] Uvicorn runs `workers=1` in `server_entry.py`.
- [ ] Frontend shows skeleton within 1 animation frame of window open; swaps to live UI on `/health` ok (no flash of error state).

## 5. Design

- Wrap heavy deps behind module-level lazy accessors: `def _chroma(): global _c; _c = _c or ChromaClient(); return _c`
  (`# ponytail: module-level memo, not a DI container`).
- `server_entry.py`: `uvicorn.run(app, host="127.0.0.1", port=8000, workers=1, loop="uvloop")`.
- Frontend: AppShell already has skeleton primitives (Phase 11.6 `ASP-002`); gate the live tree on a
  `useBackendReady()` hook polling `/health` with backoff.

## 6. File-level plan

```
EDIT backend/rag/chroma_client.py / rag/embedder.py   (lazy construction)
EDIT backend/services/**                               (import heavy deps inside functions)
EDIT backend/server_entry.py                           (workers=1, loop=uvloop)
NEW  frontend/src/hooks/useBackendReady.ts
EDIT frontend/src/layouts/AppShell.tsx                 (skeleton until ready)
NEW  backend/tests/unit/test_lazy_imports.py
```

## 7. Test plan (TDD)

- `test_lazy_imports.py`: fresh interpreter imports the app; assert `"chromadb" not in sys.modules`;
  call a RAG route; assert it is now present.
- Frontend: vitest for `useBackendReady` state machine (loading → ready → error/retry).

## 8. Plugin orchestration checklist

- [ ] `context7` — Uvicorn programmatic run options; PyInstaller lazy-import caveats (hiddenimports in spec).
- [ ] `superpowers:test-driven-development`.

## 9. Perf budget impact

Primary cold-start win; verify the `sys.modules` gate so a future careless top-level import can't
silently regress it. Bundle unaffected.

## 10. Definition of Done

Lazy imports proven by test, single worker, skeleton warmup, cold-start ≤400 ms bench attached, tests green.
