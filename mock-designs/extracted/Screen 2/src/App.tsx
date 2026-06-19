import { useEffect } from "react";
import {
  Activity,
  AlignLeft,
  ArrowRight,
  BadgeInfo,
  BarChart3,
  Briefcase,
  CheckCircle2,
  FileCheck2,
  FileText,
  Gauge,
  LayoutGrid,
  LayoutTemplate,
  Mail,
  Network,
  Plus,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Target,
  TrendingUp,
  Type,
} from "lucide-react";

export default function App() {
  return (
    <div>
      <div className="bg-neutral-950 text-neutral-50 w-full h-fit h-fit min-h-screen w-screen min-w-screen max-w-screen overflow-visible">
        <div className="min-h-screen bg-[#4c8dff]/18 p-6 w-full overflow-hidden">
          <div className="min-h-[calc(100vh-3rem)] shadow-[0_24px_80px_rgba(0,0,0,0.45),inset_0_1px_0_rgba(255,255,255,0.06)] backdrop-blur-[60px] rounded-3xl bg-neutral-900/80 border-white/60 border-1 border-solid flex overflow-hidden">
            <aside className="backdrop-blur-[40px] bg-neutral-950/35 border-white/60 border-t-0 border-r-1 border-b-0 border-l-0 border-solid flex px-4 py-5 flex-col w-60">
              <div className="flex mb-6 px-2 items-center gap-3">
                <div className="size-10 shadow-[inset_0_1px_0_rgba(255,255,255,0.12),0_10px_24px_rgba(76,141,255,0.18)] font-semibold rounded-2xl bg-neutral-200/20 text-neutral-900 text-sm leading-5 flex justify-center items-center">
                  AC
                </div>
                <div className="flex flex-col">
                  <span className="font-semibold text-neutral-50 text-sm leading-5 tracking-[-0.48px]">
                    ACOS
                  </span>
                  <span className="text-[#a1a1a1] text-xs leading-4">
                    Career OS
                  </span>
                </div>
              </div>
              <nav className="flex flex-col flex-1 gap-2">
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10.5">
                  <LayoutGrid className="size-4" />
                  <span className="font-medium text-sm leading-5">
                    Dashboard
                  </span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10.5">
                  <Network className="size-4" />
                  <span className="font-medium text-sm leading-5">
                    Knowledge Graph
                  </span>
                </div>
                <div className="cursor-pointer shadow-[inset_0_1px_0_rgba(255,255,255,0.12),0_8px_20px_rgba(76,141,255,0.16)] rounded-xl bg-neutral-200/20 text-neutral-900 flex px-3.5 items-center gap-3 h-10.5">
                  <FileText className="size-4" />
                  <span className="font-medium text-sm leading-5">Resumes</span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10.5">
                  <Mail className="size-4" />
                  <span className="font-medium text-sm leading-5">
                    Cover Letters
                  </span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10.5">
                  <BarChart3 className="size-4" />
                  <span className="font-medium text-sm leading-5">
                    ATS Analysis
                  </span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10.5">
                  <Sparkles className="size-4" />
                  <span className="font-medium text-sm leading-5">
                    Interview Prep
                  </span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10.5">
                  <Briefcase className="size-4" />
                  <span className="font-medium text-sm leading-5">
                    Applications CRM
                  </span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10.5">
                  <Gauge className="size-4" />
                  <span className="font-medium text-sm leading-5">
                    Learning Engine
                  </span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10.5">
                  <Settings className="size-4" />
                  <span className="font-medium text-sm leading-5">
                    Settings
                  </span>
                </div>
              </nav>
              <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] rounded-[18px] bg-neutral-800/40 border-white/60 border-1 border-solid mt-6 p-4">
                <div className="flex items-center gap-3">
                  <div className="size-9 rounded-full bg-neutral-200/15 text-neutral-200 flex justify-center items-center">
                    <ShieldCheck className="size-4" />
                  </div>
                  <div className="flex flex-col">
                    <span className="font-medium text-neutral-50 text-sm leading-5">
                      Local-first
                    </span>
                    <span className="text-[#a1a1a1] text-xs leading-4">
                      Privacy preserved
                    </span>
                  </div>
                </div>
              </div>
            </aside>
            <main className="flex flex-col flex-1 overflow-hidden">
              <header className="border-white/60 border-t-0 border-r-0 border-b-1 border-l-0 border-solid flex px-8 py-6 justify-between items-center">
                <div className="flex flex-col gap-1">
                  <div className="font-bold text-neutral-50 text-[34px] tracking-[-0.64px]">
                    Resume Generation Workspace
                  </div>
                  <div className="text-[#a1a1a1] text-sm leading-5">{`Senior Analytics & Technology Consultant · Apple-inspired document editor`}</div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] backdrop-blur-[20px] rounded-[14px] bg-neutral-800/40 text-[#a1a1a1] border-white/60 border-1 border-solid flex px-4 items-center gap-3 w-105 h-11.5">
                    <Search className="size-4 text-[#a1a1a1]" />
                    <span className="text-[#a1a1a1] text-sm leading-5">
                      Search knowledge graph, roles, evidence...
                    </span>
                  </div>
                  <button className="shadow-[0_10px_24px_rgba(76,141,255,0.28)] transition-transform font-semibold rounded-xl bg-neutral-200 text-neutral-900 px-4.5 py-3">
                    <RefreshCw className="inline size-4 mr-2" />
                    Regenerate
                  </button>
                </div>
              </header>
              <div className="flex p-6 flex-1 gap-6 overflow-hidden">
                <section className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_12px_30px_rgba(0,0,0,0.22)] backdrop-blur-[30px] rounded-3xl bg-neutral-800/35 border-white/60 border-1 border-solid flex p-6 flex-col gap-4 w-80">
                  <div className="flex justify-between items-start gap-4">
                    <div className="flex flex-col gap-1">
                      <div className="font-semibold uppercase text-[#a1a1a1] text-sm leading-5 tracking-[2.88px]">
                        Job Description Analysis
                      </div>
                      <div className="font-semibold text-neutral-50 text-2xl leading-8 tracking-[-0.48px]">
                        OpenAI
                      </div>
                      <div className="text-[#a1a1a1] text-sm leading-5">
                        Product Engineer
                      </div>
                    </div>
                    <div className="size-12 shadow-[0_10px_24px_rgba(76,141,255,0.18)] rounded-full bg-neutral-200/20 text-neutral-200 border-white/60 border-1 border-solid flex justify-center items-center">
                      <Target className="size-5" />
                    </div>
                  </div>
                  <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_18px_40px_rgba(0,0,0,0.22)] rounded-[28px] bg-[#4c8dff]/22 border-white/60 border-1 border-solid p-6">
                    <div className="flex justify-between items-end gap-4">
                      <div className="flex flex-col">
                        <span className="uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.88px]">
                          ATS Match
                        </span>
                        <span className="leading-none font-bold text-neutral-50 text-7xl leading-18 tracking-[-0.96px]">
                          87%
                        </span>
                      </div>
                      <div className="size-16 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] rounded-full bg-neutral-950/35 text-neutral-200 border-white/60 border-1 border-solid flex justify-center items-center">
                        <Activity className="size-7" />
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col gap-4">
                    <div className="font-semibold text-neutral-50 text-sm leading-5">
                      Keyword Coverage
                    </div>
                    <div className="flex flex-col gap-3">
                      <div className="flex flex-col gap-2">
                        <div className="text-[#a1a1a1] text-xs leading-4 flex justify-between items-center">
                          <span>Python</span>
                          <span>92%</span>
                        </div>
                        <div className="rounded-full bg-neutral-800/70 h-2">
                          <div className="w-[92%] bg-[linear-gradient(90deg,oklch(0.556_0_0),oklch(0.488_0.243_264.376))] shadow-[0_0_18px_rgba(76,141,255,0.35)] rounded-full h-2" />
                        </div>
                      </div>
                      <div className="flex flex-col gap-2">
                        <div className="text-[#a1a1a1] text-xs leading-4 flex justify-between items-center">
                          <span>Product Development</span>
                          <span>85%</span>
                        </div>
                        <div className="rounded-full bg-neutral-800/70 h-2">
                          <div className="w-[85%] bg-[linear-gradient(90deg,oklch(0.488_0.243_264.376),oklch(0.488_0.243_264.376))] shadow-[0_0_18px_rgba(76,141,255,0.35)] rounded-full h-2" />
                        </div>
                      </div>
                      <div className="flex flex-col gap-2">
                        <div className="text-[#a1a1a1] text-xs leading-4 flex justify-between items-center">
                          <span>AI Systems</span>
                          <span>78%</span>
                        </div>
                        <div className="rounded-full bg-neutral-800/70 h-2">
                          <div className="w-[78%] bg-[linear-gradient(90deg,oklch(0.488_0.243_264.376),oklch(0.627_0.265_303.9))] shadow-[0_0_18px_rgba(126,95,255,0.35)] rounded-full h-2" />
                        </div>
                      </div>
                      <div className="flex flex-col gap-2">
                        <div className="text-[#a1a1a1] text-xs leading-4 flex justify-between items-center">
                          <span>Analytics</span>
                          <span>71%</span>
                        </div>
                        <div className="rounded-full bg-neutral-800/70 h-2">
                          <div className="w-[71%] bg-[linear-gradient(90deg,oklch(0.627_0.265_303.9),oklch(0.488_0.243_264.376))] shadow-[0_0_18px_rgba(76,141,255,0.35)] rounded-full h-2" />
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
                <section className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_12px_30px_rgba(0,0,0,0.22)] backdrop-blur-[30px] rounded-3xl bg-neutral-800/35 border-white/60 border-1 border-solid flex p-6 flex-col flex-1 gap-4">
                  <div className="border-white/60 border-t-0 border-r-0 border-b-1 border-l-0 border-solid flex pb-4 justify-between items-center">
                    <div className="flex items-center gap-3">
                      <button className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] rounded-xl bg-neutral-950/35 text-neutral-50 text-sm leading-5 border-white/60 border-1 border-solid flex px-3 items-center gap-2 h-10">
                        <Type className="size-4" />
                        Inter
                      </button>
                      <button className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] rounded-xl bg-neutral-950/35 text-neutral-50 text-sm leading-5 border-white/60 border-1 border-solid flex px-3 items-center gap-2 h-10">
                        <AlignLeft className="size-4" />
                        Sections
                      </button>
                      <button className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] rounded-xl bg-neutral-950/35 text-neutral-50 text-sm leading-5 border-white/60 border-1 border-solid flex px-3 items-center gap-2 h-10">
                        <LayoutTemplate className="size-4" />
                        Layout
                      </button>
                    </div>
                    <div className="text-[#a1a1a1] text-xs leading-4 flex items-center gap-2">
                      <FileCheck2 className="size-4 text-[#00bc7d]" />
                      <span>Evidence-linked resume preview</span>
                    </div>
                  </div>
                  <div className="rounded-[28px] bg-neutral-950/20 flex p-6 justify-center flex-1 overflow-auto">
                    <div className="max-w-[760px] shadow-[0_24px_60px_rgba(0,0,0,0.38)] rounded-[18px] bg-[#f7f5ef] text-gray-900 p-10 w-full">
                      <div className="flex flex-col gap-6">
                        <div className="border-black/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid flex pb-5 justify-between items-start">
                          <div className="flex flex-col gap-2">
                            <div className="font-semibold text-gray-900 text-[28px] tracking-[-0.64px]">{`Senior Analytics & Technology Consultant`}</div>
                            <div className="text-gray-600 text-sm leading-5">
                              Privacy-focused analytics, AI-assisted
                              development, and regulatory compliance
                            </div>
                          </div>
                          <div className="text-right flex flex-col items-end gap-2">
                            <div className="font-medium text-gray-900 text-sm leading-5">
                              OpenAI
                            </div>
                            <div className="text-gray-500 text-xs leading-4">
                              San Francisco, CA
                            </div>
                          </div>
                        </div>
                        <div className="flex flex-col gap-3">
                          <div className="font-semibold uppercase text-gray-700 text-sm leading-5 tracking-[2.56px]">
                            Summary
                          </div>
                          <p className="text-gray-700 text-[13px] leading-6">
                            Senior analytics and technology consultant with deep
                            experience in litigation consulting, financial
                            investigations, product development, and AI-assisted
                            automation. Builds evidence-driven systems that
                            improve decision quality, reduce manual review, and
                            support privacy-conscious workflows across complex
                            stakeholder environments.
                          </p>
                        </div>
                        <div className="flex flex-col gap-3">
                          <div className="font-semibold uppercase text-gray-700 text-sm leading-5 tracking-[2.56px]">
                            Experience
                          </div>
                          <div className="flex flex-col gap-3">
                            <div className="flex flex-col gap-2">
                              <div className="font-semibold text-gray-900 text-[13px]">
                                AI Analytics Platform Lead
                              </div>
                              <div className="text-gray-700 text-[13px] leading-6 flex flex-col gap-2">
                                <div className="flex flex-wrap items-center gap-2">
                                  <span>
                                    Built AI-powered analytics platform reducing
                                    review time by 45%
                                  </span>
                                  <span className="inline-flex font-semibold rounded-full bg-[#00bc7d]/10 text-[#6cf0ac] text-[11px] border-[#00bc7d]/25 border-1 border-solid px-3 py-1 items-center gap-1">
                                    <CheckCircle2 className="size-3.5" />
                                    Verified
                                  </span>
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <span>
                                    Led cross-functional initiative across 6
                                    stakeholders
                                  </span>
                                  <span className="inline-flex font-semibold rounded-full bg-neutral-200/10 text-[#83b0ff] text-[11px] border-neutral-200/25 border-1 border-solid px-3 py-1 items-center gap-1">
                                    <BadgeInfo className="size-3.5" />
                                    Strong Inference
                                  </span>
                                </div>
                              </div>
                            </div>
                            <div className="flex flex-col gap-2">
                              <div className="font-semibold text-gray-900 text-[13px]">
                                Compliance Automation Consultant
                              </div>
                              <div className="text-gray-700 text-[13px] leading-6 flex flex-col gap-2">
                                <div className="flex flex-wrap items-center gap-2">
                                  <span>
                                    Developed compliance monitoring automation
                                  </span>
                                  <span className="inline-flex font-semibold rounded-full bg-[#00bc7d]/10 text-[#6cf0ac] text-[11px] border-[#00bc7d]/25 border-1 border-solid px-3 py-1 items-center gap-1">
                                    <CheckCircle2 className="size-3.5" />
                                    Verified
                                  </span>
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <span>
                                    Improved reporting consistency across
                                    recurring deliverables
                                  </span>
                                  <span className="inline-flex font-semibold rounded-full bg-neutral-200/10 text-[#83b0ff] text-[11px] border-neutral-200/25 border-1 border-solid px-3 py-1 items-center gap-1">
                                    <BadgeInfo className="size-3.5" />
                                    Strong Inference
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                        <div className="flex flex-col gap-3">
                          <div className="font-semibold uppercase text-gray-700 text-sm leading-5 tracking-[2.56px]">
                            Projects
                          </div>
                          <div className="text-gray-700 text-[13px] leading-6">
                            Knowledge graph architecture for career evidence,
                            ATS optimization workflows, and local-first
                            generation pipelines with traceable outputs.
                          </div>
                        </div>
                        <div className="flex flex-col gap-3">
                          <div className="font-semibold uppercase text-gray-700 text-sm leading-5 tracking-[2.56px]">
                            Education
                          </div>
                          <div className="text-gray-700 text-[13px] leading-6">
                            Bachelor’s degree in a quantitative discipline with
                            ongoing specialization in analytics, automation, and
                            AI systems.
                          </div>
                        </div>
                        <div className="flex flex-col gap-3">
                          <div className="font-semibold uppercase text-gray-700 text-sm leading-5 tracking-[2.56px]">
                            Skills
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <span className="font-medium rounded-full bg-black/5 text-gray-900 text-[11px] border-black/10 border-1 border-solid px-3 py-1">
                              Python
                            </span>
                            <span className="font-medium rounded-full bg-black/5 text-gray-900 text-[11px] border-black/10 border-1 border-solid px-3 py-1">
                              Data Analytics
                            </span>
                            <span className="font-medium rounded-full bg-black/5 text-gray-900 text-[11px] border-black/10 border-1 border-solid px-3 py-1">
                              AI-Assisted Development
                            </span>
                            <span className="font-medium rounded-full bg-black/5 text-gray-900 text-[11px] border-black/10 border-1 border-solid px-3 py-1">
                              Automation Engineering
                            </span>
                            <span className="font-medium rounded-full bg-black/5 text-gray-900 text-[11px] border-black/10 border-1 border-solid px-3 py-1">
                              Regulatory Compliance
                            </span>
                            <span className="font-medium rounded-full bg-black/5 text-gray-900 text-[11px] border-black/10 border-1 border-solid px-3 py-1">
                              Stakeholder Management
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
                <aside className="backdrop-blur-[40px] bg-neutral-950/25 border-white/60 border-t-0 border-r-0 border-b-0 border-l-1 border-solid flex p-6 flex-col gap-4 w-75">
                  <div className="flex justify-between items-center">
                    <div className="font-semibold text-neutral-50 text-2xl leading-8 tracking-[-0.48px]">
                      Optimization
                    </div>
                    <SlidersHorizontal className="size-5 text-[#a1a1a1]" />
                  </div>
                  <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_12px_28px_rgba(0,0,0,0.2)] rounded-3xl bg-neutral-800/40 border-white/60 border-1 border-solid flex p-4 flex-col gap-3">
                    <div className="font-semibold text-neutral-50 text-sm leading-5">
                      Missing Keywords
                    </div>
                    <div className="flex flex-col gap-2">
                      <div className="rounded-[14px] bg-[#ff6467]/10 text-[#ffb3b3] text-sm leading-5 border-[#ff6467]/20 border-1 border-solid flex px-3 py-2 justify-between items-center">
                        <span>LLM Evaluation</span>
                        <button className="text-neutral-200">
                          <Plus className="size-4" />
                        </button>
                      </div>
                      <div className="rounded-[14px] bg-[#ff6467]/10 text-[#ffb3b3] text-sm leading-5 border-[#ff6467]/20 border-1 border-solid flex px-3 py-2 justify-between items-center">
                        <span>Prompt Engineering</span>
                        <button className="text-neutral-200">
                          <Plus className="size-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                  <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_12px_28px_rgba(0,0,0,0.2)] rounded-3xl bg-neutral-800/40 border-white/60 border-1 border-solid flex p-4 flex-col gap-3">
                    <div className="font-semibold text-neutral-50 text-sm leading-5">
                      Suggestions
                    </div>
                    <div className="flex flex-col gap-2">
                      <div className="cursor-pointer transition-colors rounded-[14px] bg-neutral-950/35 text-[#a1a1a1] text-sm leading-5 border-white/60 border-1 border-solid flex p-3 justify-between items-center">
                        <span>+ Increase AI project visibility</span>
                        <ArrowRight className="size-4 text-neutral-200" />
                      </div>
                      <div className="cursor-pointer transition-colors rounded-[14px] bg-neutral-950/35 text-[#a1a1a1] text-sm leading-5 border-white/60 border-1 border-solid flex p-3 justify-between items-center">
                        <span>+ Promote Product Leadership experience</span>
                        <ArrowRight className="size-4 text-neutral-200" />
                      </div>
                    </div>
                  </div>
                  <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_18px_40px_rgba(0,0,0,0.22)] rounded-[28px] bg-[#32d583]/18 border-white/60 border-1 border-solid mt-auto p-5">
                    <div className="flex justify-between items-center">
                      <div className="flex flex-col">
                        <span className="uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.88px]">
                          Interview Probability
                        </span>
                        <span className="leading-none font-bold text-[#00bc7d] text-7xl leading-18 tracking-[-0.96px]">
                          82%
                        </span>
                        <span className="text-[#a1a1a1] text-sm leading-5 mt-1">
                          Estimated Interview Rate
                        </span>
                      </div>
                      <div className="relative size-20 flex justify-center items-center">
                        <div className="rounded-full border-[#00bc7d]/20 border-4 border-solid absolute inset-0" />
                        <div className="border-transparent border-t-chart2 border-r-chart2 rotate-[-35deg] rounded-full border-black/1 border-4 border-solid absolute inset-0" />
                        <TrendingUp className="relative size-6 text-[#00bc7d]" />
                      </div>
                    </div>
                    <div className="text-[#a1a1a1] text-xs leading-4 mt-4">
                      Based on 267 applications
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
