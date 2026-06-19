import { useEffect } from "react";
import {
  Brain,
  FileText,
  GitBranch,
  Kanban,
  LayoutDashboard,
  Lightbulb,
  Mail,
  MessageSquare,
  RefreshCw,
  ScanSearch,
  Settings,
  Sparkles,
  Star,
  TrendingUp,
  Zap,
} from "lucide-react";
import { ChartContainer, ChartTooltip } from "@/components/ui/chart";
import {
  Area,
  AreaChart as RechartsAreaChart,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts";

export default function App() {
  return (
    <div>
      <div className="bg-neutral-950 text-neutral-50 w-full h-fit h-fit min-h-screen w-screen min-w-screen max-w-screen overflow-visible">
        <div className="relative min-h-screen bg-[#4c8dff]/16 p-12 w-full overflow-hidden">
          <div className="shadow-[0_24px_80px_rgba(0,0,0,0.45),inset_0_1px_0_rgba(255,255,255,0.06)] backdrop-blur-3xl rounded-3xl bg-white/3 border-white/10 border-1 border-solid flex mx-auto w-468 h-264 overflow-hidden">
            <div className="flex-shrink-0 bg-white/4 border-white/10 border-t-0 border-r-1 border-b-0 border-l-0 border-solid flex flex-col w-60">
              <div className="border-white/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid p-6">
                <div className="flex items-center gap-3">
                  <div className="size-10 bg-[linear-gradient(135deg,#4c8dff,#7e5fff)] shadow-[0_10px_24px_rgba(76,141,255,0.28)] rounded-2xl flex justify-center items-center">
                    <Brain className="size-5 text-white" />
                  </div>
                  <div>
                    <div className="font-semibold text-neutral-50 text-[13px] tracking-tight">
                      ACOS
                    </div>
                    <div className="font-medium text-[#a1a1a1] text-[10px]">
                      Career OS
                    </div>
                  </div>
                </div>
              </div>
              <div className="overflow-y-auto flex p-3 flex-col flex-1 gap-1">
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <LayoutDashboard className="size-4" />
                  <span className="font-medium text-[13px]">Dashboard</span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <GitBranch className="size-4" />
                  <span className="font-medium text-[13px]">
                    Knowledge Graph
                  </span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <FileText className="size-4" />
                  <span className="font-medium text-[13px]">Resumes</span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <Mail className="size-4" />
                  <span className="font-medium text-[13px]">Cover Letters</span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <ScanSearch className="size-4" />
                  <span className="font-medium text-[13px]">ATS Analysis</span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <MessageSquare className="size-4" />
                  <span className="font-medium text-[13px]">
                    Interview Prep
                  </span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <Kanban className="size-4" />
                  <span className="font-medium text-[13px]">
                    Applications CRM
                  </span>
                </div>
                <div className="cursor-pointer shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] rounded-xl bg-neutral-200/15 text-neutral-200 flex px-3.5 items-center gap-3 h-11">
                  <Brain className="size-4 text-neutral-200" />
                  <span className="font-semibold text-neutral-50 text-[13px]">
                    Learning Engine
                  </span>
                </div>
                <div className="cursor-pointer transition-colors rounded-xl text-[#a1a1a1] flex px-3.5 items-center gap-3 h-11">
                  <Settings className="size-4" />
                  <span className="font-medium text-[13px]">Settings</span>
                </div>
              </div>
              <div className="border-white/10 border-t-1 border-r-0 border-b-0 border-l-0 border-solid p-4">
                <div className="shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] rounded-xl bg-neutral-900 border-white/10 border-1 border-solid flex p-3 items-center gap-3">
                  <div className="size-8 bg-[linear-gradient(135deg,#4c8dff,#7e5fff)] font-bold rounded-full text-white text-[11px] flex justify-center items-center">
                    SC
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-semibold text-neutral-50 text-xs leading-4">
                      Senior Consultant
                    </div>
                    <div className="truncate text-[#a1a1a1] text-[10px]">{`Analytics & Tech`}</div>
                  </div>
                </div>
              </div>
            </div>
            <div className="min-w-0 flex flex-col flex-1 overflow-hidden">
              <div className="flex-shrink-0 border-white/10 border-t-0 border-r-0 border-b-1 border-l-0 border-solid flex px-9 py-6 justify-between items-center">
                <div className="flex items-center gap-4">
                  <div className="size-12 shadow-[0_0_0_1px_rgba(255,255,255,0.02),0_12px_30px_rgba(76,141,255,0.12)] rounded-2xl bg-neutral-200/10 border-neutral-200/25 border-1 border-solid flex justify-center items-center">
                    <Brain className="size-5 text-neutral-200" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h1 className="font-bold text-neutral-50 text-[28px] tracking-[-0.64px]">
                        Learning Engine
                      </h1>
                      <Sparkles className="size-5 text-[#7e5fff]" />
                    </div>
                    <p className="text-[#a1a1a1] text-[13px] mt-1">
                      The system continuously improves after every application
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="rounded-xl bg-[#32d583]/10 border-[#32d583]/20 border-1 border-solid flex px-4 py-2 items-center gap-2">
                    <div className="size-2 shadow-[0_0_10px_rgba(50,213,131,0.9)] rounded-full bg-[#32d583]" />
                    <span className="font-semibold text-[#32d583] text-xs leading-4">
                      Last Updated: 2h ago
                    </span>
                  </div>
                </div>
              </div>
              <div className="overflow-y-auto flex p-8 flex-col flex-1 gap-6">
                <div className="grid grid-cols-4 gap-4">
                  <div className="shadow-[0_10px_30px_rgba(0,0,0,0.18),inset_0_1px_0_rgba(255,255,255,0.04)] rounded-[22px] bg-neutral-900 border-white/10 border-1 border-solid flex p-6 flex-col gap-3">
                    <div className="flex justify-between items-center">
                      <span className="font-medium text-neutral-200 text-[11px]">
                        Interview Rate
                      </span>
                      <div className="rounded-full bg-[#32d583]/10 border-[#32d583]/20 border-1 border-solid flex px-2 py-1 items-center gap-1">
                        <TrendingUp className="size-3 text-[#32d583]" />
                        <span className="font-bold text-[#32d583] text-[10px]">
                          +3.2%
                        </span>
                      </div>
                    </div>
                    <div className="font-bold text-neutral-50 text-[38px] tracking-[-0.96px]">
                      22.4%
                    </div>
                    <div className="text-[#a1a1a1] text-[11px]">
                      vs 19.2% last cycle
                    </div>
                  </div>
                  <div className="shadow-[0_10px_30px_rgba(0,0,0,0.18),inset_0_1px_0_rgba(255,255,255,0.04)] rounded-[22px] bg-neutral-900 border-white/10 border-1 border-solid flex p-6 flex-col gap-3">
                    <div className="flex justify-between items-center">
                      <span className="font-medium uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.88px]">
                        Avg ATS Score
                      </span>
                      <div className="rounded-full bg-[#32d583]/10 border-[#32d583]/20 border-1 border-solid flex px-2 py-1 items-center gap-1">
                        <TrendingUp className="size-3 text-[#32d583]" />
                        <span className="font-bold text-[#32d583] text-[10px]">
                          +6pts
                        </span>
                      </div>
                    </div>
                    <div className="font-bold text-neutral-50 text-[38px] tracking-[-0.96px]">
                      84%
                    </div>
                    <div className="text-[#a1a1a1] text-[11px]">
                      vs 78% last cycle
                    </div>
                  </div>
                  <div className="shadow-[0_10px_30px_rgba(0,0,0,0.18),inset_0_1px_0_rgba(255,255,255,0.04)] rounded-[22px] bg-neutral-900 border-white/10 border-1 border-solid flex p-6 flex-col gap-3">
                    <div className="flex justify-between items-center">
                      <span className="font-medium uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.88px]">
                        Resume Effectiveness
                      </span>
                      <div className="rounded-full bg-[#32d583]/10 border-[#32d583]/20 border-1 border-solid flex px-2 py-1 items-center gap-1">
                        <TrendingUp className="size-3 text-[#32d583]" />
                        <span className="font-bold text-[#32d583] text-[10px]">
                          +4%
                        </span>
                      </div>
                    </div>
                    <div className="font-bold text-neutral-50 text-[38px] tracking-[-0.96px]">
                      91%
                    </div>
                    <div className="text-[#a1a1a1] text-[11px]">
                      vs 87% last cycle
                    </div>
                  </div>
                  <div className="shadow-[0_10px_30px_rgba(0,0,0,0.18),inset_0_1px_0_rgba(255,255,255,0.04)] rounded-[22px] bg-[#ffb547]/10 border-[#ffb547]/20 border-1 border-solid flex p-6 flex-col gap-3">
                    <div className="flex justify-between items-center">
                      <span className="font-medium uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.88px]">
                        Applications This Cycle
                      </span>
                      <div className="rounded-full bg-[#ffb547]/10 border-[#ffb547]/20 border-1 border-solid flex px-2 py-1 items-center gap-1">
                        <Zap className="size-3 text-[#ffb547]" />
                        <span className="font-bold text-[#ffb547] text-[10px]">
                          In Progress
                        </span>
                      </div>
                    </div>
                    <div className="flex items-end gap-2">
                      <div className="font-bold text-neutral-50 text-[38px] tracking-[-0.96px]">
                        2
                      </div>
                      <div className="font-semibold text-[#a1a1a1] text-lg leading-7 mb-1.5">
                        / 5
                      </div>
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <div className="rounded-full bg-white/8 w-full h-1.5">
                        <div className="w-[40%] bg-[linear-gradient(90deg,#ffb547,#ff8c47)] shadow-[0_0_8px_rgba(255,181,71,0.45)] rounded-full h-full" />
                      </div>
                      <div className="text-[#a1a1a1] text-[11px]">
                        3 more until next refresh
                      </div>
                    </div>
                  </div>
                </div>
                <div className="min-h-0 flex flex-1 gap-6">
                  <div className="min-w-0 flex-[6] flex flex-col gap-4">
                    <div className="shadow-[0_14px_40px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.05)] rounded-3xl bg-neutral-900 border-white/10 border-1 border-solid flex p-6 flex-col flex-1 gap-5">
                      <div className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <TrendingUp className="size-4 text-neutral-200" />
                          <h2 className="font-semibold text-neutral-50 text-base leading-6 tracking-tight">
                            Career Performance Trends
                          </h2>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="rounded-full bg-neutral-200/10 border-neutral-200/20 border-1 border-solid flex px-3 py-1 items-center gap-1.5">
                            <div className="size-2 rounded-full bg-neutral-200" />
                            <span className="font-medium text-neutral-200 text-[11px]">
                              Interview Rate
                            </span>
                          </div>
                          <div className="rounded-full bg-[#7e5fff]/10 border-[#7e5fff]/20 border-1 border-solid flex px-3 py-1 items-center gap-1.5">
                            <div className="size-2 rounded-full bg-[#7e5fff]" />
                            <span className="font-medium text-[#7e5fff] text-[11px]">
                              ATS Score
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="min-h-0 flex flex-col flex-1 gap-4">
                        <div className="min-h-0 rounded-2xl bg-neutral-950/20 border-white/10 border-1 border-solid flex p-4 flex-col flex-1 gap-2">
                          <div className="flex justify-between items-center">
                            <span className="font-medium text-[#a1a1a1] text-[11px]">
                              Interview Rate Over Time
                            </span>
                            <span className="font-semibold text-neutral-200 text-[11px]">
                              ↑ Upward Trend
                            </span>
                          </div>
                          <div className="min-h-0 flex-1">
                            <ChartContainer
                              config={{
                                interviewRate: {
                                  label: "Interview Rate",
                                  color: "oklch(0.488 0.243 264.376)",
                                },
                              }}
                              className="w-full h-full"
                            >
                              <RechartsAreaChart
                                data={[
                                  { month: "Jan", value: 12 },
                                  { month: "Feb", value: 13.5 },
                                  { month: "Mar", value: 14 },
                                  { month: "Apr", value: 13 },
                                  { month: "May", value: 15.5 },
                                  { month: "Jun", value: 16 },
                                  { month: "Jul", value: 17 },
                                  { month: "Aug", value: 18.5 },
                                  { month: "Sep", value: 19 },
                                  { month: "Oct", value: 20 },
                                  { month: "Nov", value: 21.2 },
                                  { month: "Dec", value: 22.4 },
                                ]}
                                margin={{
                                  top: 8,
                                  right: 12,
                                  left: 0,
                                  bottom: 0,
                                }}
                              >
                                <defs>
                                  <linearGradient
                                    id="blueGrad"
                                    x1="0"
                                    y1="0"
                                    x2="0"
                                    y2="1"
                                  >
                                    <stop
                                      offset="5%"
                                      stopColor="#4c8dff"
                                      stopOpacity={0.34}
                                    />
                                    <stop
                                      offset="95%"
                                      stopColor="#4c8dff"
                                      stopOpacity={0.02}
                                    />
                                  </linearGradient>
                                </defs>
                                <CartesianGrid
                                  strokeDasharray="3 3"
                                  stroke="rgba(255,255,255,0.06)"
                                  vertical={false}
                                />
                                <XAxis
                                  dataKey="month"
                                  tick={{ fill: "#7e8794", fontSize: 10 }}
                                  axisLine={false}
                                  tickLine={false}
                                />
                                <YAxis
                                  tick={{ fill: "#7e8794", fontSize: 10 }}
                                  axisLine={false}
                                  tickLine={false}
                                  width={32}
                                />
                                <ChartTooltip />
                                <Area
                                  type="monotone"
                                  dataKey="value"
                                  stroke="#4c8dff"
                                  strokeWidth={2.5}
                                  fill="url(#blueGrad)"
                                  dot={false}
                                />
                              </RechartsAreaChart>
                            </ChartContainer>
                          </div>
                        </div>
                        <div className="bg-white/6 w-full h-px" />
                        <div className="min-h-0 rounded-2xl bg-neutral-950/20 border-white/10 border-1 border-solid flex p-4 flex-col flex-1 gap-2">
                          <div className="flex justify-between items-center">
                            <span className="font-medium text-[#a1a1a1] text-[11px]">
                              ATS Scores Over Time
                            </span>
                            <span className="font-semibold text-[#7e5fff] text-[11px]">
                              ↑ Upward Trend
                            </span>
                          </div>
                          <div className="min-h-0 flex-1">
                            <ChartContainer
                              config={{
                                atsScore: {
                                  label: "ATS Score",
                                  color: "oklch(0.627 0.265 303.9)",
                                },
                              }}
                              className="w-full h-full"
                            >
                              <RechartsAreaChart
                                data={[
                                  { month: "Jan", value: 62 },
                                  { month: "Feb", value: 65 },
                                  { month: "Mar", value: 67 },
                                  { month: "Apr", value: 66 },
                                  { month: "May", value: 70 },
                                  { month: "Jun", value: 72 },
                                  { month: "Jul", value: 74 },
                                  { month: "Aug", value: 76 },
                                  { month: "Sep", value: 78 },
                                  { month: "Oct", value: 80 },
                                  { month: "Nov", value: 82 },
                                  { month: "Dec", value: 84 },
                                ]}
                                margin={{
                                  top: 8,
                                  right: 12,
                                  left: 0,
                                  bottom: 0,
                                }}
                              >
                                <defs>
                                  <linearGradient
                                    id="purpleGrad"
                                    x1="0"
                                    y1="0"
                                    x2="0"
                                    y2="1"
                                  >
                                    <stop
                                      offset="5%"
                                      stopColor="#7e5fff"
                                      stopOpacity={0.34}
                                    />
                                    <stop
                                      offset="95%"
                                      stopColor="#7e5fff"
                                      stopOpacity={0.02}
                                    />
                                  </linearGradient>
                                </defs>
                                <CartesianGrid
                                  strokeDasharray="3 3"
                                  stroke="rgba(255,255,255,0.06)"
                                  vertical={false}
                                />
                                <XAxis
                                  dataKey="month"
                                  tick={{ fill: "#7e8794", fontSize: 10 }}
                                  axisLine={false}
                                  tickLine={false}
                                />
                                <YAxis
                                  tick={{ fill: "#7e8794", fontSize: 10 }}
                                  axisLine={false}
                                  tickLine={false}
                                  width={32}
                                />
                                <ChartTooltip />
                                <Area
                                  type="monotone"
                                  dataKey="value"
                                  stroke="#7e5fff"
                                  strokeWidth={2.5}
                                  fill="url(#purpleGrad)"
                                  dot={false}
                                />
                              </RechartsAreaChart>
                            </ChartContainer>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="min-w-0 flex-[4] flex flex-col gap-4">
                    <div className="shadow-[0_14px_40px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.05)] rounded-3xl bg-neutral-900 border-white/10 border-1 border-solid flex p-6 flex-col gap-4">
                      <div className="flex items-center gap-2">
                        <Star className="size-4 text-[#ffb547]" />
                        <h2 className="font-semibold text-neutral-50 text-[15px] tracking-tight">
                          Top Performing Experiences
                        </h2>
                      </div>
                      <div className="flex flex-col gap-4">
                        <div className="flex items-center gap-3">
                          <div className="size-6 font-bold rounded-lg bg-neutral-200/15 text-neutral-200 text-[11px] border-neutral-200/25 border-1 border-solid flex justify-center items-center">
                            1
                          </div>
                          <div className="flex flex-col flex-1 gap-1">
                            <div className="flex justify-between items-center">
                              <span className="font-medium text-neutral-50 text-[13px]">
                                Product Development
                              </span>
                              <span className="font-bold text-neutral-200 text-xs leading-4">
                                94
                              </span>
                            </div>
                            <div className="rounded-full bg-white/6 w-full h-1.5">
                              <div
                                className="bg-[linear-gradient(90deg,#4c8dff,#7e5fff)] shadow-[0_0_8px_rgba(76,141,255,0.45)] rounded-full h-full"
                                style={{ width: "94%" }}
                              />
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="size-6 font-bold rounded-lg bg-[#7e5fff]/15 text-[#7e5fff] text-[11px] border-[#7e5fff]/25 border-1 border-solid flex justify-center items-center">
                            2
                          </div>
                          <div className="flex flex-col flex-1 gap-1">
                            <div className="flex justify-between items-center">
                              <span className="font-medium text-neutral-50 text-[13px]">
                                AI Automation
                              </span>
                              <span className="font-bold text-[#7e5fff] text-xs leading-4">
                                89
                              </span>
                            </div>
                            <div className="rounded-full bg-white/6 w-full h-1.5">
                              <div
                                className="bg-[linear-gradient(90deg,#7e5fff,#a07fff)] shadow-[0_0_8px_rgba(126,95,255,0.45)] rounded-full h-full"
                                style={{ width: "89%" }}
                              />
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="size-6 font-bold rounded-lg bg-neutral-200/15 text-neutral-200 text-[11px] border-neutral-200/25 border-1 border-solid flex justify-center items-center">
                            3
                          </div>
                          <div className="flex flex-col flex-1 gap-1">
                            <div className="flex justify-between items-center">
                              <span className="font-medium text-neutral-50 text-[13px]">
                                Data Analytics
                              </span>
                              <span className="font-bold text-neutral-200 text-xs leading-4">
                                82
                              </span>
                            </div>
                            <div className="rounded-full bg-white/6 w-full h-1.5">
                              <div
                                className="bg-[linear-gradient(90deg,#4c8dff,#6ba8ff)] shadow-[0_0_8px_rgba(76,141,255,0.35)] rounded-full h-full"
                                style={{ width: "82%" }}
                              />
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="size-6 font-bold rounded-lg bg-white/6 text-[#a1a1a1] text-[11px] border-white/10 border-1 border-solid flex justify-center items-center">
                            4
                          </div>
                          <div className="flex flex-col flex-1 gap-1">
                            <div className="flex justify-between items-center">
                              <span className="font-medium text-[#a1a1a1] text-[13px]">
                                Financial Investigations
                              </span>
                              <span className="font-bold text-[#a1a1a1] text-xs leading-4">
                                76
                              </span>
                            </div>
                            <div className="rounded-full bg-white/6 w-full h-1.5">
                              <div
                                className="rounded-full bg-white/20 h-full"
                                style={{ width: "76%" }}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="shadow-[0_14px_40px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.05)] rounded-3xl bg-neutral-900 border-white/10 border-1 border-solid flex p-6 flex-col gap-4">
                      <div className="flex items-center gap-2">
                        <Lightbulb className="size-4 text-[#ffb547]" />
                        <h2 className="font-semibold text-neutral-50 text-[15px] tracking-tight">
                          Recent Learning Insights
                        </h2>
                      </div>
                      <div className="flex flex-col gap-3">
                        <div className="rounded-xl bg-[#32d583]/5 border-[#32d583] border-t-0 border-r-0 border-b-0 border-l-2 border-solid flex p-3 items-start gap-3">
                          <Lightbulb className="size-4 flex-shrink-0 text-[#32d583] mt-0.5" />
                          <div>
                            <p className="leading-relaxed font-medium text-neutral-50 text-xs leading-4">
                              Product leadership stories increase interview rate
                              by
                              <span className="font-bold text-[#32d583]">
                                18%
                              </span>
                            </p>
                            <span className="text-[#a1a1a1] text-[10px]">
                              Verified · High Confidence
                            </span>
                          </div>
                        </div>
                        <div className="rounded-xl bg-neutral-200/5 border-neutral-200 border-t-0 border-r-0 border-b-0 border-l-2 border-solid flex p-3 items-start gap-3">
                          <Lightbulb className="size-4 flex-shrink-0 text-neutral-200 mt-0.5" />
                          <div>
                            <p className="leading-relaxed font-medium text-neutral-50 text-xs leading-4">
                              AI projects outperform analytics-only projects in
                              <span className="font-bold text-neutral-200">
                                tech roles
                              </span>
                            </p>
                            <span className="text-[#a1a1a1] text-[10px]">
                              Strong Inference · Medium Confidence
                            </span>
                          </div>
                        </div>
                        <div className="rounded-xl bg-[#ffb547]/5 border-[#ffb547] border-t-0 border-r-0 border-b-0 border-l-2 border-solid flex p-3 items-start gap-3">
                          <Lightbulb className="size-4 flex-shrink-0 text-[#ffb547] mt-0.5" />
                          <div>
                            <p className="leading-relaxed font-medium text-neutral-50 text-xs leading-4">
                              Compliance experience highly valued in
                              <span className="font-bold text-[#ffb547]">
                                fintech roles
                              </span>
                            </p>
                            <span className="text-[#a1a1a1] text-[10px]">
                              Strong Inference · Medium Confidence
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="shadow-[0_14px_40px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.05)] rounded-[28px] bg-[#ffb547]/12 border-[#ffb547]/20 border-1 border-solid flex p-6 flex-col gap-4">
                      <div className="flex items-center gap-2">
                        <RefreshCw className="size-4 text-[#ffb547]" />
                        <h2 className="font-semibold text-neutral-50 text-[15px] tracking-tight">
                          Next Optimization Cycle
                        </h2>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="relative size-22 flex-shrink-0">
                          <svg viewBox="0 0 88 88" className="w-full h-full">
                            <circle
                              cx="44"
                              cy="44"
                              r="36"
                              fill="none"
                              stroke="rgba(255,255,255,0.08)"
                              strokeWidth="7"
                            />
                            <circle
                              cx="44"
                              cy="44"
                              r="36"
                              fill="none"
                              stroke="#ffb547"
                              strokeWidth="7"
                              strokeLinecap="round"
                              strokeDasharray="226.2"
                              strokeDashoffset="135.7"
                              className="drop-shadow-[0_0_10px_rgba(255,181,71,0.35)]"
                            />
                          </svg>
                          <div className="flex absolute inset-0 flex-col justify-center items-center">
                            <span className="font-bold text-neutral-50 text-lg leading-7 tracking-tight">
                              2/5
                            </span>
                            <span className="font-medium text-[#a1a1a1] text-[9px]">
                              apps
                            </span>
                          </div>
                        </div>
                        <div className="flex flex-col gap-2">
                          <p className="leading-snug font-semibold text-neutral-50 text-[13px]">
                            3 more applications until system refresh
                          </p>
                          <p className="leading-relaxed text-[#a1a1a1] text-[11px]">
                            Embeddings · Rankings · ATS · Experience Weights
                            will update
                          </p>
                          <div className="flex mt-1 flex-wrap gap-1.5">
                            <span className="font-medium rounded-full bg-[#ffb547]/10 text-[#ffb547] text-[10px] border-[#ffb547]/20 border-1 border-solid px-2 py-0.5">
                              Embeddings
                            </span>
                            <span className="font-medium rounded-full bg-[#ffb547]/10 text-[#ffb547] text-[10px] border-[#ffb547]/20 border-1 border-solid px-2 py-0.5">
                              Rankings
                            </span>
                            <span className="font-medium rounded-full bg-[#ffb547]/10 text-[#ffb547] text-[10px] border-[#ffb547]/20 border-1 border-solid px-2 py-0.5">
                              ATS
                            </span>
                            <span className="font-medium rounded-full bg-[#ffb547]/10 text-[#ffb547] text-[10px] border-[#ffb547]/20 border-1 border-solid px-2 py-0.5">
                              Exp. Weights
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
