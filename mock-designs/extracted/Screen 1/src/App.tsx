import { useEffect } from "react";
import {
  Briefcase,
  BriefcaseBusiness,
  Check,
  FileText,
  LayoutDashboard,
  LetterText,
  MessageSquareMore,
  Network,
  NotebookPen,
  ScanSearch,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Wifi,
} from "lucide-react";

import { FallbackComponent } from "./CustomComponents";

export default function App() {
  return (
    <div>
      <div className="bg-neutral-950 text-neutral-50 w-full h-fit h-fit min-h-screen w-screen min-w-screen max-w-screen overflow-visible">
        <div className="bg-[#4c8dff]/18 flex mx-auto p-8 w-480 h-270 overflow-hidden">
          <div className="shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-[60px] rounded-3xl bg-neutral-900/70 border-white/10 border-1 border-solid flex w-full overflow-hidden">
            <aside className="bg-white/4 border-white/10 border-t-0 border-r-1 border-b-0 border-l-0 border-solid flex px-4 py-6 flex-col w-60">
              <div className="flex mb-8 px-2 items-center gap-3">
                <div className="size-10 shadow-[inset_0_1px_0_rgba(255,255,255,0.12),0_10px_30px_rgba(76,141,255,0.18)] rounded-xl bg-neutral-200/15 text-neutral-900 flex justify-center items-center">
                  <BriefcaseBusiness className="size-5 text-neutral-200" />
                </div>
                <div className="leading-tight">
                  <div className="font-semibold text-neutral-50 text-[15px] tracking-[-0.64px]">
                    ACOS
                  </div>
                  <div className="text-[#a1a1a1] text-[11px]">Career OS</div>
                </div>
              </div>
              <nav className="flex flex-col flex-1 gap-2">
                <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] rounded-xl bg-neutral-200/15 text-neutral-50 flex px-3.5 items-center gap-3 h-11">
                  <LayoutDashboard className="size-4 text-neutral-200" />
                  <span className="font-medium text-[13px]">Dashboard</span>
                </div>
                <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <Network className="size-4" />
                  <span className="font-medium text-[13px]">
                    Knowledge Graph
                  </span>
                </div>
                <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <FileText className="size-4" />
                  <span className="font-medium text-[13px]">Resumes</span>
                </div>
                <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <LetterText className="size-4" />
                  <span className="font-medium text-[13px]">Cover Letters</span>
                </div>
                <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <ScanSearch className="size-4" />
                  <span className="font-medium text-[13px]">ATS Analysis</span>
                </div>
                <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <MessageSquareMore className="size-4" />
                  <span className="font-medium text-[13px]">
                    Interview Prep
                  </span>
                </div>
                <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <Briefcase className="size-4" />
                  <span className="font-medium text-[13px]">
                    Applications CRM
                  </span>
                </div>
                <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <Sparkles className="size-4" />
                  <span className="font-medium text-[13px]">
                    Learning Engine
                  </span>
                </div>
                <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <Settings2 className="size-4" />
                  <span className="font-medium text-[13px]">Settings</span>
                </div>
              </nav>
              <div className="rounded-2xl bg-neutral-800/40 border-white/10 border-1 border-solid mt-auto p-4">
                <div className="uppercase text-[#a1a1a1] text-[11px] tracking-[3.84px]">
                  Local-first
                </div>
                <div className="text-neutral-50/80 text-[13px] mt-2">
                  Encrypted knowledge graph stored on device
                </div>
              </div>
            </aside>
            <main className="min-w-0 flex flex-col flex-1">
              <header className="border-white/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid flex px-9 py-7 justify-between items-center">
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <Search className="pointer-events-none top-1/2 size-4 -translate-y-1/2 text-[#a1a1a1] absolute left-4" />
                    <input
                      className="outline-none rounded-[14px] bg-neutral-800/40 text-neutral-50 text-sm leading-5 border-white/15 border-1 border-solid pl-11 pr-4 w-105 h-12"
                      placeholder="Search Career Knowledge Graph"
                    />
                  </div>
                  <button className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] font-medium rounded-[14px] bg-neutral-800/40 text-neutral-50/90 text-[13px] border-white/15 border-1 border-solid flex px-4 items-center gap-3 h-12">
                    <Sparkles className="size-4 text-neutral-200" />
                    <span>AI Copilot</span>
                    <span className="rounded-full bg-neutral-950/40 text-[#a1a1a1] text-[11px] border-white/15 border-1 border-solid px-2 py-1">
                      ⌘K
                    </span>
                  </button>
                </div>
                <div className="flex items-center gap-3">
                  <div className="inline-flex font-semibold rounded-full bg-emerald-400/10 text-emerald-300 text-[11px] border-emerald-400/20 border-1 border-solid px-3 py-1.5 items-center gap-2">
                    <Wifi className="size-3.5" />
                    Local First
                  </div>
                  <div className="inline-flex font-semibold rounded-full bg-neutral-800/40 text-neutral-50/75 text-[11px] border-white/10 border-1 border-solid px-3 py-1.5 items-center gap-2">
                    <ShieldCheck className="size-3.5 text-emerald-300" />
                    Evidence Active
                  </div>
                </div>
              </header>
              <div className="min-h-0 flex flex-1">
                <section className="min-w-0 flex px-9 py-8 flex-col flex-1">
                  <div className="relative shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_18px_50px_rgba(0,0,0,0.28)] rounded-[28px] bg-[#4c8dff]/14.000000000000002 border-white/10 border-1 border-solid flex flex-1 overflow-hidden">
                    <div className="bg-white/3 absolute inset-0" />
                    <svg className="absolute inset-0 w-full h-full">
                      <defs>
                        <filter id="glowBlue">
                          <feGaussianBlur
                            stdDeviation="3"
                            result="coloredBlur"
                          />
                          <feMerge>
                            <feMergeNode in="coloredBlur" />
                            <feMergeNode in="SourceGraphic" />
                          </feMerge>
                        </filter>
                        <filter id="glowPurple">
                          <feGaussianBlur
                            stdDeviation="3"
                            result="coloredBlur"
                          />
                          <feMerge>
                            <feMergeNode in="coloredBlur" />
                            <feMergeNode in="SourceGraphic" />
                          </feMerge>
                        </filter>
                      </defs>
                      <path
                        d="M 360 250 C 470 220, 560 220, 660 260"
                        fill="none"
                        stroke="rgba(76,141,255,0.55)"
                        strokeWidth="2"
                        filter="url(#glowBlue)"
                      />
                      <path
                        d="M 360 250 C 470 300, 560 330, 690 360"
                        fill="none"
                        stroke="rgba(76,141,255,0.45)"
                        strokeWidth="2"
                        filter="url(#glowBlue)"
                      />
                      <path
                        d="M 360 250 C 470 180, 560 160, 700 150"
                        fill="none"
                        stroke="rgba(76,141,255,0.45)"
                        strokeWidth="2"
                        filter="url(#glowBlue)"
                      />
                      <path
                        d="M 690 360 C 760 330, 820 300, 900 280"
                        fill="none"
                        stroke="rgba(126,95,255,0.55)"
                        strokeWidth="2"
                        filter="url(#glowPurple)"
                      />
                      <path
                        d="M 690 360 C 770 390, 840 420, 930 430"
                        fill="none"
                        stroke="rgba(126,95,255,0.55)"
                        strokeWidth="2"
                        filter="url(#glowPurple)"
                      />
                      <path
                        d="M 700 150 C 790 170, 860 190, 950 210"
                        fill="none"
                        stroke="rgba(126,95,255,0.55)"
                        strokeWidth="2"
                        filter="url(#glowPurple)"
                      />
                      <path
                        d="M 900 280 C 980 250, 1060 230, 1140 220"
                        fill="none"
                        stroke="rgba(126,95,255,0.45)"
                        strokeWidth="2"
                        filter="url(#glowPurple)"
                      />
                      <path
                        d="M 930 430 C 1010 410, 1080 390, 1160 370"
                        fill="none"
                        stroke="rgba(126,95,255,0.45)"
                        strokeWidth="2"
                        filter="url(#glowPurple)"
                      />
                    </svg>
                    <div className="shadow-[0_20px_50px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-[20px] rounded-[18px] bg-neutral-200/10 border-blue-400/20 border-1 border-solid flex absolute left-8 top-8 p-5 flex-col justify-center w-55 h-27.5">
                      <div className="font-medium text-blue-200/90 text-xs leading-4">
                        Litigation Consulting
                      </div>
                      <div className="text-neutral-50/45 text-xs leading-4 mt-1">
                        Experience node
                      </div>
                    </div>
                    <div className="shadow-[0_20px_50px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-[20px] rounded-[18px] bg-neutral-200/10 border-blue-400/20 border-1 border-solid flex absolute left-8 top-37.5 p-5 flex-col justify-center w-55 h-27.5">
                      <div className="font-medium text-blue-200/90 text-xs leading-4">
                        Financial Investigations
                      </div>
                      <div className="text-neutral-50/45 text-xs leading-4 mt-1">
                        Experience node
                      </div>
                    </div>
                    <div className="shadow-[0_20px_50px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-[20px] rounded-[18px] bg-neutral-200/10 border-blue-400/20 border-1 border-solid flex absolute left-8 top-73 p-5 flex-col justify-center w-55 h-27.5">
                      <div className="font-medium text-blue-200/90 text-xs leading-4">
                        Data Analytics
                      </div>
                      <div className="text-neutral-50/45 text-xs leading-4 mt-1">
                        Experience node
                      </div>
                    </div>
                    <div className="shadow-[0_20px_50px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-[20px] rounded-[18px] bg-neutral-200/10 border-blue-400/20 border-1 border-solid flex absolute left-8 top-108.5 p-5 flex-col justify-center w-55 h-27.5">
                      <div className="font-medium text-blue-200/90 text-xs leading-4">
                        Product Development
                      </div>
                      <div className="text-neutral-50/45 text-xs leading-4 mt-1">
                        Experience node
                      </div>
                    </div>
                    <div className="shadow-[0_20px_50px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-[20px] rounded-[18px] bg-neutral-200/10 border-blue-400/20 border-1 border-solid flex absolute left-8 top-144 p-5 flex-col justify-center w-55 h-27.5">
                      <div className="font-medium text-blue-200/90 text-xs leading-4">
                        AI Automation
                      </div>
                      <div className="text-neutral-50/45 text-xs leading-4 mt-1">
                        Experience node
                      </div>
                    </div>
                    <div className="shadow-[0_20px_50px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-[20px] rounded-[18px] bg-neutral-200/10 border-violet-400/20 border-1 border-solid flex absolute left-77.5 top-27.5 p-5 flex-col justify-center w-60 h-24">
                      <div className="font-medium text-violet-200/90 text-xs leading-4">
                        Expert Witness Analytics Platform
                      </div>
                      <div className="text-neutral-50/45 text-xs leading-4 mt-1">
                        Project node
                      </div>
                    </div>
                    <div className="shadow-[0_20px_50px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-[20px] rounded-[18px] bg-neutral-200/10 border-violet-400/20 border-1 border-solid flex absolute left-77.5 top-63 p-5 flex-col justify-center w-60 h-24">
                      <div className="font-medium text-violet-200/90 text-xs leading-4">
                        Compliance Monitoring System
                      </div>
                      <div className="text-neutral-50/45 text-xs leading-4 mt-1">
                        Project node
                      </div>
                    </div>
                    <div className="shadow-[0_20px_50px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-[20px] rounded-[18px] bg-neutral-200/10 border-violet-400/20 border-1 border-solid flex absolute left-77.5 top-98.5 p-5 flex-col justify-center w-60 h-24">
                      <div className="font-medium text-violet-200/90 text-xs leading-4">
                        AI Resume Engine
                      </div>
                      <div className="text-neutral-50/45 text-xs leading-4 mt-1">
                        Project node
                      </div>
                    </div>
                    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] rounded-full bg-neutral-800/40 text-neutral-50/70 text-xs leading-4 border-white/10 border-1 border-solid absolute left-140 top-17.5 px-4 py-2">
                      Python
                    </div>
                    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] rounded-full bg-neutral-800/40 text-neutral-50/70 text-xs leading-4 border-white/10 border-1 border-solid absolute left-152.5 top-30 px-4 py-2">
                      SQL
                    </div>
                    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] rounded-full bg-neutral-800/40 text-neutral-50/70 text-xs leading-4 border-white/10 border-1 border-solid absolute left-140 top-42.5 px-4 py-2">
                      Product Strategy
                    </div>
                    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] rounded-full bg-neutral-800/40 text-neutral-50/70 text-xs leading-4 border-white/10 border-1 border-solid absolute left-155 top-55 px-4 py-2">
                      Regulatory Compliance
                    </div>
                    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] rounded-full bg-neutral-800/40 text-neutral-50/70 text-xs leading-4 border-white/10 border-1 border-solid absolute left-140 top-72.5 px-4 py-2">
                      Machine Learning
                    </div>
                  </div>
                  <div className="grid grid-cols-5 mt-6 gap-4">
                    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] rounded-[22px] bg-neutral-800/40 border-white/10 border-1 border-solid p-6">
                      <div className="text-[#a1a1a1] text-[13px]">
                        Experiences
                      </div>
                      <div className="font-bold text-neutral-50 text-[42px] tracking-tighter mt-3">
                        74
                      </div>
                    </div>
                    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] rounded-[22px] bg-neutral-800/40 border-white/10 border-1 border-solid p-6">
                      <div className="text-[#a1a1a1] text-[13px]">Projects</div>
                      <div className="font-bold text-neutral-50 text-[42px] tracking-tighter mt-3">
                        42
                      </div>
                    </div>
                    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] rounded-[22px] bg-neutral-800/40 border-white/10 border-1 border-solid p-6">
                      <div className="text-[#a1a1a1] text-[13px]">Skills</div>
                      <div className="font-bold text-neutral-50 text-[42px] tracking-tighter mt-3">
                        138
                      </div>
                    </div>
                    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] rounded-[22px] bg-neutral-800/40 border-white/10 border-1 border-solid p-6">
                      <div className="text-[#a1a1a1] text-[13px]">
                        Applications
                      </div>
                      <div className="font-bold text-neutral-50 text-[42px] tracking-tighter mt-3">
                        267
                      </div>
                    </div>
                    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] rounded-[22px] bg-neutral-800/40 border-white/10 border-1 border-solid p-6">
                      <div className="text-[#a1a1a1] text-[13px]">
                        Interview Rate
                      </div>
                      <div className="font-bold text-emerald-300 text-[42px] tracking-tighter mt-3">
                        22.4%
                      </div>
                    </div>
                  </div>
                </section>
                <aside className="shadow-[inset_1px_0_0_rgba(255,255,255,0.04)] bg-white/3 border-white/10 border-t-0 border-r-0 border-b-0 border-l-1 border-solid px-6 py-8 w-80">
                  <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] rounded-3xl bg-neutral-800/40 border-white/10 border-1 border-solid p-5">
                    <div className="flex items-start gap-3">
                      <div className="size-3 shadow-[0_0_0_4px_rgba(126,95,255,0.15)] rounded-full bg-violet-400 mt-1" />
                      <div className="min-w-0">
                        <div className="font-semibold text-neutral-50 text-lg leading-7 tracking-[-0.48px]">
                          Expert Witness Analytics Platform
                        </div>
                        <div className="text-[#a1a1a1] text-xs leading-4 mt-1">
                          Selected node
                        </div>
                      </div>
                    </div>
                    <div className="mt-5">
                      <div className="uppercase text-[#a1a1a1] text-[11px] tracking-[3.84px]">
                        Evidence Sources
                      </div>
                      <div className="flex mt-3 flex-col gap-2">
                        <div className="rounded-[14px] bg-neutral-950/30 text-neutral-50/75 text-[13px] border-white/10 border-1 border-solid flex px-3 py-2 items-center gap-3">
                          <FileText className="size-4 text-neutral-200" />
                          Resume
                        </div>
                        <div className="rounded-[14px] bg-neutral-950/30 text-neutral-50/75 text-[13px] border-white/10 border-1 border-solid flex px-3 py-2 items-center gap-3">
                          <NotebookPen className="size-4 text-violet-300" />
                          Project Notes
                        </div>
                        <div className="rounded-[14px] bg-neutral-950/30 text-neutral-50/75 text-[13px] border-white/10 border-1 border-solid flex px-3 py-2 items-center gap-3">
                          <FallbackComponent className="size-4 text-neutral-50/70" />
                          GitHub Repository
                        </div>
                        <div className="rounded-[14px] bg-neutral-950/30 text-neutral-50/75 text-[13px] border-white/10 border-1 border-solid flex px-3 py-2 items-center gap-3">
                          <MessageSquareMore className="size-4 text-emerald-300" />
                          Interview Answers
                        </div>
                      </div>
                    </div>
                    <div className="rounded-[18px] bg-emerald-400/10 border-emerald-400/20 border-1 border-solid mt-5 px-4 py-3">
                      <div className="inline-flex font-semibold rounded-full bg-emerald-400/10 text-emerald-300 text-[11px] border-emerald-400/20 border-1 border-solid px-3 py-1.5 items-center gap-2">
                        <Check className="size-3.5" />
                        Verified
                      </div>
                      <div className="text-neutral-50/60 text-xs leading-4 mt-2">
                        Confidence system active for all generated statements.
                      </div>
                    </div>
                  </div>
                </aside>
              </div>
            </main>
          </div>
        </div>
      </div>
    </div>
  );
}
