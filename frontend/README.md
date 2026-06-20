# Frontend

Tauri v2 desktop app with a React 18 + TypeScript UI. Styling via TailwindCSS, state via
Zustand, routing via React Router.

> Design rationale: [ADR-005](../docs/adr/ADR-005-tauri-react-frontend.md) ·
> Visual guidelines: [`../docs/09_DESIGN_GUIDELINES.css`](../docs/09_DESIGN_GUIDELINES.css)

## Layout

| Path | Purpose |
|------|---------|
| `src/pages/` | Top-level screens (Resume, ATS, Copilot, Optimization, Applications, Settings, …). |
| `src/components/` | Reusable UI — `ui/` primitives, `shared/`, and per-feature folders. |
| `src/layouts/` | App shell and navigation (`AppShell.tsx`). |
| `src/services/` | Typed clients for the backend REST API (`api.ts` + per-domain). |
| `src/stores/` | Zustand global state (`useAppStore.ts`). |
| `src/types/` | Shared TypeScript types (mirror backend schemas). |
| `src-tauri/` | Rust desktop shell: launches the backend sidecar and hosts the webview. |
| `e2e/` | Playwright end-to-end specs. |

## How it connects

The Tauri Rust shell (`src-tauri/`) starts the bundled backend binary as a **sidecar** and
the React UI talks to it over `http://localhost:8000`. The UI never reads the database
directly — all data flows through the backend API.

## Develop, test, build

```bash
npm install

npm run dev          # Vite dev server in the browser
npm run tauri dev    # full desktop app (needs backend running or bundled)

npx tsc --noEmit     # type checking
npx playwright test  # end-to-end tests

npm run build        # tsc + vite build (output → dist/, git-ignored)
npm run tauri build  # production desktop bundle
```

> `dist/` and `src-tauri/target/` are build output — git-ignored and safe to delete.
