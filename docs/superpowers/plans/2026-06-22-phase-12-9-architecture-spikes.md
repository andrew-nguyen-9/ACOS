# Phase 12.9 — Architecture Spikes (msgpack IPC / FAISS / PyO3 / Nuitka)

**Track:** Velocity (research) · **Depends on:** 12.2, 12.6 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned — **RESEARCH / ADR ONLY.** No production rewrite merges without an accepted ADR.

> Ponytail gate (rung 1 — "does this need to exist at all?"): for a **single-user local app**, most of
> these are speculative. This segment's job is to **measure and decide**, producing ADRs, not to rip out
> working systems. The brief's 40 `EPIC-ADV-*` epics are duplicates of two micro-opts and are folded in here.

## 1. Context

The brief proposes deep re-architecture: POSIX shm/msgpack/FlatBuffers IPC instead of HTTP-JSON;
FAISS + binary-quantized embeddings instead of Chroma; PyO3 to merge Python into the Rust binary
(delete FastAPI); Nuitka instead of PyInstaller; pinned unified memory; JIT reranking. Each is
high-effort, high-risk, and unproven for our scale. We spike, benchmark, and write a recommendation.

## 2. Goals (each → a findings note + ADR recommendation)

- **Spike 1 — IPC format:** measure JSON vs `msgpack` for a 50k-char payload across the Tauri↔backend
  boundary. Adopt only if the win is material and the complexity is contained.
- **Spike 2 — Vector store:** prototype FAISS / raw-numpy + binary-quantized (Hamming) embeddings over
  the real corpus; compare recall + latency + memory vs Chroma. (Chroma stays default unless decisively beaten.)
- **Spike 3 — Packaging:** evaluate Nuitka cold-start + runtime vs PyInstaller; build-complexity cost.
- **Spike 4 — PyO3 singularity:** feasibility study only (delete FastAPI? merge into Rust?) — almost
  certainly **defer**; document the trade-off honestly (huge rewrite, loses HTTP debuggability).
- **Folded ADV micro-opts:** (a) pinned unified-memory pages to avoid swap during generation pauses;
  (b) Numba/Jax JIT of the reranking distance matrix. Both **Low/Medium priority** — measure, likely defer.

## 3. Non-goals (YAGNI — strong here)

- No production migration off Chroma, off PyInstaller, or off FastAPI in this segment.
- No shared-memory transport implementation — measurement only.
- We do **not** implement all 40 ADV epics; they collapse to micro-opts (a) and (b) above.

## 4. Acceptance criteria

- [ ] Each spike has a reproducible micro-benchmark + a numbers table in a findings doc.
- [ ] Each spike ends in **adopt / defer / reject** with rationale.
- [ ] Any "adopt" produces an ADR (e.g. ADR-010 IPC format) and activates its conditional sub-segment in
      `2026-06-22-phase-12-9-implementation-speculative.md` (12.9.1–12.9.x) — it is **not** implemented inline.
- [ ] Default production stack (HTTP-JSON, Chroma, PyInstaller, FastAPI) remains unchanged unless an ADR says otherwise.

## 5. Design

- Throwaway benches under `scripts/perf/spikes/` (not shipped).
- Findings doc `docs/optimization/architecture-spike-findings.md` with one section per spike.
- ADRs in `docs/adr/` only for accepted items.

## 6. File-level plan

```
NEW  scripts/perf/spikes/ipc_msgpack_bench.py
NEW  scripts/perf/spikes/vector_faiss_bench.py
NEW  scripts/perf/spikes/nuitka_coldstart_notes.md
NEW  docs/optimization/architecture-spike-findings.md
NEW  docs/adr/ADR-0XX-*.md            (only for accepted spikes)
```

## 7. Test plan (TDD)

- Spikes are benchmarks, not features → no unit tests; benches must be reproducible (seed + fixed corpus).
- If any spike is adopted, its follow-up implementation segment carries the TDD.

## 8. Plugin orchestration checklist

- [ ] `context7` — msgpack, faiss-cpu, Nuitka, PyO3 (feasibility facts, current versions).
- [ ] `superpowers:verification-before-completion` (decisions must cite real numbers).
- [ ] `ponytail` — explicitly justify any "adopt" against rung 1 (does it need to exist?).

## 9. Perf budget impact

None to production unless an ADR is accepted and a follow-up segment implements it under the budgets.

## 10. Definition of Done

Four spikes + two ADV micro-opts measured, each with adopt/defer/reject + numbers; ADRs for any
adopts; production stack untouched; findings doc committed.
