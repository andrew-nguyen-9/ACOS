# Phase 5: UI/UX Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the near-empty Tauri frontend skeleton into a production-quality macOS Tahoe Liquid Glass desktop app with 8 fully-wired pages, shared component library, typed API service layer, and backend observability.

**Architecture:** React Router v6 SPA inside Tauri v2 window; Zustand for global state; typed fetch wrapper over FastAPI backend at `http://localhost:8000/api/v1`; all pages built from mock designs (Screens 1–6).

**Tech Stack:** Tauri v2 · React 18 · TypeScript · Tailwind CSS v3.4 · Vite · react-router-dom v6 · Zustand · lucide-react · recharts · tw-animate-css · shadcn/ui (radix primitives) · clsx · tailwind-merge · class-variance-authority

## Global Constraints

- Tailwind v3.4.15 is locked — do NOT upgrade to v4. Adapt all mock-design v4 syntax to v3.
- React 18 is locked — do NOT upgrade to v19.
- No new backend features, data models, or AI systems.
- Tauri window: 1280×800, CSP: `connect-src http://localhost:8000`.
- App logo (`mock-designs/app-logo.png`): `mix-blend-screen` on dark background only; do NOT display on light backgrounds.
- Design tokens: `#4c8dff` blue accent; `--verified: #30D158`; `--strong: #5AC8FA`; `--weak: #FF9F0A`.
- Font: Inter (load via `index.html` Google Fonts).
- All path imports via `@/` alias pointing to `frontend/src/`.
- No `.summary` field anywhere in resume UI — it was intentionally removed from Phase 4.
- Confidence values: exactly `"verified"` | `"strong_inference"` | `"weak_inference"`.

---

### Task 1: Foundation — Dependencies, Design Tokens, Router, AppShell

**Files:**
- Modify: `frontend/package.json` (deps)
- Modify: `frontend/vite.config.ts` (path alias)
- Modify: `frontend/tsconfig.app.json` (path alias)
- Modify: `frontend/tailwind.config.js` (design tokens, Inter font, animate plugin)
- Modify: `frontend/src/index.css` (reset, scrollbar hide, Inter font, CSS vars)
- Modify: `frontend/index.html` (Google Fonts Inter link)
- Create: `frontend/src/lib/utils.ts` (`cn` helper)
- Create: `frontend/src/layouts/AppShell.tsx` (sidebar + main area wrapper)
- Modify: `frontend/src/main.tsx` (wrap in BrowserRouter)
- Modify: `frontend/src/App.tsx` (replace stub with Routes)

**Interfaces:**
- Produces: `AppShell` used by all page components; `cn()` used everywhere; `@/` alias resolves to `frontend/src/`

- [ ] **Step 1: Install npm packages**

```bash
cd frontend
npm install react-router-dom@6 zustand lucide-react recharts tw-animate-css class-variance-authority clsx tailwind-merge @radix-ui/react-slot
npm install --save-dev @types/node
```

Expected: no errors, `node_modules` updated.

- [ ] **Step 2: Add Inter font to index.html**

In `frontend/index.html`, add inside `<head>` before the existing `<link>`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

Note: Tauri CSP must allow `fonts.googleapis.com`. Add to `src-tauri/tauri.conf.json` security CSP:
```json
"csp": "default-src 'self'; connect-src http://localhost:8000; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; script-src 'self'"
```

- [ ] **Step 3: Configure path alias in vite.config.ts**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
  },
});
```

- [ ] **Step 4: Configure path alias in tsconfig.app.json**

Add inside `"compilerOptions"`:
```json
"baseUrl": ".",
"paths": {
  "@/*": ["./src/*"]
}
```

- [ ] **Step 5: Configure Tailwind with design tokens**

Replace `frontend/tailwind.config.js` (create if not present):
```javascript
import twAnimate from "tw-animate-css";

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        accent: "#4c8dff",
        verified: "#30D158",
        strong: "#5AC8FA",
        weak: "#FF9F0A",
      },
      height: {
        "10.5": "2.625rem",
      },
    },
  },
  plugins: [twAnimate],
};
```

- [ ] **Step 6: Update index.css**

Replace `frontend/src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --accent: #4c8dff;
  --verified: #30D158;
  --strong: #5AC8FA;
  --weak: #FF9F0A;
  font-family: "Inter", ui-sans-serif, system-ui, sans-serif;
}

* {
  scrollbar-width: none;
}
*::-webkit-scrollbar {
  display: none;
}

body {
  margin: 0;
  padding: 0;
  background: #0a0a0a;
  color: #fafafa;
}
```

- [ ] **Step 7: Create cn utility**

Create `frontend/src/lib/utils.ts`:
```typescript
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 8: Create AppShell layout**

Create `frontend/src/layouts/AppShell.tsx`:
```typescript
import { type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard, FileText, Mail, BarChart3, MessageSquareMore,
  Briefcase, Sparkles, Bot, Settings, BriefcaseBusiness,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/resumes", label: "Resumes", icon: FileText },
  { to: "/cover-letters", label: "Cover Letters", icon: Mail },
  { to: "/ats", label: "ATS Analysis", icon: BarChart3 },
  { to: "/interview-prep", label: "Interview Prep", icon: MessageSquareMore },
  { to: "/applications", label: "Applications CRM", icon: Briefcase },
  { to: "/learning", label: "Learning Engine", icon: Sparkles },
  { to: "/copilot", label: "Copilot", icon: Bot },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="bg-neutral-950 text-neutral-50 min-h-screen w-screen overflow-hidden">
      <div className="bg-[#4c8dff]/[0.18] flex p-8 h-screen overflow-hidden">
        <div
          className="shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-[60px] rounded-3xl
                     bg-neutral-900/70 border border-white/10 flex w-full overflow-hidden"
        >
          <aside
            className="bg-white/[0.04] border-r border-white/10 flex px-4 py-6 flex-col w-60 flex-shrink-0"
          >
            <div className="flex mb-8 px-2 items-center gap-3">
              <div
                className="size-10 shadow-[inset_0_1px_0_rgba(255,255,255,0.12),0_10px_30px_rgba(76,141,255,0.18)]
                           rounded-xl bg-neutral-200/[0.15] flex justify-center items-center"
              >
                <BriefcaseBusiness className="size-5 text-neutral-200" />
              </div>
              <div className="leading-tight">
                <div className="font-semibold text-neutral-50 text-[15px] tracking-[-0.64px]">ACOS</div>
                <div className="text-[#a1a1a1] text-[11px]">Career OS</div>
              </div>
            </div>
            <nav className="flex flex-col flex-1 gap-2">
              {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  className={({ isActive }) =>
                    cn(
                      "rounded-xl flex px-3.5 items-center gap-3 h-11 font-medium text-[13px] transition-colors",
                      isActive
                        ? "shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] bg-neutral-200/[0.15] text-neutral-50"
                        : "text-[#a1a1a1] hover:text-neutral-300 hover:bg-white/[0.04]"
                    )
                  }
                >
                  <Icon className="size-4" />
                  <span>{label}</span>
                </NavLink>
              ))}
            </nav>
          </aside>
          <main className="flex-1 overflow-auto">{children}</main>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 9: Update main.tsx with BrowserRouter**

Replace `frontend/src/main.tsx`:
```typescript
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
```

- [ ] **Step 10: Update App.tsx with routes scaffold**

Replace `frontend/src/App.tsx`:
```typescript
import { Routes, Route } from "react-router-dom";
import AppShell from "@/layouts/AppShell";
import Dashboard from "@/pages/Dashboard";
import ResumePage from "@/pages/ResumePage";
import CoverLetterPage from "@/pages/CoverLetterPage";
import AtsPage from "@/pages/AtsPage";
import InterviewPrepPage from "@/pages/InterviewPrepPage";
import ApplicationsPage from "@/pages/ApplicationsPage";
import LearningPage from "@/pages/LearningPage";
import CopilotPage from "@/pages/CopilotPage";
import SettingsPage from "@/pages/SettingsPage";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/resumes" element={<ResumePage />} />
        <Route path="/cover-letters" element={<CoverLetterPage />} />
        <Route path="/ats" element={<AtsPage />} />
        <Route path="/interview-prep" element={<InterviewPrepPage />} />
        <Route path="/applications" element={<ApplicationsPage />} />
        <Route path="/learning" element={<LearningPage />} />
        <Route path="/copilot" element={<CopilotPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </AppShell>
  );
}
```

- [ ] **Step 11: Create stub pages so App compiles**

Create each of these as a minimal stub (replace with real implementations in later tasks):

`frontend/src/pages/Dashboard.tsx`:
```typescript
export default function Dashboard() {
  return <div className="p-8 text-neutral-50">Dashboard — coming in Task 4</div>;
}
```

Repeat for: `ResumePage.tsx`, `CoverLetterPage.tsx`, `AtsPage.tsx`, `InterviewPrepPage.tsx`, `ApplicationsPage.tsx`, `LearningPage.tsx`, `CopilotPage.tsx`, `SettingsPage.tsx`.

- [ ] **Step 12: Verify the app compiles and runs**

```bash
cd frontend && npm run build
```

Expected: exits 0. Then `npm run dev` and confirm `http://localhost:1420` loads the sidebar.

- [ ] **Step 13: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/tsconfig.app.json frontend/tailwind.config.js frontend/index.html frontend/src/
git commit -m "feat(ui): foundation — deps, design tokens, router, AppShell"
```

---

### Task 2: Shared Component Library

**Files:**
- Create: `frontend/src/components/ui/GlassCard.tsx`
- Create: `frontend/src/components/ui/ConfidenceBadge.tsx`
- Create: `frontend/src/components/ui/LoadingSpinner.tsx`
- Create: `frontend/src/components/ui/EmptyState.tsx`
- Create: `frontend/src/components/ErrorBoundary.tsx`

**Interfaces:**
- `GlassCard`: `{ children, className? }` → glass panel wrapper used by all pages
- `ConfidenceBadge`: `{ level: "verified" | "strong_inference" | "weak_inference" }` → colored pill
- `LoadingSpinner`: `{ size?: "sm" | "md" | "lg"; label?: string }` → spinning indicator
- `EmptyState`: `{ title, description, icon? }` → empty state display
- `ErrorBoundary`: wraps subtrees to catch React render errors

- [ ] **Step 1: Create GlassCard**

Create `frontend/src/components/ui/GlassCard.tsx`:
```typescript
import { cn } from "@/lib/utils";
import { type ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
}

export function GlassCard({ children, className }: GlassCardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl bg-white/[0.05] border border-white/10 shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_18px_50px_rgba(0,0,0,0.28)]",
        className
      )}
    >
      {children}
    </div>
  );
}
```

- [ ] **Step 2: Create ConfidenceBadge**

Create `frontend/src/components/ui/ConfidenceBadge.tsx`:
```typescript
import { cn } from "@/lib/utils";

type ConfidenceLevel = "verified" | "strong_inference" | "weak_inference";

const CONFIG: Record<ConfidenceLevel, { label: string; className: string }> = {
  verified: {
    label: "Verified",
    className: "bg-[#30D158]/10 text-[#30D158] border-[#30D158]/20",
  },
  strong_inference: {
    label: "Strong",
    className: "bg-[#5AC8FA]/10 text-[#5AC8FA] border-[#5AC8FA]/20",
  },
  weak_inference: {
    label: "Weak ⚠",
    className: "bg-[#FF9F0A]/10 text-[#FF9F0A] border-[#FF9F0A]/20",
  },
};

export function ConfidenceBadge({ level }: { level: ConfidenceLevel }) {
  const { label, className } = CONFIG[level] ?? CONFIG.weak_inference;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
        className
      )}
    >
      {label}
    </span>
  );
}
```

- [ ] **Step 3: Create LoadingSpinner**

Create `frontend/src/components/ui/LoadingSpinner.tsx`:
```typescript
import { cn } from "@/lib/utils";

const SIZE_MAP = { sm: "size-4", md: "size-6", lg: "size-8" };

export function LoadingSpinner({
  size = "md",
  label,
  className,
}: {
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center gap-3", className)}>
      <div
        className={cn(
          "animate-spin rounded-full border-2 border-white/20 border-t-[#4c8dff]",
          SIZE_MAP[size]
        )}
      />
      {label && <p className="text-[#a1a1a1] text-sm">{label}</p>}
    </div>
  );
}
```

- [ ] **Step 4: Create EmptyState**

Create `frontend/src/components/ui/EmptyState.tsx`:
```typescript
import { type LucideIcon } from "lucide-react";

export function EmptyState({
  title,
  description,
  icon: Icon,
}: {
  title: string;
  description: string;
  icon?: LucideIcon;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 py-16 text-center">
      {Icon && (
        <div className="size-12 rounded-2xl bg-neutral-200/[0.08] flex items-center justify-center">
          <Icon className="size-6 text-[#a1a1a1]" />
        </div>
      )}
      <div>
        <p className="font-semibold text-neutral-200 text-base">{title}</p>
        <p className="text-[#a1a1a1] text-sm mt-1 max-w-xs">{description}</p>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create ErrorBoundary**

Create `frontend/src/components/ErrorBoundary.tsx`:
```typescript
import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}
interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(err: Error): State {
    return { hasError: true, message: err.message };
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="flex flex-col items-center justify-center h-full gap-3 p-8">
            <p className="font-semibold text-red-400">Something went wrong</p>
            <p className="text-[#a1a1a1] text-sm font-mono">{this.state.message}</p>
            <button
              className="mt-2 px-4 py-2 rounded-xl bg-white/[0.08] text-neutral-200 text-sm hover:bg-white/[0.12] transition-colors"
              onClick={() => this.setState({ hasError: false, message: "" })}
            >
              Retry
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
```

- [ ] **Step 6: Wire ErrorBoundary into App.tsx**

Wrap `<AppShell>` in `App.tsx`:
```typescript
import { ErrorBoundary } from "@/components/ErrorBoundary";
// ...
return (
  <ErrorBoundary>
    <AppShell>
      <Routes>...</Routes>
    </AppShell>
  </ErrorBoundary>
);
```

- [ ] **Step 7: Verify build**

```bash
cd frontend && npm run build
```

Expected: exits 0.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/ frontend/src/App.tsx
git commit -m "feat(ui): shared component library — GlassCard, ConfidenceBadge, LoadingSpinner, EmptyState, ErrorBoundary"
```

---

### Task 3: API Service Layer + TypeScript Types + Zustand Stores

**Files:**
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/services/api.ts`
- Create: `frontend/src/services/resume.ts`
- Create: `frontend/src/services/coverLetter.ts`
- Create: `frontend/src/services/applications.ts`
- Create: `frontend/src/services/copilot.ts`
- Create: `frontend/src/services/learning.ts`
- Create: `frontend/src/stores/useAppStore.ts`

**Interfaces:**
- `api.ts` exports: `apiFetch<T>(path, init?)` — base fetch with error handling
- Each service file exports typed async functions
- `useAppStore` exports: `{ ollamaStatus, setOllamaStatus }` — global health

- [ ] **Step 1: Define TypeScript types**

Create `frontend/src/types/api.ts`:
```typescript
export type ConfidenceLevel = "verified" | "strong_inference" | "weak_inference";

export interface HealthResponse {
  status: string;
  db: string;
  version: string;
}

export interface ResumeBullet {
  text: string;
  evidence_id: string;
  confidence: ConfidenceLevel;
}

export interface ResumeExperience {
  title: string;
  company: string;
  dates: string;
  bullets: ResumeBullet[];
}

export interface ResumeContent {
  experiences: ResumeExperience[];
  skills: string[];
  projects: Array<{ name: string; description?: string; tech?: string }>;
  education: Array<{ degree: string; school: string; dates?: string }>;
}

export interface ResumeGenerateRequest {
  job_description: string;
  template_name?: string;
  application_id?: string;
}

export interface ResumeGenerateResponse {
  resume_id: string;
  content_json: ResumeContent;
  ats_score: {
    overall_score: number;
    keyword_score: number;
    skill_score: number;
    matched_keywords: string[];
    missing_keywords: string[];
  };
  weak_inference_count: number;
  requires_approval: boolean;
}

export interface Application {
  id: string;
  company: string;
  role: string;
  status: string;
  date_applied: string | null;
  notes: string | null;
  job_description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationCreate {
  company: string;
  role: string;
  status?: string;
  date_applied?: string;
  notes?: string;
  job_description?: string;
}

export interface CopilotChatRequest {
  message: string;
  conversation_history?: Array<{ role: string; content: string }>;
}

export interface CopilotChatResponse {
  response: string;
  intent: string;
  confidence: ConfidenceLevel;
  citations: Array<{ source: string; text: string; confidence: ConfidenceLevel; similarity: number }>;
  evidence_count: number;
}

export interface LearningOutcome {
  question_id: string;
  application_id: string;
  outcome: "correct" | "incorrect" | "skipped";
  time_spent_seconds?: number;
}

export interface GeneratedQuestion {
  id: string;
  question_text: string;
  question_type: string;
  difficulty: string;
  application_id: string;
  created_at: string;
}
```

- [ ] **Step 2: Create base API fetch utility**

Create `frontend/src/services/api.ts`:
```typescript
const BASE = "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<T>;
}
```

- [ ] **Step 3: Create resume service**

Create `frontend/src/services/resume.ts`:
```typescript
import { apiFetch } from "./api";
import type { ResumeGenerateRequest, ResumeGenerateResponse } from "@/types/api";

export const resumeService = {
  generate: (req: ResumeGenerateRequest) =>
    apiFetch<ResumeGenerateResponse>("/resume/generate", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  exportDocx: async (resumeId: string): Promise<Blob> => {
    const res = await fetch(
      `http://localhost:8000/api/v1/resume/${resumeId}/export`,
      { method: "GET" }
    );
    if (!res.ok) throw new Error("Export failed");
    return res.blob();
  },
};
```

- [ ] **Step 4: Create applications service**

Create `frontend/src/services/applications.ts`:
```typescript
import { apiFetch } from "./api";
import type { Application, ApplicationCreate } from "@/types/api";

export const applicationsService = {
  list: () => apiFetch<Application[]>("/applications/"),
  get: (id: string) => apiFetch<Application>(`/applications/${id}`),
  create: (data: ApplicationCreate) =>
    apiFetch<Application>("/applications/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<ApplicationCreate>) =>
    apiFetch<Application>(`/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    apiFetch<void>(`/applications/${id}`, { method: "DELETE" }),
};
```

- [ ] **Step 5: Create copilot service**

Create `frontend/src/services/copilot.ts`:
```typescript
import { apiFetch } from "./api";
import type { CopilotChatRequest, CopilotChatResponse } from "@/types/api";

export const copilotService = {
  chat: (req: CopilotChatRequest) =>
    apiFetch<CopilotChatResponse>("/copilot/chat", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  intents: () => apiFetch<{ intents: string[] }>("/copilot/intents"),
};
```

- [ ] **Step 6: Create cover letter service**

Create `frontend/src/services/coverLetter.ts`:
```typescript
import { apiFetch } from "./api";

interface CoverLetterRequest {
  job_description: string;
  application_id?: string;
}

interface CoverLetterResponse {
  cover_letter_id: string;
  content_text: string;
  weak_inference_count: number;
  requires_approval: boolean;
}

export const coverLetterService = {
  generate: (req: CoverLetterRequest) =>
    apiFetch<CoverLetterResponse>("/cover_letter/generate", {
      method: "POST",
      body: JSON.stringify(req),
    }),
};
```

- [ ] **Step 7: Create learning service**

Create `frontend/src/services/learning.ts`:
```typescript
import { apiFetch } from "./api";
import type { GeneratedQuestion, LearningOutcome } from "@/types/api";

export const learningService = {
  generateQuestions: (applicationId: string) =>
    apiFetch<{ questions: GeneratedQuestion[] }>(
      `/questions/generate?application_id=${applicationId}`,
      { method: "POST" }
    ),
  recordOutcome: (outcome: LearningOutcome) =>
    apiFetch<{ recorded: boolean }>("/learning/outcome", {
      method: "POST",
      body: JSON.stringify(outcome),
    }),
  getRecommendations: () =>
    apiFetch<{ recommendations: GeneratedQuestion[] }>("/learning/recommendations"),
};
```

- [ ] **Step 8: Create global app store**

Create `frontend/src/stores/useAppStore.ts`:
```typescript
import { create } from "zustand";

type OllamaStatus = "unknown" | "online" | "offline";

interface AppState {
  ollamaStatus: OllamaStatus;
  setOllamaStatus: (status: OllamaStatus) => void;
}

export const useAppStore = create<AppState>((set) => ({
  ollamaStatus: "unknown",
  setOllamaStatus: (status) => set({ ollamaStatus: status }),
}));
```

- [ ] **Step 9: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/types/ frontend/src/services/ frontend/src/stores/
git commit -m "feat(ui): API service layer, TypeScript types, Zustand store"
```

---

### Task 4: Dashboard Page

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

**Interfaces:**
- Consumes: `apiFetch` from `@/services/api`; `GlassCard` from `@/components/ui/GlassCard`; `LoadingSpinner` from `@/components/ui/LoadingSpinner`
- The dashboard shows: backend health pill, 4 stat cards (Resumes Generated, Applications, ATS Avg Score, Questions Answered), a "Quick Actions" panel, and system status (Ollama + ChromaDB)

- [ ] **Step 1: Write the Dashboard page (from Screen 1 design)**

Replace `frontend/src/pages/Dashboard.tsx`:
```typescript
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText, Briefcase, Target, MessageSquareMore,
  Plus, Sparkles, Bot, CheckCircle2, WifiOff, Zap,
} from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { apiFetch } from "@/services/api";
import { applicationsService } from "@/services/applications";
import type { Application } from "@/types/api";

interface Health {
  status: string;
  db: string;
  version: string;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [health, setHealth] = useState<Health | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiFetch<Health>("/health"),
      applicationsService.list(),
    ]).then(([h, apps]) => {
      setHealth(h);
      setApplications(apps);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" label="Loading dashboard…" />
      </div>
    );
  }

  const stats = [
    { label: "Applications", value: applications.length, icon: Briefcase, color: "text-[#4c8dff]" },
    { label: "Resumes Generated", value: "—", icon: FileText, color: "text-[#30D158]" },
    { label: "Avg ATS Score", value: "—", icon: Target, color: "text-[#5AC8FA]" },
    { label: "Interview Questions", value: "—", icon: MessageSquareMore, color: "text-[#FF9F0A]" },
  ];

  const quickActions = [
    { label: "Generate Resume", icon: FileText, to: "/resumes" },
    { label: "New Application", icon: Plus, to: "/applications" },
    { label: "Ask Copilot", icon: Bot, to: "/copilot" },
    { label: "Practice Interview", icon: Sparkles, to: "/interview-prep" },
  ];

  return (
    <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">Dashboard</h1>
          <p className="text-[#a1a1a1] text-sm mt-1">AI Career Operating System</p>
        </div>
        {health && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#30D158]/10 border border-[#30D158]/20">
            <CheckCircle2 className="size-3.5 text-[#30D158]" />
            <span className="text-[#30D158] text-xs font-medium">v{health.version} · online</span>
          </div>
        )}
        {!health && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/10 border border-red-500/20">
            <WifiOff className="size-3.5 text-red-400" />
            <span className="text-red-400 text-xs font-medium">Backend unreachable</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-4 gap-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <GlassCard key={label} className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[#a1a1a1] text-xs">{label}</p>
                <p className={`font-bold text-3xl tracking-tight mt-2 ${color}`}>{value}</p>
              </div>
              <div className="size-8 rounded-xl bg-white/[0.06] flex items-center justify-center">
                <Icon className={`size-4 ${color}`} />
              </div>
            </div>
          </GlassCard>
        ))}
      </div>

      <div className="grid grid-cols-[1fr_280px] gap-6 flex-1">
        <GlassCard className="p-6">
          <h2 className="font-semibold text-neutral-200 text-sm mb-4 flex items-center gap-2">
            <Briefcase className="size-4 text-[#4c8dff]" />
            Recent Applications
          </h2>
          {applications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center gap-3">
              <Briefcase className="size-8 text-neutral-600" />
              <p className="text-[#a1a1a1] text-sm">No applications yet</p>
              <button
                onClick={() => navigate("/applications")}
                className="text-[#4c8dff] text-xs hover:underline"
              >
                Track your first application →
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {applications.slice(0, 6).map((app) => (
                <div
                  key={app.id}
                  className="flex items-center justify-between px-4 py-3 rounded-xl bg-white/[0.03] hover:bg-white/[0.06] transition-colors cursor-pointer"
                  onClick={() => navigate("/applications")}
                >
                  <div>
                    <p className="font-medium text-neutral-200 text-sm">{app.role}</p>
                    <p className="text-[#a1a1a1] text-xs">{app.company}</p>
                  </div>
                  <span className="text-xs px-2.5 py-1 rounded-full bg-[#4c8dff]/10 text-[#4c8dff] border border-[#4c8dff]/20">
                    {app.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </GlassCard>

        <div className="flex flex-col gap-4">
          <GlassCard className="p-5">
            <h2 className="font-semibold text-neutral-200 text-sm mb-3 flex items-center gap-2">
              <Zap className="size-4 text-[#4c8dff]" />
              Quick Actions
            </h2>
            <div className="flex flex-col gap-2">
              {quickActions.map(({ label, icon: Icon, to }) => (
                <button
                  key={label}
                  onClick={() => navigate(to)}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-[#a1a1a1] hover:text-neutral-200 hover:bg-white/[0.06] transition-colors text-sm font-medium text-left"
                >
                  <Icon className="size-4 text-[#4c8dff]" />
                  {label}
                </button>
              ))}
            </div>
          </GlassCard>

          <GlassCard className="p-5">
            <h2 className="font-semibold text-neutral-200 text-sm mb-3">System</h2>
            <div className="flex flex-col gap-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[#a1a1a1]">Backend</span>
                <span className={health ? "text-[#30D158]" : "text-red-400"}>
                  {health ? "online" : "offline"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#a1a1a1]">Database</span>
                <span className={health?.db === "ok" ? "text-[#30D158]" : "text-[#FF9F0A]"}>
                  {health?.db ?? "—"}
                </span>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat(ui): Dashboard page — stats, recent applications, quick actions"
```

---

### Task 5: Resume Builder Page

**Files:**
- Modify: `frontend/src/pages/ResumePage.tsx`

**Interfaces:**
- Consumes: `resumeService.generate`, `GlassCard`, `LoadingSpinner`, `ConfidenceBadge`
- Produces: Resume builder UI with template picker, JD input, and generated result with evidence panel (Screen 2 + Screen 5 design)

- [ ] **Step 1: Write ResumePage (from Screen 2 + Screen 5 designs)**

Replace `frontend/src/pages/ResumePage.tsx`:
```typescript
import { useState } from "react";
import {
  FileText, Shield, CheckCircle2, AlertTriangle, Download, RefreshCw,
} from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { resumeService } from "@/services/resume";
import type { ResumeGenerateResponse } from "@/types/api";

const TEMPLATES = [
  { id: "software", label: "Software Engineer" },
  { id: "ai", label: "AI / ML" },
  { id: "product", label: "Product Manager" },
  { id: "consulting", label: "Consulting" },
  { id: "data_analytics", label: "Data Analytics" },
  { id: "healthcare", label: "Healthcare" },
];

export default function ResumePage() {
  const [jd, setJd] = useState("");
  const [template, setTemplate] = useState("software");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResumeGenerateResponse | null>(null);

  const generate = async () => {
    if (!jd.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await resumeService.generate({ job_description: jd, template_name: template });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const downloadDocx = async () => {
    if (!result) return;
    try {
      const blob = await resumeService.exportDocx(result.resume_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "resume.docx";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Export failed");
    }
  };

  return (
    <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">Resume Builder</h1>
          <p className="text-[#a1a1a1] text-sm mt-1">AI-generated from your verified evidence</p>
        </div>
        {result && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#30D158]/10 border border-[#30D158]/20">
            <Shield className="size-3.5 text-[#30D158]" />
            <span className="text-[#30D158] text-xs font-medium">Hallucination Prevention Active</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-[1fr_1fr] gap-6 flex-1">
        <div className="flex flex-col gap-4">
          <GlassCard className="p-5">
            <label className="block text-sm font-medium text-neutral-200 mb-3">Template</label>
            <div className="grid grid-cols-2 gap-2">
              {TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTemplate(t.id)}
                  className={`px-3 py-2 rounded-xl text-sm font-medium transition-colors text-left ${
                    template === t.id
                      ? "bg-[#4c8dff]/20 text-[#4c8dff] border border-[#4c8dff]/30"
                      : "bg-white/[0.04] text-[#a1a1a1] hover:text-neutral-200 hover:bg-white/[0.08] border border-transparent"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </GlassCard>

          <GlassCard className="p-5 flex-1 flex flex-col">
            <label className="block text-sm font-medium text-neutral-200 mb-3">
              Job Description
            </label>
            <textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste the full job description here…"
              className="flex-1 w-full bg-white/[0.03] border border-white/10 rounded-xl p-4 text-sm text-neutral-200 placeholder-neutral-600 resize-none focus:outline-none focus:border-[#4c8dff]/40 transition-colors min-h-[200px]"
            />
            {error && (
              <div className="mt-3 flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20">
                <AlertTriangle className="size-4 text-red-400 flex-shrink-0" />
                <span className="text-red-400 text-xs">{error}</span>
              </div>
            )}
            <button
              onClick={generate}
              disabled={loading || !jd.trim()}
              className="mt-4 w-full py-3 rounded-xl bg-[#4c8dff] text-white font-semibold text-sm transition-opacity disabled:opacity-40 hover:opacity-90 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <RefreshCw className="size-4 animate-spin" />
                  Generating…
                </>
              ) : (
                <>
                  <FileText className="size-4" />
                  Generate Resume
                </>
              )}
            </button>
          </GlassCard>
        </div>

        <div className="flex flex-col gap-4">
          {!result && !loading && (
            <GlassCard className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <FileText className="size-8 text-neutral-600 mx-auto mb-3" />
                <p className="text-[#a1a1a1] text-sm">Your generated resume will appear here</p>
              </div>
            </GlassCard>
          )}
          {loading && (
            <GlassCard className="flex-1 flex items-center justify-center">
              <LoadingSpinner size="lg" label="Generating your resume…" />
            </GlassCard>
          )}
          {result && (
            <>
              <GlassCard className="p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="size-4 text-[#30D158]" />
                    <span className="font-medium text-neutral-200 text-sm">Generated Resume</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {result.requires_approval && (
                      <span className="text-xs px-2 py-1 rounded-full bg-[#FF9F0A]/10 text-[#FF9F0A] border border-[#FF9F0A]/20">
                        {result.weak_inference_count} needs review
                      </span>
                    )}
                    <span className="text-xs px-2 py-1 rounded-full bg-[#4c8dff]/10 text-[#4c8dff] border border-[#4c8dff]/20">
                      ATS {result.ats_score.overall_score}
                    </span>
                    <button
                      onClick={downloadDocx}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.08] text-neutral-200 text-xs font-medium hover:bg-white/[0.12] transition-colors"
                    >
                      <Download className="size-3.5" />
                      .docx
                    </button>
                  </div>
                </div>
                <div className="flex flex-col gap-4 max-h-80 overflow-auto pr-2">
                  {result.content_json.experiences.map((exp, i) => (
                    <div key={i}>
                      <div className="flex items-baseline justify-between">
                        <p className="font-semibold text-neutral-100 text-sm">{exp.title} — {exp.company}</p>
                        <p className="text-[#a1a1a1] text-xs">{exp.dates}</p>
                      </div>
                      <ul className="mt-2 flex flex-col gap-1.5">
                        {exp.bullets.map((b, j) => (
                          <li key={j} className="flex items-start gap-2 text-sm text-neutral-300">
                            <span className="mt-1.5 size-1.5 rounded-full bg-[#4c8dff] flex-shrink-0" />
                            <span>{b.text}</span>
                            <ConfidenceBadge level={b.confidence} />
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </GlassCard>
              {result.content_json.skills.length > 0 && (
                <GlassCard className="p-4">
                  <p className="text-xs font-medium text-[#a1a1a1] mb-2">Skills</p>
                  <div className="flex flex-wrap gap-2">
                    {result.content_json.skills.map((s) => (
                      <span key={s} className="text-xs px-2.5 py-1 rounded-full bg-white/[0.06] text-neutral-300 border border-white/10">
                        {s}
                      </span>
                    ))}
                  </div>
                </GlassCard>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ResumePage.tsx
git commit -m "feat(ui): Resume Builder page — template picker, JD input, evidence panel, DOCX export"
```

---

### Task 6: Cover Letter Builder Page

**Files:**
- Modify: `frontend/src/pages/CoverLetterPage.tsx`

- [ ] **Step 1: Write CoverLetterPage**

Replace `frontend/src/pages/CoverLetterPage.tsx`:
```typescript
import { useState } from "react";
import { Mail, RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { coverLetterService } from "@/services/coverLetter";

interface Result {
  cover_letter_id: string;
  content_text: string;
  weak_inference_count: number;
  requires_approval: boolean;
}

export default function CoverLetterPage() {
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);

  const generate = async () => {
    if (!jd.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await coverLetterService.generate({ job_description: jd });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
      <div>
        <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">Cover Letter Builder</h1>
        <p className="text-[#a1a1a1] text-sm mt-1">Tailored to the job — grounded in your evidence</p>
      </div>

      <div className="grid grid-cols-[1fr_1fr] gap-6 flex-1">
        <GlassCard className="p-5 flex flex-col">
          <label className="block text-sm font-medium text-neutral-200 mb-3">Job Description</label>
          <textarea
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste the job description…"
            className="flex-1 w-full bg-white/[0.03] border border-white/10 rounded-xl p-4 text-sm text-neutral-200 placeholder-neutral-600 resize-none focus:outline-none focus:border-[#4c8dff]/40 transition-colors min-h-[280px]"
          />
          {error && (
            <div className="mt-3 flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20">
              <AlertTriangle className="size-4 text-red-400 flex-shrink-0" />
              <span className="text-red-400 text-xs">{error}</span>
            </div>
          )}
          <button
            onClick={generate}
            disabled={loading || !jd.trim()}
            className="mt-4 w-full py-3 rounded-xl bg-[#4c8dff] text-white font-semibold text-sm transition-opacity disabled:opacity-40 hover:opacity-90 flex items-center justify-center gap-2"
          >
            {loading ? <><RefreshCw className="size-4 animate-spin" /> Generating…</> : <><Mail className="size-4" /> Generate Cover Letter</>}
          </button>
        </GlassCard>

        <div className="flex flex-col gap-4">
          {!result && !loading && (
            <GlassCard className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Mail className="size-8 text-neutral-600 mx-auto mb-3" />
                <p className="text-[#a1a1a1] text-sm">Your cover letter will appear here</p>
              </div>
            </GlassCard>
          )}
          {loading && (
            <GlassCard className="flex-1 flex items-center justify-center">
              <LoadingSpinner size="lg" label="Writing your cover letter…" />
            </GlassCard>
          )}
          {result && (
            <GlassCard className="p-5 flex-1 overflow-auto">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="size-4 text-[#30D158]" />
                  <span className="font-medium text-neutral-200 text-sm">Cover Letter</span>
                </div>
                {result.requires_approval && (
                  <ConfidenceBadge level="weak_inference" />
                )}
              </div>
              <div className="text-sm text-neutral-300 leading-relaxed whitespace-pre-wrap">
                {result.content_text}
              </div>
            </GlassCard>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/CoverLetterPage.tsx frontend/src/services/coverLetter.ts
git commit -m "feat(ui): Cover Letter Builder page"
```

---

### Task 7: ATS Analysis Page

**Files:**
- Modify: `frontend/src/pages/AtsPage.tsx`

- [ ] **Step 1: Write AtsPage**

Replace `frontend/src/pages/AtsPage.tsx`:
```typescript
import { useState } from "react";
import { BarChart3, RefreshCw, AlertTriangle, Target } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { resumeService } from "@/services/resume";
import type { ResumeGenerateResponse } from "@/types/api";

export default function AtsPage() {
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResumeGenerateResponse | null>(null);

  const analyze = async () => {
    if (!jd.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await resumeService.generate({ job_description: jd, template_name: "software" });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const score = result?.ats_score;

  return (
    <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
      <div>
        <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">ATS Analysis</h1>
        <p className="text-[#a1a1a1] text-sm mt-1">Score your resume against any job description</p>
      </div>

      <GlassCard className="p-5">
        <label className="block text-sm font-medium text-neutral-200 mb-3">Job Description</label>
        <textarea
          value={jd}
          onChange={(e) => setJd(e.target.value)}
          placeholder="Paste the job description to analyze keyword match…"
          rows={5}
          className="w-full bg-white/[0.03] border border-white/10 rounded-xl p-4 text-sm text-neutral-200 placeholder-neutral-600 resize-none focus:outline-none focus:border-[#4c8dff]/40 transition-colors"
        />
        {error && (
          <div className="mt-3 flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20">
            <AlertTriangle className="size-4 text-red-400 flex-shrink-0" />
            <span className="text-red-400 text-xs">{error}</span>
          </div>
        )}
        <button
          onClick={analyze}
          disabled={loading || !jd.trim()}
          className="mt-4 w-full py-3 rounded-xl bg-[#4c8dff] text-white font-semibold text-sm disabled:opacity-40 hover:opacity-90 flex items-center justify-center gap-2 transition-opacity"
        >
          {loading ? <><RefreshCw className="size-4 animate-spin" /> Analyzing…</> : <><BarChart3 className="size-4" /> Analyze Match</>}
        </button>
      </GlassCard>

      {loading && (
        <GlassCard className="p-8 flex items-center justify-center">
          <LoadingSpinner size="lg" label="Analyzing keyword match…" />
        </GlassCard>
      )}

      {score && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Overall Score", value: score.overall_score, color: "#4c8dff" },
            { label: "Keyword Match", value: score.keyword_score, color: "#30D158" },
            { label: "Skills Match", value: score.skill_score, color: "#5AC8FA" },
          ].map(({ label, value, color }) => (
            <GlassCard key={label} className="p-5 text-center">
              <p className="text-[#a1a1a1] text-xs mb-2">{label}</p>
              <div className="relative size-20 mx-auto mb-2">
                <svg viewBox="0 0 36 36" className="size-20 -rotate-90">
                  <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="2.5" />
                  <circle
                    cx="18" cy="18" r="15.9"
                    fill="none"
                    stroke={color}
                    strokeWidth="2.5"
                    strokeDasharray={`${value} ${100 - value}`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="font-bold text-neutral-50 text-lg">{value}</span>
                </div>
              </div>
            </GlassCard>
          ))}
          <GlassCard className="col-span-3 p-5">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="text-xs font-medium text-[#30D158] mb-2 flex items-center gap-1">
                  <Target className="size-3.5" /> Matched Keywords
                </p>
                <div className="flex flex-wrap gap-2">
                  {score.matched_keywords.map((k) => (
                    <span key={k} className="text-xs px-2.5 py-1 rounded-full bg-[#30D158]/10 text-[#30D158] border border-[#30D158]/20">{k}</span>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs font-medium text-[#FF9F0A] mb-2 flex items-center gap-1">
                  <AlertTriangle className="size-3.5" /> Missing Keywords
                </p>
                <div className="flex flex-wrap gap-2">
                  {score.missing_keywords.map((k) => (
                    <span key={k} className="text-xs px-2.5 py-1 rounded-full bg-[#FF9F0A]/10 text-[#FF9F0A] border border-[#FF9F0A]/20">{k}</span>
                  ))}
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/AtsPage.tsx
git commit -m "feat(ui): ATS Analysis page — keyword match scores, matched/missing keywords"
```

---

### Task 8: Applications CRM Page

**Files:**
- Modify: `frontend/src/pages/ApplicationsPage.tsx`

**Interfaces:**
- Consumes: `applicationsService.list/create/update/delete`
- Produces: kanban-like list (Screen 3 design) with add modal, status filtering

- [ ] **Step 1: Write ApplicationsPage (from Screen 3 design)**

Replace `frontend/src/pages/ApplicationsPage.tsx`:
```typescript
import { useEffect, useState } from "react";
import { Plus, Briefcase, Search, Filter, CheckCircle2, Clock3, XCircle } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { applicationsService } from "@/services/applications";
import type { Application, ApplicationCreate } from "@/types/api";

const STATUS_OPTIONS = ["applied", "interviewing", "offer", "rejected", "saved"];

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  applied: { label: "Applied", color: "text-[#4c8dff]", bg: "bg-[#4c8dff]/10 border-[#4c8dff]/20" },
  interviewing: { label: "Interviewing", color: "text-[#FF9F0A]", bg: "bg-[#FF9F0A]/10 border-[#FF9F0A]/20" },
  offer: { label: "Offer", color: "text-[#30D158]", bg: "bg-[#30D158]/10 border-[#30D158]/20" },
  rejected: { label: "Rejected", color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
  saved: { label: "Saved", color: "text-[#a1a1a1]", bg: "bg-white/[0.06] border-white/10" },
};

function AddApplicationModal({
  onClose,
  onAdd,
}: {
  onClose: () => void;
  onAdd: (app: Application) => void;
}) {
  const [form, setForm] = useState<ApplicationCreate>({ company: "", role: "", status: "applied" });
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!form.company || !form.role) return;
    setLoading(true);
    try {
      const app = await applicationsService.create(form);
      onAdd(app);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-neutral-900 border border-white/10 rounded-2xl p-6 w-[420px] shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <h2 className="font-semibold text-neutral-50 text-lg mb-5">Add Application</h2>
        <div className="flex flex-col gap-4">
          {(["company", "role"] as const).map((field) => (
            <div key={field}>
              <label className="block text-xs font-medium text-[#a1a1a1] mb-1.5 capitalize">{field}</label>
              <input
                value={form[field] as string}
                onChange={(e) => setForm((f) => ({ ...f, [field]: e.target.value }))}
                placeholder={field === "company" ? "Acme Corp" : "Senior Engineer"}
                className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-neutral-200 placeholder-neutral-600 focus:outline-none focus:border-[#4c8dff]/40 transition-colors"
              />
            </div>
          ))}
          <div>
            <label className="block text-xs font-medium text-[#a1a1a1] mb-1.5">Status</label>
            <select
              value={form.status}
              onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
              className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-neutral-200 focus:outline-none focus:border-[#4c8dff]/40 transition-colors"
            >
              {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{STATUS_CONFIG[s]?.label ?? s}</option>)}
            </select>
          </div>
          <div className="flex gap-3 mt-2">
            <button onClick={onClose} className="flex-1 py-2.5 rounded-xl bg-white/[0.06] text-neutral-300 text-sm font-medium hover:bg-white/[0.1] transition-colors">Cancel</button>
            <button onClick={submit} disabled={loading || !form.company || !form.role} className="flex-1 py-2.5 rounded-xl bg-[#4c8dff] text-white text-sm font-semibold disabled:opacity-40 hover:opacity-90 transition-opacity">
              {loading ? "Adding…" : "Add Application"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [showAdd, setShowAdd] = useState(false);

  useEffect(() => {
    applicationsService.list().then(setApplications).finally(() => setLoading(false));
  }, []);

  const filtered = applications.filter((a) => {
    const matchSearch = !search || `${a.company} ${a.role}`.toLowerCase().includes(search.toLowerCase());
    const matchStatus = filterStatus === "all" || a.status === filterStatus;
    return matchSearch && matchStatus;
  });

  const statusCounts = STATUS_OPTIONS.reduce<Record<string, number>>((acc, s) => {
    acc[s] = applications.filter((a) => a.status === s).length;
    return acc;
  }, {});

  if (loading) {
    return <div className="flex items-center justify-center h-full"><LoadingSpinner size="lg" label="Loading applications…" /></div>;
  }

  return (
    <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
      {showAdd && (
        <AddApplicationModal
          onClose={() => setShowAdd(false)}
          onAdd={(app) => setApplications((prev) => [app, ...prev])}
        />
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">Applications</h1>
          <p className="text-[#a1a1a1] text-sm mt-1">Career CRM — {applications.length} tracked applications</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#4c8dff] text-white text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          <Plus className="size-4" />
          Add Application
        </button>
      </div>

      <div className="grid grid-cols-5 gap-3">
        {STATUS_OPTIONS.map((s) => {
          const cfg = STATUS_CONFIG[s];
          return (
            <GlassCard
              key={s}
              className={`p-4 cursor-pointer transition-all ${filterStatus === s ? "ring-1 ring-[#4c8dff]/40" : ""}`}
              onClick={() => setFilterStatus(filterStatus === s ? "all" : s)}
            >
              <p className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</p>
              <p className="font-bold text-neutral-50 text-2xl mt-1">{statusCounts[s] ?? 0}</p>
            </GlassCard>
          );
        })}
      </div>

      <div className="flex gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-neutral-600" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by company or role…"
            className="w-full bg-white/[0.04] border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm text-neutral-200 placeholder-neutral-600 focus:outline-none focus:border-[#4c8dff]/40 transition-colors"
          />
        </div>
        <button
          onClick={() => setFilterStatus("all")}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.06] text-[#a1a1a1] text-sm hover:bg-white/[0.1] transition-colors"
        >
          <Filter className="size-4" />
          {filterStatus === "all" ? "All" : STATUS_CONFIG[filterStatus]?.label}
        </button>
      </div>

      <div className="flex flex-col gap-2">
        {filtered.length === 0 ? (
          <GlassCard className="p-8 flex items-center justify-center">
            <div className="text-center">
              <Briefcase className="size-8 text-neutral-600 mx-auto mb-3" />
              <p className="text-[#a1a1a1] text-sm">No applications {filterStatus !== "all" ? `with status "${filterStatus}"` : "yet"}</p>
            </div>
          </GlassCard>
        ) : (
          filtered.map((app) => {
            const cfg = STATUS_CONFIG[app.status] ?? STATUS_CONFIG.saved;
            return (
              <GlassCard key={app.id} className="p-4 hover:bg-white/[0.03] transition-colors cursor-default">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="size-10 rounded-xl bg-white/[0.06] flex items-center justify-center flex-shrink-0">
                      <Briefcase className="size-4 text-[#a1a1a1]" />
                    </div>
                    <div>
                      <p className="font-semibold text-neutral-100 text-sm">{app.role}</p>
                      <p className="text-[#a1a1a1] text-xs">{app.company}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {app.date_applied && (
                      <span className="text-[#a1a1a1] text-xs flex items-center gap-1">
                        <Clock3 className="size-3" />
                        {new Date(app.date_applied).toLocaleDateString()}
                      </span>
                    )}
                    <span className={`text-xs px-2.5 py-1 rounded-full border ${cfg.bg} ${cfg.color}`}>
                      {cfg.label}
                    </span>
                  </div>
                </div>
              </GlassCard>
            );
          })
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/ApplicationsPage.tsx
git commit -m "feat(ui): Applications CRM page — list, add modal, status filter, search"
```

---

### Task 9: Interview Prep / Q&A Page

**Files:**
- Modify: `frontend/src/pages/InterviewPrepPage.tsx`

- [ ] **Step 1: Write InterviewPrepPage**

Replace `frontend/src/pages/InterviewPrepPage.tsx`:
```typescript
import { useState } from "react";
import { MessageSquareMore, RefreshCw, CheckCircle2, XCircle, SkipForward } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { learningService } from "@/services/learning";
import { applicationsService } from "@/services/applications";
import type { GeneratedQuestion, Application } from "@/types/api";
import { useEffect } from "react";

export default function InterviewPrepPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>("");
  const [questions, setQuestions] = useState<GeneratedQuestion[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [showAnswer, setShowAnswer] = useState(false);

  useEffect(() => {
    applicationsService.list().then(setApplications).catch(console.error);
  }, []);

  const generateQuestions = async () => {
    if (!selectedAppId) return;
    setGenerating(true);
    try {
      const res = await learningService.generateQuestions(selectedAppId);
      setQuestions(res.questions ?? []);
      setCurrentIdx(0);
      setShowAnswer(false);
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(false);
    }
  };

  const recordOutcome = async (outcome: "correct" | "incorrect" | "skipped") => {
    const q = questions[currentIdx];
    if (!q) return;
    setLoading(true);
    try {
      await learningService.recordOutcome({
        question_id: q.id,
        application_id: q.application_id,
        outcome,
      });
    } catch {
      // best-effort
    } finally {
      setLoading(false);
    }
    setShowAnswer(false);
    setCurrentIdx((i) => i + 1);
  };

  const current = questions[currentIdx];
  const done = currentIdx >= questions.length && questions.length > 0;

  return (
    <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
      <div>
        <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">Interview Prep</h1>
        <p className="text-[#a1a1a1] text-sm mt-1">Practice questions generated from your applications</p>
      </div>

      <GlassCard className="p-5">
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-xs font-medium text-[#a1a1a1] mb-1.5">Application</label>
            <select
              value={selectedAppId}
              onChange={(e) => setSelectedAppId(e.target.value)}
              className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-neutral-200 focus:outline-none focus:border-[#4c8dff]/40 transition-colors"
            >
              <option value="">Select application…</option>
              {applications.map((a) => (
                <option key={a.id} value={a.id}>{a.role} at {a.company}</option>
              ))}
            </select>
          </div>
          <button
            onClick={generateQuestions}
            disabled={generating || !selectedAppId}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#4c8dff] text-white text-sm font-semibold disabled:opacity-40 hover:opacity-90 transition-opacity"
          >
            {generating ? <><RefreshCw className="size-4 animate-spin" /> Generating…</> : <><MessageSquareMore className="size-4" /> Generate Questions</>}
          </button>
        </div>
      </GlassCard>

      {questions.length === 0 && !generating && (
        <GlassCard className="flex-1">
          <EmptyState
            icon={MessageSquareMore}
            title="No questions yet"
            description="Select an application and generate questions to start practicing."
          />
        </GlassCard>
      )}

      {generating && (
        <GlassCard className="flex-1 flex items-center justify-center">
          <LoadingSpinner size="lg" label="Generating interview questions…" />
        </GlassCard>
      )}

      {done && (
        <GlassCard className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <CheckCircle2 className="size-12 text-[#30D158] mx-auto mb-4" />
            <p className="font-semibold text-neutral-50 text-lg">Session Complete!</p>
            <p className="text-[#a1a1a1] text-sm mt-1">You've answered all {questions.length} questions.</p>
            <button onClick={() => { setCurrentIdx(0); setShowAnswer(false); }} className="mt-4 px-4 py-2 rounded-xl bg-[#4c8dff] text-white text-sm font-medium hover:opacity-90 transition-opacity">
              Restart
            </button>
          </div>
        </GlassCard>
      )}

      {current && !done && (
        <div className="flex flex-col gap-4 flex-1">
          <div className="flex items-center justify-between">
            <span className="text-[#a1a1a1] text-sm">{currentIdx + 1} / {questions.length}</span>
            <div className="flex items-center gap-2">
              <span className="text-xs px-2.5 py-1 rounded-full bg-white/[0.06] text-[#a1a1a1] border border-white/10">{current.difficulty}</span>
              <span className="text-xs px-2.5 py-1 rounded-full bg-white/[0.06] text-[#a1a1a1] border border-white/10">{current.question_type}</span>
            </div>
          </div>

          <GlassCard className="p-6 flex-1">
            <p className="font-semibold text-neutral-50 text-lg leading-relaxed">{current.question_text}</p>
            {showAnswer && (
              <div className="mt-6 p-4 rounded-xl bg-[#4c8dff]/[0.08] border border-[#4c8dff]/20">
                <p className="text-xs font-medium text-[#4c8dff] mb-2">Suggested structure</p>
                <p className="text-neutral-300 text-sm">Use the STAR method: Situation → Task → Action → Result. Focus on specific metrics and outcomes from your experience.</p>
              </div>
            )}
            {!showAnswer && (
              <button onClick={() => setShowAnswer(true)} className="mt-6 px-4 py-2 rounded-xl bg-white/[0.08] text-neutral-300 text-sm hover:bg-white/[0.12] transition-colors">
                Show guidance
              </button>
            )}
          </GlassCard>

          <div className="flex gap-3">
            <button onClick={() => recordOutcome("incorrect")} disabled={loading} className="flex-1 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm font-medium hover:bg-red-500/20 transition-colors flex items-center justify-center gap-2">
              <XCircle className="size-4" /> Missed
            </button>
            <button onClick={() => recordOutcome("skipped")} disabled={loading} className="px-5 py-3 rounded-xl bg-white/[0.06] border border-white/10 text-[#a1a1a1] text-sm font-medium hover:bg-white/[0.1] transition-colors flex items-center gap-2">
              <SkipForward className="size-4" /> Skip
            </button>
            <button onClick={() => recordOutcome("correct")} disabled={loading} className="flex-1 py-3 rounded-xl bg-[#30D158]/10 border border-[#30D158]/20 text-[#30D158] text-sm font-medium hover:bg-[#30D158]/20 transition-colors flex items-center justify-center gap-2">
              <CheckCircle2 className="size-4" /> Got it
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/InterviewPrepPage.tsx
git commit -m "feat(ui): Interview Prep page — question flashcards, outcome recording"
```

---

### Task 10: Copilot Chat Page

**Files:**
- Modify: `frontend/src/pages/CopilotPage.tsx`

**Interfaces:**
- Consumes: `copilotService.chat`, `ConfidenceBadge`
- Produces: multi-turn chat UI with citations panel (Screen 4 design)

- [ ] **Step 1: Write CopilotPage (from Screen 4 design)**

Replace `frontend/src/pages/CopilotPage.tsx`:
```typescript
import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, BookOpen } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { copilotService } from "@/services/copilot";
import type { CopilotChatResponse } from "@/types/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  meta?: CopilotChatResponse;
}

export default function CopilotPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    try {
      const history = messages.slice(-4).map((m) => ({ role: m.role, content: m.content }));
      const res = await copilotService.chat({ message: text, conversation_history: history });
      setMessages((prev) => [...prev, { role: "assistant", content: res.response, meta: res }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I encountered an error. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && m.meta);

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex-1 flex flex-col p-8 gap-4">
        <div>
          <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight flex items-center gap-3">
            <div className="size-9 rounded-xl bg-[#4c8dff]/20 flex items-center justify-center">
              <Bot className="size-5 text-[#4c8dff]" />
            </div>
            Career Copilot
          </h1>
          <p className="text-[#a1a1a1] text-sm mt-1 ml-12">AI assistant grounded in your verified career evidence</p>
        </div>

        <GlassCard className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-auto p-5 flex flex-col gap-4">
            {messages.length === 0 && (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center max-w-sm">
                  <div className="size-14 rounded-2xl bg-[#4c8dff]/10 flex items-center justify-center mx-auto mb-4">
                    <Bot className="size-7 text-[#4c8dff]" />
                  </div>
                  <p className="font-semibold text-neutral-200 text-base">How can I help with your career?</p>
                  <p className="text-[#a1a1a1] text-sm mt-2">Ask me about your experience, interview prep, job matching, or anything career-related.</p>
                  <div className="mt-4 flex flex-col gap-2">
                    {[
                      "What are my strongest skills?",
                      "Help me prepare for a PM interview",
                      "What roles should I target?",
                    ].map((suggestion) => (
                      <button
                        key={suggestion}
                        onClick={() => { setInput(suggestion); }}
                        className="text-sm px-4 py-2 rounded-xl bg-white/[0.04] border border-white/10 text-[#a1a1a1] hover:text-neutral-200 hover:bg-white/[0.08] transition-colors text-left"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
                <div className={`size-8 rounded-xl flex-shrink-0 flex items-center justify-center ${
                  msg.role === "user" ? "bg-[#4c8dff]/20" : "bg-neutral-200/[0.08]"
                }`}>
                  {msg.role === "user" ? <User className="size-4 text-[#4c8dff]" /> : <Bot className="size-4 text-neutral-400" />}
                </div>
                <div className={`max-w-[75%] ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col gap-1`}>
                  <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-[#4c8dff]/20 text-neutral-100 rounded-tr-sm"
                      : "bg-white/[0.06] text-neutral-200 rounded-tl-sm"
                  }`}>
                    {msg.content}
                  </div>
                  {msg.meta && (
                    <div className="flex items-center gap-2 px-1">
                      <ConfidenceBadge level={msg.meta.confidence} />
                      <span className="text-[#a1a1a1] text-[11px]">{msg.meta.intent}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="size-8 rounded-xl bg-neutral-200/[0.08] flex items-center justify-center">
                  <Bot className="size-4 text-neutral-400" />
                </div>
                <div className="px-4 py-3 rounded-2xl bg-white/[0.06] rounded-tl-sm">
                  <LoadingSpinner size="sm" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="p-4 border-t border-white/10">
            <div className="flex gap-3">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
                placeholder="Ask about your career…"
                disabled={loading}
                className="flex-1 bg-white/[0.04] border border-white/10 rounded-xl px-4 py-2.5 text-sm text-neutral-200 placeholder-neutral-600 focus:outline-none focus:border-[#4c8dff]/40 transition-colors disabled:opacity-60"
              />
              <button
                onClick={send}
                disabled={loading || !input.trim()}
                className="size-10 rounded-xl bg-[#4c8dff] flex items-center justify-center disabled:opacity-40 hover:opacity-90 transition-opacity flex-shrink-0"
              >
                <Send className="size-4 text-white" />
              </button>
            </div>
          </div>
        </GlassCard>
      </div>

      {lastAssistant?.meta?.citations && lastAssistant.meta.citations.length > 0 && (
        <div className="w-72 p-8 pl-0 flex-shrink-0">
          <GlassCard className="p-4 h-full overflow-auto">
            <p className="text-xs font-medium text-[#a1a1a1] mb-3 flex items-center gap-2">
              <BookOpen className="size-3.5" /> Evidence Citations
            </p>
            <div className="flex flex-col gap-3">
              {lastAssistant.meta.citations.map((c, i) => (
                <div key={i} className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-medium text-neutral-300 truncate">{c.source}</span>
                    <ConfidenceBadge level={c.confidence} />
                  </div>
                  <p className="text-[#a1a1a1] text-xs leading-relaxed">{c.text}</p>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/CopilotPage.tsx
git commit -m "feat(ui): Copilot Chat page — multi-turn chat, citations panel, intent labels"
```

---

### Task 11: Learning Engine Page

**Files:**
- Modify: `frontend/src/pages/LearningPage.tsx`

**Interfaces:**
- Consumes: `learningService.getRecommendations`, recharts `AreaChart`; Screen 6 design

- [ ] **Step 1: Install recharts types if missing**

```bash
cd frontend && npm install @types/recharts 2>/dev/null; true
```

Note: recharts ships its own types in v2+, no @types needed. Skip if erroring.

- [ ] **Step 2: Write LearningPage (from Screen 6 design)**

Replace `frontend/src/pages/LearningPage.tsx`:
```typescript
import { useEffect, useState } from "react";
import { Sparkles, TrendingUp, Brain, Zap, Star } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { learningService } from "@/services/learning";
import type { GeneratedQuestion } from "@/types/api";

const MOCK_CHART_DATA = [
  { week: "W1", score: 42 },
  { week: "W2", score: 58 },
  { week: "W3", score: 65 },
  { week: "W4", score: 71 },
  { week: "W5", score: 79 },
  { week: "W6", score: 85 },
];

const DIFFICULTY_CONFIG: Record<string, { color: string; bg: string }> = {
  easy: { color: "text-[#30D158]", bg: "bg-[#30D158]/10 border-[#30D158]/20" },
  medium: { color: "text-[#FF9F0A]", bg: "bg-[#FF9F0A]/10 border-[#FF9F0A]/20" },
  hard: { color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
};

export default function LearningPage() {
  const [recommendations, setRecommendations] = useState<GeneratedQuestion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    learningService.getRecommendations()
      .then((res) => setRecommendations(res.recommendations ?? []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
      <div>
        <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight flex items-center gap-3">
          <div className="size-9 rounded-xl bg-[linear-gradient(135deg,#4c8dff,#7e5fff)] flex items-center justify-center shadow-[0_10px_24px_rgba(76,141,255,0.28)]">
            <Brain className="size-5 text-white" />
          </div>
          Learning Engine
        </h1>
        <p className="text-[#a1a1a1] text-sm mt-1 ml-12">Adaptive practice powered by your outcome history</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Questions Answered", value: "—", icon: Zap, color: "text-[#4c8dff]" },
          { label: "Avg Performance", value: "—", icon: TrendingUp, color: "text-[#30D158]" },
          { label: "Current Streak", value: "—", icon: Star, color: "text-[#FF9F0A]" },
        ].map(({ label, value, icon: Icon, color }) => (
          <GlassCard key={label} className="p-5 flex items-center gap-4">
            <div className="size-10 rounded-xl bg-white/[0.06] flex items-center justify-center flex-shrink-0">
              <Icon className={`size-5 ${color}`} />
            </div>
            <div>
              <p className="text-[#a1a1a1] text-xs">{label}</p>
              <p className={`font-bold text-2xl tracking-tight ${color}`}>{value}</p>
            </div>
          </GlassCard>
        ))}
      </div>

      <GlassCard className="p-5">
        <p className="font-medium text-neutral-200 text-sm mb-4 flex items-center gap-2">
          <TrendingUp className="size-4 text-[#4c8dff]" />
          Performance Trend
        </p>
        <ResponsiveContainer width="100%" height={140}>
          <AreaChart data={MOCK_CHART_DATA}>
            <defs>
              <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4c8dff" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#4c8dff" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="week" tick={{ fill: "#a1a1a1", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#a1a1a1", fontSize: 11 }} axisLine={false} tickLine={false} domain={[0, 100]} />
            <Tooltip
              contentStyle={{ background: "#1a1a1a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, color: "#fafafa" }}
              cursor={{ stroke: "rgba(76,141,255,0.3)" }}
            />
            <Area type="monotone" dataKey="score" stroke="#4c8dff" strokeWidth={2} fill="url(#areaGrad)" dot={{ fill: "#4c8dff", strokeWidth: 0, r: 3 }} />
          </AreaChart>
        </ResponsiveContainer>
      </GlassCard>

      <GlassCard className="p-5 flex-1">
        <p className="font-medium text-neutral-200 text-sm mb-4 flex items-center gap-2">
          <Sparkles className="size-4 text-[#4c8dff]" />
          Recommended Practice
        </p>
        {loading && <LoadingSpinner size="md" label="Loading recommendations…" />}
        {!loading && recommendations.length === 0 && (
          <EmptyState
            icon={Brain}
            title="No recommendations yet"
            description="Complete some interview practice sessions to unlock personalized recommendations."
          />
        )}
        {!loading && recommendations.length > 0 && (
          <div className="flex flex-col gap-2">
            {recommendations.map((q) => {
              const cfg = DIFFICULTY_CONFIG[q.difficulty] ?? DIFFICULTY_CONFIG.medium;
              return (
                <div key={q.id} className="flex items-start justify-between p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-colors">
                  <p className="text-neutral-200 text-sm leading-relaxed flex-1 mr-3">{q.question_text}</p>
                  <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                    <span className={`text-[11px] px-2 py-0.5 rounded-full border ${cfg.bg} ${cfg.color}`}>{q.difficulty}</span>
                    <span className="text-[#a1a1a1] text-[11px]">{q.question_type}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </GlassCard>
    </div>
  );
}
```

- [ ] **Step 3: Create Settings stub**

Create `frontend/src/pages/SettingsPage.tsx`:
```typescript
import { Settings } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";

export default function SettingsPage() {
  return (
    <div className="p-8 flex flex-col gap-6 h-full">
      <div>
        <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">Settings</h1>
        <p className="text-[#a1a1a1] text-sm mt-1">Application configuration</p>
      </div>
      <GlassCard className="p-8 flex items-center justify-center flex-1">
        <div className="text-center">
          <Settings className="size-8 text-neutral-600 mx-auto mb-3" />
          <p className="text-[#a1a1a1] text-sm">Settings coming soon</p>
        </div>
      </GlassCard>
    </div>
  );
}
```

- [ ] **Step 4: Remove stub pages directory leftovers and verify full build**

```bash
cd frontend && npm run build 2>&1 | tail -20
```

Expected: exits 0, no TypeScript errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/LearningPage.tsx frontend/src/pages/SettingsPage.tsx
git commit -m "feat(ui): Learning Engine page — performance chart, recommendations; Settings stub"
```

---

### Task 12: Backend Observability + Structured Error Responses

**Files:**
- Create: `backend/middleware/timing.py`
- Create: `backend/middleware/__init__.py`
- Modify: `backend/main.py` (add middleware)

**Interfaces:**
- `TimingMiddleware`: adds `X-Response-Time` header (ms) to every response
- Structured errors: existing FastAPI HTTPException handler already returns JSON; add global handler for unhandled `Exception` → `{"detail": "Internal server error", "type": "internal_error"}`

- [ ] **Step 1: Create middleware package**

Create `backend/middleware/__init__.py` (empty).

- [ ] **Step 2: Create timing middleware**

Create `backend/middleware/timing.py`:
```python
from __future__ import annotations

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
        return response
```

- [ ] **Step 3: Register middleware and global error handler in main.py**

In `backend/main.py`, after the existing imports, add:
```python
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from backend.middleware.timing import TimingMiddleware
```

After `app = FastAPI(...)` line, add:
```python
app.add_middleware(TimingMiddleware)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).error("Unhandled error on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": "internal_error"},
    )
```

- [ ] **Step 4: Verify backend still starts**

```bash
source .venv/bin/activate && python -c "from backend.main import app; print('OK')"
```

Expected: `OK`.

- [ ] **Step 5: Run full test suite**

```bash
source .venv/bin/activate && pytest backend/tests/ -q --tb=short 2>&1 | tail -5
```

Expected: ≥90% coverage, all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/middleware/ backend/main.py
git commit -m "feat(observability): timing middleware, global error handler"
```

---

## Final Validation

After all 12 tasks:

- [ ] `cd frontend && npm run build` — exits 0
- [ ] `npx tsc --noEmit` (in frontend/) — 0 TypeScript errors
- [ ] `source .venv/bin/activate && pytest backend/tests/ -q` — ≥90% coverage
- [ ] Start dev server: `npm run tauri dev` (or `npm run dev` in frontend/) and manually verify all 8 nav items load without errors
- [ ] Confirm Dashboard shows health pill and applications list
- [ ] Confirm Copilot chat sends messages and receives responses
- [ ] Confirm Resume page generates a resume when JD is pasted
