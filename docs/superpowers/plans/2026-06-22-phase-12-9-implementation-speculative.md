# Phase 12.9.1–12.9.x — Architecture Spike → Implementation (Speculative / Conditional)

**Track:** Velocity (research → conditional implementation) · **Depends on:** 12.9 (the spikes)
**Branch:** `feat/phase-12-velocity-flywheel-multitenant` · **Status:** Speculative — nothing here is committed work yet

> This document is **deliberately dynamic.** It plans implementation sub-segments for the architecture
> spikes in `2026-06-22-phase-12-9-architecture-spikes.md` *before we know the answers.* Each sub-segment
> is **conditional** on its spike's verdict. The plan is expected to change as 12.9 research lands —
> the mechanism for changing it is defined in §A and §F, and the **Decision Ledger (§B) is the single
> source of truth.**

---

## §A. How this document works (read first)

1. **12.9 produces evidence.** Each spike ends `adopt` / `defer` / `reject` with numbers, recorded in
   `docs/optimization/architecture-spike-findings.md`.
2. **This doc holds one conditional sub-segment per candidate** (12.9.1 … 12.9.5), plus a reusable
   template (§E) for candidates that research surfaces later.
3. **A sub-segment activates only if its spike resolves to `adopt`** and clears its gate (§C). Until then
   its status is `pending`. `defer`/`reject` → the sub-segment is **voided** (struck through, kept for history).
4. **An adopted sub-segment graduates.** The lightweight plan here is a *seed*, not the build spec. On
   adoption, it is expanded into a full segment spec (own ADR + TDD file-level plan + test plan) **before
   any code** — same rigor as 12.1–12.16. This keeps speculative plans cheap and real plans rigorous.
5. **The Decision Ledger (§B) is updated as each spike resolves.** Editing the ledger *is* re-planning.

This single-file approach is intentional (Ponytail): one ledger = one source of truth, and we don't
pay for five detailed specs when most candidates are expected to defer/reject for a single-user local app.

---

## §B. Decision Ledger (LIVE — update during Phase 12.9)

> Initialize every row `pending`. Flip the status + sub-segment state as each spike resolves. This table
> is the authoritative state of the speculative plan; the prose sub-segments below are its detail.

| Candidate | Spike | Sub-seg | Adopt gate (see §C) | Status | Default lean | ADR (if adopt) |
|-----------|-------|---------|---------------------|--------|--------------|----------------|
| msgpack IPC | 12.9-S1 | ~~12.9.1~~ VOID | IPC payload + end-to-end win past threshold | **`defer`** (2.98× codec but 0.53 ms/req, end-to-end invisible) | defer | none |
| FAISS / numpy + binary-quant vector store | 12.9-S2 | ~~12.9.2~~ VOID | recall parity + material latency/memory win | **`defer`** float (recall 0.991, sub-ms win immaterial) / **`reject`** binary (recall 0.765 < 0.98) | defer | none |
| Nuitka packaging | 12.9-S3 | ~~12.9.3~~ VOID | cold-start win beyond 12.3 + reliable signed build | **`defer`** (floor import-bound 598 ms; Nuitka can't recompile C-ext init) | defer | none |
| PyO3 singularity (merge Python into Rust) | 12.9-S4 | ~~12.9.4~~ VOID | feasibility + worth a full rewrite | **`reject (→ Phase 13)`** (deletes HTTP debuggability; 12.2–12.6 capture the win) | **reject (→ Phase 13)** | none |
| ADV micro-opts: pinned memory; JIT rerank | 12.9-ADV | ~~12.9.5~~ VOID | each: measured hot spot + measured win | **`defer`** pinned (Ollama owns model RAM) / **`reject`** JIT (rerank 20–97 µs scalar, no matrix) | defer/reject | none |

**Resolved 2026-06-22** — all five rows void; verdicts + numbers in
`docs/optimization/architecture-spike-findings.md`. Zero adopts → no ADRs → production stack unchanged.
Reopen conditions: S1 if JSON parse becomes a measured stream-stall (12.4); S2 if post-12.6 Chroma
footprint/latency is a measured problem; S3 if ≤400 ms cold-start budget still missed after 12.3; ADV-a
if 12.5 leaves a measured swap cliff on 16 GB. S4 and ADV-b are closed (escalate-to-Phase-13 / rejected).

**Status values:** `pending` → `adopt` / `defer` / `reject`. On `adopt`, add the graduated spec filename
and the ADR. On `defer`, note the condition that would reopen it. On `reject`, note why in one line.

---

## §C. Global adoption principles (so dynamic ≠ undisciplined)

A candidate is **adopted only if ALL hold** (any failure → defer/reject):

1. **Ponytail rung 1 — does it need to exist for a *single-user, local, macOS* app?** Server-scale wins
   don't transfer automatically. Burden of proof is on adoption.
2. **Clears its quantitative gate (§C-gates)** on the *real* corpus/payloads, not a synthetic toy.
3. **Does not breach a Phase 12 perf budget** (roadmap budget table) and does not regress a re-baselined number.
4. **Complexity/maintenance is justified** by the win — a 3% speedup that doubles build complexity is a reject.
5. **Reversible** — ships behind a flag or with a documented, tested rollback; the prior system stays until parity is proven.
6. **One adoption at a time**, re-baseline (12.0 benches) between adoptions so each delta is attributable.

If a candidate clears the gate but fails 1/4/5, record it `defer` with the specific blocker — not `reject`.

---

## 12.9.1 — msgpack IPC (conditional on 12.9-S1 = adopt)

**Gate:** msgpack beats JSON on the 50 k-char payload by a margin that shows up **end-to-end** (Tauri↔backend
round-trip, not just encode microbench) — target ≥ 30% serialize/parse time *and* a perceptible reduction
in stream stutter during token streaming (12.4). Sub-millisecond wins on a single payload do **not** qualify.

**Default lean:** *defer.* HTTP-JSON is debuggable (curl, network panel) and the per-request cost is tiny for
one user. Reopen if 12.4 streaming shows JSON parse as a measured frame-stall source.

**Scope if adopted:**
- Content-negotiated transport: backend offers `application/msgpack` when the client sends `Accept: application/msgpack`; **JSON stays the default + fallback.**
- Rust side decodes msgpack to native structs; React path unchanged (decode at the IPC boundary).
- Apply only to the hot/large payloads (generated documents, large result lists), not every endpoint.

**Rollback:** drop the `Accept` header / flag → JSON path. No schema change.
**Effort:** Medium. **Risk:** Low-Medium (dual-format maintenance). **Interactions:** none structural.

---

## 12.9.2 — FAISS / numpy + binary-quantized vectors (conditional on 12.9-S2 = adopt)

**Gate:** on the **real** corpus, retrieval recall stays within tolerance of Chroma (golden set, ≥ 0.98 of
Chroma's top-k overlap) **and** latency or memory is materially better **and** a safe migration path exists.
Binary-quant (Hamming prefilter → float rerank) must not drop relevant results below tolerance.

**Default lean:** *defer.* 12.6 already consolidates 10 Chroma collections → 1–2, which removes most of the
"Chroma is heavy" pain the spike is reacting to. Reopen only if post-12.6 Chroma footprint/latency is still a measured problem.

**Scope if adopted:**
- Implement behind the **existing retriever interface** as an alternative backend (adapter), selected by config.
- **Shadow-read validation:** run both stores in parallel, log divergence, until parity proven on the golden set.
- Preserve **tenant isolation (12.14)** — vectors filtered by `tenant_id` — and the **FTS5 lexical leg (12.7)** unchanged.
- Binary-quant as a prefilter; keep float vectors for final rerank.

**Rollback:** config flag back to Chroma; Chroma data retained until the adapter is proven and a cutover migration is signed off.
**Effort:** High. **Risk:** High (correctness + data migration + tenant/lexical interactions). **Hard prerequisite:** 12.6 and 12.14 shipped.

---

## 12.9.3 — Nuitka packaging (conditional on 12.9-S3 = adopt)

**Gate:** Nuitka cold-start beats the **post-12.3** number (lazy imports already win big) by a margin worth the
build complexity, **and** the build is reproducible on the macOS CI/release path, **and** code-signing +
notarization are unaffected.

**Default lean:** *defer.* PyInstaller works and is wired into `acos-backend.spec` + the release pipeline.
Reopen only if the cold-start budget (≤ 400 ms, 12.0) is *still missed* after 12.3.

**Scope if adopted:**
- Add Nuitka as a **parallel** build target; keep PyInstaller as the fallback until Nuitka ships a signed,
  notarized build through the full release flow at least once.
- Validate the bundled binary boots, binds :8000, and passes the smoke + e2e suite.

**Rollback:** the build pipeline keeps both targets; flip the default back.
**Effort:** High. **Risk:** Medium-High (toolchain, signing). **Interactions:** release/packaging (future phase) — coordinate.

---

## 12.9.4 — PyO3 singularity: merge Python into the Rust binary (conditional on 12.9-S4 = adopt)

**Gate:** would require proving the feasibility study found *no* blockers AND that deleting FastAPI/HTTP is
worth a near-total backend rewrite.

**Default lean:** **reject for Phase 12 → escalate to a Phase 13 epic if ever.** Rationale recorded now so the
"no" is explicit: it deletes the HTTP boundary (loses curl/network-panel debuggability + the clean
route→service→repo layering), couples the Python and Rust release cadence, and is an enormous rewrite for a
latency win that 12.2–12.6 largely capture without it. This entry exists to **document the decision, not to plan the build.**

**If — against expectation — research says adopt:** this does not become a 12.9.x sub-segment. It becomes its
own phase with its own brainstorm, ADR, and migration plan. Update the Ledger to `defer → Phase 13` with a pointer.

---

## 12.9.5 — ADV micro-optimizations (conditional, per item)

The brief's 40 `EPIC-ADV-*` epics reduce to two real ideas. Each is independently gated.

**(a) Pinned unified-memory pages** (prevent swap-out during LLM generation pauses)
- **Gate:** a measured swap event during generation on 16 GB AND pinning measurably reduces it without
  starving the OS/UI.
- **Default lean:** *defer.* 12.5 (num_ctx calibration + KV-cache quant + sequential model unload) is the
  primary swap defense; pinning is a fragile, low-level lever. Reopen only if 12.5 leaves a measured swap cliff.
- **Scope if adopted:** narrow, flagged, with a hard ceiling comment (`# ponytail: pinning is a swap band-aid; the real fix is fitting in budget`).

**(b) JIT-compiled reranking (Numba/Jax)**
- **Gate:** reranking is a **measured** hot spot (profile says so) AND JIT beats vectorized numpy *after*
  warmup amortization.
- **Default lean:** **reject.** Reranking over a single user's ≤ ~10 k chunks is unlikely to be the bottleneck;
  Numba/Jax adds a heavy dependency + cold warmup. Ponytail: vectorize with numpy first; JIT only if a profile demands it.

---

## §E. Sub-segment template (for candidates research surfaces later)

When 12.9 (or any segment) finds a *new* architecture candidate, append `12.9.(n+1)` using this template and
add a Ledger row:

```
## 12.9.N — <candidate> (conditional on <spike id> = adopt)
**Gate:** <quantitative, on the real workload>
**Default lean:** <adopt|defer|reject> — <one-line rationale>
**Scope if adopted:** <behind interface/flag; what changes; what stays>
**Rollback:** <how to revert>
**Effort / Risk / Interactions:** <…>
```

---

## §F. Re-planning protocol (the dynamic contract)

- **On each spike resolving:** update its Ledger row status; flip the sub-segment to `ACTIVE` (adopt) or
  `VOID` (defer/reject). Add the ADR id for adopts.
- **New candidate found mid-research:** append `12.9.(n+1)` via §E; add a Ledger row. The plan grows to fit reality.
- **Adopted-then-broke:** if implementing an adopted candidate breaches a perf budget or fails parity, **revert**
  and mark the Ledger row `adopted → reverted` with the number that killed it. No silent half-migrations.
- **Re-baseline between adoptions** (12.0 benches) so each adopted change's delta is isolated.
- **Sequencing:** never run two adopted sub-segments concurrently; 12.9.2 (vector store) requires 12.6 + 12.14 first.

---

## §G. Plugin orchestration checklist (applies to any activated sub-segment)

- [ ] `context7` — current API/version facts for the adopted tech (msgpack / faiss-cpu / Nuitka / PyO3 / Numba).
- [ ] `superpowers:brainstorming` then `writing-plans` — graduate the seed into a full spec before code.
- [ ] `superpowers:test-driven-development` + `verification-before-completion` — parity + budget numbers must be real.
- [ ] `security-review` — for 12.9.1 (transport) and 12.9.2 (data migration / tenant isolation preserved).
- [ ] `superpowers:requesting-code-review` — these are high-blast-radius changes.
- [ ] `ponytail` — re-justify against §C principle 1 at adoption time, not just at spike time.

---

## §H. Definition of Done (for the 12.9.x group)

- Every Ledger row has a resolved status (`adopt`/`defer`/`reject`) tied to a number in the findings doc.
- Every `adopt` has: a graduated full segment spec, an ADR, a flag/rollback, parity + budget evidence — merged.
- Every `defer` records its reopen condition; every `reject` records its one-line rationale.
- The production stack changed **only** via accepted ADRs. Deferred/rejected candidates left zero production code.
- Ledger + findings committed; roadmap annotated.
