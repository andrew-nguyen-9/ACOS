# ADR-015: Local Encryption Layer — Key Management & Scope

**Status:** Accepted (Phase 16.2)
**Date:** 2026-06-23
**Deciders:** Andrew Nguyen
**Phase:** 16.2
**Extends:** ADR-013 §encryption (opt-in `EncryptedText` on `Application.notes`, default off)

---

## Context

Phase 14.3 (ADR-013) introduced opt-in field encryption — Fernet-backed `EncryptedText`,
**off by default**, on `Application.notes` only, threat-model = local disk theft. Phase 16's
brief widens encryption to **resumes, cover letters, applications, personal notes, and career
history**, "optional but supported." That raises two real questions ADR-013 left open: *which
fields* and *where does the key live*.

## Decision

1. **Scope: all sensitive user content, opt-in.** `EncryptedText` (or table-level wrapping)
   extends to the sensitive columns across resumes, cover letters, applications, notes, and
   career-history/experience records. Still **default OFF** — encryption is a toggle in
   Settings, not a forced mode (the brief says "optional but supported").

2. **Key lives in BOTH a passphrase-derived key and the Keychain.** Two unlock paths:
   - **Passphrase → KDF** (Argon2id/scrypt) derives the data-encryption key. Portable, works
     if the Keychain is unavailable, survives machine migration.
   - **Keychain-wrapped** copy of the same key (ADR-014 trust root) for frictionless unlock on
     the enrolled machine.
   The data key is generated once; the passphrase-KDF and the Keychain each *wrap* it. Either
   unlocks. This is the standard "key encryption key" pattern — rotate the wrapping without
   re-encrypting all data.

3. **Honest threat model.** Encryption-at-rest defends **local disk theft / file exfiltration**
   while locked. It is **not** a defense against a compromised running process or another
   authenticated user at runtime — that is ADR-014's job (auth) + ADR-008-successor isolation.
   Docs state this plainly; we do not overclaim (CLAUDE.md #1).

4. **Reproducibility + backup still work with it ON.** The 14.1 seeded-reproducibility spine
   and 11.4 backup/recovery must round-trip with encryption enabled (asserted in tests);
   backups of encrypted data stay encrypted.

## Consequences

**Positive** — a single coherent encryption story; lose-the-disk no longer means lose-the-data
to a thief; two unlock paths avoid a single point of lockout.

**Negative / accepted** — KDF unlock adds a passphrase the user must not lose (no recovery —
ADR-001 local-first); enabling encryption disables some plaintext debugging conveniences;
`security-review` mandatory on the key-wrapping code. Default-off means most users get no
protection unless they opt in — accepted, it's their choice (the brief's "optional").

**Relation:** depends on ADR-014 (Keychain trust root). Supersedes the narrow ADR-013
encryption scope.
