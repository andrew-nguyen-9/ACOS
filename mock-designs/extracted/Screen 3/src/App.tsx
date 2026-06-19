import { useEffect } from "react";
import {
  Brain,
  BriefcaseBusiness,
  Check,
  CheckCircle2,
  CircleDot,
  Clock3,
  Dot as LucideDot,
  FileSearch,
  FileText,
  Filter,
  LayoutGrid,
  MessageSquareText,
  Network,
  Search,
  SearchCheck,
  Send,
  Settings2,
  Sparkles,
  XCircle,
} from "lucide-react";

export default function App() {
  return (
    <div>
      <div className="bg-neutral-950 text-neutral-50 p-8 w-full h-fit h-fit min-h-screen w-screen min-w-screen max-w-screen overflow-visible">
        <div className="shadow-[0_24px_80px_rgba(0,0,0,0.45)] rounded-3xl bg-[#4c8dff]/16 border-white/10 border-1 border-solid flex mx-auto w-464 h-260 overflow-hidden">
          <aside className="backdrop-blur-[40px] bg-white/4 border-white/10 border-t-0 border-r-1 border-b-0 border-l-0 border-solid flex px-4 py-6 flex-col w-60">
            <div className="flex mb-8 px-2 items-center gap-3">
              <div className="size-10 shadow-[inset_0_1px_0_rgba(255,255,255,0.12)] font-semibold rounded-full bg-neutral-200/20 text-neutral-900 text-sm leading-5 flex justify-center items-center">
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
            <nav className="flex flex-col flex-1 gap-1">
              <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10">
                <LayoutGrid className="size-4" />
                <span className="text-sm leading-5">Dashboard</span>
              </div>
              <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10">
                <Network className="size-4" />
                <span className="text-sm leading-5">Knowledge Graph</span>
              </div>
              <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10">
                <FileText className="size-4" />
                <span className="text-sm leading-5">Resumes</span>
              </div>
              <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10">
                <MessageSquareText className="size-4" />
                <span className="text-sm leading-5">Cover Letters</span>
              </div>
              <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10">
                <SearchCheck className="size-4" />
                <span className="text-sm leading-5">ATS Analysis</span>
              </div>
              <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10">
                <Brain className="size-4" />
                <span className="text-sm leading-5">Interview Prep</span>
              </div>
              <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.12)] rounded-xl bg-neutral-200/15 text-neutral-900 flex px-3.5 items-center gap-3 h-10">
                <BriefcaseBusiness className="size-4" />
                <span className="font-medium text-sm leading-5">
                  Applications CRM
                </span>
              </div>
              <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10">
                <Sparkles className="size-4" />
                <span className="text-sm leading-5">Learning Engine</span>
              </div>
              <div className="rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-10">
                <Settings2 className="size-4" />
                <span className="text-sm leading-5">Settings</span>
              </div>
            </nav>
            <div className="shadow-[0_10px_30px_rgba(0,0,0,0.22)] rounded-[18px] bg-neutral-900 border-white/10 border-1 border-solid mt-6 p-4">
              <div className="uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.88px]">
                Learning
              </div>
              <div className="font-medium text-neutral-50 text-sm leading-5 mt-2">
                Improves after every 5 applications
              </div>
              <div className="text-[#a1a1a1] text-xs leading-4 mt-1">
                Embeddings, rankings, ATS recommendations
              </div>
            </div>
          </aside>
          <main className="min-w-0 flex flex-col flex-1">
            <header className="border-white/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid flex px-9 py-7 justify-between items-center">
              <div className="flex flex-col gap-2">
                <h1 className="font-bold text-neutral-50 text-[34px] tracking-[-0.64px]">
                  Applications
                </h1>
                <p className="text-[#a1a1a1] text-sm leading-5">
                  Career CRM — 267 tracked applications
                </p>
              </div>
              <div className="flex items-center gap-3">
                <div className="shadow-[0_8px_24px_rgba(0,0,0,0.18)] backdrop-blur-[20px] rounded-[14px] bg-neutral-900 text-[#a1a1a1] border-white/10 border-1 border-solid flex px-4 items-center gap-3 w-105 h-11.5">
                  <Search className="size-4" />
                  <span className="text-sm leading-5">Search applications</span>
                </div>
                <div className="shadow-[0_8px_24px_rgba(0,0,0,0.16)] rounded-full bg-neutral-800 text-neutral-50 text-sm leading-5 border-white/10 border-1 border-solid flex px-4 items-center gap-2 h-11.5">
                  <Filter className="size-4" />
                  Filter
                </div>
                <button className="shadow-[0_10px_24px_rgba(76,141,255,0.28)] font-semibold rounded-xl bg-neutral-200 text-neutral-900 px-4.5 py-3">
                  + New Application
                </button>
              </div>
            </header>
            <div className="grid grid-cols-4 px-9 py-6 gap-4">
              <div className="shadow-[0_12px_30px_rgba(0,0,0,0.18)] rounded-[22px] bg-neutral-900 border-white/10 border-1 border-solid p-6">
                <div className="text-[#a1a1a1] text-[13px]">
                  Applications Sent
                </div>
                <div className="font-bold text-[#83b0ff] text-[42px] tracking-tighter mt-3">
                  267
                </div>
              </div>
              <div className="shadow-[0_12px_30px_rgba(0,0,0,0.18)] rounded-[22px] bg-neutral-900 border-white/10 border-1 border-solid p-6">
                <div className="text-[#a1a1a1] text-[13px]">Responses</div>
                <div className="font-bold text-[#7e5fff] text-[42px] tracking-tighter mt-3">
                  54
                </div>
              </div>
              <div className="shadow-[0_12px_30px_rgba(0,0,0,0.18)] rounded-[22px] bg-neutral-900 border-white/10 border-1 border-solid p-6">
                <div className="text-[#a1a1a1] text-[13px]">Interviews</div>
                <div className="font-bold text-[#6cf0ac] text-[42px] tracking-tighter mt-3">
                  18
                </div>
              </div>
              <div className="shadow-[0_12px_30px_rgba(0,0,0,0.18)] rounded-[22px] bg-neutral-900 border-white/10 border-1 border-solid p-6">
                <div className="text-[#a1a1a1] text-[13px]">Offers</div>
                <div className="font-bold text-[#ffcb7b] text-[42px] tracking-tighter mt-3">
                  3
                </div>
              </div>
            </div>
            <div className="min-h-0 flex px-9 pb-8 flex-1 gap-6">
              <section className="min-w-0 shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_16px_40px_rgba(0,0,0,0.28)] rounded-3xl bg-neutral-900 border-white/10 border-1 border-solid flex flex-col flex-1 overflow-hidden">
                <div className="border-white/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid px-6 py-4">
                  <div className="grid grid-cols-[1.6fr_1.2fr_1fr_0.8fr_1fr_0.9fr] uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.56px] gap-4">
                    <div>Company</div>
                    <div>Role</div>
                    <div>Status</div>
                    <div>ATS Score</div>
                    <div>Interview Probability</div>
                    <div>Last Activity</div>
                  </div>
                </div>
                <div className="flex-1 overflow-hidden">
                  <div className="flex flex-col h-full">
                    <div className="grid grid-cols-[1.6fr_1.2fr_1fr_0.8fr_1fr_0.9fr] text-neutral-50 text-sm leading-5 border-white/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid px-6 py-4 items-center gap-4">
                      <div className="flex items-center gap-3">
                        <div className="size-9 font-semibold rounded-full bg-neutral-800 text-[#a1a1a1] text-xs leading-4 flex justify-center items-center">
                          S
                        </div>
                        <span>Stripe</span>
                      </div>
                      <div className="text-[#a1a1a1]">
                        Senior Product Analyst
                      </div>
                      <div>
                        <span className="inline-flex font-semibold rounded-full bg-[#32d583]/12 text-[#6cf0ac] text-[11px] border-[#32d583]/25 border-1 border-solid px-3 py-1 items-center gap-1">
                          <CheckCircle2 className="size-3.5" />
                          Interview Scheduled
                        </span>
                      </div>
                      <div className="font-medium text-neutral-50">91%</div>
                      <div className="font-medium text-neutral-50">88%</div>
                      <div className="text-[#a1a1a1]">2h ago</div>
                    </div>
                    <div className="grid grid-cols-[1.6fr_1.2fr_1fr_0.8fr_1fr_0.9fr] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] bg-neutral-200/8 text-neutral-50 text-sm leading-5 border-white/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid px-6 py-4 items-center gap-4">
                      <div className="flex items-center gap-3">
                        <div className="size-9 ring-1 ring-primary/20 font-semibold rounded-full bg-neutral-200/15 text-[#83b0ff] text-xs leading-4 flex justify-center items-center">
                          O
                        </div>
                        <span className="font-medium">OpenAI</span>
                      </div>
                      <div className="text-[#a1a1a1]">Product Engineer</div>
                      <div>
                        <span className="inline-flex shadow-[0_6px_18px_rgba(76,141,255,0.12)] font-semibold rounded-full bg-neutral-200/12 text-[#83b0ff] text-[11px] border-neutral-200/25 border-1 border-solid px-3 py-1 items-center gap-1">
                          <Send className="size-3.5" />
                          Applied
                        </span>
                      </div>
                      <div className="font-medium text-neutral-50">87%</div>
                      <div className="font-medium text-neutral-50">82%</div>
                      <div className="text-[#a1a1a1]">1d ago</div>
                    </div>
                    <div className="grid grid-cols-[1.6fr_1.2fr_1fr_0.8fr_1fr_0.9fr] text-neutral-50 text-sm leading-5 border-white/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid px-6 py-4 items-center gap-4">
                      <div className="flex items-center gap-3">
                        <div className="size-9 font-semibold rounded-full bg-neutral-800 text-[#a1a1a1] text-xs leading-4 flex justify-center items-center">
                          A
                        </div>
                        <span>Anthropic</span>
                      </div>
                      <div className="text-[#a1a1a1]">
                        Technical Program Manager
                      </div>
                      <div>
                        <span className="inline-flex font-semibold rounded-full bg-[#ffb547]/12 text-[#ffcb7b] text-[11px] border-[#ffb547]/25 border-1 border-solid px-3 py-1 items-center gap-1">
                          <FileSearch className="size-3.5" />
                          Resume Review
                        </span>
                      </div>
                      <div className="font-medium text-neutral-50">79%</div>
                      <div className="font-medium text-neutral-50">74%</div>
                      <div className="text-[#a1a1a1]">3d ago</div>
                    </div>
                    <div className="grid grid-cols-[1.6fr_1.2fr_1fr_0.8fr_1fr_0.9fr] text-neutral-50 text-sm leading-5 border-white/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid px-6 py-4 items-center gap-4">
                      <div className="flex items-center gap-3">
                        <div className="size-9 font-semibold rounded-full bg-neutral-800 text-[#a1a1a1] text-xs leading-4 flex justify-center items-center">
                          P
                        </div>
                        <span>Palantir</span>
                      </div>
                      <div className="text-[#a1a1a1]">Senior Data Analyst</div>
                      <div>
                        <span className="inline-flex font-semibold rounded-full bg-[#7e5fff]/12 text-[#c2b2ff] text-[11px] border-[#7e5fff]/25 border-1 border-solid px-3 py-1 items-center gap-1">
                          <Clock3 className="size-3.5" />
                          Screening
                        </span>
                      </div>
                      <div className="font-medium text-neutral-50">83%</div>
                      <div className="font-medium text-neutral-50">79%</div>
                      <div className="text-[#a1a1a1]">5d ago</div>
                    </div>
                    <div className="grid grid-cols-[1.6fr_1.2fr_1fr_0.8fr_1fr_0.9fr] text-neutral-50 text-sm leading-5 px-6 py-4 items-center gap-4">
                      <div className="flex items-center gap-3">
                        <div className="size-9 font-semibold rounded-full bg-neutral-800 text-[#a1a1a1] text-xs leading-4 flex justify-center items-center">
                          M
                        </div>
                        <span>McKinsey</span>
                      </div>
                      <div className="text-[#a1a1a1]">Analytics Consultant</div>
                      <div>
                        <span className="inline-flex font-semibold rounded-full bg-[#ff6b6b]/12 text-[#ff9a9a] text-[11px] border-[#ff6b6b]/25 border-1 border-solid px-3 py-1 items-center gap-1">
                          <XCircle className="size-3.5" />
                          Rejected
                        </span>
                      </div>
                      <div className="font-medium text-neutral-50">72%</div>
                      <div className="font-medium text-[#a1a1a1]">—</div>
                      <div className="text-[#a1a1a1]">1w ago</div>
                    </div>
                  </div>
                </div>
              </section>
              <aside className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_16px_40px_rgba(0,0,0,0.28)] backdrop-blur-[40px] bg-neutral-900 border-white/10 border-t-0 border-r-0 border-b-0 border-l-1 border-solid flex p-6 flex-col w-85">
                <div className="border-white/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid flex pb-5 justify-between items-start gap-4">
                  <div>
                    <div className="uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.88px]">
                      Selected Application
                    </div>
                    <div className="font-semibold text-neutral-50 text-2xl leading-8 tracking-[-0.48px] mt-2">
                      OpenAI — Product Engineer
                    </div>
                  </div>
                  <div className="font-semibold rounded-full bg-neutral-200/12 text-[#83b0ff] text-[11px] border-neutral-200/25 border-1 border-solid px-3 py-1">
                    Active
                  </div>
                </div>
                <div className="flex mt-6 flex-col gap-5">
                  <div>
                    <div className="uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.88px]">
                      Timeline
                    </div>
                    <div className="flex mt-4 flex-col gap-4">
                      <div className="flex gap-3">
                        <div className="flex flex-col items-center">
                          <div className="size-7 rounded-full bg-[#32d583]/15 text-[#6cf0ac] flex justify-center items-center">
                            <Check className="size-4" />
                          </div>
                          <div className="bg-white/10 mt-1 w-px h-8" />
                        </div>
                        <div>
                          <div className="font-medium text-neutral-50 text-sm leading-5">
                            Resume Generated
                          </div>
                          <div className="text-[#a1a1a1] text-xs leading-4">
                            Evidence mapped and formatted
                          </div>
                        </div>
                      </div>
                      <div className="flex gap-3">
                        <div className="flex flex-col items-center">
                          <div className="size-7 rounded-full bg-[#32d583]/15 text-[#6cf0ac] flex justify-center items-center">
                            <Check className="size-4" />
                          </div>
                          <div className="bg-white/10 mt-1 w-px h-8" />
                        </div>
                        <div>
                          <div className="font-medium text-neutral-50 text-sm leading-5">
                            ATS Analysis
                          </div>
                          <div className="text-[#a1a1a1] text-xs leading-4">
                            Keyword alignment scored
                          </div>
                        </div>
                      </div>
                      <div className="flex gap-3">
                        <div className="flex flex-col items-center">
                          <div className="size-7 rounded-full bg-[#32d583]/15 text-[#6cf0ac] flex justify-center items-center">
                            <Check className="size-4" />
                          </div>
                          <div className="bg-white/10 mt-1 w-px h-8" />
                        </div>
                        <div>
                          <div className="font-medium text-neutral-50 text-sm leading-5">
                            Application Submitted
                          </div>
                          <div className="text-[#a1a1a1] text-xs leading-4">
                            Submitted 1 day ago
                          </div>
                        </div>
                      </div>
                      <div className="flex gap-3">
                        <div className="flex flex-col items-center">
                          <div className="size-7 shadow-[0_0_0_0_rgba(76,141,255,0.35)] rounded-full bg-neutral-200/15 text-[#83b0ff] flex justify-center items-center">
                            <CircleDot className="size-4 animate-pulse" />
                          </div>
                          <div className="bg-white/10 mt-1 w-px h-8" />
                        </div>
                        <div>
                          <div className="font-medium text-neutral-50 text-sm leading-5">
                            Recruiter Viewed Profile
                          </div>
                          <div className="text-[#a1a1a1] text-xs leading-4">
                            Profile activity detected
                          </div>
                        </div>
                      </div>
                      <div className="flex gap-3">
                        <div className="flex flex-col items-center">
                          <div className="size-7 rounded-full bg-neutral-800 text-[#a1a1a1] flex justify-center items-center">
                            <LucideDot className="size-4" />
                          </div>
                        </div>
                        <div>
                          <div className="font-medium text-neutral-50 text-sm leading-5">
                            Follow-up Pending
                          </div>
                          <div className="text-[#a1a1a1] text-xs leading-4">
                            Awaiting response window
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="shadow-[0_10px_30px_rgba(0,0,0,0.22)] rounded-3xl bg-neutral-950 border-white/10 border-1 border-solid p-5">
                    <div className="uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.88px]">
                      AI Notes
                    </div>
                    <p className="italic text-[#a1a1a1] text-sm leading-6 mt-3">
                      Strong keyword alignment detected. Product leadership
                      framing recommended for follow-up.
                    </p>
                  </div>
                  <div className="shadow-[0_10px_30px_rgba(0,0,0,0.22)] rounded-3xl bg-neutral-950 border-white/10 border-1 border-solid p-5">
                    <div className="uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.88px]">
                      Learning Signals
                    </div>
                    <div className="flex mt-4 flex-wrap gap-2">
                      <div className="font-medium rounded-full bg-neutral-200/12 text-[#83b0ff] text-xs leading-4 border-neutral-200/25 border-1 border-solid px-3 py-1">
                        Product Development up
                      </div>
                      <div className="font-medium rounded-full bg-[#32d583]/12 text-[#6cf0ac] text-xs leading-4 border-[#32d583]/25 border-1 border-solid px-3 py-1">
                        AI Automation up
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
  );
}
