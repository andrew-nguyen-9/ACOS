import {
  LayoutDashboard, FileText, Mail, BarChart3, MessageSquareMore,
  Briefcase, Sparkles, Wand2, Bot, Settings, type LucideIcon,
} from "lucide-react";
import { lazyOnIntent, type LazyOnIntent } from "@/components/ui/lazyOnIntent";

/**
 * Single source of truth for the app's pages (Phase 11.5).
 *
 * Both the router (App.tsx) and the sidebar (AppShell.tsx) read this, so the two
 * can't drift. Each page is `lazyOnIntent`, so the sidebar can warm a route's
 * chunk on hover (PERF-IL-001) and the router renders the same lazy component.
 */
export interface RouteDef extends LazyOnIntent<Record<string, never>> {
  path: string;
  label: string;
  icon: LucideIcon;
  /** NavLink `end` matching — only Dashboard needs exact-match on "/". */
  end?: boolean;
}

export const ROUTES: RouteDef[] = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard, end: true, ...lazyOnIntent(() => import("@/pages/Dashboard")) },
  { path: "/resumes", label: "Resumes", icon: FileText, ...lazyOnIntent(() => import("@/pages/ResumePage")) },
  { path: "/cover-letters", label: "Cover Letters", icon: Mail, ...lazyOnIntent(() => import("@/pages/CoverLetterPage")) },
  { path: "/ats", label: "ATS Analysis", icon: BarChart3, ...lazyOnIntent(() => import("@/pages/AtsPage")) },
  { path: "/interview-prep", label: "Interview Prep", icon: MessageSquareMore, ...lazyOnIntent(() => import("@/pages/InterviewPrepPage")) },
  { path: "/applications", label: "Applications CRM", icon: Briefcase, ...lazyOnIntent(() => import("@/pages/ApplicationsPage")) },
  { path: "/learning", label: "Learning Engine", icon: Sparkles, ...lazyOnIntent(() => import("@/pages/LearningPage")) },
  { path: "/optimization", label: "Optimization", icon: Wand2, ...lazyOnIntent(() => import("@/pages/OptimizationPage")) },
  { path: "/copilot", label: "Copilot", icon: Bot, ...lazyOnIntent(() => import("@/pages/CopilotPage")) },
  { path: "/settings", label: "Settings", icon: Settings, ...lazyOnIntent(() => import("@/pages/SettingsPage")) },
];
