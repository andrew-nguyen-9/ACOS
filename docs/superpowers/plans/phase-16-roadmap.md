# Phase 16 — Enterprise Security, Privacy & System Isolation (Roadmap)

> **STATUS (2026-06-23): SHIPPED on `feat/phase-16-security-isolation`.** All 7 segments
> built + committed: 16.1 auth/keychain (ADR-014) · 16.2 encryption/KEK (ADR-015) · 16.3 audit
> log (ADR-016) · 16.4 injection defense (ADR-017) · 16.5 ingestion hardening + isolation · 16.6
> plugin permissions (ADR-018) · 16.7 adversarial corpus + close-out. ADR-014..018 ratified
> (Accepted). Suite 1147 green, pyright clean, Rust+vitest green. Deferred (recorded): runtime
> third-party plugin engine, cloud auth, encryption-as-runtime-boundary. Final v1 arc = Phases
> 16–18; after 18, work is adhoc/v2 (`docs/v2/`).

**Branch:** `feat/phase-16-security-isolation` (cut off `main` after Phase 15 merges).
**Predecessor:** Phases 0–15 shipped. Exists: tenant isolation (12.14, ADR-008), opt-in field
encryption (14.3, ADR-013), ingestion security (`backend/ingestion/security.py`), asset://
chokepoint (`lib.rs`), observability/drift (14.2), controlled-autonomy boundary (ADR-012).
**Phase ends at 16.7 (close-out).** No 16.8+.

---

## Why this is mostly *harden + formalize*, not net-new engines

Like 14–15 reconciled "platform brief" against shipped reality, Phase 16 reconciles an
"enterprise security" brief against a local-first single-→multi-user app. Most items extend a
primitive that already exists (isolation, ingestion security, opt-in encryption). The genuinely
net-new pieces are **real auth (ADR-014)**, the **injection-defense layer (ADR-017)**, the
**audit log (ADR-016)**, and the **adversarial test corpus**. Each boundary-shifting decision
gets an ADR written FIRST.

## Reconciliation — brief vs shipped reality

| Brief item | Shipped already | Phase 16 disposition |
|---|---|---|
| 1. Prompt-injection defense (malicious JD / hidden PDF instr / injected system prompt / exfil) | none; ingestion validates files but not injection | **NEW layered defense** (heuristic→classifier→LLM-screen, ingestion + assembly checkpoints) → 16.4, **ADR-017**. |
| 2. Data isolation (tenant sep / no memory leak / no vector contamination / no prompt bleed) | tenant scoping (12.14, ADR-008) — but **unauthenticated** selector | **Real auth (ADR-014) FIRST** → 16.1; then harden isolation + assert no cross-tenant read/vector/prompt bleed → 16.5. |
| 3. Secure file ingestion (sanitize / parse sandbox / validate / normalize; block exec/macros/scripts) | `ingestion/security.py` (allowlist+size+malformed catch), parsers | **Harden**: macro/script/exec blocking, parse isolation, schema normalization → 16.5. |
| 4. Permissioned plugin system (declare data access / actions / boundaries; no full access) | ADR-013 **deferred** runtime engine; `docs/07` = dev workflow | **Permission manifest + enforced boundary** (no runtime sandbox yet) → 16.6, **ADR-018** (amends 013). |
| 5. Local encryption (resumes / CL / applications / notes / career history; optional) | opt-in `EncryptedText` on `Application.notes` only (14.3) | **Extend scope + key mgmt** (Keychain + KDF, default off) → 16.2, **ADR-015** (extends 013). |
| 6. Audit logging (every gen / retrieval / ATS / optimization; immutable) | none | **NEW tamper-evident hash-chained log**, configurable strictness → 16.3, **ADR-016**. |
| 7. Adversarial testing (injection / corrupted docs / malicious JD) | none | **NEW attack-fixture corpus** exercising 16.3/16.4/16.5 → 16.7. |

## Segment map (dependency-ordered) — 7 segments

```
16.1  Auth + keychain sessions (ADR-014)              ← 15 ✓   FIRST; supersedes ADR-008 selector; gates isolation
16.2  Local encryption expansion (ADR-015)            ← 16.1   Keychain+KDF key; EncryptedText → all sensitive fields; default off
16.3  Audit logging (ADR-016)                         ← 16.1   tamper-evident hash chain; no-unlogged-inference; configurable strictness
16.4  Prompt-injection defense (ADR-017)              ← 16.1   layered detect/flag/block; ingestion + assembly checkpoints; fence untrusted
16.5  Secure ingestion + isolation hardening          ← 16.1   macro/script/exec block, parse isolation, schema norm; no cross-tenant/vector/prompt bleed
16.6  Plugin permission framework (ADR-018)           ← 16.1   capability manifest + enforced default-closed boundary; runtime engine still deferred
16.7  Adversarial test layer + close-out              ← all    attack corpus + security-review + ADR ratification + docs → merge
```

**Critical path:** `16.1 → {16.2, 16.3, 16.4, 16.5, 16.6 parallel after auth} → 16.7`.
ADR-014 (auth) is the gate — isolation, encryption-key binding, and the audit tenant scope all
depend on a real authenticated identity. Write it before any other 16.x.

## ADRs this phase produces

- **ADR-014** — Real auth, keychain-backed sessions (**supersedes ADR-008**). 16.1.
- **ADR-015** — Local encryption key mgmt + scope (Keychain+KDF, default off; **extends ADR-013**). 16.2.
- **ADR-016** — Audit log tamper-evidence (hash chain, configurable strictness, user-owned). 16.3.
- **ADR-017** — Prompt-injection defense (layered, two-checkpoint, flag-over-block). 16.4.
- **ADR-018** — Plugin permission model (capability manifest, no full access; **amends ADR-013**). 16.6.

## Carried-forward gates (every applicable segment)

- **No hallucination + 3-level confidence (ADR-006)** on user-facing figures; **no silent data
  access, no unlogged inference, no cross-tenant leakage, no unsafe parsing** (Phase-16 strict
  rules) — each is asserted by a test, not just claimed.
- **TDD** (failing test first, ≥90% new-code cov, suite green); **pyright** / **tsc**; per-segment
  **code-review**; **`security-review` mandatory** on 16.1/16.2/16.3/16.4/16.5/16.6 (the whole phase
  is a security surface).
- **Frontend perf gates** (Phase 11 standard) where there's UI (auth/settings/audit views): 60fps,
  0 long-tasks, CLS ≈ 0, entry ≤ 80.8 kB gz, Off tier usable, CSP unchanged.
- **verification-before-completion:** every "secure"/"isolated"/"blocked" claim backed by a real
  test/scan output pasted (the adversarial corpus in 16.7 is the phase-level proof).

## Plugins (per `docs/07`)

`security-guidance` (primary, every segment) · `serena` (adversarial reasoning, 16.4/16.7) ·
`code-review` (security auditing, per segment) · `pr-review-toolkit` (release validation, 16.7).

## Deferred (recorded, not dropped)

| Item | Why deferred | Reopen when |
|------|--------------|-------------|
| Runtime third-party plugin execution engine (sandbox/WASM loader) | Permission *model* built (ADR-018); engine speculative until a real 3rd-party plugin exists | a real third-party plugin is wanted (v2 / `docs/v2/ROADMAP.md`) |
| Cloud / network auth provider | Local-first (ADR-001); auth is on-device (ADR-014) | multi-device sync or hosted deploy is chosen → own ADR |
| Encryption as a *runtime* multi-user boundary | At-rest encryption defends disk theft only (ADR-015 threat model); runtime isolation is auth's job | never (wrong tool — documented) |

## Token-efficiency ("Both")

- **Dev-time:** RTK on shell ops · caveman+ponytail prose · ONE `context7` batch up front (crypto
  lib, keychain crate, Argon2/Fernet — never from memory) · ONE read pass bounded to the segment.
- **Runtime:** audit writes batched/async off the generation hot path (ADR-016 §5); injection
  LLM-screen is escalation-only (ADR-017 layer 3), not per-request; encryption adds no network cost.
