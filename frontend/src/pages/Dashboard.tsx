import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { m } from "framer-motion";
import {
  FileText, Briefcase, Target, MessageSquareMore,
  Plus, Sparkles, Bot, CheckCircle2, WifiOff, Zap,
} from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { fadeUp, scaleIn, staggerContainer } from "@/motion";
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
    let settled = 0;
    const done = () => { settled += 1; if (settled === 2) setLoading(false); };

    apiFetch<Health>("/health")
      .then(setHealth)
      .catch(console.error)
      .finally(done);

    applicationsService.list()
      .then(setApplications)
      .catch(console.error)
      .finally(done);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <LoadingSpinner size="lg" label="Loading dashboard…" />
      </div>
    );
  }

  const stats = [
    { label: "Applications", value: applications.length, icon: Briefcase, color: "text-accent" },
    { label: "Resumes Generated", value: "—", icon: FileText, color: "text-verified" },
    { label: "Avg ATS Score", value: "—", icon: Target, color: "text-strong" },
    { label: "Interview Questions", value: "—", icon: MessageSquareMore, color: "text-weak" },
  ];

  const quickActions = [
    { label: "Generate Resume", icon: FileText, to: "/resumes" },
    { label: "New Application", icon: Plus, to: "/applications" },
    { label: "Ask Copilot", icon: Bot, to: "/copilot" },
    { label: "Practice Interview", icon: Sparkles, to: "/interview-prep" },
  ];

  return (
    <m.div
      className="flex h-full flex-col gap-6 overflow-auto p-8"
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
    >
      <m.div className="flex items-center justify-between" variants={fadeUp}>
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-neutral-50">Dashboard</h1>
          <p className="mt-1 text-sm text-[var(--fg-muted)]">AI Career Operating System</p>
        </div>
        {health && (
          <div className="flex items-center gap-2 rounded-full border border-verified/20 bg-verified/10 px-3 py-1.5">
            <CheckCircle2 className="size-3.5 text-verified" />
            <span className="text-xs font-medium text-verified">v{health.version} · online</span>
          </div>
        )}
        {!health && (
          <div className="flex items-center gap-2 rounded-full border border-red-500/20 bg-red-500/10 px-3 py-1.5">
            <WifiOff className="size-3.5 text-red-400" />
            <span className="text-xs font-medium text-red-400">Backend unreachable</span>
          </div>
        )}
      </m.div>

      <m.div className="grid grid-cols-4 gap-4" variants={staggerContainer}>
        {stats.map(({ label, value, icon: Icon, color }) => (
          <m.div key={label} variants={scaleIn}>
            <GlassCard className="p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-[var(--fg-muted)]">{label}</p>
                  <p className={`mt-2 text-3xl font-bold tabular-nums tracking-tight ${color}`}>{value}</p>
                </div>
                <div className="flex size-8 items-center justify-center rounded-xl bg-white/[0.06]">
                  <Icon className={`size-4 ${color}`} />
                </div>
              </div>
            </GlassCard>
          </m.div>
        ))}
      </m.div>

      <m.div className="grid flex-1 grid-cols-[1fr_280px] gap-6" variants={fadeUp}>
        <GlassCard className="p-6">
          <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-neutral-200">
            <Briefcase className="size-4 text-accent" />
            Recent Applications
          </h2>
          {applications.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
              <Briefcase className="size-8 text-neutral-600" />
              <p className="text-sm text-[var(--fg-muted)]">No applications yet</p>
              <button
                onClick={() => navigate("/applications")}
                className="text-xs text-accent hover:underline"
              >
                Track your first application →
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {applications.slice(0, 6).map((app) => (
                <div
                  key={app.id}
                  className="flex cursor-pointer items-center justify-between rounded-xl bg-white/[0.03] px-4 py-3 transition-colors duration-fast hover:bg-white/[0.06]"
                  onClick={() => navigate("/applications")}
                >
                  <div>
                    <p className="text-sm font-medium text-neutral-200">{app.role}</p>
                    <p className="text-xs text-[var(--fg-muted)]">{app.company}</p>
                  </div>
                  <span className="rounded-full border border-accent/20 bg-accent/10 px-2.5 py-1 text-xs text-accent">
                    {app.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </GlassCard>

        <div className="flex flex-col gap-4">
          <GlassCard className="p-5">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-neutral-200">
              <Zap className="size-4 text-accent" />
              Quick Actions
            </h2>
            <div className="flex flex-col gap-2">
              {quickActions.map(({ label, icon: Icon, to }) => (
                <button
                  key={label}
                  onClick={() => navigate(to)}
                  className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium text-[var(--fg-muted)] transition-colors duration-fast hover:bg-white/[0.06] hover:text-neutral-200"
                >
                  <Icon className="size-4 text-accent" />
                  {label}
                </button>
              ))}
            </div>
          </GlassCard>

          <GlassCard className="p-5">
            <h2 className="mb-3 text-sm font-semibold text-neutral-200">System</h2>
            <div className="flex flex-col gap-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[var(--fg-muted)]">Backend</span>
                <span className={health ? "text-verified" : "text-red-400"}>
                  {health ? "online" : "offline"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[var(--fg-muted)]">Database</span>
                <span className={health?.db === "ok" ? "text-verified" : "text-weak"}>
                  {health?.db ?? "—"}
                </span>
              </div>
            </div>
          </GlassCard>
        </div>
      </m.div>
    </m.div>
  );
}
