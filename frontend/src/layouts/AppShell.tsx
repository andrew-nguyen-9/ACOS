import { type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, FileText, Mail, BarChart3, MessageSquareMore,
  Briefcase, Sparkles, Bot, Settings, BriefcaseBusiness,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/resumes", label: "Resumes", icon: FileText },
  { to: "/cover-letters", label: "Cover Letters", icon: Mail },
  { to: "/ats", label: "ATS Analysis", icon: BarChart3 },
  { to: "/interview-prep", label: "Interview Prep", icon: MessageSquareMore },
  { to: "/applications", label: "Applications CRM", icon: Briefcase },
  { to: "/learning", label: "Learning Engine", icon: Sparkles },
  { to: "/copilot", label: "Copilot", icon: Bot },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="bg-neutral-950 text-neutral-50 min-h-screen w-screen overflow-hidden">
      <div className="bg-[#4c8dff]/[0.18] flex p-8 h-screen overflow-hidden">
        <div
          className="shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-[60px] rounded-3xl
                     bg-neutral-900/70 border border-white/10 flex w-full overflow-hidden"
        >
          <aside
            className="bg-white/[0.04] border-r border-white/10 flex px-4 py-6 flex-col w-60 flex-shrink-0"
          >
            <div className="flex mb-8 px-2 items-center gap-3">
              <div
                className="size-10 shadow-[inset_0_1px_0_rgba(255,255,255,0.12),0_10px_30px_rgba(76,141,255,0.18)]
                           rounded-xl bg-neutral-200/[0.15] flex justify-center items-center"
              >
                <BriefcaseBusiness className="size-5 text-neutral-200" />
              </div>
              <div className="leading-tight">
                <div className="font-semibold text-neutral-50 text-[15px] tracking-[-0.64px]">ACOS</div>
                <div className="text-[#a1a1a1] text-[11px]">Career OS</div>
              </div>
            </div>
            <nav className="flex flex-col flex-1 gap-2">
              {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  className={({ isActive }) =>
                    cn(
                      "rounded-xl flex px-3.5 items-center gap-3 h-11 font-medium text-[13px] transition-colors",
                      isActive
                        ? "shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] bg-neutral-200/[0.15] text-neutral-50"
                        : "text-[#a1a1a1] hover:text-neutral-300 hover:bg-white/[0.04]"
                    )
                  }
                >
                  <Icon className="size-4" />
                  <span>{label}</span>
                </NavLink>
              ))}
            </nav>
          </aside>
          <main className="flex-1 overflow-auto">{children}</main>
        </div>
      </div>
    </div>
  );
}
