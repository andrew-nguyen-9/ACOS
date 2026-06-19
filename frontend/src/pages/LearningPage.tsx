import { useEffect, useState } from "react";
import { Sparkles, TrendingUp, Brain, Zap, Star } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { GlassCard } from "@/components/ui/GlassCard";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { learningService } from "@/services/learning";
import type { GeneratedQuestion } from "@/types/api";

const MOCK_CHART_DATA = [
  { week: "W1", score: 42 },
  { week: "W2", score: 58 },
  { week: "W3", score: 65 },
  { week: "W4", score: 71 },
  { week: "W5", score: 79 },
  { week: "W6", score: 85 },
];

const DIFFICULTY_CONFIG: Record<string, { color: string; bg: string }> = {
  easy: { color: "text-[#30D158]", bg: "bg-[#30D158]/10 border-[#30D158]/20" },
  medium: { color: "text-[#FF9F0A]", bg: "bg-[#FF9F0A]/10 border-[#FF9F0A]/20" },
  hard: { color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
};

export default function LearningPage() {
  const [recommendations, setRecommendations] = useState<GeneratedQuestion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    learningService.getRecommendations()
      .then((res) => setRecommendations(res.recommendations ?? []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 flex flex-col gap-6 h-full overflow-auto">
      <div>
        <h1 className="font-semibold text-neutral-50 text-2xl tracking-tight flex items-center gap-3">
          <div className="size-9 rounded-xl bg-[linear-gradient(135deg,#4c8dff,#7e5fff)] flex items-center justify-center shadow-[0_10px_24px_rgba(76,141,255,0.28)]">
            <Brain className="size-5 text-white" />
          </div>
          Learning Engine
        </h1>
        <p className="text-[#a1a1a1] text-sm mt-1 ml-12">Adaptive practice powered by your outcome history</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Questions Answered", value: "—", icon: Zap, color: "text-[#4c8dff]" },
          { label: "Avg Performance", value: "—", icon: TrendingUp, color: "text-[#30D158]" },
          { label: "Current Streak", value: "—", icon: Star, color: "text-[#FF9F0A]" },
        ].map(({ label, value, icon: Icon, color }) => (
          <GlassCard key={label} className="p-5 flex items-center gap-4">
            <div className="size-10 rounded-xl bg-white/[0.06] flex items-center justify-center flex-shrink-0">
              <Icon className={`size-5 ${color}`} />
            </div>
            <div>
              <p className="text-[#a1a1a1] text-xs">{label}</p>
              <p className={`font-bold text-2xl tracking-tight ${color}`}>{value}</p>
            </div>
          </GlassCard>
        ))}
      </div>

      <GlassCard className="p-5">
        <p className="font-medium text-neutral-200 text-sm mb-4 flex items-center gap-2">
          <TrendingUp className="size-4 text-[#4c8dff]" />
          Performance Trend
        </p>
        <ResponsiveContainer width="100%" height={140}>
          <AreaChart data={MOCK_CHART_DATA}>
            <defs>
              <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4c8dff" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#4c8dff" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="week" tick={{ fill: "#a1a1a1", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#a1a1a1", fontSize: 11 }} axisLine={false} tickLine={false} domain={[0, 100]} />
            <Tooltip
              contentStyle={{ background: "#1a1a1a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, color: "#fafafa" }}
              cursor={{ stroke: "rgba(76,141,255,0.3)" }}
            />
            <Area type="monotone" dataKey="score" stroke="#4c8dff" strokeWidth={2} fill="url(#areaGrad)" dot={{ fill: "#4c8dff", strokeWidth: 0, r: 3 }} />
          </AreaChart>
        </ResponsiveContainer>
      </GlassCard>

      <GlassCard className="p-5 flex-1">
        <p className="font-medium text-neutral-200 text-sm mb-4 flex items-center gap-2">
          <Sparkles className="size-4 text-[#4c8dff]" />
          Recommended Practice
        </p>
        {loading && <LoadingSpinner size="md" label="Loading recommendations…" />}
        {!loading && recommendations.length === 0 && (
          <EmptyState
            icon={Brain}
            title="No recommendations yet"
            description="Complete some interview practice sessions to unlock personalized recommendations."
          />
        )}
        {!loading && recommendations.length > 0 && (
          <div className="flex flex-col gap-2">
            {recommendations.map((q) => {
              const cfg = DIFFICULTY_CONFIG[q.difficulty] ?? DIFFICULTY_CONFIG.medium;
              return (
                <div key={q.id} className="flex items-start justify-between p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] hover:bg-white/[0.05] transition-colors">
                  <p className="text-neutral-200 text-sm leading-relaxed flex-1 mr-3">{q.question_text}</p>
                  <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                    <span className={`text-[11px] px-2 py-0.5 rounded-full border ${cfg.bg} ${cfg.color}`}>{q.difficulty}</span>
                    <span className="text-[#a1a1a1] text-[11px]">{q.question_type}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </GlassCard>
    </div>
  );
}
