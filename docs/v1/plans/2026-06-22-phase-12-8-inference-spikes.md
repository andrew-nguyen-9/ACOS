# Phase 12.8 — Advanced Inference Spikes (GBNF / Logit Bias / Speculative Decoding)

**Track:** Velocity (optional) · **Depends on:** 12.4, 12.5 · **Branch:** `feat/phase-12-velocity-flywheel-multitenant`
**Status:** Planned — **OPTIONAL / FLAGGED.** Run only if 12.5 leaves a measured gap.

> Ponytail gate: each item ships behind a default-off flag and must beat its baseline on a bench, or
> it does not merge. These are accelerators, not requirements. Order by effort: GBNF → logit bias → spec-decoding.

## 1. Context

After 12.5 calibration, remaining wins are at the decoding layer. Three independent spikes:
1. **GBNF constrained decoding** — guarantee valid JSON for extraction routes (skills, ATS parse),
   eliminating retry loops and parse failures.
2. **Negative logit bias** — suppress filler preamble ("Here is your cover letter:") to cut tokens.
3. **Speculative decoding** — a tiny draft model (e.g. `qwen2.5:0.5b`) drafting for the 8B model.

## 2. Goals (each a standalone, accept/reject spike)

- Spike A: pass a GBNF grammar to Ollama for JSON-extraction routes; measure retry-rate → 0 and parse-error → 0.
- Spike B: logit-bias array banning known filler token ids; measure tokens-saved per generation.
- Spike C: evaluate whether Ollama (current version) exposes speculative/draft decoding; if yes, A/B
  tokens/sec; if not, record "not viable without llama.cpp bindings" and stop.

## 3. Non-goals (YAGNI)

- No switch to raw llama.cpp bindings in this segment (that escalates to a 12.9 architecture decision).
- No grammar for free-text generation (resume/cover-letter prose) — JSON routes only.
- Spikes that don't beat baseline are documented and dropped, not force-merged.

## 4. Acceptance criteria (per accepted spike)

- [ ] **A:** JSON-extraction routes use GBNF; a fuzz test of 50 inputs yields 100% valid JSON, 0 retries; behind `ENABLE_GBNF` (default off → on once proven).
- [ ] **B:** logit bias reduces mean output tokens on a fixed prompt set by a documented %, no quality regression (LLM-judge or golden diff).
- [ ] **C:** a written go/no-go with tokens/sec numbers; if no-go, no code merged for C.
- [ ] Each accepted spike has a flag, a test, and a bench delta; rejected spikes leave only a findings note.

## 5. Design

- GBNF: grammar files under `backend/prompts/grammars/`; `ollama_client.generate(..., grammar=...)`.
- Logit bias: precompute filler token ids once; pass `options.logit_bias`-equivalent (verify Ollama support via `context7`).
- Spec-decoding: config-driven draft model; measure with 12.0 TTFT/throughput bench.

## 6. File-level plan

```
NEW  backend/prompts/grammars/*.gbnf            (if A accepted)
EDIT backend/services/ollama_client.py          (grammar / logit_bias params, flagged)
NEW  backend/tests/unit/test_gbnf_json.py        (if A)
NEW  backend/tests/unit/test_logit_bias.py       (if B)
NEW  docs/optimization/inference-spike-findings.md (always — records all 3 outcomes)
```

## 7. Test plan (TDD)

- A: 50-input fuzz → all valid JSON, 0 retries.
- B: token-count assertion on fixed prompts with bias on/off; golden quality unchanged.
- C: no code test — bench note only.

## 8. Plugin orchestration checklist

- [ ] `context7` — Ollama GBNF/grammar support, logit_bias support, speculative decoding availability (version-specific — verify, don't assume).
- [ ] `superpowers:test-driven-development` (accepted spikes) + `verification-before-completion`.

## 9. Perf budget impact

Upside only when accepted; flags keep the default path unchanged. Findings doc records each delta.

## 10. Definition of Done

All three spikes evaluated with numbers; accepted ones flagged + tested + benched; findings doc written; nothing force-merged.
