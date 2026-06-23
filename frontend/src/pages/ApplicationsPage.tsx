import { useEffect, useRef, useState, useTransition, type Dispatch, type SetStateAction } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, m } from "framer-motion";
import { Plus, Briefcase, Search, Filter, Clock3, AlertTriangle, ListChecks, X } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { JobPrioritization } from "@/components/strategy/JobPrioritization";
import { ApplicationSuggestion } from "@/components/strategy/ApplicationSuggestion";
import { PageSkeleton } from "@/components/ui/Skeleton";
import { VirtualList } from "@/components/ui/VirtualList";
import { useDeferredLoading } from "@/hooks/useDeferredLoading";
import { useScrollKinematics } from "@/hooks/useScrollKinematics";
import { useVelocityDismiss } from "@/hooks/useVelocityDismiss";
import { springs } from "@/motion";
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
  // KMP-001: drag the sheet down; a fast fling carries its release velocity into
  // the exit spring. Slow short drags snap back via dragConstraints elastic.
  const { dragProps, exitTransition } = useVelocityDismiss(onClose);

  // Escape closes (keyboard parity with the drag/backdrop dismissals).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

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
    <m.div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={onClose}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <m.div
        className="bg-neutral-900 border border-white/10 rounded-2xl p-6 w-[420px] shadow-2xl cursor-grab active:cursor-grabbing"
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1, transition: springs.snappy }}
        exit={{ opacity: 0, y: 320 }}
        transition={exitTransition()}
        {...dragProps}
      >
        {/* Grab handle — affords the drag-to-dismiss. */}
        <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-white/15" />
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
      </m.div>
    </m.div>
  );
}

function ApplicationRow({ app, onOpen }: { app: Application; onOpen: (app: Application) => void }) {
  const cfg = STATUS_CONFIG[app.status] ?? STATUS_CONFIG.saved;
  return (
    <GlassCard
      onClick={() => onOpen(app)}
      className="mb-2 p-4 hover:bg-white/[0.03] transition-colors cursor-pointer"
    >
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
}

function ApplicationDetailSheet({
  app,
  onClose,
  onApplied,
  onTailor,
}: {
  app: Application;
  onClose: () => void;
  onApplied: (updated: Application) => void;
  onTailor: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <m.div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={onClose}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <m.div
        className="bg-neutral-900 border border-white/10 rounded-2xl p-6 w-[480px] max-h-[85vh] overflow-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1, transition: springs.snappy }}
        exit={{ opacity: 0, y: 24, scale: 0.97 }}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="font-semibold text-neutral-50 text-lg">{app.role}</h2>
            <p className="text-[#a1a1a1] text-xs">{app.company}</p>
          </div>
          <button onClick={onClose} className="text-neutral-500 hover:text-neutral-300 transition-colors">
            <X className="size-5" />
          </button>
        </div>
        <ApplicationSuggestion app={app} onApplied={onApplied} onTailor={onTailor} />
      </m.div>
    </m.div>
  );
}

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const showSkeleton = useDeferredLoading(loading, 200);

  useEffect(() => {
    applicationsService
      .list()
      .then(setApplications)
      .catch((e) => setFetchError(e instanceof Error ? e.message : "Failed to load applications"))
      .finally(() => setLoading(false));
  }, []);

  // Mount the kinematic view only once data is ready: its scroll container must
  // exist in the same commit `useScrollKinematics` binds to, otherwise framer's
  // `useScroll` attaches to a null ref and the header/progress silently no-op.
  if (loading) return showSkeleton ? <PageSkeleton /> : null;

  return (
    <ApplicationsView
      applications={applications}
      setApplications={setApplications}
      fetchError={fetchError}
    />
  );
}

function ApplicationsView({
  applications,
  setApplications,
  fetchError,
}: {
  applications: Application[];
  setApplications: Dispatch<SetStateAction<Application[]>>;
  fetchError: string | null;
}) {
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [showAdd, setShowAdd] = useState(false);
  const [showPrioritize, setShowPrioritize] = useState(false);
  const [selected, setSelected] = useState<Application | null>(null);
  const navigate = useNavigate();
  // Saved JDs already tracked on applications — feed the prioritization surface.
  const savedJds = applications
    .map((a) => a.job_description)
    .filter((jd): jd is string => Boolean(jd && jd.trim()));
  // ASP-003: filtering a large list is the heavy update — keep typing/clicks
  // responsive by marking the derived-list recompute as a transition.
  const [, startTransition] = useTransition();
  const [query, setQuery] = useState({ search: "", status: "all" });

  const scrollRef = useRef<HTMLDivElement>(null);
  const { headerStyle, progressScaleX } = useScrollKinematics(scrollRef);

  const onSearch = (v: string) => {
    setSearch(v); // controlled input updates synchronously (responsive)
    startTransition(() => setQuery((q) => ({ ...q, search: v })));
  };
  const onFilter = (status: string) => {
    setFilterStatus(status);
    startTransition(() => setQuery((q) => ({ ...q, status })));
  };

  const filtered = applications.filter((a) => {
    const matchSearch = !query.search || `${a.company} ${a.role}`.toLowerCase().includes(query.search.toLowerCase());
    const matchStatus = query.status === "all" || a.status === query.status;
    return matchSearch && matchStatus;
  });

  const statusCounts = STATUS_OPTIONS.reduce<Record<string, number>>((acc, s) => {
    acc[s] = applications.filter((a) => a.status === s).length;
    return acc;
  }, {});

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <AnimatePresence>
        {showAdd && (
          <AddApplicationModal
            onClose={() => setShowAdd(false)}
            onAdd={(app) => setApplications((prev) => [app, ...prev])}
          />
        )}
        {selected && (
          <ApplicationDetailSheet
            app={selected}
            onClose={() => setSelected(null)}
            onApplied={(updated) => {
              setApplications((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
              setSelected(updated);
            }}
            onTailor={() => navigate("/resumes")}
          />
        )}
      </AnimatePresence>

      {/* Scroll progress (KMP-002) — scaleX only, compositor-driven. */}
      <m.div
        className="h-0.5 origin-left bg-accent/70"
        style={{ scaleX: progressScaleX, transformOrigin: "left" }}
        aria-hidden
      />

      <div className="flex flex-col gap-6 p-8 pb-0 flex-shrink-0">
        {fetchError && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20">
            <AlertTriangle className="size-4 text-red-400 flex-shrink-0" />
            <p className="text-sm text-red-400">{fetchError}</p>
          </div>
        )}

        {/* Collapsing header (KMP-002) — opacity + y, bound to list scroll. */}
        <m.div style={headerStyle} className="flex items-center justify-between">
          <div>
            <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight">Applications</h1>
            <p className="text-[#a1a1a1] text-sm mt-1">Career CRM — {applications.length} tracked applications</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowPrioritize((v) => !v)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors ${showPrioritize ? "bg-[#4c8dff]/15 text-[#4c8dff]" : "bg-white/[0.06] text-[#a1a1a1] hover:bg-white/[0.1]"}`}
            >
              <ListChecks className="size-4" />
              Prioritize jobs
            </button>
            <button
              onClick={() => setShowAdd(true)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#4c8dff] text-white text-sm font-semibold hover:opacity-90 transition-opacity"
            >
              <Plus className="size-4" />
              Add Application
            </button>
          </div>
        </m.div>

        {showPrioritize && (
          <GlassCard className="p-5">
            <JobPrioritization savedJds={savedJds} />
          </GlassCard>
        )}

        <div className="grid grid-cols-5 gap-3">
          {STATUS_OPTIONS.map((s) => {
            const cfg = STATUS_CONFIG[s];
            return (
              <GlassCard
                key={s}
                className={`p-4 cursor-pointer transition-all ${filterStatus === s ? "ring-1 ring-[#4c8dff]/40" : ""}`}
                onClick={() => onFilter(filterStatus === s ? "all" : s)}
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
              onChange={(e) => onSearch(e.target.value)}
              placeholder="Search by company or role…"
              className="w-full bg-white/[0.04] border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm text-neutral-200 placeholder-neutral-600 focus:outline-none focus:border-[#4c8dff]/40 transition-colors"
            />
          </div>
          <button
            onClick={() => onFilter("all")}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.06] text-[#a1a1a1] text-sm hover:bg-white/[0.1] transition-colors"
          >
            <Filter className="size-4" />
            {filterStatus === "all" ? "All" : STATUS_CONFIG[filterStatus]?.label}
          </button>
        </div>
      </div>

      {/* Virtualized list (PERF-RP-003) — its own scroll container, also drives
          the collapsing header above. contain-paint isolates its repaints. */}
      <div ref={scrollRef} className="contain-paint flex-1 overflow-auto px-8 pt-2 pb-8">
        {filtered.length === 0 ? (
          <GlassCard className="p-8 flex items-center justify-center">
            <div className="text-center">
              <Briefcase className="size-8 text-neutral-600 mx-auto mb-3" />
              <p className="text-[#a1a1a1] text-sm">No applications {filterStatus !== "all" ? `with status "${filterStatus}"` : "yet"}</p>
            </div>
          </GlassCard>
        ) : (
          <VirtualList
            items={filtered}
            scrollRef={scrollRef}
            estimateSize={80}
            getKey={(app) => app.id}
            renderItem={(app) => <ApplicationRow app={app} onOpen={setSelected} />}
          />
        )}
      </div>
    </div>
  );
}
