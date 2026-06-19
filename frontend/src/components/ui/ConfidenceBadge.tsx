import { cn } from "@/lib/utils";

type ConfidenceLevel = "verified" | "strong_inference" | "weak_inference";

const CONFIG: Record<ConfidenceLevel, { label: string; className: string }> = {
  verified: {
    label: "Verified",
    className: "bg-[#30D158]/10 text-[#30D158] border-[#30D158]/20",
  },
  strong_inference: {
    label: "Strong",
    className: "bg-[#5AC8FA]/10 text-[#5AC8FA] border-[#5AC8FA]/20",
  },
  weak_inference: {
    label: "Weak ⚠",
    className: "bg-[#FF9F0A]/10 text-[#FF9F0A] border-[#FF9F0A]/20",
  },
};

export function ConfidenceBadge({ level }: { level: ConfidenceLevel }) {
  const { label, className } = CONFIG[level] ?? CONFIG.weak_inference;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
        className
      )}
    >
      {label}
    </span>
  );
}
