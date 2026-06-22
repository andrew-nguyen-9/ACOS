import { lazy, Suspense, useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import AppShell from "@/layouts/AppShell";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { getOnboardingStatus } from "@/services/settings";
import FirstRunWizard from "@/pages/FirstRunWizard";
import FpsOverlay from "@/components/dev/FpsOverlay";

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

const Dashboard = lazy(() => import("@/pages/Dashboard"));
const ResumePage = lazy(() => import("@/pages/ResumePage"));
const CoverLetterPage = lazy(() => import("@/pages/CoverLetterPage"));
const AtsPage = lazy(() => import("@/pages/AtsPage"));
const InterviewPrepPage = lazy(() => import("@/pages/InterviewPrepPage"));
const ApplicationsPage = lazy(() => import("@/pages/ApplicationsPage"));
const LearningPage = lazy(() => import("@/pages/LearningPage"));
const CopilotPage = lazy(() => import("@/pages/CopilotPage"));
const SettingsPage = lazy(() => import("@/pages/SettingsPage"));
const OptimizationPage = lazy(() => import("@/pages/OptimizationPage"));

const PageFallback = () => (
  <div className="flex flex-1 items-center justify-center p-16">
    <LoadingSpinner size="lg" />
  </div>
);

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
    <ErrorBoundary>
      {showPerf && <FpsOverlay />}
      <AppShell>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/resumes" element={<ResumePage />} />
            <Route path="/cover-letters" element={<CoverLetterPage />} />
            <Route path="/ats" element={<AtsPage />} />
            <Route path="/interview-prep" element={<InterviewPrepPage />} />
            <Route path="/applications" element={<ApplicationsPage />} />
            <Route path="/learning" element={<LearningPage />} />
            <Route path="/optimization" element={<OptimizationPage />} />
            <Route path="/copilot" element={<CopilotPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </Suspense>
      </AppShell>
    </ErrorBoundary>
  );
}
