# Phase 11.3 — Performance Optimization + Long-Term Learning Stability

**Track:** Backend · **Depends on:** 11.0, 11.2 (metrics store) · **Status:** Planned

> Read the roadmap index first. Global rule: stability > optimization. Needs **live Ollama** for
> the real-latency portions (Phase 10 deferred perf work for the same reason — see project memory).

---

## 1. Context

Implements brief items **#5 Performance Optimization** and **#6 Long-Term Learning Stability**.

Two halves:
- **Perf**: optimize startup, resume-generation latency, copilot response time, embedding refresh.
  11.0 gives baselines; this segment makes measured improvements and re-baselines.
- **Learning stability**: prevent the learning/optimization system from overfitting to recent
  applications, decaying older successful patterns, or losing high-performing resume strategies.
  Introduce weighted historical memory retention + a success-anchoring system.

Current seams:
- `services/learning/ranker.py`, `services/strategy/outcome_learner.py`,
  `services/strategy/resume_strategy_selector.py`, `services/optimization/*`.
- `models/memory.py`, `models/outcome.py`, `models/optimization.py`, `models/strategy.py`.
- Phase 10 `services/intelligence/context_memory.py`.
- Metrics store from 11.2 (`interview_conversion`, `ats_score`) feeds anchoring signals.

## 2. Goals

### Performance
- Profile and reduce **startup** (lazy-import heavy modules; defer Chroma client init until first use).
- Reduce **resume-generation** latency (cache static template/layout work; avoid recomputing
  embeddings already cached; parallelize independent LLM-free steps).
- Reduce **copilot** first-token latency (prompt assembly + retrieval warm path).
- **Embedding refresh** time (batch embed; skip unchanged content via content-hash from 11.1).

### Learning stability
- **Weighted historical memory retention**: outcomes/strategies are weighted by recency *and*
  success, with a decay floor so proven-but-old winners never drop to zero.
- **Success anchoring**: high-performing resume strategies (by `interview_conversion`/`ats_score`)
  are pinned as anchors that the selector always considers, immune to recency-only drift.
- Guarantee (testable): adding many recent low-success applications does **not** evict or
  out-rank a previously high-success anchor.

## 3. Non-goals (YAGNI)

- No model retraining / fine-tuning. No GPU work.
- No new ML framework — weighting is arithmetic over existing records.
- No autonomous re-indexing (suggest-only → 11.4).
- No micro-optimizations that complicate code for <5% gains; require a measured win.

## 4. Acceptance criteria

- [ ] Startup median improves vs 11.0 baseline (or is documented as already optimal with evidence).
- [ ] Resume-generate p95 (mocked LLM) improves or holds within budget; live-Ollama number recorded.
- [ ] Embedding refresh skips unchanged content (content-hash) — measured fewer embed calls.
- [ ] `retention.weight(outcome)` combines recency + success with a documented decay floor.
- [ ] Anchoring test: N recent low-success items added → a prior high-success strategy still ranked in top-k.
- [ ] `PERFORMANCE_LOG.md` updated with before/after for each metric.
- [ ] ≥90% coverage on new logic; existing tests green.

## 5. Design

### Performance
- `scripts/perf/profile_startup.py`: cProfile around `create_app()`; identify import-time cost.
- Lazy seams: wrap heavy imports (Chroma, large services) behind functions/`functools.cache`;
  defer `rag.chroma_client` connection to first query.
- `services/resume/generator.py`: memoize template/layout selection per (template_id) within a
  request; reuse cached embeddings via content-hash lookup.
- Embedding: `rag/embedder.py` + `rag/indexer.py` batch API; `indexer` checks content-hash and
  skips unchanged (depends on 11.1 hashing). `refresh_embeddings(only_changed=True)`.

### Learning stability
- `backend/services/learning/retention.py`:
  `weight(success_score, age_days) = max(floor, success_score * recency_factor(age_days))`
  where `recency_factor` is a gentle exponential and `floor = k * success_score` so high-success
  items keep a permanent base weight. Constants in `system_config` (tunable — leave the knob).
- `backend/services/learning/anchors.py`: `select_anchors(session, top_n)` picks strategies whose
  success metrics exceed a percentile; `outcome_learner`/`resume_strategy_selector` always merge
  anchors into the candidate set before ranking.
- Wire into `resume_strategy_selector.py` and `outcome_learner.py` candidate assembly.

## 6. File-level plan

```
NEW  scripts/perf/profile_startup.py
NEW  backend/services/learning/retention.py
NEW  backend/services/learning/anchors.py
EDIT backend/main.py / backend/rag/chroma_client.py  (lazy Chroma init)
EDIT backend/rag/embedder.py, backend/rag/indexer.py (batch + skip-unchanged refresh)
EDIT backend/services/resume/generator.py            (memoize template/layout; reuse cached embeds)
EDIT backend/services/strategy/resume_strategy_selector.py (merge anchors)
EDIT backend/services/strategy/outcome_learner.py          (apply retention weights)
EDIT docs/PERFORMANCE_LOG.md                          (before/after table)
NEW  backend/tests/unit/test_retention.py
NEW  backend/tests/unit/test_anchors.py
NEW  backend/tests/unit/test_embedding_refresh_skips.py
NEW  backend/tests/benchmark/test_startup_after.py   (regression vs baseline)
```

## 7. Test plan (TDD)

- `test_retention.py`: recency decays weight; high-success floor prevents zero; monotonic properties.
- `test_anchors.py`: flooding recent low-success items keeps a high-success anchor in selection.
- `test_embedding_refresh_skips.py`: unchanged content → 0 embed calls; changed → embedded.
- `test_startup_after.py`: startup within budget; compare to 11.0 baseline JSON.

## 8. Plugin orchestration checklist

- [ ] `context7` — ChromaDB batch embedding API, cProfile usage.
- [ ] `superpowers:test-driven-development`.
- [ ] `serena` — system-wide analysis to find import-time hotspots and candidate-assembly call sites.
- [ ] `superpowers:verification-before-completion` — paste real before/after numbers (live Ollama for latency).

## 9. Perf budget impact

This segment *spends* the budget deliberately to *gain* performance. Any change that doesn't show a
measured win in 11.0 benches is reverted (YAGNI). Re-baseline `PERFORMANCE_LOG.md` after.

## 10. Risks & mitigations

- *Lazy init hides errors to runtime* → add a `/health` warmup probe that triggers Chroma init.
- *Anchoring ossifies / blocks new winners* → anchors are *added* to candidates, not pinned to
  output; ranking still decides. Cap anchor count.
- *Live-Ollama variance* → report medians over N runs; mark machine.

## 11. Definition of Done

Measured perf improvements (or documented already-optimal), embedding skip-unchanged, retention +
anchoring implemented with the eviction-resistance test passing, `PERFORMANCE_LOG.md` updated,
≥90% coverage, PR with before/after.
