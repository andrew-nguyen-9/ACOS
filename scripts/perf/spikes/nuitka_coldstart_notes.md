# Spike 3 (Phase 12.9) — Nuitka cold-start: go/no-go notes

**Verdict: DEFER — notes only, no Nuitka build shipped.** Like 12.8 Spike C, the
build cost is high enough that a go/no-go note with the build-complexity case is
the acceptable outcome (spec §3; brief allowance for heavy spikes).

## Viability (context7 `/websites/nuitka_net_user-documentation`)

Nuitka *can* target macOS app bundles: `--macos-create-app-bundle` /
`--mode=app`, standalone + onefile modes, and a Nuitka-Action CI path all exist
and are current. So packaging-with-Nuitka is **feasible**. The question is not
"can it build" but "does it move the number we care about, for the cost."

## What the number actually is (12.3, re-confirmed this session)

Cold start is **import-bound, not interpreter-startup-bound**. Current reference
(`scripts/perf/baselines/startup.json`, 12.3): **median 597.96 ms**, p95 794.97 ms.

Per-module self import-time (`profile_startup.py --importtime`, this session):

| module      | self import (ms) |
|-------------|-----------------:|
| backend     | 174.6 |
| sqlalchemy  | 151.8 |
| fastapi     | 134.2 |
| pydantic    | 35.0 |
| docx        | 28.5 |
| pydantic_core | 16.9 |
| lxml        | 17.5 |

The floor is the cost of **executing module-level code** in these heavy libs
(class/table/route registration, Pydantic model building), required to bind the
app. 12.3 already pushed everything lazy that can be lazy (the
`test_lazy_imports.py` gate holds the line).

## Why Nuitka is unlikely to move it (honest framing)

Nuitka compiles **pure-Python** to C and speeds up Python-level execution. But
the dominant cost here is:

1. **C-extension module init** — `pydantic_core` (Rust), `lxml` (libxml2),
   parts of SQLAlchemy/`greenlet`. Nuitka does **not** recompile these; their
   init runs identically in a Nuitka build. ponytail: Nuitka can't optimize code
   it isn't compiling.
2. **Unavoidable registration work** — SQLAlchemy mapper configuration and
   Pydantic v2 model construction execute the same operations regardless of
   whether the surrounding Python is bytecode or Nuitka-C. The work is the work.

So the realistic expected win is a modest shave on the Python-glue fraction, not
a step change on a ~600 ms import-bound floor. PyInstaller (`acos-backend.spec`)
already produces a working, signing-compatible bundle.

## Build-complexity cost (the reject side of the ledger)

- Nuitka needs a working **C toolchain** + minutes-scale compiles (vs
  PyInstaller's collect-and-freeze seconds); CI time and cache complexity grow.
- **Code-signing + notarization** of a Nuitka onefile/app-bundle is a separate
  validation exercise the release pipeline hasn't done; risk is non-trivial.
- A whole-backend standalone compile of FastAPI + SQLAlchemy + chromadb +
  python-docx + lxml is exactly the kind of heavy build the spec says not to
  ship speculatively.

## Decision

**DEFER.** Reopen only if the cold-start budget (≤ 400 ms, 12.0) is *still
missed after 12.3* on the release machine — it currently is not a measured
production problem, and Nuitka does not target the part of the 600 ms that
dominates. No build performed; PyInstaller remains the packaging path.
