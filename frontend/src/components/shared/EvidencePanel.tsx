import { ShieldCheck, AlertTriangle } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import type { ConfidenceLevel } from "@/types/api";

export interface EvidenceItem {
  id: string;
  text?: string;
  confidence: ConfidenceLevel;
}

export function EvidencePanel({ items, title = "Evidence" }: { items: EvidenceItem[]; title?: string }) {
  return (
    <GlassCard className="p-4 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <ShieldCheck className="size-4 text-[#30D158]" />
        <span className="text-sm font-medium text-neutral-200">{title}</span>
        <span className="ml-auto text-xs text-[#a1a1a1]">{items.length} record{items.length !== 1 ? "s" : ""}</span>
      </div>
      {items.length === 0 ? (
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[#FF9F0A]/10 border border-[#FF9F0A]/20">
          <AlertTriangle className="size-3.5 text-[#FF9F0A] flex-shrink-0" />
          <span className="text-[11px] text-[#FF9F0A]">No evidence — AI could not ground this output</span>
        </div>
      ) : (
        <div className="flex flex-col gap-2 max-h-72 overflow-auto">
          {items.map((item) => (
            <div key={item.id} className="flex items-start gap-2 p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <div className="flex-1 min-w-0">
                <p className="text-[11px] text-[#a1a1a1] font-mono truncate">{item.id}</p>
                {item.text && <p className="text-xs text-neutral-300 mt-0.5 line-clamp-2">{item.text}</p>}
              </div>
              <ConfidenceBadge level={item.confidence} />
            </div>
          ))}
        </div>
      )}
    </GlassCard>
  );
}
