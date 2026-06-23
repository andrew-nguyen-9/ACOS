# ACOS Backlog — bugs, issues, ideas → batched phases

Single local-first capture point for everything not yet scheduled. No GitHub Issues; the
repo stays self-contained and offline. Items flow **Inbox → Triaged → Batched** and a phase
is cut from a coherent batch.

## How to file (one line, append to Inbox)

```
- [ ] (TYPE) <area> — <short description>   [<date>]
```

- **TYPE**: `BUG` (broken) · `ISS` (works but wrong/risky) · `IDEA` (new capability) · `DEBT` (cleanup)
- **area**: `backend` `frontend` `rag` `llm` `db` `security` `packaging` `extension` `docs` `infra`
- Keep it raw. Don't triage at capture time — capture is cheap, triage is deliberate.

## Triage (move from Inbox → Triaged table)

Assign **severity** and a **target phase**. Severity drives batching priority:

| Sev | Meaning | SLA intent |
|-----|---------|-----------|
| S1  | data loss / security / crash / hallucination | next phase, non-negotiable |
| S2  | wrong output, broken golden path | next or next+1 phase |
| S3  | degraded UX, perf, papercut | batch when area is touched |
| S4  | nice-to-have, polish | opportunistic |

## Batching convention (how phases get cut)

1. **Group triaged items by `area`** — a phase batch is area-coherent, not a random grab bag.
2. **Pull all S1/S2 in that area + any S3/S4 cheap to do alongside.** S1/S2 force a batch;
   S3/S4 ride along only when the area is already open.
3. **Size the batch to ~3–6 segments** (one segment ≈ one build session, matching the
   phase-11→18 cadence). Bigger → split into two phases.
4. **Name it** `phase-<N>` and move the items under `## Batched`. The phase plan
   (`docs/superpowers/plans/phase-<N>-roadmap.md`) lists them as acceptance criteria.
5. **A batch ships when every S1/S2 in it is closed.** S3/S4 may roll to the next batch.

> Post-v1 (after Phase 18) phases are **adhoc** — they exist only when a batch crosses the
> S1/S2 threshold or an `IDEA` graduates from [`v2/IDEAS.md`](v2/IDEAS.md). No fixed roadmap.

---

## Inbox (raw capture — untriaged)

_none yet_

## Triaged

| ID | Type | Area | Sev | Description | Target phase |
|----|------|------|-----|-------------|--------------|
| —  | —    | —    | —   | _none yet_  | —            |

## Batched

_none yet — first adhoc batch forms after Phase 18._
