# ADR-005: Tauri + React + TypeScript for Desktop Frontend

**Status:** Accepted  
**Date:** 2026-06-18  
**Deciders:** Andrew Nguyen

---

## Context

ACOS is a desktop application (macOS-first). The frontend needs to:
- Display rich UI (document previews, chat interface, kanban board)
- Communicate with the local FastAPI backend
- Package into a distributable DMG
- Support local file system access

---

## Decision

Use **Tauri v2** for the desktop shell and **React 18 + TypeScript** for the UI layer,
with **TailwindCSS** for styling.

---

## Consequences

**Positive:**
- Tauri produces significantly smaller binaries than Electron (Rust webview vs bundled Chromium)
- React has the largest ecosystem for complex UI components
- TypeScript prevents entire class of runtime bugs in frontend logic
- TailwindCSS enables rapid UI development without custom CSS files
- Tauri IPC allows secure communication with local filesystem and backend
- Tauri v2 has stable macOS support and DMG packaging

**Negative:**
- Tauri requires Rust toolchain to build (one-time setup)
- Tauri IPC has different patterns from web fetch — developers must learn the Tauri command model
- Less mature than Electron for desktop-specific features

**Mitigations:**
- Use `context7` for Tauri v2 docs before any IPC implementation
- FastAPI backend handles all business logic; Tauri IPC only used for system operations (file paths, open dialogs)
- Frontend communicates with FastAPI via standard `fetch()` — Tauri IPC is a minimal surface

---

## Frontend Architecture

```
frontend/src/
├── pages/           (route-level components)
├── components/      (reusable UI components)
│   ├── ui/          (design system primitives)
│   ├── resume/      (resume-specific components)
│   ├── cover_letter/
│   ├── copilot/
│   ├── applications/
│   └── shared/
├── hooks/           (custom React hooks)
├── services/        (API client functions)
├── stores/          (Zustand state stores)
├── layouts/         (page layout wrappers)
└── types/           (TypeScript type definitions)
```

---

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Electron | 3–4x larger binary; slower startup; more resource-heavy |
| Native Swift (macOS) | Windows/Linux portability impossible; smaller ecosystem |
| Flutter Desktop | Dart ecosystem is foreign; React preferred |
| Web app (browser) | Cannot access local filesystem securely |
| PyQt / Tkinter | Python UI frameworks are significantly behind React in capability |
