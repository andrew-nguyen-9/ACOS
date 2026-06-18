# ACOS Plugin Orchestration

## Philosophy

Plugins are not optional. They encode engineering discipline that prevents the system from
becoming a prototype. No feature is "complete" until every required gate has been run.

---

## Feature Development Lifecycle

```
1. Brainstorm / Architecture    → compound-engineering:ce-brainstorm
2. Plan                         → superpowers:writing-plans
3. Research (framework docs)    → context7
4. Security review (if needed)  → security-review skill
5. Implement (TDD)              → superpowers:test-driven-development
6. Type checking                → LSP (pyright for backend, tsc for frontend)
7. Code review                  → code-review skill
8. Simplification               → pr-review-toolkit:code-simplifier
9. E2E test                     → playwright skill
10. Documentation update        → claude-md-management:claude-md-improver
11. Commit                      → commit-commands:commit
```

Every step is required. Steps may not be skipped.

---

## Plugin Reference by Phase

### Phase 0: Bootstrap

| Plugin | Purpose |
|--------|---------|
| `superpowers:writing-plans` | Document all plans before implementation |
| `compound-engineering:ce-plan` | Architecture decomposition |

---

### Phase 1: Database & Knowledge Graph

| Plugin | Purpose | When |
|--------|---------|------|
| `context7` (SQLAlchemy) | Verify SQLAlchemy 2.0 ORM patterns | Before models |
| `compound-engineering:ce-architecture-strategist` | Validate schema design | Before migrations |
| `superpowers:test-driven-development` | Drive model testing | During implementation |
| `compound-engineering:ce-correctness-reviewer` | Logic review | After implementation |

---

### Phase 2: Document Ingestion

| Plugin | Purpose | When |
|--------|---------|------|
| `security-review` | File parsing vulnerability review | Before implementation |
| `context7` (python-docx, pypdf) | Safe parsing patterns | Before implementation |
| `compound-engineering:ce-security-reviewer` | Ingestion security gate | After implementation |
| `hookify:hookify` | Folder watcher for auto-ingestion | After base ingestion |

**Security requirements for ingestion (mandatory):**
- All file paths must be validated against an allowlist of directories
- No shell execution from parsed content
- File size limits enforced before parsing
- Malformed PDFs/DOCX handled without crashes
- Checksums prevent reprocessing the same file twice

---

### Phase 3: RAG & Embeddings

| Plugin | Purpose | When |
|--------|---------|------|
| `context7` (ChromaDB) | ChromaDB API patterns | Before implementation |
| `context7` (Ollama) | Ollama embedding API | Before implementation |
| `compound-engineering:ce-performance-reviewer` | Embedding batch size / throughput | After implementation |

---

### Phase 4: Resume Engine

| Plugin | Purpose | When |
|--------|---------|------|
| `feature-dev:feature-dev` | Feature blueprint | Before implementation |
| `compound-engineering:ce-brainstorm` | Generation pipeline design | Before implementation |
| `playground` | Prompt experimentation | During prompt development |
| `compound-engineering:ce-correctness-reviewer` | ATS scoring logic review | After implementation |

---

### Phase 5: Cover Letter Engine

| Plugin | Purpose | When |
|--------|---------|------|
| `feature-dev:feature-dev` | Feature blueprint | Before implementation |
| `ralph-loop:ralph-loop` | Optimization of voice matching | After baseline |
| `ralph-skills:ralph` | Skill extraction from historical letters | During implementation |

---

### Phase 6: Q&A Engine

| Plugin | Purpose | When |
|--------|---------|------|
| `feature-dev:feature-dev` | Feature blueprint | Before implementation |
| `skill-creator:skill-creator` | Skill ontology design for categorization | Before implementation |
| `ralph-skills:prd` | PRD for question bank requirements | Before implementation |

---

### Phase 7: Career Copilot

| Plugin | Purpose | When |
|--------|---------|------|
| `agent-sdk-dev:new-sdk-app` | Copilot agent design | Before implementation |
| `feature-dev:feature-dev` | Feature blueprint | Before implementation |
| `compound-engineering:ce-agent-native-architecture` | Agent-native design review | Before implementation |
| `compound-engineering:ce-reliability-reviewer` | Retry / failure handling | After implementation |

---

### Phase 8: Application CRM

| Plugin | Purpose | When |
|--------|---------|------|
| `feature-dev:feature-dev` | Feature blueprint | Before implementation |
| `compound-engineering:ce-correctness-reviewer` | CRM logic review | After implementation |

---

### Phase 9: Frontend (Tauri + React)

| Plugin | Purpose | When |
|--------|---------|------|
| `frontend-design:frontend-design` | Design system before any UI | Before implementation |
| `figma:figma-generate-design` | Generate Figma mockups | Before implementation |
| `context7` (React, Tauri) | Current API patterns | Before implementation |
| `compound-engineering:ce-design-implementation-reviewer` | Design fidelity check | After each page |
| `compound-engineering:ce-julik-frontend-races-reviewer` | Async UI race conditions | After async components |
| `chrome-devtools-mcp:chrome-devtools` | UI debugging | During development |
| `compound-engineering:ce-test-browser` | Browser testing | After each feature |

---

### Phase 10: Learning Engine

| Plugin | Purpose | When |
|--------|---------|------|
| `ralph-loop:ralph-loop` | Iterative ranking optimization | During implementation |
| `compound-engineering:ce-performance-reviewer` | Re-indexing performance | After implementation |

---

### All Phases: Quality Gates

| Plugin | When Required |
|--------|-------------|
| `superpowers:test-driven-development` | Before any implementation |
| `code-review` | After every completed feature |
| `pr-review-toolkit:code-simplifier` | After large implementations (>100 LOC) |
| `compound-engineering:ce-security-sentinel` | Before any file I/O, network, or user input |
| `commit-commands:commit` | After each passing quality gate |
| `claude-md-management:claude-md-improver` | When docs fall out of sync |

---

## context7 Usage Protocol

Always resolve the library ID before fetching docs:

```
1. mcp__plugin_context7_context7__resolve-library-id (library name)
2. mcp__plugin_context7_context7__query-docs (resolved ID, specific question)
```

Required for these libraries before implementation:
- `tauri` — before any Tauri IPC or system commands
- `react` — before any hooks or context patterns
- `fastapi` — before any route or dependency design
- `sqlalchemy` — before any ORM models or queries
- `chromadb` — before any collection operations
- `ollama` — before any model or embedding calls
- `python-docx` — before DOCX parsing
- `pypdf` — before PDF parsing

---

## Definition of Done Checklist

```
[ ] feature-dev blueprint approved
[ ] All failing tests written first (TDD)
[ ] Implementation complete
[ ] All tests pass
[ ] Type checking passes (pyright / tsc)
[ ] code-review run and findings addressed
[ ] security-review run (if applicable)
[ ] code-simplifier run (if >100 LOC)
[ ] Playwright E2E test written (if UI)
[ ] Documentation updated
[ ] Commit generated
```

No feature moves to the next phase until this checklist is complete.
