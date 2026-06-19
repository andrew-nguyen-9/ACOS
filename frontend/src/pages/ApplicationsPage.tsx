import { useEffect, useState } from "react";
import { Plus, Briefcase, Search, Filter, Clock3, AlertTriangle } from "lucide-react";
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
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!form.company || !form.role) return;
    setLoading(true);
    setError(null);
    try {
      const app = await applicationsService.create(form);
      onAdd(app);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add application");
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
          {error && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20">
              <AlertTriangle className="size-4 text-red-400 flex-shrink-0" />
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
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
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [showAdd, setShowAdd] = useState(false);

  useEffect(() => {
    applicationsService
      .list()
      .then(setApplications)
      .catch((e) => setFetchError(e instanceof Error ? e.message : "Failed to load applications"))
      .finally(() => setLoading(false));
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

      {fetchError && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20">
          <AlertTriangle className="size-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400">{fetchError}</p>
        </div>
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
