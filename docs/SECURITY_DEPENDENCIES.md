# Security — Dependency Vulnerability Triage

Tracks the disposition of every GitHub Dependabot alert against ACOS dependencies.
Each alert is **fixed** (upgraded past the patched version), **accepted-with-rationale**,
or **deferred-with-ticket** (with the compensating control in place).

Established in **Phase 12.0** (2026-06-22). Re-pull the live list before each triage pass:

```bash
gh api repos/andrew-nguyen-9/ACOS/dependabot/alerts --paginate \
  -q '[.[] | select(.state=="open")] | group_by(.security_vulnerability.package.name)[] \
       | {pkg: .[0].security_vulnerability.package.name, count: length}'
```

---

## 2026-06-22 — Phase 12.0 triage

**Alert landscape at start:** 41 open (3 high, 32 medium, 6 low) across 5 packages.

**End state:** **0 high**, 1 medium deferred (transitive, Linux-only, not in the shipped
macOS artifact). All 40 application/dev-dependency alerts fixed by version bump. Full
backend suite (842 tests, 92.99% coverage) green after the bumps; `pypdf 6.13.3` re-verified
on a real resume PDF (3647 chars extracted, malformed-xref objects skipped gracefully).

| Package | Alerts | Severity | Action | Patched-to | Disposition |
|---------|-------:|----------|--------|-----------|-------------|
| `python-multipart` | 7 | 3 high · 1 med · 3 low | bump `0.0.20 → 0.0.31` | ≥ all (max needed 0.0.31) | ✅ **fixed** |
| `pypdf` | 30 | 27 med · 3 low | bump `5.1.0 → 6.13.3` | ≥ all (max needed 6.13.3) | ✅ **fixed** |
| `requests` | 2 | 2 med | bump `2.32.3 → 2.33.0` | ≥ all (max needed 2.33.0) | ✅ **fixed** |
| `pytest` (dev) | 1 | 1 med | bump `8.3.4 → 9.0.3` | 9.0.3 | ✅ **fixed** |
| `glib` (Rust, transitive) | 1 | 1 med | — | 0.20.0 (unreachable) | ⏸ **deferred-with-ticket** |

### `python-multipart` — fixed (priority 1: live upload attack surface)

FastAPI multipart upload parsing (`POST /api/v1/ingest`). The 3 high alerts are real DoS /
arbitrary-file-write vectors even on a local install. `0.0.31` clears all 7:

| GHSA | Sev | Patched | Summary |
|------|-----|---------|---------|
| GHSA-wp53-j4wj-2cfg | high | 0.0.22 | Arbitrary file write via non-default configuration |
| GHSA-pp6c-gr5w-3c5g | high | 0.0.27 | DoS via unbounded multipart part headers |
| GHSA-5rvq-cxj2-64vf | high | 0.0.30 | Quadratic-time querystring parsing (semicolon) → CPU DoS |
| GHSA-mj87-hwqh-73pj | med  | 0.0.26 | DoS via large multipart preamble/epilogue |
| GHSA-6jv3-5f52-599m | low  | 0.0.30 | Semicolon-as-separator parameter smuggling |
| GHSA-vffw-93wf-4j4q | low  | 0.0.30 | Content-Disposition parameter smuggling (RFC 2231/5987) |
| GHSA-v9pg-7xvm-68hf | low  | 0.0.31 | Negative Content-Length buffers whole body in memory |

### `pypdf` — fixed (priority 1: user-PDF ingestion surface)

ACOS ingests user PDFs (`backend/ingestion/parsers/pdf.py`); ties to CLAUDE.md "never crash
on malformed files". All 30 advisories are malicious-PDF RAM-exhaustion / infinite-loop /
long-runtime classes, each patched somewhere in the 6.x line; **6.13.3 clears all 30**.

The 5→6 major bump is API-safe for our usage: we call only `PdfReader(path, strict=False)`,
iterate `reader.pages`, and `page.extract_text()` — all unchanged in 6.x (verified via
context7; the 6.0 breaking changes are dropping Python 3.8 — we run 3.12 — and removing
long-deprecated camelCase aliases we never used). Re-verified live: 3647 chars extracted
from a real resume, malformed-xref recovery warnings logged, no crash.

Patched-version range across the 30 (all ≤ 6.13.3): `6.0.0` GHSA-7hfw-26vp-jp8m ·
`6.1.3` GHSA-jfx9-29x2-rv3j, GHSA-vr63-x8vc-m265 · `6.4.0` GHSA-m449-cwjh-6pw7 ·
`6.6.0` GHSA-4f6g-68pf-7vhv, GHSA-4xc4-762w-m6cg · `6.6.2` GHSA-2q4j-m29v-hq73 ·
`6.7.1` GHSA-996q-pr4m-cvgq, GHSA-9mvc-8737-8j8h, GHSA-wgvp-vg3v-2xq3 ·
`6.7.2` GHSA-2rw7-x74f-jg35 · `6.7.3` GHSA-x7hp-r3qg-r3cj · `6.7.4` GHSA-f2v5-7jq9-h8cg ·
`6.7.5` GHSA-9m86-7pmv-2852 · `6.8.0` GHSA-hqmh-ppp3-xvm7 · `6.9.1` GHSA-qpxp-75px-xjcp ·
`6.9.2` GHSA-87mj-5ggw-8qc3 · `6.10.0` GHSA-3crg-w4f6-42mx · `6.10.1` GHSA-jj6c-8h6c-hppx ·
`6.10.2` GHSA-4pxv-j86v-mhcw, GHSA-7gw9-cf7v-778f, GHSA-x284-j5p8-9c5p ·
`6.12.0` GHSA-248m-82v9-q6g6, GHSA-cj93-chg6-vgv8 · `6.12.1` GHSA-wjqc-6w8f-h24c ·
`6.12.2` GHSA-5hgr-hg42-57jg, GHSA-j543-4vmf-qm7v · `6.13.0` GHSA-52x6-gq3r-vpf4,
GHSA-m2v9-299j-rv96 · `6.13.3` GHSA-jm82-fx9c-mx94.

> Residual-risk note (per 12.0 non-goal §3): the upgrade is the fix; ACOS's existing
> ingestion size limits + the Phase 11.1 retry/dead-letter path remain the defense-in-depth
> against any future pypdf DoS class. No new app-side parse hardening was added inline.

### `requests` — fixed

| GHSA | Sev | Patched | Summary |
|------|-----|---------|---------|
| GHSA-9hjg-9r4m-mvj7 | med | 2.32.4 | `.netrc` credential leak via malicious URLs |
| GHSA-gc5v-m9x4-r6x2 | med | 2.33.0 | Insecure temp-file reuse in `extract_zipped_paths()` |

`2.33.0` clears both. `requests` is a dev/test dependency (`requirements-dev.txt`), not on
the runtime path.

### `pytest` — fixed (dev-only)

`GHSA-6w46-j5rx-g56g` (med, vulnerable tmpdir handling, patched 9.0.3). Dev-only, no runtime
exposure. Bumped `8.3.4 → 9.0.3`; `pytest-cov 6.0.0`, `pytest-benchmark 5.2.3`, `respx 0.21.1`
all remained compatible (842 tests pass on pytest 9).

### `glib` (Rust, transitive) — deferred-with-ticket

`GHSA-wrw7-89jp-8q8g` (med) — unsoundness in `Iterator`/`DoubleEndedIterator` impls for
`glib::VariantStrIter`. Vulnerable range `>= 0.15.0, < 0.20.0`; locked at **0.18.5**.

**Why deferred (not fixable by `cargo update`):** `glib 0.18.5` is pulled transitively by
`gtk 0.18.2` → `tauri 2.11.3`, and `gtk 0.18.2` pins `glib = "^0.18"`. Cargo treats the 0.x
minor as the breaking version, so `cargo update -p glib --precise 0.20.0` fails:

```
error: failed to select a version for the requirement `glib = "^0.18"`
candidate versions found which didn't match: 0.20.0
required by package `gtk v0.18.2` ... which satisfies `tauri = "^2"`
```

Reaching `glib 0.20` requires Tauri itself to move its gtk stack to `glib 0.20` — out of
scope for a 12.0 dependency bump (would re-platform the Linux GUI backend).

**Compensating control:** `glib`/`gtk`/`webkit2gtk` are the **Linux** GUI backend. ACOS
targets **macOS (Apple Silicon)**, where Tauri uses WKWebView — `glib` is `cfg(linux)`-gated
and **not compiled into the shipped macOS artifact**; it is present in `Cargo.lock` only for
cross-platform graph completeness. The vulnerable `VariantStrIter` iterator is never invoked
by ACOS code. Net runtime exposure on the target platform: none.

**Ticket / revisit condition:** clear automatically when Tauri bumps its gtk/glib stack to
`>= 0.20` (re-run `cargo update` then), or sooner if a Linux build target is ever added.
Re-check on the next dependency triage pass.
