import { useEffect } from "react";
import {
  BadgeCheck,
  Bot,
  BriefcaseBusiness,
  CheckCircle2,
  FilePenLine,
  FileText,
  Gauge,
  LayoutDashboard,
  LetterText,
  MessageSquareMore,
  MessageSquareQuote,
  Network,
  Scale,
  ScanSearch,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

export default function App() {
  return (
    <div>
      <div className="bg-neutral-950 text-neutral-50 w-full h-fit h-fit min-h-screen w-screen min-w-screen max-w-screen overflow-visible">
        <div className="min-h-[1080px] bg-[#4c8dff]/18 p-8 w-full overflow-hidden">
          <div className="min-h-[1040px] shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-[40px] rounded-3xl bg-neutral-900/70 border-white/10 border-1 border-solid flex overflow-hidden">
            <aside className="bg-white/3 border-white/10 border-t-0 border-r-1 border-b-0 border-l-0 border-solid flex px-4 py-6 flex-col w-60">
              <div className="flex mb-8 px-2 items-center gap-3">
                <div className="size-10 shadow-[inset_0_1px_0_rgba(255,255,255,0.12)] rounded-xl bg-neutral-200/15 text-neutral-200 flex justify-center items-center">
                  <Sparkles className="size-5" />
                </div>
                <div className="space-y-1">
                  <div className="font-semibold text-neutral-50 text-lg leading-7 tracking-[-0.64px]">
                    ACOS
                  </div>
                  <div className="text-[#a1a1a1] text-xs leading-4">
                    Career OS
                  </div>
                </div>
              </div>
              <nav className="flex flex-col flex-1 gap-2">
                <div className="font-medium rounded-xl text-[#a1a1a1] text-sm leading-5 flex px-3 py-2.5 items-center gap-3">
                  <LayoutDashboard className="size-4" />
                  <span>Dashboard</span>
                </div>
                <div className="font-medium rounded-xl text-[#a1a1a1] text-sm leading-5 flex px-3 py-2.5 items-center gap-3">
                  <Network className="size-4" />
                  <span>Knowledge Graph</span>
                </div>
                <div className="font-medium rounded-xl text-[#a1a1a1] text-sm leading-5 flex px-3 py-2.5 items-center gap-3">
                  <FileText className="size-4" />
                  <span>Resumes</span>
                </div>
                <div className="font-medium rounded-xl text-[#a1a1a1] text-sm leading-5 flex px-3 py-2.5 items-center gap-3">
                  <LetterText className="size-4" />
                  <span>Cover Letters</span>
                </div>
                <div className="font-medium rounded-xl text-[#a1a1a1] text-sm leading-5 flex px-3 py-2.5 items-center gap-3">
                  <ScanSearch className="size-4" />
                  <span>ATS Analysis</span>
                </div>
                <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] font-medium rounded-xl bg-neutral-200/15 text-neutral-50 text-sm leading-5 flex px-3 py-2.5 items-center gap-3">
                  <MessageSquareMore className="size-4 text-neutral-200" />
                  <span>Interview Prep</span>
                </div>
                <div className="font-medium rounded-xl text-[#a1a1a1] text-sm leading-5 flex px-3 py-2.5 items-center gap-3">
                  <BriefcaseBusiness className="size-4" />
                  <span>Applications CRM</span>
                </div>
                <div className="font-medium rounded-xl text-[#a1a1a1] text-sm leading-5 flex px-3 py-2.5 items-center gap-3">
                  <Gauge className="size-4" />
                  <span>Learning Engine</span>
                </div>
                <div className="font-medium rounded-xl text-[#a1a1a1] text-sm leading-5 flex px-3 py-2.5 items-center gap-3">
                  <Settings2 className="size-4" />
                  <span>Settings</span>
                </div>
              </nav>
              <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] rounded-2xl bg-neutral-800/40 border-white/10 border-1 border-solid mt-6 p-4">
                <div className="uppercase text-[#a1a1a1] text-xs leading-4 tracking-[3.84px]">
                  Status
                </div>
                <div className="text-neutral-50/80 text-[13px] flex mt-2 items-center gap-2">
                  <span className="size-2 shadow-[0_0_0_4px_rgba(52,211,153,0.12)] rounded-full bg-emerald-400" />
                  Local-first active
                </div>
              </div>
            </aside>
            <main className="min-w-0 flex flex-col flex-1">
              <header className="border-white/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid flex px-9 py-7 justify-between items-center">
                <div className="flex items-center gap-4">
                  <div className="size-12 shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_10px_30px_rgba(0,0,0,0.25)] rounded-2xl bg-neutral-900/80 text-neutral-200 border-white/10 border-1 border-solid flex justify-center items-center">
                    <Sparkles className="size-6" />
                  </div>
                  <div className="space-y-2">
                    <div className="font-bold text-neutral-50 text-[34px] tracking-tighter">
                      Career Copilot
                    </div>
                    <div className="text-[#a1a1a1] text-sm leading-5">
                      Powered by your Career Knowledge Graph — Local First
                    </div>
                  </div>
                </div>
                <div className="inline-flex shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] font-semibold rounded-full bg-emerald-500/10 text-emerald-300 text-[11px] border-emerald-500/20 border-1 border-solid px-3 py-1 items-center gap-2">
                  <CheckCircle2 className="size-3.5" />
                  Knowledge Graph Active
                </div>
              </header>
              <div className="min-h-0 flex px-8 py-6 flex-1 gap-6">
                <section className="min-w-0 flex justify-center flex-1">
                  <div className="max-w-[900px] shadow-[0_30px_90px_rgba(0,0,0,0.42)] backdrop-blur-[50px] rounded-[30px] bg-white/5 border-white/10 border-1 border-solid flex flex-col w-full h-full overflow-hidden">
                    <div className="border-white/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid flex px-6 py-4 justify-between items-center">
                      <div className="flex items-center gap-3">
                        <div className="size-9 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] rounded-xl bg-neutral-200/15 text-neutral-200 flex justify-center items-center">
                          <Bot className="size-4" />
                        </div>
                        <div>
                          <div className="font-semibold text-neutral-50 text-sm leading-5">
                            Interview Prep Copilot
                          </div>
                          <div className="text-[#a1a1a1] text-xs leading-4">
                            Context-aware, evidence-backed responses
                          </div>
                        </div>
                      </div>
                      <div className="text-[#a1a1a1] text-xs leading-4 flex items-center gap-2">
                        <ShieldCheck className="size-4 text-emerald-400" />
                        Traceable output
                      </div>
                    </div>
                    <div className="min-h-0 overflow-y-auto p-6 flex-1">
                      <div className="flex justify-end">
                        <div className="max-w-[72%] shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_12px_30px_rgba(0,0,0,0.22)] backdrop-blur-[20px] rounded-[22px] bg-[#4c8dff]/22 text-neutral-50 text-sm leading-7 border-neutral-200/20 border-1 border-solid px-5 py-4">
                          How should I answer why OpenAI should hire me?
                        </div>
                      </div>
                      <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_16px_40px_rgba(0,0,0,0.24)] rounded-3xl bg-white/5 border-white/10 border-1 border-solid mt-5 p-6">
                        <div className="bg-[linear-gradient(90deg,oklch(0.627_0.265_303.9),oklch(0.488_0.243_264.376))] rounded-full mb-4 w-full h-1" />
                        <div className="space-y-5 text-[#a1a1a1] text-sm leading-7">
                          <p>
                            Based on your verified career history, here are
                            three compelling reasons OpenAI should hire you:
                          </p>
                          <div className="space-y-4">
                            <div className="flex gap-3">
                              <div className="size-7 shrink-0 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] font-semibold rounded-full bg-neutral-800 text-neutral-50/70 text-xs leading-4 flex justify-center items-center">
                                1
                              </div>
                              <div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="font-semibold text-neutral-50">
                                    Product Leadership at Scale
                                  </span>
                                  <span className="inline-flex font-semibold rounded-full bg-emerald-500/10 text-emerald-300 text-[11px] border-emerald-500/20 border-1 border-solid px-2.5 py-1 items-center gap-1">
                                    <BadgeCheck className="size-3.5" />
                                    Verified
                                  </span>
                                </div>
                                <p className="text-neutral-50/70 mt-2">
                                  You have led cross-functional initiatives that
                                  translate ambiguous business needs into
                                  shipped, measurable outcomes. That maps well
                                  to OpenAI’s need for people who can operate
                                  across research, product, and execution.
                                </p>
                              </div>
                            </div>
                            <div className="flex gap-3">
                              <div className="size-7 shrink-0 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] font-semibold rounded-full bg-neutral-800 text-neutral-50/70 text-xs leading-4 flex justify-center items-center">
                                2
                              </div>
                              <div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="font-semibold text-neutral-50">
                                    AI-Native Development Experience
                                  </span>
                                  <span className="inline-flex font-semibold rounded-full bg-neutral-200/10 text-neutral-200 text-[11px] border-neutral-200/20 border-1 border-solid px-2.5 py-1 items-center gap-1">
                                    <Sparkles className="size-3.5" />
                                    Strong
                                  </span>
                                </div>
                                <p className="text-neutral-50/70 mt-2">
                                  Your hands-on work with AI-assisted
                                  development, automation engineering, and
                                  knowledge systems shows you can build with AI
                                  as a first-class tool, not just talk about it.
                                </p>
                              </div>
                            </div>
                            <div className="flex gap-3">
                              <div className="size-7 shrink-0 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] font-semibold rounded-full bg-neutral-800 text-neutral-50/70 text-xs leading-4 flex justify-center items-center">
                                3
                              </div>
                              <div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="font-semibold text-neutral-50">
                                    Analytics Consulting Depth
                                  </span>
                                  <span className="inline-flex font-semibold rounded-full bg-emerald-500/10 text-emerald-300 text-[11px] border-emerald-500/20 border-1 border-solid px-2.5 py-1 items-center gap-1">
                                    <BadgeCheck className="size-3.5" />
                                    Verified
                                  </span>
                                </div>
                                <p className="text-neutral-50/70 mt-2">
                                  Your litigation consulting, financial
                                  investigations, and regulatory work
                                  demonstrate rigor, judgment, and the ability
                                  to reason from evidence — all critical for
                                  high-stakes AI product work.
                                </p>
                              </div>
                            </div>
                          </div>
                          <div className="border-white/10 border-t-1 border-r-0 border-b-0 border-l-0 border-solid mt-6 pt-5">
                            <div className="uppercase text-[#a1a1a1] text-xs leading-4 tracking-[3.84px] mb-3">
                              Generated from Knowledge Graph
                            </div>
                            <div className="flex flex-wrap gap-2">
                              <div className="inline-flex font-medium rounded-full bg-neutral-200/10 text-neutral-200 text-xs leading-4 border-neutral-200/20 border-1 border-solid px-3 py-1.5 items-center gap-2">
                                <BriefcaseBusiness className="size-3.5" />
                                Product Leadership
                              </div>
                              <div className="inline-flex font-medium rounded-full bg-neutral-200/10 text-neutral-200 text-xs leading-4 border-neutral-200/20 border-1 border-solid px-3 py-1.5 items-center gap-2">
                                <Scale className="size-3.5" />
                                Analytics Consulting
                              </div>
                              <div className="inline-flex font-medium rounded-full bg-violet-500/10 text-violet-300 text-xs leading-4 border-violet-500/20 border-1 border-solid px-3 py-1.5 items-center gap-2">
                                <Bot className="size-3.5" />
                                AI Development
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="border-white/10 border-t-1 border-r-0 border-b-0 border-l-0 border-solid px-6 py-5">
                      <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-[20px] rounded-[18px] bg-neutral-900/80 border-white/10 border-1 border-solid flex px-4 py-3 items-center gap-3">
                        <Search className="size-4 text-[#a1a1a1]" />
                        <div className="text-[#a1a1a1] text-sm leading-5 flex-1">
                          Ask your Career Copilot anything...
                        </div>
                        <button className="size-10 shadow-[0_10px_24px_rgba(76,141,255,0.35)] rounded-xl bg-neutral-200 text-neutral-900 flex justify-center items-center">
                          <Send className="size-4" />
                        </button>
                      </div>
                      <div className="flex mt-4 flex-wrap gap-3">
                        <button className="inline-flex shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] font-medium rounded-xl bg-neutral-800 text-neutral-50 text-[13px] border-white/10 border-1 border-solid px-4 py-3 items-center gap-2">
                          <MessageSquareQuote className="size-4" />
                          Generate STAR Story
                        </button>
                        <button className="inline-flex shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] font-medium rounded-xl bg-neutral-800 text-neutral-50 text-[13px] border-white/10 border-1 border-solid px-4 py-3 items-center gap-2">
                          <FilePenLine className="size-4" />
                          Generate Resume Bullet
                        </button>
                        <button className="inline-flex shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] font-medium rounded-xl bg-neutral-800 text-neutral-50 text-[13px] border-white/10 border-1 border-solid px-4 py-3 items-center gap-2">
                          <LetterText className="size-4" />
                          Generate Cover Letter
                        </button>
                        <button className="inline-flex shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] font-medium rounded-xl bg-neutral-800 text-neutral-50 text-[13px] border-white/10 border-1 border-solid px-4 py-3 items-center gap-2">
                          <MessageSquareMore className="size-4" />
                          Generate Interview Answer
                        </button>
                      </div>
                    </div>
                  </div>
                </section>
                <aside className="backdrop-blur-[40px] bg-white/3 border-white/10 border-t-0 border-r-0 border-b-0 border-l-1 border-solid px-5 py-6 w-75">
                  <div className="space-y-6">
                    <div>
                      <div className="uppercase text-[#a1a1a1] text-xs leading-4 tracking-[3.84px] mb-3">
                        Referenced Evidence
                      </div>
                      <div className="space-y-3">
                        <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] rounded-[18px] bg-neutral-900/80 border-white/10 border-1 border-solid p-4">
                          <div className="flex justify-between items-start gap-3">
                            <div>
                              <div className="font-semibold text-neutral-50 text-sm leading-5">
                                AI Resume Engine
                              </div>
                              <div className="text-[#a1a1a1] text-xs leading-5 mt-1">
                                Project evidence tied to AI-assisted document
                                generation.
                              </div>
                            </div>
                            <div className="inline-flex font-semibold rounded-full bg-neutral-200/10 text-neutral-200 text-[11px] border-neutral-200/20 border-1 border-solid px-2.5 py-1 items-center gap-1">
                              <Sparkles className="size-3.5" />
                              Strong
                            </div>
                          </div>
                        </div>
                        <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] rounded-[18px] bg-neutral-900/80 border-white/10 border-1 border-solid p-4">
                          <div className="flex justify-between items-start gap-3">
                            <div>
                              <div className="font-semibold text-neutral-50 text-sm leading-5">
                                Compliance Analytics Platform
                              </div>
                              <div className="text-[#a1a1a1] text-xs leading-5 mt-1">
                                Evidence of regulated analytics and
                                stakeholder-facing delivery.
                              </div>
                            </div>
                            <div className="inline-flex font-semibold rounded-full bg-emerald-500/10 text-emerald-300 text-[11px] border-emerald-500/20 border-1 border-solid px-2.5 py-1 items-center gap-1">
                              <BadgeCheck className="size-3.5" />
                              Verified
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div>
                      <div className="uppercase text-[#a1a1a1] text-xs leading-4 tracking-[3.84px] mb-3">
                        Experiences
                      </div>
                      <div className="space-y-2">
                        <div className="rounded-[14px] bg-neutral-900/80 border-white/10 border-1 border-solid flex px-4 py-3 justify-between items-center">
                          <div className="text-neutral-50/80 text-[13px]">
                            Litigation Consulting
                          </div>
                          <div className="inline-flex font-semibold rounded-full bg-emerald-500/10 text-emerald-300 text-[11px] border-emerald-500/20 border-1 border-solid px-2.5 py-1 items-center gap-1">
                            <BadgeCheck className="size-3.5" />
                            Verified
                          </div>
                        </div>
                        <div className="rounded-[14px] bg-neutral-900/80 border-white/10 border-1 border-solid flex px-4 py-3 justify-between items-center">
                          <div className="text-neutral-50/80 text-[13px]">
                            Product Development
                          </div>
                          <div className="inline-flex font-semibold rounded-full bg-emerald-500/10 text-emerald-300 text-[11px] border-emerald-500/20 border-1 border-solid px-2.5 py-1 items-center gap-1">
                            <BadgeCheck className="size-3.5" />
                            Verified
                          </div>
                        </div>
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
