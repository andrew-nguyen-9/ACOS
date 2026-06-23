# Deferred Optimization Backlog (Phase 12.9 → Phases 13–18)

**Source of truth for verdicts + numbers:** `docs/optimization/architecture-spike-findings.md`
**Ledger:** `docs/superpowers/plans/2026-06-22-phase-12-9-implementation-speculative.md` §B (all rows VOID).
**Status:** none adopted in Phase 12. Production stack (HTTP-JSON · Chroma · PyInstaller · FastAPI) unchanged.

Phase 12.9 measured six architecture candidates and deferred/rejected all six (0 adopts). This file is the
**single registry** future phases (13–18) consult before re-litigating any of them. A candidate may only be
reopened by its **measured reopen condition firing** — paste the real number, then run the fixed order
(brainstorm → writing-plans → ADR → TDD → implement → verify). No number → it stays VOID (Ponytail rung 1).

> Every "potential win" below is the spike's measured number, not a promise. Re-baseline against the live
> Phase 12.0 harness on real corpus/payloads before adopting — throwaway spike benches are not shipped gates.

## Reopenable options (future development)

| ID | Candidate | Verdict | Likely future home | Reopen condition (MUST fire with a measured number) | Hard prereqs |
|----|-----------|---------|--------------------|------------------------------------------------------|--------------|
| 12.9.1 | msgpack IPC (content-negotiated, JSON stays default) | DEFER | Phase 13+ (transport) | 12.4 streaming profile shows JSON parse as a **measured frame-stall source** (cite ms) | — |
| 12.9.2 | FAISS float vector backend (adapter behind retriever iface) | DEFER | Phase 13+ / scale (multi-tenant) | post-12.6 Chroma footprint/latency a **measured problem** (cite ms or MB) | 12.6 + 12.14 shipped |
| 12.9.3 | Nuitka parallel build target (PyInstaller stays fallback) | DEFER | Phase 13 (packaging) | ≤400 ms cold-start budget (12.0) **still missed after 12.3** on the release machine (cite cold-start ms) | — |
| 12.9.5a | Pinned unified memory (Ollama/OS config, **not** Python) | DEFER | Phase 13+ (ops / `MODEL_SETUP.md`) | 12.5 leaves a **measured swap cliff** on 16 GB during generation (cite swap number) | lever is Ollama ops, zero backend code |

## Escalations / closed

| ID | Candidate | Verdict | Disposition |
|----|-----------|---------|-------------|
| 12.9.4 | PyO3 singularity (merge Python into Rust binary) | REJECT → **Phase 13 epic** | Not a 12.9.x sub-segment. If ever pursued: own brainstorm + ADR + migration plan. Deletes HTTP debuggability; 12.2–12.6 already capture the latency win. |
| 12.9.5b | JIT rerank (Numba/Jax) | **REJECT — CLOSED** | Do **not** reopen. Post-12.7 `rerank()` is a 20–97 µs scalar fusion loop with no distance matrix to JIT (dense sim is upstream in Chroma C++). |
| 12.9.2-bin | FAISS binary-quantized vectors | **REJECT — CLOSED** | Do **not** ship. Recall 0.765 < 0.98 tolerance — trades ¼ of retrieval relevance for a few MB. |

## Adoption guardrails (apply to any reopen)

1. **One at a time** — re-baseline the 12.0 bench between adoptions (§C principle 6).
2. **Reversible** — ship behind a flag/config with a tested rollback; the prior system stays until parity is proven.
3. **Real corpus/payloads** — re-prove the gate on production data + add TDD; throwaway benches don't become shipped tests.
4. **No perf-budget regression** — re-baseline so the delta is real (roadmap budget table).
5. **security-review required** — for 12.9.1 (transport) and 12.9.2 (data migration + tenant isolation preserved).
6. **Re-justify Ponytail rung 1 at adoption time** — "does a single-user local app need this?" — the burden is on adopt, not defer.
