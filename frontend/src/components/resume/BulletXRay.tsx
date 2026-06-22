/**
 * X-Ray Impact Mapping (Phase 11.8, RCL-002).
 *
 * Intent-delayed hover on a resume bullet reveals a glass popover showing the
 * bullet's *structural math* — its action verb, whether it's quantified, which
 * ATS keywords it covers, and the evidence confidence. Every datum is derived
 * from data the resume/ATS endpoints already return; nothing is re-scored. A
 * datum the backend didn't provide (e.g. no ATS keyword list) hides its chip.
 *
 * The popover is portaled to <body> (so list overflow can't clip it) and tracks
 * the cursor imperatively from the 11.5 transient store — position never routes
 * through React state, so hovering doesn't trigger a re-render storm.
 */
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { m } from "framer-motion";
import { Activity, Hash, KeyRound, Type } from "lucide-react";
import { getPointer, subscribePointer } from "@/stores/useTransientInput";
import { springs } from "@/motion";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import type { ConfidenceLevel } from "@/types/api";

const INTENT_MS = 260;
// First word of a well-formed bullet is its action verb (Harvard/WIT rule).
const METRIC_RE = /\d[\d,.]*\s?(%|x|×|k\b|m\b|b\b|hrs?\b|hours?|days?|weeks?|months?)?/i;

interface XRay {
  verb: string;
  metric: string | null;
  matched: string[] | null;
}

function analyze(text: string, matchedKeywords?: string[]): XRay {
  const words = new Set((text.toLowerCase().match(/[a-z0-9+#.]+/g) ?? []));
  return {
    verb: text.trim().split(/\s+/)[0]?.replace(/[^A-Za-z]/g, "") ?? "",
    metric: text.match(METRIC_RE)?.[0]?.trim() ?? null,
    matched: matchedKeywords
      ? matchedKeywords.filter((k) => words.has(k.toLowerCase()))
      : null,
  };
}

function Chip({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  tone: "neutral" | "good" | "warn";
}) {
  const tint =
    tone === "good"
      ? "text-verified"
      : tone === "warn"
        ? "text-weak"
        : "text-neutral-300";
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="flex items-center gap-1.5 text-[var(--fg-muted)]">
        <Icon className="size-3.5" />
        {label}
      </span>
      <span className={`font-medium ${tint}`}>{value}</span>
    </div>
  );
}

export function BulletXRay({
  text,
  confidence,
  matchedKeywords,
  children,
}: {
  text: string;
  confidence: ConfidenceLevel;
  matchedKeywords?: string[];
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const popRef = useRef<HTMLDivElement>(null);

  // Cancel a pending intent timer if the bullet unmounts mid-hover (e.g. the
  // resume is regenerated while hovering) so it can't setState after unmount.
  useEffect(() => () => clearTimeout(timer.current), []);

  useEffect(() => {
    if (!open) return;
    const place = (x: number, y: number) => {
      const el = popRef.current;
      if (!el) return;
      const px = Math.min(x + 18, window.innerWidth - el.offsetWidth - 12);
      const py = Math.min(y + 18, window.innerHeight - el.offsetHeight - 12);
      el.style.transform = `translate3d(${px}px, ${py}px, 0)`;
    };
    const p = getPointer();
    requestAnimationFrame(() => place(p.x, p.y));
    return subscribePointer((pt) => place(pt.x, pt.y));
  }, [open]);

  const onEnter = () => {
    timer.current = setTimeout(() => setOpen(true), INTENT_MS);
  };
  const onLeave = () => {
    clearTimeout(timer.current);
    setOpen(false);
  };

  const { verb, metric, matched } = analyze(text, matchedKeywords);

  return (
    <span onPointerEnter={onEnter} onPointerLeave={onLeave}>
      {children}
      {open &&
        createPortal(
          <div
            ref={popRef}
            className="pointer-events-none fixed left-0 top-0 z-50"
            style={{ transform: "translate3d(-9999px,0,0)" }}
          >
            <m.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={springs.snappy}
              className="w-64 rounded-2xl border border-[var(--glass-border)] bg-[var(--glass-bg)] p-4 shadow-panel backdrop-blur-xl"
            >
              <div className="mb-3 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[2px] text-[var(--fg-muted)]">
                <Activity className="size-3.5 text-[var(--accent)]" />
                Impact X-Ray
              </div>
              <div className="flex flex-col gap-2.5">
                {verb && (
                  <Chip icon={Type} label="Action verb" value={verb} tone="neutral" />
                )}
                <Chip
                  icon={Hash}
                  label="Quantified"
                  value={metric ?? "Not quantified"}
                  tone={metric ? "good" : "warn"}
                />
                {matched && (
                  <Chip
                    icon={KeyRound}
                    label="ATS keywords"
                    value={
                      matched.length ? `${matched.length} matched` : "None matched"
                    }
                    tone={matched.length ? "good" : "warn"}
                  />
                )}
                {matched && matched.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {matched.map((k) => (
                      <span
                        key={k}
                        className="rounded-full border border-[var(--glass-border)] bg-white/[0.06] px-2 py-0.5 text-[10px] text-neutral-300"
                      >
                        {k}
                      </span>
                    ))}
                  </div>
                )}
                <div className="flex items-center justify-between border-t border-[var(--glass-border)] pt-2.5 text-xs">
                  <span className="text-[var(--fg-muted)]">Confidence</span>
                  <ConfidenceBadge level={confidence} />
                </div>
              </div>
            </m.div>
          </div>,
          document.body,
        )}
    </span>
  );
}
