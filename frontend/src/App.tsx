import { Routes, Route } from "react-router-dom";
import { ErrorBoundary } from "@/components/ErrorBoundary";
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
    <ErrorBoundary>
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
    </ErrorBoundary>
  );
}
