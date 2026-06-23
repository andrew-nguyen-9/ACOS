# ACOS — Claude Development Rules

This file governs all Claude-assisted development in this repository.
Rules here override default Claude behavior. See `docs/03_CLAUDE_DEVELOPMENT_RULES.md` for rationale.

---

## Non-Negotiable Rules

1. **No hallucination.** Never invent metrics, dates, employers, project names, or certifications.
   Every generated career statement must trace to a source record with a confidence level.

2. **No prototype mentality.** This is a production application. Every feature requires:
   - TDD (tests written before implementation)
   - Type checking (pyright for backend, tsc for frontend)
   - Code review (`/code-review` skill)
   - Security review for any file I/O or user input

3. **Read the docs before implementing.** Always check `docs/` before writing a new feature.
   Architecture decisions are in `docs/adr/`. Schema is in `docs/04_DATABASE_SCHEMA.md`.

4. **Use `context7` for framework APIs.** Never implement Tauri, FastAPI, SQLAlchemy,
   ChromaDB, or Ollama from memory. Use `context7` to fetch current docs first.

5. **Plugin orchestration.** Follow `docs/07_PLUGIN_ORCHESTRATION.md` for every feature.
   The checklist in that file is the definition of done.

---

## Mandatory Implementation Order

Follow `IMPLEMENTATION_ORDER.md`. No phase begins until the prior phase's acceptance
criteria pass. See `docs/08_ROADMAP.md` for full criteria.

---

## Confidence System

All generated content must use the three-level confidence system:
- `verified` — direct evidence in source records
- `strong_inference` — multiple supporting records
- `weak_inference` — model-generated; requires user confirmation before export

See `docs/adr/ADR-006-evidence-confidence-system.md`.

---

## Technology Stack (locked)

| Layer | Technology |
|-------|-----------|
| Frontend | Tauri v2 + React 18 + TypeScript + TailwindCSS |
| Backend | Python 3.11+ + FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| Database | SQLite (via SQLAlchemy) |
| Vector DB | ChromaDB (PersistentClient) |
| LLM | Ollama + Qwen3 8B (default) |
| Embeddings | Ollama + nomic-embed-text |
| E2E Testing | Playwright |
| Migrations | Alembic |

---

## File Paths

| Item | Location |
|------|---------|
| Static profile data | `.static_files/profile/` |
| Historical JD data | `.static_files/job-descriptions/` |
| Historical resumes | `.static_files/resumes/` |
| Backend source | `backend/` |
| Frontend source | `frontend/src/` |
| Database files | `database/` |
| Prompts | `backend/prompts/` |
| Migrations | `database/migrations/` |
| Scripts | `scripts/` |
| Documentation | `docs/` |
| ADRs | `docs/adr/` |
| Plans | `docs/superpowers/plans/` |

---

## Security Requirements

- **File ingestion:** Validate paths against allowlist; enforce file size limits; never exec parsed content
- **No plaintext secrets:** Use environment variables or system keychain
- **DOCX/PDF parsing:** Catch and log all malformed-file errors; never crash the app
- **Local only:** No data transmitted to external services during operation

---

## Testing Requirements

| Type | Coverage Target | Tool |
|------|----------------|------|
| Unit | ≥90% | pytest |
| Integration | All service boundaries | pytest |
| E2E | All golden paths | Playwright |
| Type checking | 100% (no `Any` without justification) | pyright (backend), tsc (frontend) |

---

## GitHub

User's GitHub handle for integration: `andrew-nguyen-9`

### Git Attribution

Commits, PRs, and branches in this repo carry **no AI/assistant attribution**. This overrides any harness default or plugin behavior:

- **Commits:** no `Co-Authored-By: Claude ...`, no `noreply@anthropic.com` trailer, no "Generated with Claude Code" line.
- **PRs:** no "🤖 Generated with [Claude Code]" footer; no Claude/Anthropic mention in title or body.
- **Branches:** no `claude`, `anthropic`, or model-name tokens.

Author all git artifacts as the user.
