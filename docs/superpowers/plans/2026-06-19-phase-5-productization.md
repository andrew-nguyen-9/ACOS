# Phase 5: Productization, Hardening & Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn ACOS from a working API + empty frontend scaffold into a polished, production-grade local-first desktop app with a Tahoe "Liquid Glass" design system, six fully wired module UIs, structured backend errors, observability, and graceful degradation.

**Architecture:** Backend hardening lands first (structured error envelope, per-request timing + structured operation logs, consistent Ollama-unavailable degradation contract) so the frontend consumes a stable shape. Then the frontend foundation (deps, Tahoe theme, design-system primitives, app shell + router, typed API/query layer, error boundary), then the six module UIs, then production-readiness (evidence/confidence parity, degradation banner, lazy-loading, e2e).

**Tech Stack:** Backend: FastAPI + SQLAlchemy 2.0 + Pydantic v2 (unchanged). Frontend: Tauri v2 + React 18 + TypeScript + TailwindCSS (locked) + React Router (nav) + TanStack Query (data cache + lazy loads) + Zustand (UI state) + lucide-react (icons) + Vitest + @testing-library/react (component TDD) + @playwright/test (e2e).

## Global Constraints

- **No new features, AI systems, or data models.** Polish, integration, error handling, observability only. No Alembic migrations.
- **No architectural changes** unless fixing a critical bug. The locked stack (Tauri/React/TS/Tailwind, FastAPI/SQLAlchemy/Pydantic, SQLite, ChromaDB, Ollama/Qwen3) does not change.
- **Confidence system unchanged:** only `verified` | `strong_inference` | `weak_inference`. `weak_inference` outputs surface a "review required" affordance in the UI.
- **No hallucination:** every AI output in the UI shows its evidence + confidence; outputs with no evidence are visibly marked.
- **Local only:** the frontend talks only to `http://localhost:8000` (matches the Tauri CSP `connect-src`). No external calls, fonts, or analytics.
- **Every new Python file** starts with `from __future__ import annotations`.
- **Backend coverage gate stays ≥90%** (`pytest --cov=backend --cov-fail-under=90`). New backend code is TDD.
- **Backend error envelope (canonical shape) — every non-2xx JSON response from `/api/v1/*` is exactly:**
  `{"error": {"code": <STRING>, "message": <STRING>, "detail": <object|null>}}`
- **Confidence color tokens (from `docs/09_DESIGN_GUIDELINES.css`):** verified `#30D158`, strong `#5AC8FA`, weak `#FF9F0A`. Apple system blue `#007AFF`. Backgrounds `--bg-0..3` `#090b0f / #11141a / #171b24 / #202635`.
- **App logo** lives at `mock-designs/app-logo.png`. Usage rules: size adjustment only; on dark surfaces use CSS `mix-blend-mode: screen`; on light surfaces use `filter: invert(1)` then `mix-blend-mode: screen`. Never recolor or distort it.
- **Mock designs** are extracted (read-only reference, rough — fix as noted) at `mock-designs/extracted/Screen N/src/App.tsx`. Mapping: 1=Knowledge Graph, 2=Resume Builder, 3=Applications CRM, 4=Copilot Chat, 5=Evidence/Confidence panel, 6=Learning Engine. Mocks use hard-coded pixel canvas sizes (`w-480 h-270`), fake data, and no API wiring — all three must be fixed.
- **Backend run:** `source .venv/bin/activate` first. **Frontend run:** from `frontend/`, `npm run dev` (Vite on :1420). Backend on :8000 via `uvicorn backend.main:app`.

---

## Backend Error Envelope — Canonical Reference (used by Tasks 1, 8, 16)

```json
{ "error": { "code": "VALIDATION_ERROR", "message": "human readable", "detail": null } }
```

Codes used in this phase: `VALIDATION_ERROR` (422), `NOT_FOUND` (404), `CONFLICT` (409, FK/integrity), `LLM_UNAVAILABLE` (503, Ollama down and no fallback possible), `INTERNAL` (500, unexpected). Routes that already degrade gracefully (resume/ATS returning a zero-score with an `explanation`) keep returning 200 — the envelope is only for actual error responses.

---

## TRACK A — BACKEND HARDENING

### Task 1: Structured error envelope + global exception handlers

**Files:**
- Create: `backend/api/errors.py`
- Create: `backend/tests/unit/test_error_envelope.py`
- Modify: `backend/main.py` (register handlers in `create_app`)

**Interfaces:**
- Produces: `class APIError(Exception)` with `__init__(self, code: str, message: str, status_code: int, detail: dict | None = None)`; `def install_error_handlers(app: FastAPI) -> None` registering handlers for `APIError`, FastAPI `RequestValidationError`, Starlette `HTTPException`, and bare `Exception`. All emit the canonical envelope `{"error": {"code","message","detail"}}`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_error_envelope.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.errors import APIError, install_error_handlers


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/boom")
    def boom():
        raise APIError("NOT_FOUND", "thing missing", 404, {"id": "x"})

    @app.get("/starlette")
    def starlette():
        raise StarletteHTTPException(status_code=403, detail="nope")

    @app.get("/crash")
    def crash():
        raise RuntimeError("unexpected")

    @app.get("/validate")
    def validate(n: int):  # missing required query param -> RequestValidationError
        return {"n": n}

    return app


def test_apierror_envelope():
    c = TestClient(_app(), raise_server_exceptions=False)
    r = c.get("/boom")
    assert r.status_code == 404
    body = r.json()
    assert body == {"error": {"code": "NOT_FOUND", "message": "thing missing", "detail": {"id": "x"}}}


def test_validation_error_envelope():
    c = TestClient(_app(), raise_server_exceptions=False)
    r = c.get("/validate")
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["detail"], (list, dict))


def test_starlette_http_exception_envelope():
    c = TestClient(_app(), raise_server_exceptions=False)
    r = c.get("/starlette")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "HTTP_403"


def test_unhandled_exception_envelope():
    c = TestClient(_app(), raise_server_exceptions=False)
    r = c.get("/crash")
    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == "INTERNAL"
    assert "message" in body["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest backend/tests/unit/test_error_envelope.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.api.errors`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/api/errors.py
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("acos.error")


class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int, detail: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail


def _envelope(code: str, message: str, detail: object | None) -> dict:
    return {"error": {"code": code, "message": message, "detail": detail}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _api(_: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code,
                            content=_envelope(exc.code, exc.message, exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422,
                            content=_envelope("VALIDATION_ERROR", "Request validation failed", exc.errors()))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code,
                            content=_envelope(f"HTTP_{exc.status_code}", str(exc.detail), None))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception: %s", exc)
        return JSONResponse(status_code=500,
                            content=_envelope("INTERNAL", "Internal server error", None))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/unit/test_error_envelope.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Wire into the app**

In `backend/main.py`, inside `create_app` after `app = FastAPI(...)` and before routers, add:
```python
from backend.api.errors import install_error_handlers
# ...
    install_error_handlers(app)
```

- [ ] **Step 6: Verify no regressions**

Run: `pytest backend/tests/ -q`
Expected: all pass. Note: existing integration tests that assert `response.json()["detail"]` on error paths will now see `response.json()["error"]["message"]`. Update only those assertions that break, preserving each test's intent. Run again until green.

- [ ] **Step 7: Commit**

```bash
git add backend/api/errors.py backend/tests/unit/test_error_envelope.py backend/main.py backend/tests/integration
git commit -m "feat(api): structured error envelope with global exception handlers"
```

---

### Task 2: Observability — request timing middleware + structured operation logger

**Files:**
- Create: `backend/observability.py`
- Create: `backend/tests/unit/test_observability.py`
- Modify: `backend/main.py` (add middleware), `backend/logging_config.py` (add `request` + `perf` logger names to quiet-list tuning only if needed)

**Interfaces:**
- Produces:
  - `def log_operation(op: str, **fields: object) -> None` — emits one structured line `acos.op` at INFO: `op=<op> key=value ...`. Used by services for generation/retrieval/ATS/application logs.
  - `class TimingMiddleware(BaseHTTPMiddleware)` — wraps each request, logs `acos.perf` line `method=<m> path=<p> status=<s> ms=<float>` and sets response header `X-Process-Time-Ms`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_observability.py
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.observability import TimingMiddleware, log_operation


def test_log_operation_emits_structured_line(caplog):
    with caplog.at_level(logging.INFO, logger="acos.op"):
        log_operation("resume_generate", resume_id="abc", bullets=4, confidence="strong_inference")
    msgs = [r.getMessage() for r in caplog.records if r.name == "acos.op"]
    assert any("op=resume_generate" in m and "resume_id=abc" in m and "bullets=4" in m for m in msgs)


def test_timing_middleware_sets_header_and_logs(caplog):
    app = FastAPI()
    app.add_middleware(TimingMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    c = TestClient(app)
    with caplog.at_level(logging.INFO, logger="acos.perf"):
        r = c.get("/ping")
    assert r.status_code == 200
    assert "X-Process-Time-Ms" in r.headers
    assert float(r.headers["X-Process-Time-Ms"]) >= 0.0
    perf = [rec.getMessage() for rec in caplog.records if rec.name == "acos.perf"]
    assert any("path=/ping" in m and "status=200" in m and "ms=" in m for m in perf)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/unit/test_observability.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.observability`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/observability.py
from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_op_logger = logging.getLogger("acos.op")
_perf_logger = logging.getLogger("acos.perf")


def log_operation(op: str, **fields: object) -> None:
    parts = [f"op={op}"] + [f"{k}={v}" for k, v in fields.items()]
    _op_logger.info(" ".join(parts))


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        _perf_logger.info(
            "method=%s path=%s status=%s ms=%.2f",
            request.method, request.url.path, response.status_code, elapsed_ms,
        )
        return response
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/unit/test_observability.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Wire middleware into the app**

In `backend/main.py` `create_app`, after `install_error_handlers(app)`:
```python
from backend.observability import TimingMiddleware
# ...
    app.add_middleware(TimingMiddleware)
```

- [ ] **Step 6: Add operation logs at the five required call sites**

Add `from backend.observability import log_operation` and one `log_operation(...)` call each in:
- `backend/services/resume/generator.py` — after a resume is built: `log_operation("resume_generate", resume_id=resume_id, template=template_name, bullets=<count>, weak=<weak_inference_count>)`
- `backend/services/rag/service.py` — after retrieval in `query`: `log_operation("rag_retrieve", intent=intent, evidence=len(evidence))`
- `backend/services/ats/scorer.py` — after a score is produced: `log_operation("ats_score", overall=<overall_score>)`
- `backend/services/copilot/engine.py` — after `chat` builds its result: `log_operation("copilot_chat", intent=intent, citations=len(citations))`
- `backend/api/v1/routes/application.py` — after create + after status change: `log_operation("application_event", application_id=<id>, event="created"|"status_change", status=<status>)`

Use values already present in each function; do not compute new data. Wrap each call so a logging failure can never break the request (they won't, but keep them after the core result is computed).

- [ ] **Step 7: Verify**

Run: `pytest backend/tests/ -q`
Expected: all pass (the added log calls are side-effect-only; existing tests still pass).

- [ ] **Step 8: Commit**

```bash
git add backend/observability.py backend/tests/unit/test_observability.py backend/main.py backend/services backend/api
git commit -m "feat(obs): request timing middleware + structured operation logs at generation/retrieval/ATS/copilot/application sites"
```

---

### Task 3: Graceful Ollama-degradation contract on `/health/ollama` + a typed degradation summary

**Files:**
- Modify: `backend/api/v1/routes/health.py`
- Create: `backend/tests/integration/test_health_degradation.py`

**Interfaces:**
- Produces: `GET /api/v1/health/ollama` returns `{"available": bool, "models": list[str], "required_models": ["qwen3:8b","nomic-embed-text"], "missing_models": list[str], "degraded": bool}` where `degraded` is `True` when unavailable OR any required model missing. This is the single source the frontend polls to show its "AI offline / degraded" banner. No 503 here — it always returns 200 with the status object so the UI can always render.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/integration/test_health_degradation.py
from __future__ import annotations

from unittest.mock import patch


def test_ollama_health_reports_degraded_when_unavailable(client):
    with patch("backend.api.v1.routes.health.OllamaClient") as M:
        inst = M.return_value
        inst.is_available.return_value = False
        inst.list_models.return_value = []
        r = client.get("/api/v1/health/ollama")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is False
    assert body["degraded"] is True
    assert set(body["missing_models"]) == {"qwen3:8b", "nomic-embed-text"}


def test_ollama_health_reports_healthy_when_all_models_present(client):
    with patch("backend.api.v1.routes.health.OllamaClient") as M:
        inst = M.return_value
        inst.is_available.return_value = True
        inst.list_models.return_value = ["qwen3:8b", "nomic-embed-text:latest", "other"]
        r = client.get("/api/v1/health/ollama")
    body = r.json()
    assert body["available"] is True
    assert body["degraded"] is False
    assert body["missing_models"] == []


def test_ollama_health_partial_models_is_degraded(client):
    with patch("backend.api.v1.routes.health.OllamaClient") as M:
        inst = M.return_value
        inst.is_available.return_value = True
        inst.list_models.return_value = ["qwen3:8b"]
        r = client.get("/api/v1/health/ollama")
    body = r.json()
    assert body["degraded"] is True
    assert body["missing_models"] == ["nomic-embed-text"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/integration/test_health_degradation.py -v`
Expected: FAIL — current route returns only `available`/`models`.

- [ ] **Step 3: Implement**

Replace `health_ollama` in `backend/api/v1/routes/health.py` with:
```python
_REQUIRED_MODELS = ["qwen3:8b", "nomic-embed-text"]


@router.get("/ollama")
def health_ollama() -> dict:
    settings = get_settings()
    client = OllamaClient(base_url=settings.ollama_base_url, timeout=5)
    available = client.is_available()
    models = client.list_models() if available else []
    # Match on prefix so "nomic-embed-text:latest" satisfies "nomic-embed-text".
    present = {m.split(":")[0] for m in models}
    missing = [m for m in _REQUIRED_MODELS if m.split(":")[0] not in present]
    degraded = (not available) or bool(missing)
    return {
        "available": available,
        "models": models,
        "required_models": _REQUIRED_MODELS,
        "missing_models": missing,
        "degraded": degraded,
    }
```

- [ ] **Step 4: Run tests**

Run: `pytest backend/tests/integration/test_health_degradation.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Verify + coverage gate**

Run: `pytest backend/tests/ --cov=backend --cov-fail-under=90 -q`
Expected: all pass, coverage ≥90%.

- [ ] **Step 6: Commit**

```bash
git add backend/api/v1/routes/health.py backend/tests/integration/test_health_degradation.py
git commit -m "feat(health): ollama degradation contract with required/missing model reporting"
```

---

## TRACK B — FRONTEND FOUNDATION

### Task 4: Frontend dependencies, Tahoe theme tokens, and Vitest harness

**Files:**
- Modify: `frontend/package.json` (deps + scripts), `frontend/tailwind.config.js` (Tahoe tokens), `frontend/src/index.css` (CSS variables + base), `frontend/tsconfig.json` (path alias `@/`), `frontend/vite.config.ts` (alias + vitest config)
- Create: `frontend/vitest.config.ts` is folded into `vite.config.ts`; `frontend/src/test/setup.ts`; `frontend/src/test/smoke.test.tsx`

**Interfaces:**
- Produces: working `npm run test` (Vitest jsdom), `npm run dev`, `npm run build`; Tailwind theme exposing `bg-tahoe-0..3`, `text-tahoe-primary/secondary/muted`, `confidence-verified/strong/weak`, `accent` (=#007AFF); `@/` resolves to `frontend/src/`.

- [ ] **Step 1: Add dependencies**

From `frontend/`:
```bash
npm install react-router-dom @tanstack/react-query zustand lucide-react clsx tailwind-merge
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @vitejs/plugin-react @types/node
```

- [ ] **Step 2: Add scripts to `frontend/package.json`**

Add to `"scripts"`: `"test": "vitest run"`, `"test:watch": "vitest"`, `"lint:types": "tsc --noEmit"`.

- [ ] **Step 3: Configure Tailwind tokens**

Replace `frontend/tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        tahoe: { 0: "#090b0f", 1: "#11141a", 2: "#171b24", 3: "#202635" },
        "tahoe-primary": "#ffffff",
        "tahoe-secondary": "#c4cad3",
        "tahoe-muted": "#8c94a1",
        accent: "#007AFF",
        confidence: { verified: "#30D158", strong: "#5AC8FA", weak: "#FF9F0A" },
      },
      borderRadius: { sm: "12px", md: "18px", lg: "24px", xl: "32px", floating: "40px" },
      fontFamily: {
        display: ['"SF Pro Display"', "Inter", "sans-serif"],
        body: ['"SF Pro Text"', "Inter", "sans-serif"],
        mono: ['"SF Mono"', '"JetBrains Mono"', "monospace"],
      },
      boxShadow: {
        "depth-1": "0 4px 12px rgba(0,0,0,.15)",
        "depth-2": "0 10px 30px rgba(0,0,0,.22)",
        "depth-3": "0 24px 60px rgba(0,0,0,.35)",
        "depth-4": "0 40px 100px rgba(0,0,0,.45)",
      },
    },
  },
  plugins: [],
};
```

- [ ] **Step 4: Base CSS**

Replace `frontend/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root { color-scheme: dark; }

html, body, #root { height: 100%; }
body {
  margin: 0;
  background: #090b0f;
  color: #fff;
  font-family: "SF Pro Text", Inter, sans-serif;
  -webkit-font-smoothing: antialiased;
}

@layer components {
  .material-thin   { background: rgba(255,255,255,.04); backdrop-filter: blur(20px) saturate(180%); }
  .material-medium { background: rgba(255,255,255,.06); backdrop-filter: blur(35px) saturate(180%); }
  .material-thick  { background: rgba(255,255,255,.08); backdrop-filter: blur(50px) saturate(200%); }
}

/* App logo blend rules — see Global Constraints */
.logo-on-dark  { mix-blend-mode: screen; }
.logo-on-light { filter: invert(1); mix-blend-mode: screen; }
```

- [ ] **Step 5: Path alias + Vitest in `frontend/vite.config.ts`**

Replace with (keeps Tauri settings, adds alias + test):
```ts
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig(async () => ({
  plugins: [react()],
  clearScreen: false,
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: { port: 1420, strictPort: true, watch: { ignored: ["**/src-tauri/**"] } },
  envPrefix: ["VITE_", "TAURI_ENV_*"],
  build: {
    target: process.env.TAURI_ENV_PLATFORM === "windows" ? "chrome105" : "safari13",
    minify: !process.env.TAURI_ENV_DEBUG ? "esbuild" : false,
    sourcemap: !!process.env.TAURI_ENV_DEBUG,
  },
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test/setup.ts"], css: true },
}));
```

In `frontend/tsconfig.json` add under `compilerOptions`: `"baseUrl": ".", "paths": { "@/*": ["src/*"] }`.

- [ ] **Step 6: Test setup + smoke test**

```ts
// frontend/src/test/setup.ts
import "@testing-library/jest-dom";
```
```tsx
// frontend/src/test/smoke.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

function Hello() { return <div>hello acos</div>; }

describe("vitest harness", () => {
  it("renders", () => {
    render(<Hello />);
    expect(screen.getByText("hello acos")).toBeInTheDocument();
  });
});
```

- [ ] **Step 7: Verify harness + build**

Run: `cd frontend && npm run test && npm run lint:types && npm run build`
Expected: Vitest 1 passing, `tsc --noEmit` clean, Vite build succeeds.

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tailwind.config.js frontend/src/index.css frontend/vite.config.ts frontend/tsconfig.json frontend/src/test
git commit -m "build(frontend): add router/query/zustand deps, Tahoe theme tokens, vitest harness"
```

---

### Task 5: Design-system primitives (utility + glass components)

**Files:**
- Create: `frontend/src/lib/cn.ts`
- Create: `frontend/src/components/ui/GlassPanel.tsx`, `Button.tsx`, `Badge.tsx`, `ConfidenceBadge.tsx`, `Spinner.tsx`, `EmptyState.tsx`
- Create: `frontend/src/components/ui/ConfidenceBadge.test.tsx`, `Button.test.tsx`

**Interfaces:**
- Produces:
  - `cn(...classes) => string` (clsx + tailwind-merge).
  - `<GlassPanel material="thin"|"medium"|"thick" depth?={1|2|3|4} className>` → div with glass material + radius-lg.
  - `<Button variant="primary"|"glass"|"ghost" size?="sm"|"md" loading?={bool} ...buttonProps>`.
  - `<Badge tone="neutral"|"accent"|"green"|"amber" >`.
  - `<ConfidenceBadge level="verified"|"strong_inference"|"weak_inference">` → colored pill; `weak_inference` also renders the text "Review".
  - `<Spinner size?>`, `<EmptyState icon title description action?>`.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/components/ui/ConfidenceBadge.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ConfidenceBadge } from "./ConfidenceBadge";

describe("ConfidenceBadge", () => {
  it("labels verified", () => {
    render(<ConfidenceBadge level="verified" />);
    expect(screen.getByText(/verified/i)).toBeInTheDocument();
  });
  it("flags weak inference for review", () => {
    render(<ConfidenceBadge level="weak_inference" />);
    expect(screen.getByText(/review/i)).toBeInTheDocument();
  });
});
```
```tsx
// frontend/src/components/ui/Button.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { Button } from "./Button";

describe("Button", () => {
  it("fires onClick", async () => {
    const fn = vi.fn();
    render(<Button onClick={fn}>Go</Button>);
    await userEvent.click(screen.getByText("Go"));
    expect(fn).toHaveBeenCalledOnce();
  });
  it("disables and shows spinner when loading", () => {
    render(<Button loading>Go</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npm run test`
Expected: FAIL — modules not found.

- [ ] **Step 3: Implement primitives**

```ts
// frontend/src/lib/cn.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
```
```tsx
// frontend/src/components/ui/GlassPanel.tsx
import { cn } from "@/lib/cn";
const MATERIAL = { thin: "material-thin", medium: "material-medium", thick: "material-thick" } as const;
const DEPTH = { 1: "shadow-depth-1", 2: "shadow-depth-2", 3: "shadow-depth-3", 4: "shadow-depth-4" } as const;
export function GlassPanel(
  { material = "medium", depth, className, children }:
  { material?: keyof typeof MATERIAL; depth?: keyof typeof DEPTH; className?: string; children?: React.ReactNode },
) {
  return (
    <div className={cn("rounded-lg border border-white/5", MATERIAL[material], depth && DEPTH[depth], className)}>
      {children}
    </div>
  );
}
```
```tsx
// frontend/src/components/ui/Spinner.tsx
import { cn } from "@/lib/cn";
export function Spinner({ className }: { className?: string }) {
  return <span className={cn("inline-block size-4 animate-spin rounded-full border-2 border-white/30 border-t-white", className)} />;
}
```
```tsx
// frontend/src/components/ui/Button.tsx
import { cn } from "@/lib/cn";
import { Spinner } from "./Spinner";
type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "glass" | "ghost"; size?: "sm" | "md"; loading?: boolean;
};
const VARIANT = {
  primary: "bg-gradient-to-b from-[#3f93ff] to-accent text-white",
  glass: "material-thin border border-white/10 text-white",
  ghost: "text-tahoe-secondary hover:text-white",
} as const;
const SIZE = { sm: "h-9 px-3 text-[13px]", md: "h-10 px-[18px] text-sm" } as const;
export function Button({ variant = "primary", size = "md", loading, className, children, disabled, ...rest }: Props) {
  return (
    <button
      className={cn("inline-flex items-center justify-center gap-2 rounded-[14px] font-medium transition disabled:opacity-50", VARIANT[variant], SIZE[size], className)}
      disabled={disabled || loading} {...rest}
    >
      {loading && <Spinner />}{children}
    </button>
  );
}
```
```tsx
// frontend/src/components/ui/Badge.tsx
import { cn } from "@/lib/cn";
const TONE = {
  neutral: "bg-white/8 text-tahoe-secondary border-white/10",
  accent: "bg-accent/12 text-[#7db4ff] border-accent/20",
  green: "bg-confidence-verified/12 text-confidence-verified border-confidence-verified/20",
  amber: "bg-confidence-weak/12 text-confidence-weak border-confidence-weak/20",
} as const;
export function Badge({ tone = "neutral", className, children }: { tone?: keyof typeof TONE; className?: string; children: React.ReactNode }) {
  return <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-semibold", TONE[tone], className)}>{children}</span>;
}
```
```tsx
// frontend/src/components/ui/ConfidenceBadge.tsx
import { Badge } from "./Badge";
export type Confidence = "verified" | "strong_inference" | "weak_inference";
const MAP = {
  verified: { tone: "green", label: "Verified" },
  strong_inference: { tone: "accent", label: "Strong" },
  weak_inference: { tone: "amber", label: "Review" },
} as const;
export function ConfidenceBadge({ level }: { level: Confidence }) {
  const m = MAP[level];
  return <Badge tone={m.tone}>{m.label}</Badge>;
}
```
```tsx
// frontend/src/components/ui/EmptyState.tsx
import type { LucideIcon } from "lucide-react";
export function EmptyState({ icon: Icon, title, description, action }: { icon: LucideIcon; title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <Icon className="size-8 text-tahoe-muted" />
      <div className="text-base font-semibold">{title}</div>
      {description && <div className="max-w-sm text-sm text-tahoe-muted">{description}</div>}
      {action}
    </div>
  );
}
```

- [ ] **Step 4: Run tests**

Run: `cd frontend && npm run test && npm run lint:types`
Expected: PASS (smoke + 4 component assertions), types clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib frontend/src/components/ui
git commit -m "feat(ui): Tahoe glass design-system primitives (GlassPanel, Button, Badge, ConfidenceBadge, Spinner, EmptyState)"
```

---

### Task 6: Typed API client + TanStack Query hooks + error normalization

**Files:**
- Create: `frontend/src/lib/api.ts` (fetch wrapper that unwraps the error envelope), `frontend/src/lib/queryClient.ts`
- Create: `frontend/src/types/api.ts` (shared response types)
- Create: `frontend/src/lib/api.test.ts`

**Interfaces:**
- Produces:
  - `class ApiError extends Error { code: string; status: number; detail: unknown }`.
  - `apiGet<T>(path) => Promise<T>`, `apiPost<T>(path, body) => Promise<T>`, `apiPatch<T>(path, body) => Promise<T>`, `apiDelete(path) => Promise<void>` — all prefix `http://localhost:8000/api/v1`, and on non-2xx parse the canonical envelope and throw `ApiError(code, message, status, detail)`.
  - `queryClient` (TanStack) with sane defaults (`staleTime: 30s`, `retry: 1`).
  - Types in `types/api.ts`: `Confidence`, `EvidenceItem`, `ResumeContent`, `AtsScore`, `Application`, `CopilotResponse`, `Citation`, `Question`, `Answer`, `LearningReport`, `OllamaHealth` (mirror the backend shapes from this plan's API map appendix).

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/lib/api.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiGet, ApiError } from "./api";

describe("api client", () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  it("returns parsed json on 200", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ ok: 1 }), { status: 200 })));
    await expect(apiGet<{ ok: number }>("/health")).resolves.toEqual({ ok: 1 });
  });

  it("throws ApiError with code from envelope on 4xx", async () => {
    const body = JSON.stringify({ error: { code: "NOT_FOUND", message: "missing", detail: null } });
    vi.stubGlobal("fetch", vi.fn(async () => new Response(body, { status: 404 })));
    await expect(apiGet("/x")).rejects.toMatchObject({ code: "NOT_FOUND", status: 404 });
    await expect(apiGet("/x")).rejects.toBeInstanceOf(ApiError);
  });

  it("throws ApiError code NETWORK on fetch rejection", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("failed to fetch"); }));
    await expect(apiGet("/x")).rejects.toMatchObject({ code: "NETWORK" });
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npm run test -- api.test`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```ts
// frontend/src/lib/api.ts
const BASE = "http://localhost:8000/api/v1";

export class ApiError extends Error {
  code: string; status: number; detail: unknown;
  constructor(code: string, message: string, status: number, detail: unknown) {
    super(message); this.code = code; this.status = status; this.detail = detail;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    throw new ApiError("NETWORK", "Cannot reach the ACOS backend. Is it running on :8000?", 0, String(e));
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const json = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const env = json?.error ?? {};
    throw new ApiError(env.code ?? `HTTP_${res.status}`, env.message ?? "Request failed", res.status, env.detail ?? null);
  }
  return json as T;
}

export const apiGet = <T>(p: string) => request<T>("GET", p);
export const apiPost = <T>(p: string, b?: unknown) => request<T>("POST", p, b ?? {});
export const apiPatch = <T>(p: string, b?: unknown) => request<T>("PATCH", p, b ?? {});
export const apiDelete = (p: string) => request<void>("DELETE", p);
```
```ts
// frontend/src/lib/queryClient.ts
import { QueryClient } from "@tanstack/react-query";
export const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false } },
});
```

Create `frontend/src/types/api.ts` mirroring the **API Map appendix** at the end of this plan (one `export interface`/`type` per documented shape).

- [ ] **Step 4: Run tests + types**

Run: `cd frontend && npm run test && npm run lint:types`
Expected: PASS, clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/queryClient.ts frontend/src/types/api.ts frontend/src/lib/api.test.ts
git commit -m "feat(frontend): typed API client unwrapping error envelope + query client + shared types"
```

---

### Task 7: App shell — router, sidebar nav, top bar, logo, error boundary, degradation banner

**Files:**
- Create: `frontend/src/components/shell/AppShell.tsx`, `Sidebar.tsx`, `TopBar.tsx`, `DegradationBanner.tsx`, `ErrorBoundary.tsx`, `Logo.tsx`
- Create: `frontend/src/hooks/useOllamaHealth.ts`
- Create: `frontend/src/router.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/main.tsx`
- Copy asset: `mock-designs/app-logo.png` → `frontend/src/assets/app-logo.png`
- Create: `frontend/src/components/shell/Sidebar.test.tsx`, `ErrorBoundary.test.tsx`

**Interfaces:**
- Consumes: `useOllamaHealth()` → `{ data?: OllamaHealth }` via TanStack Query polling `/health/ollama` every 15s. `ApiError` from Task 6.
- Produces: `<AppShell>` wrapping `<Outlet/>` with sidebar + top bar + degradation banner + error boundary; `NAV_ITEMS` list of `{ to, label, icon }` for the six modules + Dashboard; `<Logo variant="dark"|"light" className>`.

- [ ] **Step 1: Copy the logo asset**

```bash
mkdir -p frontend/src/assets && cp mock-designs/app-logo.png frontend/src/assets/app-logo.png
```

- [ ] **Step 2: Write the failing tests**

```tsx
// frontend/src/components/shell/Sidebar.test.tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import { Sidebar } from "./Sidebar";

describe("Sidebar", () => {
  it("renders all six module links plus dashboard", () => {
    render(<MemoryRouter><Sidebar /></MemoryRouter>);
    ["Dashboard", "Resumes", "Cover Letters", "ATS Analysis", "Applications", "Copilot", "Questions"]
      .forEach((label) => expect(screen.getByText(label)).toBeInTheDocument());
  });
});
```
```tsx
// frontend/src/components/shell/ErrorBoundary.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

function Boom(): JSX.Element { throw new Error("kaboom"); }

describe("ErrorBoundary", () => {
  it("renders fallback when a child throws", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(<ErrorBoundary><Boom /></ErrorBoundary>);
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run to verify failure**

Run: `cd frontend && npm run test -- Sidebar ErrorBoundary`
Expected: FAIL — modules missing.

- [ ] **Step 4: Implement shell pieces**

```tsx
// frontend/src/components/shell/Logo.tsx
import logo from "@/assets/app-logo.png";
import { cn } from "@/lib/cn";
export function Logo({ variant = "dark", className }: { variant?: "dark" | "light"; className?: string }) {
  return <img src={logo} alt="ACOS" className={cn("size-10 object-contain", variant === "light" ? "logo-on-light" : "logo-on-dark", className)} />;
}
```
```ts
// frontend/src/hooks/useOllamaHealth.ts
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { OllamaHealth } from "@/types/api";
export function useOllamaHealth() {
  return useQuery({
    queryKey: ["ollama-health"],
    queryFn: () => apiGet<OllamaHealth>("/health/ollama"),
    refetchInterval: 15_000,
  });
}
```
```tsx
// frontend/src/components/shell/Sidebar.tsx
import { NavLink } from "react-router-dom";
import { LayoutDashboard, FileText, Mail, ScanSearch, Briefcase, Sparkles, NotebookPen } from "lucide-react";
import { cn } from "@/lib/cn";
import { Logo } from "./Logo";
export const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/resumes", label: "Resumes", icon: FileText },
  { to: "/cover-letters", label: "Cover Letters", icon: Mail },
  { to: "/ats", label: "ATS Analysis", icon: ScanSearch },
  { to: "/applications", label: "Applications", icon: Briefcase },
  { to: "/copilot", label: "Copilot", icon: Sparkles },
  { to: "/questions", label: "Questions", icon: NotebookPen },
] as const;
export function Sidebar() {
  return (
    <aside className="flex w-60 flex-col gap-2 border-r border-white/10 px-4 py-6 material-thin">
      <div className="mb-6 flex items-center gap-3 px-2">
        <Logo />
        <div className="leading-tight">
          <div className="text-[15px] font-semibold tracking-tight">ACOS</div>
          <div className="text-[11px] text-tahoe-muted">Career OS</div>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end}
            className={({ isActive }) => cn(
              "flex h-11 items-center gap-3 rounded-xl px-3.5 text-[13px] font-medium transition",
              isActive ? "bg-white/15 text-white" : "text-tahoe-muted hover:text-white")}>
            <Icon className="size-4" /><span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
```
```tsx
// frontend/src/components/shell/DegradationBanner.tsx
import { AlertTriangle } from "lucide-react";
import { useOllamaHealth } from "@/hooks/useOllamaHealth";
export function DegradationBanner() {
  const { data } = useOllamaHealth();
  if (!data || !data.degraded) return null;
  const msg = !data.available
    ? "AI engine offline — Ollama is not reachable. Outputs fall back to templates without AI reasoning."
    : `AI degraded — missing model(s): ${data.missing_models.join(", ")}. Run: ollama pull ${data.missing_models[0] ?? ""}`;
  return (
    <div className="flex items-center gap-2 border-b border-confidence-weak/20 bg-confidence-weak/10 px-9 py-2 text-[12px] text-confidence-weak">
      <AlertTriangle className="size-3.5" />{msg}
    </div>
  );
}
```
```tsx
// frontend/src/components/shell/TopBar.tsx
import { ShieldCheck, Wifi } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
export function TopBar({ title }: { title: string }) {
  return (
    <header className="flex items-center justify-between border-b border-white/10 px-9 py-6">
      <h1 className="text-[22px] font-bold tracking-tight">{title}</h1>
      <div className="flex items-center gap-3">
        <Badge tone="green"><Wifi className="size-3.5" />Local First</Badge>
        <Badge tone="neutral"><ShieldCheck className="size-3.5 text-confidence-verified" />Evidence Active</Badge>
      </div>
    </header>
  );
}
```
```tsx
// frontend/src/components/shell/ErrorBoundary.tsx
import { Component, type ReactNode } from "react";
import { Button } from "@/components/ui/Button";
export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error) { console.error("[ErrorBoundary]", error); }
  render() {
    if (this.state.error) {
      return (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-12 text-center">
          <div className="text-lg font-semibold">Something went wrong</div>
          <div className="max-w-md text-sm text-tahoe-muted">{this.state.error.message}</div>
          <Button onClick={() => this.setState({ error: null })}>Try again</Button>
        </div>
      );
    }
    return this.props.children;
  }
}
```
```tsx
// frontend/src/components/shell/AppShell.tsx
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar, NAV_ITEMS } from "./Sidebar";
import { TopBar } from "./TopBar";
import { DegradationBanner } from "./DegradationBanner";
import { ErrorBoundary } from "./ErrorBoundary";
export function AppShell() {
  const { pathname } = useLocation();
  const active = [...NAV_ITEMS].reverse().find((n) => (n.to === "/" ? pathname === "/" : pathname.startsWith(n.to)));
  return (
    <div className="flex h-screen overflow-hidden bg-tahoe-0 text-white">
      <Sidebar />
      <main className="flex min-w-0 flex-1 flex-col">
        <DegradationBanner />
        <TopBar title={active?.label ?? "ACOS"} />
        <div className="min-h-0 flex-1 overflow-y-auto">
          <ErrorBoundary><Outlet /></ErrorBoundary>
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 5: Router with lazy module routes**

```tsx
// frontend/src/router.tsx
import { lazy, Suspense } from "react";
import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "@/components/shell/AppShell";
import { Spinner } from "@/components/ui/Spinner";

const lazyPage = (factory: () => Promise<{ default: React.ComponentType }>) => {
  const C = lazy(factory);
  return (
    <Suspense fallback={<div className="flex flex-1 items-center justify-center p-16"><Spinner className="size-6" /></div>}>
      <C />
    </Suspense>
  );
};

export const router = createBrowserRouter([
  {
    path: "/", element: <AppShell />,
    children: [
      { index: true, element: lazyPage(() => import("@/pages/DashboardPage")) },
      { path: "resumes", element: lazyPage(() => import("@/pages/ResumePage")) },
      { path: "cover-letters", element: lazyPage(() => import("@/pages/CoverLetterPage")) },
      { path: "ats", element: lazyPage(() => import("@/pages/AtsPage")) },
      { path: "applications", element: lazyPage(() => import("@/pages/ApplicationsPage")) },
      { path: "copilot", element: lazyPage(() => import("@/pages/CopilotPage")) },
      { path: "questions", element: lazyPage(() => import("@/pages/QuestionsPage")) },
    ],
  },
]);
```

Create temporary placeholder pages so the router compiles (each module task replaces its page): for each of `DashboardPage, ResumePage, CoverLetterPage, AtsPage, ApplicationsPage, CopilotPage, QuestionsPage` create `frontend/src/pages/<Name>.tsx`:
```tsx
export default function Page() { return <div className="p-8 text-tahoe-muted">Coming soon</div>; }
```

- [ ] **Step 6: Wire main + App**

```tsx
// frontend/src/App.tsx
import { RouterProvider } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/lib/queryClient";
import { router } from "@/router";
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
```
Ensure `frontend/src/main.tsx` imports `./index.css` and renders `<App/>` in `<React.StrictMode>`.

- [ ] **Step 7: Run tests, types, build**

Run: `cd frontend && npm run test && npm run lint:types && npm run build`
Expected: all green; build emits separate chunks for each lazy page.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/shell frontend/src/hooks frontend/src/router.tsx frontend/src/App.tsx frontend/src/main.tsx frontend/src/pages frontend/src/assets
git commit -m "feat(shell): router, glass sidebar/topbar, logo, error boundary, Ollama degradation banner, lazy routes"
```

---

## TRACK C — MODULE UIs

> **Each module task is the same shape:** read its mock at `mock-designs/extracted/Screen N/src/App.tsx` for the visual language ONLY (glass surfaces, spacing, type scale). Then build a real, API-wired page using Task 5 primitives + Task 6 hooks. **Fix the three mock problems every time:** (1) remove fixed-canvas sizing (`w-480 h-270`, `min-h-[1080px]`, `w-464`) — pages must be fluid and fill the shell's scroll area; (2) replace all hard-coded fake data with live API data + loading/error/empty states; (3) keep the sidebar/topbar OUT of the page (the shell owns them). Shared workflow vocabulary across modules: **Generate → Review → Edit → Export**. Every AI output must show evidence + `ConfidenceBadge`.

### Task 8: Resume Builder UI (`/resumes`)

**Files:**
- Create: `frontend/src/pages/ResumePage.tsx` (replaces placeholder)
- Create: `frontend/src/features/resume/useResume.ts` (mutations), `ResumePreview.tsx`, `EvidencePanel.tsx`, `TemplatePicker.tsx`
- Create: `frontend/src/features/resume/ResumePage.test.tsx`
- Reference (read-only): `mock-designs/extracted/Screen 2/src/App.tsx`

**Interfaces:**
- Consumes: `apiPost<ResumeGenerateResponse>("/resume/generate", { job_description, template_name })`; `apiPost("/resume/analyze-ats", { resume_text, job_description })`; download via `POST /resume/generate/download` (blob). Template names: `software, ai, product, consulting, data_analytics, healthcare`.
- Produces: `useGenerateResume()` mutation hook returning `{ mutate, data, isPending, error }`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/features/resume/ResumePage.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ResumePage from "@/pages/ResumePage";

const wrap = (ui: React.ReactNode) => (
  <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>
);

describe("ResumePage", () => {
  beforeEach(() => vi.restoreAllMocks());
  it("generates a resume and shows bullets with confidence badges", async () => {
    const payload = {
      resume_id: "r1",
      content_json: { experiences: [{ title: "Data Eng", company: "Acme", dates: "2022", bullets: [{ text: "Built ETL", evidence_id: "e1", confidence: "verified" }] }], skills: ["Python"], projects: [], education: [] },
      ats_score: { overall_score: 0, keyword_score: 0, skill_score: 0, experience_score: 0, industry_score: 0, matched_keywords: [], missing_keywords: [], explanation: "" },
      weak_inference_count: 0, requires_approval: false,
    };
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(payload), { status: 200 })));
    render(wrap(<ResumePage />));
    await userEvent.type(screen.getByPlaceholderText(/job description/i), "Senior PM at fintech");
    await userEvent.click(screen.getByRole("button", { name: /generate/i }));
    expect(await screen.findByText("Built ETL")).toBeInTheDocument();
    expect(screen.getByText(/verified/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify failure** — `cd frontend && npm run test -- ResumePage` → FAIL.

- [ ] **Step 3: Implement** the page with this structure (use mock Screen 2 for styling):
  - Left column: `TemplatePicker` (the 6 templates as glass chips), a `<textarea>` with placeholder `Paste the job description…`, and a primary `Generate` button (`Button loading={isPending}`).
  - Center: `ResumePreview` rendering `content_json.experiences[].bullets[]`, each bullet row showing the text + `<ConfidenceBadge level={bullet.confidence}>`; skills as chips; projects list. An `Export DOCX` `Button` (downloads the blob) and a `Copy text` ghost button — this is the Generate→Review→Edit→Export flow (Edit = bullets are contenteditable or an editable textarea in this iteration; keep edit local-state only, no new endpoint).
  - Right: `EvidencePanel` (always visible per spec) listing each bullet's `evidence_id` and confidence.
  - States: `isPending` → skeleton/spinner; `error` (ApiError) → inline error card with `error.message`; no data → `EmptyState`.

`useResume.ts` wraps the mutations with TanStack `useMutation`. For DOCX download, fetch the blob directly (not via the JSON client) and trigger an `<a download>`.

- [ ] **Step 4: Run tests + types** — `cd frontend && npm run test -- ResumePage && npm run lint:types` → PASS.
- [ ] **Step 5: Commit** — `git add frontend/src/pages/ResumePage.tsx frontend/src/features/resume && git commit -m "feat(resume): Resume Builder UI with evidence panel + confidence badges (Generate/Review/Edit/Export)"`

---

### Task 9: Cover Letter Builder UI (`/cover-letters`)

**Files:**
- Create: `frontend/src/pages/CoverLetterPage.tsx`, `frontend/src/features/cover_letter/useCoverLetter.ts`, `CoverLetterPage.test.tsx`
- Reference: `mock-designs/extracted/Screen 4/src/App.tsx` (closest glass language)

**Interfaces:**
- Consumes: `apiPost("/cover-letter/generate", { job_description, company, position })` → `{ content, confidence_summary, evidence }` (see API appendix); `POST /cover-letter/generate/download` (blob); `POST /cover-letter/learn-voice` is **not** exposed in UI this phase (voice modeling already wired server-side). Confirm exact request fields by reading `backend/api/v1/routes/cover_letter.py` before implementing.

- [ ] **Step 1:** Write `CoverLetterPage.test.tsx` mirroring the resume test: type company + JD, click Generate (mocked fetch), assert the returned letter body text renders and an evidence/confidence element appears.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement: left = inputs (`company`, `position`, JD textarea); center = generated letter in an editable area with `Export DOCX`; right = `EvidencePanel` + overall `ConfidenceBadge` from `confidence_summary`. Same Generate→Review→Edit→Export flow, loading/error/empty states.
- [ ] **Step 4:** Run tests + types → PASS.
- [ ] **Step 5:** Commit `feat(cover-letter): Cover Letter Builder UI with evidence + confidence`.

---

### Task 10: ATS Analysis Dashboard (`/ats`)

**Files:**
- Create: `frontend/src/pages/AtsPage.tsx`, `frontend/src/features/ats/AtsRing.tsx`, `AtsPage.test.tsx`
- Reference: `mock-designs/extracted/Screen 2/src/App.tsx` (ATS panels) + the `.ats-ring` conic-gradient in `docs/09_DESIGN_GUIDELINES.css`.

**Interfaces:**
- Consumes: `apiPost<AtsScore>("/resume/analyze-ats", { resume_text, job_description })`.

- [ ] **Step 1:** Write `AtsPage.test.tsx`: paste resume text + JD, mock fetch returning an `AtsScore` with `overall_score: 84, matched_keywords:["python"], missing_keywords:["kafka"]`, click Analyze, assert `84` renders and both a matched and a missing keyword chip appear.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement: two textareas (resume, JD) + Analyze button; results = `AtsRing` (conic-gradient ring filled to `overall_score`%), the four sub-scores (keyword/skill/experience/industry) as labeled bars, matched keywords as green chips, missing as amber chips, and the `explanation` text. If `explanation` contains an Ollama error string, show the degradation note instead of a raw error. Loading/error/empty states.
- [ ] **Step 4:** Tests + types → PASS.
- [ ] **Step 5:** Commit `feat(ats): ATS Analysis dashboard with match ring + keyword breakdown`.

---

### Task 11: Application CRM Dashboard (`/applications`)

**Files:**
- Create: `frontend/src/pages/ApplicationsPage.tsx`, `frontend/src/features/crm/useApplications.ts`, `StatusColumn.tsx`, `ApplicationCard.tsx`, `NewApplicationDialog.tsx`, `ApplicationsPage.test.tsx`
- Reference: `mock-designs/extracted/Screen 3/src/App.tsx`

**Interfaces:**
- Consumes: `apiGet<Application[]>("/applications")`; `apiPost<Application>("/applications", body)`; `apiPatch("/applications/{id}/status", { status })`; `apiGet("/applications/{id}/timeline")`. Statuses (pipeline columns): `draft, applied, phone_screen, interview, final_round, offer, rejected, withdrawn`.

- [ ] **Step 1:** Write `ApplicationsPage.test.tsx`: mock `GET /applications` returning two apps in different statuses; assert both company names render under the correct status column headers.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement a board grouped by status (columns in the canonical order above), each `ApplicationCard` showing company, position, source, and a status `Badge`; a "New Application" button opening `NewApplicationDialog` (company, position, JD, source select) that POSTs then invalidates the `["applications"]` query; changing a card's status PATCHes and invalidates. Use TanStack Query for fetch + mutations. Loading skeleton, error card, `EmptyState` when no applications. (Drag-and-drop is out of scope — status change via a dropdown on the card.)
- [ ] **Step 4:** Tests + types → PASS.
- [ ] **Step 5:** Commit `feat(crm): Application CRM board with status pipeline + create/update`.

---

### Task 12: Career Copilot Chat (`/copilot`)

**Files:**
- Create: `frontend/src/pages/CopilotPage.tsx`, `frontend/src/features/copilot/useCopilot.ts`, `MessageBubble.tsx`, `CitationList.tsx`, `CopilotPage.test.tsx`
- Reference: `mock-designs/extracted/Screen 4/src/App.tsx`

**Interfaces:**
- Consumes: `apiPost<CopilotResponse>("/copilot/chat", { message, conversation_history })` → `{ response, intent, confidence, citations[], evidence_count }`; `apiGet<{intents:string[]}>("/copilot/intents")`. `conversation_history` is an array of `{ role, content }` the page maintains in local state (last turns).

- [ ] **Step 1:** Write `CopilotPage.test.tsx`: mock chat POST returning `{ response:"Here is advice", intent:"career_advice", confidence:"strong_inference", citations:[{source:"exp:1", text:"Led team", confidence:"verified", similarity:0.9}], evidence_count:1 }`; type a message, send, assert the assistant response text, the intent label, and a citation render.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement: scrollable message list (`MessageBubble` user/assistant), composer textarea + Send (Enter to send, Shift+Enter newline), each assistant message footer showing intent `Badge`, overall `ConfidenceBadge`, and `CitationList` (each citation: source, truncated text, `ConfidenceBadge`, similarity %). Maintain `conversation_history` in state and pass it on each call. Pending → typing indicator; error → inline assistant error bubble using `error.message`; empty → welcome `EmptyState`.
- [ ] **Step 4:** Tests + types → PASS.
- [ ] **Step 5:** Commit `feat(copilot): evidence-cited chat interface with intent + confidence`.

---

### Task 13: Question/Answer Manager + Learning summary (`/questions`)

**Files:**
- Create: `frontend/src/pages/QuestionsPage.tsx`, `frontend/src/features/questions/useQuestions.ts`, `QuestionCard.tsx`, `AnswerEditor.tsx`, `QuestionsPage.test.tsx`
- Reference: `mock-designs/extracted/Screen 6/src/App.tsx` (Learning Engine metric cards for the summary strip)

**Interfaces:**
- Consumes: `apiPost("/questions/generate", { job_description, company, position, industry, tech_stack })`; `apiGet<Question[]>("/questions")` (optional `?category=`); `apiPost("/questions/{id}/answer", { variables, application_id, length_target })`; `apiPatch("/questions/{id}/answers/{answer_id}", { edited_text, diff_summary })`; `apiGet("/questions/{id}/answers")`. `length_target` ∈ `short|medium|long`.

- [ ] **Step 1:** Write `QuestionsPage.test.tsx`: mock `GET /questions` returning two questions; assert both `question_template` strings render and a category filter control exists.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement: top strip = small Learning summary cards if `/learning/report` resolves (interview rate, avg ATS — read-only, optional, hide on error); a "Generate Questions" form (company, position, industry, tech stack, JD); a list of `QuestionCard`s each expandable to `AnswerEditor` (generate answer with length selector, edit + save via PATCH with a `diff_summary`, show `ConfidenceBadge` + evidence ids). Loading/error/empty states.
- [ ] **Step 4:** Tests + types → PASS.
- [ ] **Step 5:** Commit `feat(qa): Question/Answer manager with generation, editing learning loop, confidence`.

---

### Task 14: Dashboard landing page (`/`)

**Files:**
- Create: `frontend/src/pages/DashboardPage.tsx`, `DashboardPage.test.tsx`
- Reference: `mock-designs/extracted/Screen 1/src/App.tsx` (knowledge-graph hero) + Screen 6 metric cards.

**Interfaces:**
- Consumes: `apiGet("/applications")` (count + recent), `apiGet("/learning/report")` (optional metrics), `useOllamaHealth()`.

- [ ] **Step 1:** Write `DashboardPage.test.tsx`: mock `/applications` returning 3 apps; assert a total count `3` and quick-link cards to each module render.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement a calm overview: greeting, a row of stat cards (applications total, by-status counts, optional learning metrics), and large glass quick-action cards linking to Resumes / Cover Letters / Copilot / ATS. No knowledge-graph SVG re-implementation required — a simple hero glass panel with the logo suffices (keep it light; the graph mock is decorative). Loading/error/empty states.
- [ ] **Step 4:** Tests + types → PASS.
- [ ] **Step 5:** Commit `feat(dashboard): overview landing with stats + quick actions`.

---

## TRACK D — INTEGRATION & PRODUCTION READINESS

### Task 15: Shared EvidencePanel + confidence parity audit

**Files:**
- Create: `frontend/src/components/shared/EvidencePanel.tsx` (promote the resume one to shared), `EvidencePanel.test.tsx`
- Modify: resume, cover-letter, copilot, q&a pages to consume the shared component.

**Interfaces:**
- Produces: `<EvidencePanel items={EvidenceItem[]} emptyHint?>` where `EvidenceItem = { evidence_id|source, text?, confidence }`; always-visible, renders each item with a `ConfidenceBadge`; shows an explicit "No evidence — AI could not ground this output" state (the no-hallucination guarantee made visible).

- [ ] **Step 1:** Write `EvidencePanel.test.tsx`: render with two items (one verified, one weak) → both badges show; render with `[]` → the "No evidence" message shows.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement shared panel; refactor the four AI pages to import it (delete the resume-local copy). Verify each AI output surface (resume bullets, cover letter, copilot citations, q&a answers) shows evidence + confidence — this is the spec's "Evidence panel always visible" + "Confidence scoring visible" requirement.
- [ ] **Step 4:** `cd frontend && npm run test && npm run lint:types` → PASS (no regressions in the four pages' tests).
- [ ] **Step 5:** Commit `refactor(frontend): shared always-visible EvidencePanel with no-evidence guarantee across AI surfaces`.

---

### Task 16: Backend integration smoke tests (cross-system wiring)

**Files:**
- Create: `backend/tests/integration/test_phase5_integration.py`

**Interfaces:** verifies the five integration seams named in the spec resolve end-to-end through the API with Ollama mocked, asserting the error envelope and confidence fields are present.

- [ ] **Step 1: Write the tests**

Cover, using the `client` fixture and patching Ollama/RAG where needed (follow existing Phase 4 integration patterns):
1. Resume↔KG: `POST /resume/generate` returns `content_json` whose bullets carry a `confidence` in the allowed set.
2. ATS↔RAG: `POST /resume/analyze-ats` returns an `AtsScore` with all five score fields present.
3. Copilot↔Evidence: `POST /copilot/chat` returns `citations` and a `confidence` in the allowed set.
4. CRM↔Outcome: `POST /applications` then `POST /learning/outcome` for that application returns a `signal_weight`.
5. Error envelope: a deliberately bad request (e.g. `POST /applications` with an invalid status, or `GET /applications/{missing}`) returns the canonical `{"error":{"code",...}}` shape.

- [ ] **Step 2: Run** → iterate until green: `pytest backend/tests/integration/test_phase5_integration.py -v`.
- [ ] **Step 3: Coverage gate** → `pytest backend/tests/ --cov=backend --cov-fail-under=90 -q`.
- [ ] **Step 4: Commit** `test(integration): phase 5 cross-system smoke tests + error envelope assertions`.

---

### Task 17: Performance — lazy-load verification + bundle report

**Files:**
- Modify: `frontend/vite.config.ts` (manualChunks for heavy vendor libs if needed)
- Create: `docs/superpowers/phase-5-bundle-report.md`

- [ ] **Step 1:** Build with reporting: `cd frontend && npm run build`. Record per-chunk sizes. Confirm each module page is its own lazy chunk (from Task 7's `lazy()` routes) so Copilot/CRM/ATS are not in the initial bundle.
- [ ] **Step 2:** If any vendor lib (e.g. `recharts` if used, `@tanstack/react-query`) bloats the entry chunk, add a `build.rollupOptions.output.manualChunks` grouping vendors. Rebuild.
- [ ] **Step 3:** Write `docs/superpowers/phase-5-bundle-report.md` with the chunk table, initial-load JS total, and a note on which modules are lazy. Target: initial (shell + dashboard) JS < 300KB gzipped; note actuals.
- [ ] **Step 4:** `npm run lint:types && npm run test` → green.
- [ ] **Step 5:** Commit `perf(frontend): verify per-module lazy chunks + bundle report`.

---

### Task 18: E2E golden paths (Playwright) + final verification

**Files:**
- Create: `frontend/playwright.config.ts`, `frontend/e2e/golden-paths.spec.ts`
- Modify: `frontend/package.json` (`"e2e": "playwright test"`)

**Interfaces:** Playwright drives the running app (Vite :1420) against a running backend (:8000). Tests must tolerate Ollama being offline (assert on UI structure + degradation banner, not on LLM content).

- [ ] **Step 1: Install + config**

```bash
cd frontend && npm install -D @playwright/test && npx playwright install chromium
```
`playwright.config.ts`: `webServer` starts `npm run dev`, `baseURL: http://localhost:1420`, project chromium.

- [ ] **Step 2: Write golden-path specs**

`e2e/golden-paths.spec.ts` — navigation + presence (resilient to AI being offline):
1. App loads, sidebar shows all 7 nav items; clicking each routes and renders its page title.
2. Resumes: a template is selectable, JD textarea accepts input, Generate button is enabled.
3. Copilot: composer accepts text; Send is present.
4. Applications: "New Application" opens the dialog.
5. Degradation: if `/health/ollama` reports degraded, the banner is visible (conditional assertion).

- [ ] **Step 3: Run** (backend must be up): `source .venv/bin/activate && uvicorn backend.main:app --port 8000 &` then `cd frontend && npm run e2e`. Iterate until green.

- [ ] **Step 4: Final full verification**

Run all gates:
```bash
source .venv/bin/activate && pytest backend/tests/ --cov=backend --cov-fail-under=90 -q
cd frontend && npm run lint:types && npm run test && npm run build && npm run e2e
```
Expected: backend ≥90% coverage all-pass; frontend types clean, all component tests pass, build succeeds, e2e green.

- [ ] **Step 5: Commit** `test(e2e): playwright golden-path coverage + final phase-5 verification`.

---

## API Map Appendix (authoritative shapes for `frontend/src/types/api.ts`)

Implementers MUST confirm each shape by reading the corresponding `backend/api/v1/routes/*.py` and service return values before finalizing types; the below is the contract as of Phase 4.

```ts
export type Confidence = "verified" | "strong_inference" | "weak_inference";

export interface EvidenceItem { evidence_id?: string; source?: string; text?: string; confidence: Confidence; similarity_score?: number; }

export interface ResumeBullet { text: string; evidence_id: string; confidence: Confidence; }
export interface ResumeExperience { title: string; company: string; dates: string; bullets: ResumeBullet[]; }
export interface ResumeProject { name: string; description: string; tech: string[] | string; evidence_id: string; }
export interface ResumeContent { experiences: ResumeExperience[]; skills: string[]; projects: ResumeProject[]; education: unknown[]; }
export interface AtsScore { overall_score: number; keyword_score: number; skill_score: number; experience_score: number; industry_score: number; matched_keywords: string[]; missing_keywords: string[]; explanation: string; }
export interface ResumeGenerateResponse { resume_id: string; content_json: ResumeContent; ats_score: AtsScore; weak_inference_count: number; requires_approval: boolean; }

export interface Application { id: string; company: string; position: string; status: string; source?: string; work_arrangement?: string; created_at?: string; }

export interface Citation { source: string; text: string; confidence: Confidence; similarity: number; }
export interface CopilotResponse { response: string; intent: string; confidence: Confidence; citations: Citation[]; evidence_count: number; }

export interface Question { id: string; question_template: string; category: string; source?: string; }
export interface Answer { answer_id: string; question_id: string; original_answer?: string; edited_answer?: string; confidence_level?: Confidence; requires_approval?: boolean; evidence_ids?: string[]; }

export interface OllamaHealth { available: boolean; models: string[]; required_models: string[]; missing_models: string[]; degraded: boolean; }
export interface LearningReport { template_rankings: { template_name: string; score: number; signal_count: number }[]; ats_vs_outcome: { buckets: { range: string; outcome_rate: number; count: number }[]; total_signals: number }; }
```

---

## Definition of Done (Phase 5)

- Backend: structured error envelope on all error paths; timing middleware + the five operation logs; `/health/ollama` degradation contract; coverage ≥90%.
- Frontend: Tahoe design system; app shell with router, sidebar, logo (correct blend rules), error boundary, degradation banner; six wired module UIs + dashboard; every AI output shows always-visible evidence + confidence; Generate→Review→Edit→Export present where applicable; per-module lazy chunks; component tests + Playwright golden paths green; `tsc --noEmit` clean; production build succeeds.
- No new features, AI systems, data models, or migrations introduced.
