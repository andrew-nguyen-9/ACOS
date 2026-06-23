# Phase 16 — Per-Segment Build Prompts

Copy ONE block per session into a fresh Claude Code run. Each is self-contained and
token-budgeted. **7 segments** (6 build + close-out). Map + reconciliation:
`phase-16-roadmap.md`. Phase ends at **16.7** — no .8+.

## Recommended order (dependency-correct)

```
16.1 auth + keychain sessions (ADR-014)        FIRST — supersedes ADR-008; gates all isolation
16.2 encryption expansion (ADR-015)            ← 16.1   ┐
16.3 audit logging (ADR-016)                   ← 16.1   │ parallel after auth
16.4 prompt-injection defense (ADR-017)        ← 16.1   │
16.5 secure ingestion + isolation hardening    ← 16.1   ┘
16.6 plugin permission framework (ADR-018)     ← 16.1
16.7 adversarial tests + close-out             ← all shipped
```

## Session-wide invariants (true for ALL — stated once, assume in every prompt)

- **Branch:** `feat/phase-16-security-isolation` (off `main`, Phase 15 merged). Each segment = one
  commit. **PR deferred to 16.7.** Git Attribution: NO Claude/Anthropic in commits/PRs/branches.
- **Rules in force (CLAUDE.md):** no hallucination + ADR-006 confidence on user-facing figures;
  read `docs/` before coding; **`context7` for framework APIs** (crypto/keychain libs, FastAPI,
  SQLAlchemy 2.0, Tauri v2 Rust — never from memory). TDD: failing test FIRST, ≥90% new code,
  suite green. Ponytail: rung 1 (does this app need it? — re-justify each new table/service);
  descriptive before model. Caveman: terse prose; **code/commits/security normal**.
- **Phase-16 strict rules (assert, don't just claim):** NO silent data access · NO cross-tenant
  leakage · NO unlogged inference · NO unsafe parsing. Each has a test.
- **`security-guidance` is the primary plugin every segment; `security-review` is mandatory** on
  every build segment (this whole phase is a security surface). `serena` for adversarial reasoning
  on 16.4/16.7.
- **Token-efficiency:** RTK on shell ops. ONE `context7` batch up front. ONE read pass — segment
  spec + ONLY touched files; STOP at the contract + acceptance. Do NOT re-read shipped phase plans
  (state is in `MEMORY.md` + schema/route docs + services on disk). Land small: ADR (if not yet
  written) → failing test → thin code → green → `security-review` → verify with real output → commit.
- **Backend test seam (unchanged since 12):** `backend/tests/conftest.py` `_SyncSessionBridge`,
  in-memory SQLite (StaticPool, FK ON), default tenant seeded; `test_session` units, `client`
  routes. **Alembic isolation:** migrations run ONLY with `ACOS_DB_PATH=$(mktemp -u).db`; verify
  up→head AND down→base. New model → register in `backend/models/__init__.py`; non-ORM tables need
  an `after_create` hook (FTS5 precedent, 12.7).
- **Shipped surface you build on (verify shapes from the file — don't assume fields):**
  - **Tenancy/config:** `backend/models/tenant.py`, `backend/config.py`, `backend/database.py`,
    `backend/main.py` (middleware wiring), the `X-Tenant-Id` resolution (ADR-008).
  - **Encryption (14.3):** the `EncryptedText` type + `requirements-encryption.txt`; currently on
    `Application.notes` only — find where it's defined and how it's keyed.
  - **Ingestion:** `backend/ingestion/security.py` (allowlist+size+malformed), `parsers/`,
    `pipeline.py`, `jobs.py`, `normalizer.py`, `entity_extractor.py`.
  - **RAG/embeddings:** `backend/services/rag/`, Chroma collections (tenant metadata, 12.6/12.7).
  - **Tauri boundary:** `frontend/src-tauri/src/lib.rs` (sidecar spawn + `resolve_asset_path`
    chokepoint), `haptics.rs` (the `generate_handler!` invoke surface pattern for a keychain cmd).
  - **Settings/UI:** `routes/settings.py`, `models/system_config.py`, `SettingsPage.tsx`,
    `FirstRunWizard.tsx`. **Observability/signals:** `backend/observability.py`,
    `services/observability/`, `models/signal.py`/`metric.py` (audit/telemetry feed).
  - **Plugin doc:** `docs/07_PLUGIN_ORCHESTRATION.md` (the contract ADR-018 formalizes).

---

## 16.1 — Real Authentication + Keychain-Backed Sessions (ADR-014)

Implement Phase 16.1 — replace the unauthenticated `X-Tenant-Id` selector with a real
authenticated, keychain-backed per-user session. **ADR-014 FIRST** (supersedes ADR-008). This
gates every other 16.x — isolation, encryption-key binding, and audit tenant scope all need a
real identity. Brief item 2 (the auth half).

PRECONDITION: Phase 15 merged. `X-Tenant-Id` resolves a tenant *unauthenticated* today
(ADR-008). The Tauri/Rust invoke surface exists (`lib.rs` `generate_handler!`, haptics precedent).

Read first (STOP at the tenant-resolution middleware + the Rust invoke surface): (1)
`phase-16-roadmap.md` + `docs/adr/ADR-014-*.md` (already drafted — confirm/ratify it). (2)
`backend/main.py` + wherever `X-Tenant-Id` is resolved + `backend/models/tenant.py`. (3)
`frontend/src-tauri/src/lib.rs` + `haptics.rs` (the invoke-command pattern for a `keychain_*`
command) — `context7` the keychain crate (`keyring` / Security framework). (4) `SettingsPage.tsx`
/ `FirstRunWizard.tsx` (where login/enrollment UI fits).

Order: ratify ADR-014 → TDD (backend: a request with no valid session → **no tenant**, default-
closed, 401/empty — NOT a fallback tenant; a valid session resolves the bound tenant; a self-
asserted `X-Tenant-Id` without a session is rejected) → implement (session-token middleware
server-side; Rust keychain command stores/reads the session secret; FE login/enroll) → implement
the cross-platform credential-store **interface** (mac Keychain impl only) → `security-review` →
verify.

Traps: (1) **Default-closed** — no session must resolve to *nothing*, never a default tenant
(that's the ADR-008 hole being closed). A test asserts it. (2) **Secret never in SQLite/dotfile**
— only the Keychain holds the long-lived secret; the sidecar sees a short-lived token. (3)
**Local-first** — no remote IdP/reset (ADR-001/014); recovery = OS account + Keychain, documented
honestly. (4) **Interface, not lock-in** — abstract the credential store so Win/Linux can back it
later (Phase 18), but implement only macOS now (ponytail: one impl, seam for the rest).

Files: ratify `docs/adr/ADR-014-*.md`, EDIT `backend/main.py`/middleware + `models/tenant.py`,
NEW Rust keychain command in `lib.rs`, FE login/enroll in `SettingsPage`/`FirstRunWizard`,
backend + Rust tests. Def-of-done: unauthenticated selector gone (default-closed asserted) +
keychain-backed session + cross-platform credential interface (mac impl) + `security-review` clean
+ suites green, commit.

---

## 16.2 — Local Encryption Layer Expansion (ADR-015)

Implement Phase 16.2 — extend opt-in field encryption from `Application.notes` to all sensitive
user content (resumes, cover letters, applications, notes, career history), with a proper key:
Keychain-wrapped + passphrase-KDF, **default OFF**. Brief item 5; **ADR-015**.

PRECONDITION: 16.1 (Keychain trust root). `EncryptedText` exists (14.3) on one column. Backup
(11.4) + reproducibility (14.1) must still round-trip with encryption ON.

Read first (STOP at the EncryptedText definition + the sensitive columns): (1) ADR-015 (drafted).
(2) the `EncryptedText` type + `requirements-encryption.txt` + how it keys today. (3) the
sensitive models: `models/resume.py`, `models/document.py` (cover letters), `models/application.py`,
`models/experience.py`/`skill.py` (career history). (4) `backend/services/backup/` + the 14.1
reproducibility tests (must survive encryption ON). `context7` the KDF (Argon2id) + Fernet/AES.

Order: ratify ADR-015 → TDD (round-trip write→encrypted-at-rest→read-back across all targeted
fields; **OFF path byte-identical** to today; **two unlock paths** — KDF and Keychain both unwrap
the same data key; backup of encrypted data stays encrypted; reproducibility holds with ON) →
implement (key-encryption-key: one data key, wrapped by KDF and by Keychain; extend EncryptedText
to the columns; Settings toggle) → `security-review` → verify.

Traps: (1) **Default OFF** — the toggle is the brief's "optional"; OFF path must not change. (2)
**KEK pattern** — wrap the data key, don't derive a different key per field; rotating a wrap must
not re-encrypt all rows. (3) **Honest threat model** — disk-theft-at-rest only; NOT a runtime/
multi-user boundary (that's 16.1). Docs say so. (4) **No passphrase recovery** (ADR-001) — warn
the user; losing it loses encrypted data. (5) reproducibility + backup tests stay green with ON.

Files: ratify ADR-015, EDIT the EncryptedText type + the sensitive models + key-mgmt module +
`SettingsPage`, tests. Def-of-done: encryption extends to all sensitive fields (round-trip tested)
+ Keychain+KDF dual-unwrap + default-OFF unchanged + backup/reproducibility green with ON +
`security-review` clean, commit.

---

## 16.3 — Audit Logging (ADR-016)

Implement Phase 16.3 — a tamper-evident, hash-chained, append-only audit log of every generation,
retrieval, ATS scoring, and optimization recommendation, with configurable strictness. Brief
item 6 + the "no unlogged inference" strict rule; **ADR-016**.

PRECONDITION: 16.1 (audit rows are tenant-scoped). Signals infra exists (`models/signal.py`/
`metric.py`, `observability.py`).

Read first (STOP at the inference chokepoints + the signal model): (1) ADR-016 (drafted). (2) the
generation/retrieval/ATS/optimization entry points: `services/resume/`, `services/cover_letter/`,
`services/rag/` (retrieval), `services/ats/`, `services/optimization/` — find the single
chokepoint each passes through. (3) `models/signal.py`/`metric.py` (existing event shape to extend
or mirror). (4) `SettingsPage`/`system_config.py` (the strictness policy knob).

Order: ratify ADR-016 → TDD (each chokepoint emits an audit row; `verify_audit_chain()` passes on
a clean chain and **fails when a past row is edited/deleted**; content is digests+metadata not
bodies by default; `enforced` policy warns on startup tamper, `relaxed` lets the user prune with a
risk-surfaced UI; **a test asserts no inference path skips the log**) → implement (append-only table
with `prev_hash`/`row_hash`; emit at chokepoints, batched/async off the generation hot path; startup
verify; policy knob) → `security-review` → verify.

Traps: (1) **Tamper-evident, not -proof** — hash chain detects; the owner can still delete (honest,
ADR-016). (2) **No unlogged inference** — the test is the guarantee; a new generation path must
emit. (3) **Off-hot-path** — audit insert must not add latency to generation (batch/async; assert).
(4) **No plaintext leak** — digests respect ADR-015 (don't log decrypted bodies by default). (5)
**Configurable + risk-surfaced** — `relaxed` mode UI states plainly it breaks tamper-evidence (Q3).

Files: ratify ADR-016, NEW `backend/models/audit.py` (register in `__init__.py`; `after_create` if
non-ORM bits) + audit service + chokepoint hooks + policy in `system_config.py`/`SettingsPage`,
migration (up/down on temp db), tests. Def-of-done: hash-chained append-only audit over all four
op types + chain-verify (tamper detected) + no-unlogged-inference test + off-hot-path + configurable
strictness + `security-review` clean, commit.

---

## 16.4 — Prompt-Injection Defense Layer (ADR-017)

Implement Phase 16.4 — a layered injection-defense pipeline (heuristic/denylist → local classifier
→ opt-in LLM-screen) at two checkpoints (ingestion-time + prompt-assembly-time), flag-over-block.
Brief item 1; **ADR-017**. Use `serena` for adversarial reasoning.

PRECONDITION: 16.1. Ingestion exists (`ingestion/security.py`, `parsers/`, `jobs.py`); RAG
assembly composes retrieved context into prompts (`services/rag/`, prompt assembly in the
generators).

Read first (STOP at the ingestion entry + the prompt-assembly point): (1) ADR-017 (drafted). (2)
`backend/ingestion/security.py` + `parsers/` (where JD/PDF text enters — add the ingestion-time
screen) + `ingestion/jobs.py`. (3) `services/rag/` + a generator's prompt assembly (where retrieved
untrusted context is fenced before the model — the assembly-time guard). (4) ADR-016 (blocked/
flagged events get audited).

Order: ratify ADR-017 → TDD (denylist catches known markers / zero-width / hidden-PDF-layer
artifacts; ambiguous text scored by the classifier; **high-confidence → block (not embedded/stored),
medium → flag+sanitize+fence, low → pass-but-fenced**; assembly fences untrusted content as data,
never instructions; blocked/flagged events audited; a corpus of injection fixtures is detected) →
implement (versioned denylist file; classifier scorer; opt-in LLM-screen escalation gated like
12.8; fencing at assembly) → `security-review` + `serena` adversarial pass → verify.

Traps: (1) **Fencing is the backstop** — even undetected injections are delimited+role-marked as
data at assembly, limiting blast radius. (2) **Flag-over-block default** — don't lose a legit-but-
weird JD; hard-block only on high confidence (ADR-017 policy). (3) **LLM-screen is escalation-only**
— not per request (latency); gated. (4) **Denylist is versioned + updatable** without code change.
(5) **Honest** — no detector is perfect; docs + the user-facing "why blocked" say so.

Files: ratify ADR-017, NEW injection-defense module + versioned denylist, EDIT
`ingestion/security.py` (ingestion checkpoint) + the RAG/prompt-assembly fence, audit hook, tests +
fixtures. Def-of-done: two-checkpoint layered defense + flag/block policy + assembly fencing +
audited events + adversarial fixtures detected + `security-review`/`serena` clean, commit.

---

## 16.5 — Secure Ingestion Hardening + Data-Isolation Enforcement

Implement Phase 16.5 — harden file ingestion (block executable payloads / macros / hidden scripts;
parse isolation; schema normalization) AND enforce data isolation (no cross-tenant read, no vector
contamination, no prompt bleed). Brief items 3 + 2 (isolation half).

PRECONDITION: 16.1 (auth/identity). `ingestion/security.py` + `parsers/` exist; Chroma collections
carry tenant metadata (12.6/12.7).

Read first (STOP at the parser surfaces + the tenant-scoped retrieval): (1) roadmap rows 2/3. (2)
`ingestion/security.py` + `parsers/` (DOCX/PDF — macro/script/embedded-object handling) +
`normalizer.py` (schema normalization). (3) `services/rag/` + the Chroma query (confirm every
retrieval filters by tenant; embeddings are tenant-partitioned). (4) `lib.rs` `resolve_asset_path`
(the path chokepoint to reconfirm).

Order: brainstorm (confirm two threads: (A) ingestion — reject/strip macros + embedded scripts/
executables, isolate parsing so a malformed/malicious file can't crash or escape, normalize to the
canonical schema; (B) isolation — **every** retrieval/memory/vector access is tenant-filtered; a
cross-tenant read is impossible) → ADR? skip (consumes ADR-014/008-successor) → TDD (malicious-DOCX
macro stripped/blocked; embedded executable rejected; parser survives a fuzzed/corrupt file without
crash; **cross-tenant query returns nothing** — seeded two tenants, A cannot read B's docs/vectors/
memory; no prompt bleed — A's generation context contains no B content) → implement → `security-
review` → verify.

Traps: (1) **No exec on parsed content** (existing policy) — reconfirm; macros never run. (2)
**Parse isolation** — a bad file fails closed, logged (ADR-016), never crashes the app (CLAUDE.md).
(3) **Isolation is the load-bearing test** — seed 2 tenants, assert zero leakage across docs,
vectors, and memory; this is the brief's core. (4) **Vector partitioning** — Chroma metadata filter
on every query; a missing filter is the contamination bug. (5) ponytail: harden the existing
`security.py`/parsers, don't rewrite the pipeline.

Files: EDIT `ingestion/security.py` + `parsers/` + `normalizer.py`, EDIT `services/rag/` (enforce
tenant filter), isolation + malicious-file tests + fixtures. Def-of-done: macro/script/exec blocked
+ parse-isolation (no crash on hostile file) + schema-normalized + cross-tenant leakage impossible
(doc/vector/memory/prompt, tested) + `security-review` clean, commit.

---

## 16.6 — Permissioned Plugin Framework (ADR-018)

Implement Phase 16.6 — a capability-manifest permission model (declare data access / actions /
boundaries; default-closed; no full-system access), enforced first on the existing internal
service modules. Brief item 4; **ADR-018** (amends ADR-013). **Runtime third-party engine stays
deferred.**

PRECONDITION: 16.1. The "plugin system" is `docs/07` (dev workflow) + the internal service-module
boundary; there is no runtime engine and we are NOT building one.

Read first (STOP at the service-module boundary + the doc): (1) ADR-018 (drafted) + ADR-013 (the
deferral being amended). (2) `docs/07_PLUGIN_ORCHESTRATION.md` (the contract to formalize). (3) the
service-module layout (`backend/services/*`) + how a module accesses tenant data today (the access
layer where a permission check sits). (4) ADR-016 (denials are audited).

Order: ratify ADR-018 → TDD (a module declares a manifest: `data_access`/`actions`/`boundaries`;
an access **outside** the manifest is **denied** (raises), and denial is audited; least-privilege
default — unlisted = denied not warned; an in-manifest access passes) → implement (manifest schema
+ a permission check at the data/action boundary; attach manifests to existing modules) →
`security-review` → verify.

Traps: (1) **Default-closed** — unlisted access denied, not logged-and-allowed (ADR-018). (2)
**Scope honesty** — this governs *trusted internal* modules; it is NOT a sandbox for untrusted
third-party code (don't claim isolation we didn't build). (3) **Forward-compatible schema** — design
the manifest so a future runtime engine attaches without redesign, but build no engine (ponytail
rung 1 — speculative until a real plugin exists; v2). (4) denials audited (ADR-016).

Files: ratify ADR-018, NEW manifest schema + permission-check at the access boundary, manifests on
existing service modules, EDIT `docs/07_PLUGIN_ORCHESTRATION.md` (formalize the contract), audit
hook, tests. Def-of-done: capability manifests + enforced default-closed boundary on internal
modules + audited denials + `docs/07` formalized + runtime engine recorded deferred (ADR-018) +
`security-review` clean, commit.

---

## 16.7 — Adversarial Test Layer + Phase-16 Close-out

Run Phase 16.7 — build the adversarial attack corpus that proves the phase, then verification +
docs + ADR ratification, branch ready to merge. Brief item 7. `serena` (attack design) +
`pr-review-toolkit` (release validation).

PRECONDITION: 16.1–16.6 shipped. First action: enumerate what shipped (git log) + what stayed
deferred (runtime plugin engine, cloud auth, encryption-as-runtime-boundary).

Read first (STOP at the shipped surfaces + the doc list): (1) `phase-16-roadmap.md` (reconciliation
+ deferred). (2) the 16.4 injection fixtures + 16.5 isolation tests (extend into a corpus). (3)
`docs/SECURITY_DEPENDENCIES.md` + `MEMORY.md` ledger.

Order: a checklist. (1) **Adversarial corpus:** prompt-injection attempts (the ADR-017 set,
broadened with `serena`), corrupted/malicious documents (16.5 fixtures), malicious job descriptions
— assert the system blocks/flags/survives each; this corpus is the phase-level proof. (2)
**Security/privacy audit:** end-to-end `security-guidance` + `security-review` — no silent data
access, no cross-tenant leakage, no unlogged inference, no unsafe parsing (the four strict rules,
each backed by a passing test). (3) **Docs:** update `02_TECHNICAL_ARCHITECTURE`, `ARCHITECTURE_
OVERVIEW`, `SECURITY_DEPENDENCIES`, `USER_GUIDE` (auth/encryption/audit/injection), `08_ROADMAP`,
`INDEX`. (4) **ADRs:** ratify ADR-014..018 (Accepted). (5) **Roadmap annotation:** segment map
shipped/deferred.

Traps: (1) **verification-before-completion** — every "secure"/"isolated"/"blocked" backed by a
re-run + pasted output; the corpus is the evidence. (2) **Close out only what shipped** — deferrals
(runtime plugin engine, cloud) documented, not dropped. (3) **The four strict rules are the
headline** — docs state them plainly with the test that enforces each.

Plugins: `security-guidance`, `security-review`, `serena`, `pr-review-toolkit`, `code-review`,
`claude-md-management`, `verification-before-completion`. Files: NEW adversarial test corpus, docs
edits, ADR ratifications, roadmap annotation — no new services. Def-of-done: adversarial corpus
green (injection/corrupt-doc/malicious-JD all handled) + four strict rules each test-backed +
security audit clean + docs + ADRs ratified → **Phase 16 ready to merge to `main`** (PR opens here).
