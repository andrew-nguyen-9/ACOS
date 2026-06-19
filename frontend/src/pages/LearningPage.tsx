import { useEffect, useState } from "react";
import {
  Brain,
  Lightbulb,
  RefreshCw,
  Sparkles,
  Star,
  TrendingUp,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts";
import { ChartContainer, ChartTooltip } from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { learningService, type TemplateRanking, type AtsVsOutcome } from "@/services/learning";
import { applicationsService } from "@/services/applications";
import type { Application } from "@/types/api";

// ── Static insights (no API endpoint) ─────────────────────────────────────────
const STATIC_INSIGHTS = [
  {
    type: "verified" as const,
    text: "Product leadership stories increase interview rate by ",
    highlight: "18%",
    meta: "Verified · High Confidence",
  },
  {
    type: "strong" as const,
    text: "AI projects outperform analytics-only projects in ",
    highlight: "tech roles",
    meta: "Strong Inference · Medium Confidence",
  },
  {
    type: "weak" as const,
    text: "Compliance experience highly valued in ",
    highlight: "fintech roles",
    meta: "Strong Inference · Medium Confidence",
  },
];

const INSIGHT_STYLES: Record<string, { card: string; border: string; icon: string; highlight: string }> = {
  verified: {
    card: "rounded-xl bg-[#32d583]/5 border-l-2 border-[#32d583] flex p-3 items-start gap-3",
    border: "",
    icon: "text-[#32d583]",
    highlight: "font-bold text-[#32d583]",
  },
  strong: {
    card: "rounded-xl bg-neutral-200/5 border-l-2 border-neutral-200 flex p-3 items-start gap-3",
    border: "",
    icon: "text-neutral-200",
    highlight: "font-bold text-neutral-200",
  },
  weak: {
    card: "rounded-xl bg-[#ffb547]/5 border-l-2 border-[#ffb547] flex p-3 items-start gap-3",
    border: "",
    icon: "text-[#ffb547]",
    highlight: "font-bold text-[#ffb547]",
  },
};

// ── Rank badge styles ─────────────────────────────────────────────────────────
function rankBadgeClass(rank: number): string {
  if (rank === 1) return "size-6 font-bold rounded-lg bg-neutral-200/15 text-neutral-200 text-[11px] border border-neutral-200/25 flex justify-center items-center";
  if (rank === 2) return "size-6 font-bold rounded-lg bg-[#7e5fff]/15 text-[#7e5fff] text-[11px] border border-[#7e5fff]/25 flex justify-center items-center";
  return "size-6 font-bold rounded-lg bg-white/6 text-[#a1a1a1] text-[11px] border border-white/10 flex justify-center items-center";
}

function rankBarClass(rank: number): string {
  if (rank === 1) return "bg-[linear-gradient(90deg,#4c8dff,#7e5fff)] shadow-[0_0_8px_rgba(76,141,255,0.45)] rounded-full h-full";
  if (rank === 2) return "bg-[linear-gradient(90deg,#7e5fff,#a07fff)] shadow-[0_0_8px_rgba(126,95,255,0.45)] rounded-full h-full";
  return "bg-[linear-gradient(90deg,#4c8dff,#6ba8ff)] shadow-[0_0_8px_rgba(76,141,255,0.35)] rounded-full h-full";
}

function rankScoreClass(rank: number): string {
  if (rank === 1) return "font-bold text-neutral-200 text-xs leading-4";
  if (rank === 2) return "font-bold text-[#7e5fff] text-xs leading-4";
  return "font-bold text-[#a1a1a1] text-xs leading-4";
}

// ── Derive score and width for a ranking row ──────────────────────────────────
function rankingScore(r: TemplateRanking): number {
  if (r.win_rate != null) return Math.round(r.win_rate * 100);
  if (r.avg_ats_score != null) return Math.round(r.avg_ats_score);
  return 0;
}

function rankingWidth(r: TemplateRanking): string {
  const score = rankingScore(r);
  return `${Math.min(score, 100)}%`;
}

// ── Build chart data from ats_vs_outcome ──────────────────────────────────────
function buildChartData(atsVsOutcome: AtsVsOutcome[]): Array<{ label: string; value: number }> {
  return atsVsOutcome.map((item) => ({
    label: item.signal_type,
    value: item.avg_ats_score != null ? Math.round(item.avg_ats_score) : 0,
  }));
}

// ── Circular progress SVG constants ──────────────────────────────────────────
const CIRCLE_R = 36;
const CIRCLE_CIRC = 2 * Math.PI * CIRCLE_R; // ~226.2

function circleOffset(done: number, needed: number): number {
  const pct = needed > 0 ? done / needed : 0;
  return CIRCLE_CIRC * (1 - pct);
}

// ─────────────────────────────────────────────────────────────────────────────

export default function LearningPage() {
  const [rankings, setRankings] = useState<TemplateRanking[]>([]);
  const [atsVsOutcome, setAtsVsOutcome] = useState<AtsVsOutcome[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      learningService.getReport(),
      applicationsService.list(),
    ])
      .then(([report, apps]) => {
        setRankings(report.template_rankings ?? []);
        setAtsVsOutcome(report.ats_vs_outcome ?? []);
        setApplications(apps ?? []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // ── Derived stats ───────────────────────────────────────────────────────────
  const totalApps = applications.length;
  const top = rankings[0] ?? null;

  const interviewCount = atsVsOutcome
    .filter((x) => x.signal_type === "interview")
    .reduce((acc, x) => acc + x.count, 0);
  const interviewRate = totalApps > 0 ? ((interviewCount / totalApps) * 100).toFixed(1) : "—";

  const avgAtsScore = top?.avg_ats_score != null ? `${Math.round(top.avg_ats_score)}%` : "—";
  const resumeEffectiveness = top?.win_rate != null ? `${Math.round(top.win_rate * 100)}%` : "—";

  const CYCLE_NEEDED = 5;
  const cycleDone = totalApps % CYCLE_NEEDED;
  const cycleLeft = CYCLE_NEEDED - cycleDone;
  const cycleOffset = circleOffset(cycleDone, CYCLE_NEEDED);

  const chartData = buildChartData(atsVsOutcome);

  // ── Loading ─────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <LoadingSpinner size="lg" label="Loading learning data…" />
      </div>
    );
  }

  // ── Empty state ─────────────────────────────────────────────────────────────
  if (!loading && rankings.length === 0) {
    return (
      <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
        <PageHeader />
        <div className="flex-1 flex items-center justify-center">
          <EmptyState
            icon={Brain}
            title="No learning data yet"
            description="No learning data yet. Start by generating resumes and tracking applications."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
      <PageHeader />

      {/* ── Stats row ─────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-4">
        {/* Interview Rate */}
        <div className="shadow-[0_10px_30px_rgba(0,0,0,0.18),inset_0_1px_0_rgba(255,255,255,0.04)] rounded-[22px] bg-neutral-900 border border-white/10 flex p-6 flex-col gap-3">
          <div className="flex justify-between items-center">
            <span className="font-medium text-neutral-200 text-[11px]">Interview Rate</span>
            <div className="rounded-full bg-[#32d583]/10 border border-[#32d583]/20 flex px-2 py-1 items-center gap-1">
              <TrendingUp className="size-3 text-[#32d583]" />
              <span className="font-bold text-[#32d583] text-[10px]">Live</span>
            </div>
          </div>
          <div className="font-bold text-neutral-50 text-[38px] tracking-[-0.96px]">
            {interviewRate}{typeof interviewRate === "string" && interviewRate !== "—" ? "" : ""}
          </div>
          <div className="text-[#a1a1a1] text-[11px]">
            {interviewCount} interviews / {totalApps} apps
          </div>
        </div>

        {/* Avg ATS Score */}
        <div className="shadow-[0_10px_30px_rgba(0,0,0,0.18),inset_0_1px_0_rgba(255,255,255,0.04)] rounded-[22px] bg-neutral-900 border border-white/10 flex p-6 flex-col gap-3">
          <div className="flex justify-between items-center">
            <span className="font-medium uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.88px]">Avg ATS Score</span>
            <div className="rounded-full bg-[#32d583]/10 border border-[#32d583]/20 flex px-2 py-1 items-center gap-1">
              <TrendingUp className="size-3 text-[#32d583]" />
              <span className="font-bold text-[#32d583] text-[10px]">Top template</span>
            </div>
          </div>
          <div className="font-bold text-neutral-50 text-[38px] tracking-[-0.96px]">{avgAtsScore}</div>
          <div className="text-[#a1a1a1] text-[11px]">
            {top ? top.template_name : "No data"}
          </div>
        </div>

        {/* Resume Effectiveness */}
        <div className="shadow-[0_10px_30px_rgba(0,0,0,0.18),inset_0_1px_0_rgba(255,255,255,0.04)] rounded-[22px] bg-neutral-900 border border-white/10 flex p-6 flex-col gap-3">
          <div className="flex justify-between items-center">
            <span className="font-medium uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.88px]">Resume Effectiveness</span>
            <div className="rounded-full bg-[#32d583]/10 border border-[#32d583]/20 flex px-2 py-1 items-center gap-1">
              <TrendingUp className="size-3 text-[#32d583]" />
              <span className="font-bold text-[#32d583] text-[10px]">Win rate</span>
            </div>
          </div>
          <div className="font-bold text-neutral-50 text-[38px] tracking-[-0.96px]">{resumeEffectiveness}</div>
          <div className="text-[#a1a1a1] text-[11px]">
            {top ? `${top.application_count} applications tracked` : "No data"}
          </div>
        </div>

        {/* Applications This Cycle */}
        <div className="shadow-[0_10px_30px_rgba(0,0,0,0.18),inset_0_1px_0_rgba(255,255,255,0.04)] rounded-[22px] bg-[#ffb547]/10 border border-[#ffb547]/20 flex p-6 flex-col gap-3">
          <div className="flex justify-between items-center">
            <span className="font-medium uppercase text-[#a1a1a1] text-xs leading-4 tracking-[2.88px]">Applications This Cycle</span>
            <div className="rounded-full bg-[#ffb547]/10 border border-[#ffb547]/20 flex px-2 py-1 items-center gap-1">
              <Zap className="size-3 text-[#ffb547]" />
              <span className="font-bold text-[#ffb547] text-[10px]">In Progress</span>
            </div>
          </div>
          <div className="flex items-end gap-2">
            <div className="font-bold text-neutral-50 text-[38px] tracking-[-0.96px]">{cycleDone}</div>
            <div className="font-semibold text-[#a1a1a1] text-lg leading-7 mb-1.5">/ {CYCLE_NEEDED}</div>
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="rounded-full bg-white/8 w-full h-1.5">
              <div
                className="bg-[linear-gradient(90deg,#ffb547,#ff8c47)] shadow-[0_0_8px_rgba(255,181,71,0.45)] rounded-full h-full"
                style={{ width: `${(cycleDone / CYCLE_NEEDED) * 100}%` }}
              />
            </div>
            <div className="text-[#a1a1a1] text-[11px]">{cycleLeft} more until next refresh</div>
          </div>
        </div>
      </div>

      {/* ── Main content row ──────────────────────────────────────────────────── */}
      <div className="min-h-0 flex flex-1 gap-6">

        {/* Left column: chart + rankings */}
        <div className="min-w-0 flex-[6] flex flex-col gap-4">

          {/* Area chart */}
          <div className="shadow-[0_14px_40px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.05)] rounded-3xl bg-neutral-900 border border-white/10 p-6 flex flex-col gap-5">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <TrendingUp className="size-4 text-neutral-200" />
                <h2 className="font-semibold text-neutral-50 text-base leading-6 tracking-tight">
                  Application Performance
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <div className="rounded-full bg-[#7e5fff]/10 border border-[#7e5fff]/20 flex px-3 py-1 items-center gap-1.5">
                  <div className="size-2 rounded-full bg-[#7e5fff]" />
                  <span className="font-medium text-[#7e5fff] text-[11px]">ATS Score by Signal</span>
                </div>
              </div>
            </div>
            <div className="rounded-2xl bg-neutral-950/20 border border-white/10 p-4 h-[160px]">
              {chartData.length > 0 ? (
                <ChartContainer className="w-full h-full">
                  <AreaChart
                    data={chartData}
                    margin={{ top: 8, right: 12, left: 0, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="learningGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#7e5fff" stopOpacity={0.34} />
                        <stop offset="95%" stopColor="#7e5fff" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                    <XAxis dataKey="label" tick={{ fill: "#7e8794", fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "#7e8794", fontSize: 10 }} axisLine={false} tickLine={false} width={32} domain={[0, 100]} />
                    <ChartTooltip />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#7e5fff"
                      strokeWidth={2.5}
                      fill="url(#learningGrad)"
                      dot={false}
                    />
                  </AreaChart>
                </ChartContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-[#a1a1a1] text-sm">
                  No signal data yet
                </div>
              )}
            </div>
          </div>

          {/* Template Rankings */}
          <div className="shadow-[0_14px_40px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.05)] rounded-3xl bg-neutral-900 border border-white/10 p-6 flex flex-col gap-4 flex-1">
            <div className="flex items-center gap-2">
              <Star className="size-4 text-[#ffb547]" />
              <h2 className="font-semibold text-neutral-50 text-[15px] tracking-tight">
                Top Performing Templates
              </h2>
            </div>
            <div className="flex flex-col gap-4">
              {rankings.map((r, i) => {
                const rank = i + 1;
                const score = rankingScore(r);
                const width = rankingWidth(r);
                return (
                  <div key={r.template_name} className="flex items-center gap-3">
                    <div className={rankBadgeClass(rank)}>{rank}</div>
                    <div className="flex flex-col flex-1 gap-1">
                      <div className="flex justify-between items-center">
                        <span className="font-medium text-neutral-50 text-[13px]">{r.template_name}</span>
                        <span className={rankScoreClass(rank)}>{score}</span>
                      </div>
                      <div className="rounded-full bg-white/6 w-full h-1.5">
                        <div className={rankBarClass(rank)} style={{ width }} />
                      </div>
                    </div>
                  </div>
                );
              })}
              {rankings.length === 0 && (
                <p className="text-[#a1a1a1] text-sm">No template data yet.</p>
              )}
            </div>
          </div>
        </div>

        {/* Right column: insights + cycle */}
        <div className="min-w-0 flex-[4] flex flex-col gap-4">

          {/* Recent Learning Insights */}
          <div className="shadow-[0_14px_40px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.05)] rounded-3xl bg-neutral-900 border border-white/10 p-6 flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <Lightbulb className="size-4 text-[#ffb547]" />
              <h2 className="font-semibold text-neutral-50 text-[15px] tracking-tight">
                Recent Learning Insights
              </h2>
            </div>
            <div className="flex flex-col gap-3">
              {STATIC_INSIGHTS.map((insight) => {
                const styles = INSIGHT_STYLES[insight.type];
                return (
                  <div key={insight.meta} className={styles.card}>
                    <Lightbulb className={`size-4 flex-shrink-0 ${styles.icon} mt-0.5`} />
                    <div>
                      <p className="leading-relaxed font-medium text-neutral-50 text-xs leading-4">
                        {insight.text}
                        <span className={styles.highlight}>{insight.highlight}</span>
                      </p>
                      <span className="text-[#a1a1a1] text-[10px]">{insight.meta}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Next Optimization Cycle */}
          <div className="shadow-[0_14px_40px_rgba(0,0,0,0.22),inset_0_1px_0_rgba(255,255,255,0.05)] rounded-[28px] bg-[#ffb547]/[0.12] border border-[#ffb547]/20 p-6 flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <RefreshCw className="size-4 text-[#ffb547]" />
              <h2 className="font-semibold text-neutral-50 text-[15px] tracking-tight">
                Next Optimization Cycle
              </h2>
            </div>
            <div className="flex items-center gap-6">
              {/* Circular progress */}
              <div className="relative size-22 flex-shrink-0">
                <svg viewBox="0 0 88 88" className="w-full h-full">
                  <circle
                    cx="44"
                    cy="44"
                    r={CIRCLE_R}
                    fill="none"
                    stroke="rgba(255,255,255,0.08)"
                    strokeWidth="7"
                  />
                  <circle
                    cx="44"
                    cy="44"
                    r={CIRCLE_R}
                    fill="none"
                    stroke="#ffb547"
                    strokeWidth="7"
                    strokeLinecap="round"
                    strokeDasharray={CIRCLE_CIRC}
                    strokeDashoffset={cycleOffset}
                    className="drop-shadow-[0_0_10px_rgba(255,181,71,0.35)]"
                    style={{ transform: "rotate(-90deg)", transformOrigin: "center" }}
                  />
                </svg>
                <div className="flex absolute inset-0 flex-col justify-center items-center">
                  <span className="font-bold text-neutral-50 text-lg leading-7 tracking-tight">
                    {cycleDone}/{CYCLE_NEEDED}
                  </span>
                  <span className="font-medium text-[#a1a1a1] text-[9px]">apps</span>
                </div>
              </div>
              <div className="flex flex-col gap-2">
                <p className="leading-snug font-semibold text-neutral-50 text-[13px]">
                  {cycleLeft} more application{cycleLeft !== 1 ? "s" : ""} until system refresh
                </p>
                <p className="leading-relaxed text-[#a1a1a1] text-[11px]">
                  Embeddings · Rankings · ATS · Experience Weights will update
                </p>
                <div className="flex mt-1 flex-wrap gap-1.5">
                  {["Embeddings", "Rankings", "ATS", "Exp. Weights"].map((tag) => (
                    <span
                      key={tag}
                      className="font-medium rounded-full bg-[#ffb547]/10 text-[#ffb547] text-[10px] border border-[#ffb547]/20 px-2 py-0.5"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Sub-component: page header ────────────────────────────────────────────────
function PageHeader() {
  return (
    <div className="flex-shrink-0 flex justify-between items-center">
      <div className="flex items-center gap-4">
        <div className="size-12 shadow-[0_0_0_1px_rgba(255,255,255,0.02),0_12px_30px_rgba(76,141,255,0.12)] rounded-2xl bg-neutral-200/10 border border-neutral-200/25 flex justify-center items-center">
          <Brain className="size-5 text-neutral-200" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-bold text-neutral-50 text-[28px] tracking-[-0.64px]">Learning Engine</h1>
            <Sparkles className="size-5 text-[#7e5fff]" />
          </div>
          <p className="text-[#a1a1a1] text-[13px] mt-1">
            The system continuously improves after every application
          </p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-[#32d583]/10 border border-[#32d583]/20 flex px-4 py-2 items-center gap-2">
          <div className="size-2 shadow-[0_0_10px_rgba(50,213,131,0.9)] rounded-full bg-[#32d583]" />
          <span className="font-semibold text-[#32d583] text-xs leading-4">Last Updated: just now</span>
        </div>
      </div>
    </div>
  );
}
