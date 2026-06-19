import { useEffect } from "react";
import {
  BadgeInfo,
  CheckCircle2,
  Code2,
  FilePenLine,
  FileText,
  MessageSquareText,
  NotebookPen,
  Search,
  Shield,
  Trophy,
} from "lucide-react";

export default function App() {
  return (
    <div>
      <div className="bg-neutral-950 text-neutral-50 w-full h-fit h-fit min-h-screen w-screen min-w-screen max-w-screen overflow-visible">
        <div className="min-h-[1080px] bg-[#4c8dff]/16 p-8">
          <div className="max-w-[1856px] shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-[40px] rounded-3xl bg-neutral-900/70 border-white/10 border-1 border-solid mx-auto overflow-hidden">
            <div className="min-h-[1040px] flex flex-col">
              <div className="bg-[#32d583]/14.000000000000002 border-white/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid px-9 py-4">
                <div className="flex justify-between items-center gap-6">
                  <div className="flex items-center gap-4">
                    <div className="size-11 shadow-[0_0_0_1px_rgba(255,255,255,0.04),0_0_28px_rgba(50,213,131,0.18)] rounded-2xl bg-[#32d583]/14.000000000000002 border-[#32d583]/28.000000000000004 border-1 border-solid flex justify-center items-center">
                      <Shield className="size-5 text-[#6cf0ac]" />
                    </div>
                    <div>
                      <div className="flex items-center gap-3">
                        <div className="font-semibold text-neutral-50 text-lg leading-7 tracking-[-0.32px]">
                          Hallucination Prevention Active
                        </div>
                        <div className="font-medium rounded-full bg-[#32d583]/10 text-[#8fe8b8] text-[11px] border-[#32d583]/22 border-1 border-solid flex px-3 py-1 items-center gap-2">
                          <span className="size-2 shadow-[0_0_0_0_rgba(50,213,131,0.45)] animate-pulse rounded-full bg-[#32d583]" />
                          Live verification
                        </div>
                      </div>
                      <div className="text-[#a1a1a1] text-sm leading-5 mt-1">
                        Only verified claims are treated as facts — every
                        statement is traceable to source evidence
                      </div>
                    </div>
                  </div>
                  <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] rounded-full bg-neutral-800/60 text-[#a1a1a1] text-sm leading-5 border-white/10 border-1 border-solid hidden px-4 py-2">
                    <Search className="size-4" />
                    <span>Search evidence</span>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-[380px_minmax(0,1fr)_360px] p-6 flex-1 gap-6">
                <section className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_18px_50px_rgba(0,0,0,0.28)] rounded-3xl bg-white/5 border-[#4c8dff]/16 border-1 border-solid p-6">
                  <div className="flex flex-col gap-6 h-full">
                    <div className="space-y-2">
                      <div className="font-medium text-[#83b0ff] text-sm leading-5 flex items-center gap-2">
                        <FileText className="size-4" />
                        Generated Statement
                      </div>
                      <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_0_0_1px_rgba(76,141,255,0.06)] rounded-2xl bg-[#4c8dff]/12 border-[#4c8dff]/18 border-1 border-solid p-5">
                        <div className="italic font-semibold text-neutral-50 text-[28px] leading-8 tracking-[-0.48px] border-[#4c8dff] border-t-0 border-r-0 border-b-0 border-l-4 border-solid pl-4">
                          “Built AI-powered analytics platform reducing review
                          time by 45%”
                        </div>
                      </div>
                    </div>
                    <div className="inline-flex shadow-[0_0_24px_rgba(50,213,131,0.08)] font-semibold rounded-full bg-[#32d583]/10 text-[#6cf0ac] text-xs leading-4 border-[#32d583]/22 border-1 border-solid px-4 py-2 items-center gap-2 w-fit">
                      <CheckCircle2 className="size-4" />
                      Verified
                    </div>
                    <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] rounded-2xl bg-neutral-800/40 border-white/10 border-1 border-solid p-5">
                      <div className="flex justify-between items-center">
                        <div className="font-medium text-neutral-50 text-sm leading-5">
                          Confidence Score
                        </div>
                        <div className="font-semibold text-[#6cf0ac] text-sm leading-5">
                          97%
                        </div>
                      </div>
                      <div className="rounded-full bg-neutral-950/70 mt-4 h-3">
                        <div className="w-[97%] bg-[linear-gradient(90deg,#32d583,#6cf0ac)] shadow-[0_0_18px_rgba(50,213,131,0.35)] rounded-full h-3" />
                      </div>
                      <div className="text-[#a1a1a1] text-xs leading-5 mt-3">
                        High confidence verified through multiple evidence
                        sources
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div className="font-medium text-neutral-50 text-sm leading-5">
                        Used In
                      </div>
                      <div className="space-y-2">
                        <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] rounded-2xl bg-neutral-800/35 text-[#a1a1a1] text-sm leading-5 border-white/10 border-1 border-solid flex px-4 py-3 items-center gap-3">
                          <FileText className="size-4 text-[#4c8dff]" />
                          Resume (OpenAI Application)
                        </div>
                        <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] rounded-2xl bg-neutral-800/35 text-[#a1a1a1] text-sm leading-5 border-white/10 border-1 border-solid flex px-4 py-3 items-center gap-3">
                          <FilePenLine className="size-4 text-[#4c8dff]" />
                          Cover Letter Draft
                        </div>
                        <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] rounded-2xl bg-neutral-800/35 text-[#a1a1a1] text-sm leading-5 border-white/10 border-1 border-solid flex px-4 py-3 items-center gap-3">
                          <MessageSquareText className="size-4 text-[#4c8dff]" />
                          Interview Answer #14
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
                <section className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_18px_50px_rgba(0,0,0,0.24)] rounded-3xl bg-white/4 border-[#4c8dff]/14.000000000000002 border-1 border-solid p-6">
                  <div className="flex flex-col gap-6 h-full">
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-semibold text-neutral-50 text-lg leading-7 tracking-[-0.32px]">
                          Evidence Chain
                        </div>
                        <div className="text-[#a1a1a1] text-sm leading-5 mt-1">
                          Chronological trace from source documents to generated
                          claim
                        </div>
                      </div>
                      <div className="font-medium rounded-full bg-[#4c8dff]/8 text-[#83b0ff] text-xs leading-4 border-[#4c8dff]/18 border-1 border-solid px-3 py-1">
                        4 linked sources
                      </div>
                    </div>
                    <div className="relative pl-8 flex-1">
                      <div className="h-[calc(100%-2rem)] shadow-[0_0_18px_rgba(76,141,255,0.35)] bg-[#4c8dff]/95 absolute left-4 top-4 w-px" />
                      <div className="space-y-5">
                        <div className="relative shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_0_0_1px_rgba(50,213,131,0.04)] rounded-3xl bg-white/5 border-[#32d583]/18 border-1 border-solid p-5">
                          <div className="size-4 shadow-[0_0_0_6px_rgba(50,213,131,0.12),0_0_24px_rgba(50,213,131,0.35)] rounded-full bg-[#32d583] absolute -left-6 top-6" />
                          <div className="flex justify-between items-start gap-4">
                            <div className="flex items-start gap-3">
                              <FileText className="size-5 text-[#4c8dff] mt-0.5" />
                              <div>
                                <div className="font-semibold text-neutral-50 text-sm leading-5">
                                  Resume Entry
                                </div>
                                <div className="text-[#a1a1a1] text-sm leading-5 mt-1">{`Senior Analytics & Technology Consultant`}</div>
                              </div>
                            </div>
                            <div className="text-[#a1a1a1] text-xs leading-4">
                              2023-08-15
                            </div>
                          </div>
                          <div className="inline-flex font-semibold rounded-full bg-[#32d583]/10 text-[#6cf0ac] text-[11px] border-[#32d583]/22 border-1 border-solid mt-2 px-3 py-1 items-center gap-2">
                            <CheckCircle2 className="size-3.5" />
                            Verified
                          </div>
                        </div>
                        <div className="relative shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] rounded-3xl bg-white/5 border-[#7e5fff]/16 border-1 border-solid p-5">
                          <div className="size-4 shadow-[0_0_0_6px_rgba(50,213,131,0.12),0_0_24px_rgba(50,213,131,0.28)] rounded-full bg-[#32d583] absolute -left-6 top-6" />
                          <div className="flex justify-between items-start gap-4">
                            <div className="flex items-start gap-3">
                              <NotebookPen className="size-5 text-[#7e5fff] mt-0.5" />
                              <div>
                                <div className="font-semibold text-neutral-50 text-sm leading-5">
                                  Project Notes
                                </div>
                                <div className="text-[#a1a1a1] text-sm leading-5 mt-1">
                                  Analytics platform review reduction initiative
                                </div>
                              </div>
                            </div>
                            <div className="text-[#a1a1a1] text-xs leading-4">
                              2023-07-22
                            </div>
                          </div>
                          <div className="inline-flex font-semibold rounded-full bg-[#32d583]/10 text-[#6cf0ac] text-[11px] border-[#32d583]/22 border-1 border-solid mt-2 px-3 py-1 items-center gap-2">
                            <CheckCircle2 className="size-3.5" />
                            Verified
                          </div>
                        </div>
                        <div className="relative shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] rounded-3xl bg-white/5 border-[#32d583]/16 border-1 border-solid p-5">
                          <div className="size-4 shadow-[0_0_0_6px_rgba(50,213,131,0.12),0_0_24px_rgba(50,213,131,0.28)] rounded-full bg-[#32d583] absolute -left-6 top-6" />
                          <div className="flex justify-between items-start gap-4">
                            <div className="flex items-start gap-3">
                              <Code2 className="size-5 text-[#32d583] mt-0.5" />
                              <div>
                                <div className="font-semibold text-neutral-50 text-sm leading-5">
                                  GitHub Repository
                                </div>
                                <div className="text-[#a1a1a1] text-sm leading-5 mt-1">
                                  Commit hash: a8f3c2d · analytics-automation
                                </div>
                              </div>
                            </div>
                            <div className="text-[#a1a1a1] text-xs leading-4">
                              2023-06-10
                            </div>
                          </div>
                          <div className="inline-flex font-semibold rounded-full bg-[#32d583]/10 text-[#6cf0ac] text-[11px] border-[#32d583]/22 border-1 border-solid mt-2 px-3 py-1 items-center gap-2">
                            <CheckCircle2 className="size-3.5" />
                            Verified
                          </div>
                        </div>
                        <div className="relative shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] rounded-3xl bg-white/5 border-[#ffb547]/16 border-1 border-solid p-5">
                          <div className="size-4 shadow-[0_0_0_6px_rgba(50,213,131,0.12),0_0_24px_rgba(50,213,131,0.28)] rounded-full bg-[#32d583] absolute -left-6 top-6" />
                          <div className="flex justify-between items-start gap-4">
                            <div className="flex items-start gap-3">
                              <Trophy className="size-5 text-[#ffb547] mt-0.5" />
                              <div>
                                <div className="font-semibold text-neutral-50 text-sm leading-5">
                                  Application Outcome
                                </div>
                                <div className="text-[#a1a1a1] text-sm leading-5 mt-1">
                                  Interview Secured
                                </div>
                              </div>
                            </div>
                            <div className="text-[#a1a1a1] text-xs leading-4">
                              2023-09-01
                            </div>
                          </div>
                          <div className="inline-flex font-medium rounded-full bg-[#32d583]/10 text-[#6cf0ac] text-xs leading-4 border-[#32d583]/22 border-1 border-solid mt-4 px-3 py-1 items-center gap-2">
                            <CheckCircle2 className="size-3.5" />
                            Verified
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
                <section className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_18px_50px_rgba(0,0,0,0.24)] rounded-3xl bg-white/4 border-[#4c8dff]/14.000000000000002 border-1 border-solid p-6">
                  <div className="flex flex-col gap-5 h-full">
                    <div>
                      <div className="font-semibold text-neutral-50 text-lg leading-7 tracking-[-0.32px]">
                        Source Documents
                      </div>
                      <div className="text-[#a1a1a1] text-sm leading-5 mt-1">
                        Inspect the evidence behind each generated claim
                      </div>
                    </div>
                    <div className="space-y-4">
                      <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] rounded-3xl bg-white/5 border-[#32d583]/16 border-1 border-solid p-5">
                        <div className="flex justify-between items-start gap-4">
                          <div>
                            <div className="font-semibold text-neutral-50 text-sm leading-5">
                              Project Documentation
                            </div>
                            <div className="inline-flex font-semibold rounded-full bg-[#32d583]/10 text-[#6cf0ac] text-[11px] border-[#32d583]/22 border-1 border-solid mt-2 px-3 py-1 items-center gap-2">
                              <CheckCircle2 className="size-3.5" />
                              Verified
                            </div>
                          </div>
                          <div className="text-[#a1a1a1] text-xs leading-4">
                            2023-07-22
                          </div>
                        </div>
                        <div className="space-y-2 mt-5">
                          <div className="text-[#a1a1a1] text-xs leading-4 flex justify-between items-center">
                            <span>Confidence</span>
                            <span>97%</span>
                          </div>
                          <div className="rounded-full bg-neutral-950/70 h-2">
                            <div className="w-[97%] bg-[linear-gradient(90deg,#32d583,#6cf0ac)] rounded-full h-2" />
                          </div>
                        </div>
                        <div className="font-medium text-[#83b0ff] text-sm leading-5 mt-4">
                          View Source
                        </div>
                      </div>
                      <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] rounded-3xl bg-white/5 border-[#4c8dff]/16 border-1 border-solid p-5">
                        <div className="flex justify-between items-start gap-4">
                          <div>
                            <div className="font-semibold text-neutral-50 text-sm leading-5">
                              Meeting Notes
                            </div>
                            <div className="inline-flex font-semibold rounded-full bg-[#4c8dff]/10 text-[#83b0ff] text-[11px] border-[#4c8dff]/22 border-1 border-solid mt-2 px-3 py-1 items-center gap-2">
                              <BadgeInfo className="size-3.5" />
                              Strong Inference
                            </div>
                          </div>
                          <div className="text-[#a1a1a1] text-xs leading-4">
                            2023-07-15
                          </div>
                        </div>
                        <div className="space-y-2 mt-5">
                          <div className="text-[#a1a1a1] text-xs leading-4 flex justify-between items-center">
                            <span>Confidence</span>
                            <span>84%</span>
                          </div>
                          <div className="rounded-full bg-neutral-950/70 h-2">
                            <div className="w-[84%] bg-[linear-gradient(90deg,#4c8dff,#7e5fff)] rounded-full h-2" />
                          </div>
                        </div>
                        <div className="font-medium text-[#83b0ff] text-sm leading-5 mt-4">
                          View Source
                        </div>
                      </div>
                      <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] rounded-3xl bg-white/5 border-[#32d583]/16 border-1 border-solid p-5">
                        <div className="flex justify-between items-start gap-4">
                          <div>
                            <div className="font-semibold text-neutral-50 text-sm leading-5">
                              GitHub Commits
                            </div>
                            <div className="inline-flex font-semibold rounded-full bg-[#32d583]/10 text-[#6cf0ac] text-[11px] border-[#32d583]/22 border-1 border-solid mt-2 px-3 py-1 items-center gap-2">
                              <CheckCircle2 className="size-3.5" />
                              Verified
                            </div>
                          </div>
                          <div className="text-[#a1a1a1] text-xs leading-4">
                            2023-06-10
                          </div>
                        </div>
                        <div className="space-y-2 mt-5">
                          <div className="text-[#a1a1a1] text-xs leading-4 flex justify-between items-center">
                            <span>Confidence</span>
                            <span>99%</span>
                          </div>
                          <div className="rounded-full bg-neutral-950/70 h-2">
                            <div className="w-[99%] bg-[linear-gradient(90deg,#32d583,#6cf0ac)] rounded-full h-2" />
                          </div>
                        </div>
                        <div className="font-medium text-[#83b0ff] text-sm leading-5 mt-4">
                          View Source
                        </div>
                      </div>
                      <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] rounded-3xl bg-white/5 border-[#32d583]/16 border-1 border-solid p-5">
                        <div className="flex justify-between items-start gap-4">
                          <div>
                            <div className="font-semibold text-neutral-50 text-sm leading-5">
                              Interview Responses
                            </div>
                            <div className="inline-flex font-semibold rounded-full bg-[#32d583]/10 text-[#6cf0ac] text-[11px] border-[#32d583]/22 border-1 border-solid mt-2 px-3 py-1 items-center gap-2">
                              <CheckCircle2 className="size-3.5" />
                              Verified
                            </div>
                          </div>
                          <div className="text-[#a1a1a1] text-xs leading-4">
                            2023-09-01
                          </div>
                        </div>
                        <div className="space-y-2 mt-5">
                          <div className="text-[#a1a1a1] text-xs leading-4 flex justify-between items-center">
                            <span>Confidence</span>
                            <span>95%</span>
                          </div>
                          <div className="rounded-full bg-neutral-950/70 h-2">
                            <div className="w-[95%] bg-[linear-gradient(90deg,#32d583,#6cf0ac)] rounded-full h-2" />
                          </div>
                        </div>
                        <div className="font-medium text-[#83b0ff] text-sm leading-5 mt-4">
                          View Source
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
