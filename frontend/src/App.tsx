import { Suspense, useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import { LazyMotion, LayoutGroup, MotionConfig } from "framer-motion";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import AppShell from "@/layouts/AppShell";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { PageSkeleton } from "@/components/ui/Skeleton";
import { useDeferredLoading } from "@/hooks/useDeferredLoading";
import { getOnboardingStatus } from "@/services/settings";
import FirstRunWizard from "@/pages/FirstRunWizard";
import FpsOverlay from "@/components/dev/FpsOverlay";
import { ROUTES } from "@/routes";

/** Dev-only: show the FPS overlay when `?perf=1` is set or via Cmd+Shift+P. */
function usePerfOverlay(): boolean {
  const [on, setOn] = useState(
    () =>
      import.meta.env.DEV &&
      new URLSearchParams(window.location.search).get("perf") === "1",
  );
  useEffect(() => {
    if (!import.meta.env.DEV) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey && e.shiftKey && e.code === "KeyP") {
        e.preventDefault();
        setOn((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return on;
}

// Async framer-motion features — code-split out of the initial bundle.
const loadMotionFeatures = () => import("@/motion/features").then((m) => m.default);

// Perceptual load masking (ASP-002): while a route chunk loads, show nothing for
// the first 200ms, then a structural skeleton — never a spinner flash. The
// fallback mounts the instant Suspense triggers, so `loading` is true from mount.
const PageFallback = () => {
  const show = useDeferredLoading(true, 200);
  return show ? <PageSkeleton /> : null;
};

export default function App() {
  const [onboardingDone, setOnboardingDone] = useState<boolean | null>(null);
  const [backendError, setBackendError] = useState(false);
  const perfRequested = usePerfOverlay();
  const showPerf = import.meta.env.DEV && perfRequested;

  useEffect(() => {
    const checkWithRetry = async (attemptsLeft: number): Promise<void> => {
      try {
        const done = await getOnboardingStatus();
        setOnboardingDone(done);
      } catch {
        if (attemptsLeft > 1) {
          await new Promise((r) => setTimeout(r, 2000));
          return checkWithRetry(attemptsLeft - 1);
        }
        // All retries exhausted — backend not reachable
        setBackendError(true);
      }
    };
    void checkWithRetry(3);
  }, []);

  if (backendError) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950 text-white">
        <div className="text-center">
          <h1 className="text-xl font-semibold mb-2">Backend not reachable</h1>
          <p className="text-gray-400 text-sm">ACOS backend failed to start. Try relaunching the app.</p>
        </div>
      </div>
    );
  }

  if (onboardingDone === null) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!onboardingDone) {
    return (
      <ErrorBoundary>
        <FirstRunWizard onComplete={() => setOnboardingDone(true)} />
      </ErrorBoundary>
    );
  }

  return (
    // `strict` enforces the `m.*` components (lean bundle); reducedMotion="user"
    // is the global accessibility guard — framer drops transform/layout motion
    // and keeps opacity when the OS asks for reduced motion.
    <LazyMotion strict features={loadMotionFeatures}>
      <MotionConfig reducedMotion="user">
        <ErrorBoundary>
          {showPerf && <FpsOverlay />}
          <AppShell>
            {/* LayoutGroup scopes shared-element (layoutId) transitions across
                the routed tree — e.g. a list card expanding into a detail view
                (KMP-003). Only small elements opt in via layoutId. */}
            <LayoutGroup>
              <Suspense fallback={<PageFallback />}>
                <Routes>
                  {ROUTES.map(({ path, Component }) => (
                    <Route key={path} path={path} element={<Component />} />
                  ))}
                </Routes>
              </Suspense>
            </LayoutGroup>
          </AppShell>
        </ErrorBoundary>
      </MotionConfig>
    </LazyMotion>
  );
}
