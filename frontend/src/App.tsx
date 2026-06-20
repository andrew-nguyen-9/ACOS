import { lazy, Suspense, useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import AppShell from "@/layouts/AppShell";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { getOnboardingStatus } from "@/services/settings";
import FirstRunWizard from "@/pages/FirstRunWizard";

const Dashboard = lazy(() => import("@/pages/Dashboard"));
const ResumePage = lazy(() => import("@/pages/ResumePage"));
const CoverLetterPage = lazy(() => import("@/pages/CoverLetterPage"));
const AtsPage = lazy(() => import("@/pages/AtsPage"));
const InterviewPrepPage = lazy(() => import("@/pages/InterviewPrepPage"));
const ApplicationsPage = lazy(() => import("@/pages/ApplicationsPage"));
const LearningPage = lazy(() => import("@/pages/LearningPage"));
const CopilotPage = lazy(() => import("@/pages/CopilotPage"));
const SettingsPage = lazy(() => import("@/pages/SettingsPage"));

const PageFallback = () => (
  <div className="flex flex-1 items-center justify-center p-16">
    <LoadingSpinner size="lg" />
  </div>
);

export default function App() {
  const [onboardingDone, setOnboardingDone] = useState<boolean | null>(null);

  useEffect(() => {
    getOnboardingStatus()
      .then(setOnboardingDone)
      .catch(() => setOnboardingDone(true)); // fallback: skip wizard if backend unreachable
  }, []);

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
            <Route path="/copilot" element={<CopilotPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </Suspense>
      </AppShell>
    </ErrorBoundary>
  );
}
