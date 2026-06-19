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
