import { type ReactNode, useState, useEffect } from "react";
import { NavLink } from "react-router-dom";
import { m } from "framer-motion";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { springs } from "@/motion";
import { ROUTES } from "@/routes";
import { warmRoute } from "@/services/prefetch";
import MaterialBackground from "@/webgl/MaterialBackground";
import CelebrationFallback from "@/components/CelebrationFallback";
import { PageSkeleton } from "@/components/ui/Skeleton";
import { UpdateBanner } from "@/components/UpdateBanner";
import { useBackendReady } from "@/hooks/useBackendReady";

// Material proxy (PERF-AC-002): a STATIC, pre-blurred aurora instead of a live
// `backdrop-filter: blur(60px)`. Soft radial gradients are inherently "blurred",
// cost a single composited paint, and the translucent glass panel above lets
// them read as frosted depth — no per-frame filter recompute on scroll/nav.
const AURORA =
  "radial-gradient(55rem 45rem at 12% -8%, rgb(var(--accent-rgb) / 0.22), transparent 60%)," +
  "radial-gradient(45rem 40rem at 108% 6%, rgb(var(--strong-rgb) / 0.12), transparent 55%)," +
  "radial-gradient(40rem 38rem at 50% 116%, rgb(var(--accent-rgb) / 0.10), transparent 60%)";

export default function AppShell({ children }: { children: ReactNode }) {
  const [degraded, setDegraded] = useState<{ degraded: boolean; message: string } | null>(null);
  // Sidecar warmup (12.3): the shell chrome paints within the first frame; the
  // content area shows a skeleton until /health binds, then swaps to live. Never
  // flashes an error here — the hook holds "loading" through the warmup budget,
  // and App.tsx owns the terminal "backend unreachable" screen.
  const backend = useBackendReady();

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/v1/health/ollama");
        if (res.ok) {
          const data = await res.json();
          if (data.degraded) {
            const msg = !data.available
              ? "AI engine offline — Ollama is not reachable. Outputs fall back to templates."
              : `AI degraded — missing model(s): ${data.missing_models.join(", ")}`;
            setDegraded({ degraded: true, message: msg });
          } else {
            setDegraded({ degraded: false, message: "" });
          }
        }
      } catch {
        setDegraded({ degraded: true, message: "AI engine offline — backend unreachable." });
      }
    };
    check();
    const id = setInterval(check, 15_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="relative min-h-screen w-screen overflow-hidden bg-[var(--bg)] text-neutral-50">
      {/* Static aurora layer — the cheap Off-tier fallback and the base the WebGL
          canvas blends over. Opacity animates in, never the blur. */}
      <m.div
        aria-hidden
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={springs.gentle}
        className="contain-strict pointer-events-none absolute inset-0"
        style={{ background: AURORA }}
      />

      {/* WebGL material (HAM-001) behind the glass shell. Lazy + capability-gated;
          renders nothing on the Off tier, leaving the static aurora above. */}
      <MaterialBackground />

      {/* Off-tier celebration payoff (particles cover Full/Reduced). */}
      <CelebrationFallback />

      <div className="relative flex h-screen overflow-hidden p-8">
        <div className="flex w-full overflow-hidden rounded-3xl border border-[var(--glass-border)] bg-[var(--glass-bg)] shadow-panel">
          <aside className="flex w-60 flex-shrink-0 flex-col border-r border-[var(--glass-border)] bg-white/[0.04] px-4 py-6">
            <div className="mb-8 flex items-center gap-3 px-2">
              {/* Brand logo. `app-logo` applies mix-blend screen (dark) +
                  invert on light theme — see tokens.css. */}
              <img src="/app-logo.png" alt="ACOS" className="app-logo size-10 rounded-xl" />
              <div className="leading-tight">
                <div className="font-display text-[15px] font-semibold tracking-[-0.64px] text-neutral-50">ACOS</div>
                <div className="text-[11px] text-[var(--fg-muted)]">Career OS</div>
              </div>
            </div>
            <nav className="flex flex-1 flex-col gap-2">
              {ROUTES.map(({ path, label, icon: Icon, end }) => (
                <NavLink
                  key={path}
                  to={path}
                  end={end}
                  // Predictive prefetch (ASP-001): warm the route chunk AND its
                  // backend data on hover/focus, before the click lands.
                  onPointerEnter={() => warmRoute(path)}
                  onFocus={() => warmRoute(path)}
                  className={({ isActive }) =>
                    cn(
                      "flex h-11 items-center gap-3 rounded-xl px-3.5 text-[13px] font-medium transition-colors duration-fast",
                      isActive
                        ? "bg-neutral-200/[0.15] text-neutral-50 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]"
                        : "text-[var(--fg-muted)] hover:bg-white/[0.04] hover:text-neutral-300",
                    )
                  }
                >
                  <Icon className="size-4" />
                  <span>{label}</span>
                </NavLink>
              ))}
            </nav>
          </aside>
          <main className="flex flex-1 flex-col overflow-auto">
            {degraded?.degraded && (
              <div className="flex flex-shrink-0 items-center gap-2 border-b border-weak/20 bg-weak/10 px-6 py-2 text-xs text-weak">
                <AlertTriangle className="size-3.5 flex-shrink-0" />
                {degraded.message}
              </div>
            )}
            <div className="flex-1 overflow-auto">
              {backend === "ready" ? (
                <>
                  <UpdateBanner />
                  {children}
                </>
              ) : (
                <PageSkeleton />
              )}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
