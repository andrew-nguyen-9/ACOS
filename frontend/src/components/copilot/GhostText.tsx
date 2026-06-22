/**
 * Ghost-Writing Ink Trail (Phase 11.8, COP-003).
 *
 * Renders the copilot's inline suggestion as faint accent "ink" in an overlay
 * laid over the input — never the input's value, so it can't fight IME or the
 * controlled input. The ghost writes in left-to-right (a clip-path "ink trail")
 * when it appears; reduced-motion shows it instantly.
 *
 * The overlay mirrors the input's typed `value` invisibly so the ghost starts
 * exactly where the caret sits.
 */
import { m } from "framer-motion";
import { prefersReducedMotion } from "@/motion";

export function GhostText({ value, ghost }: { value: string; ghost: string }) {
  if (!ghost) return null;
  const reduced = prefersReducedMotion();

  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 flex items-center overflow-hidden text-sm leading-5 text-[var(--accent)]"
    >
      <span className="whitespace-pre invisible">{value}</span>
      {reduced ? (
        <span className="opacity-60">{ghost}</span>
      ) : (
        <m.span
          key={ghost}
          initial={{ clipPath: "inset(0 100% 0 0)", opacity: 0.2 }}
          animate={{ clipPath: "inset(0 0% 0 0)", opacity: 0.62 }}
          transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
          className="whitespace-pre"
        >
          {ghost}
          <span className="ml-1.5 rounded border border-[var(--accent)]/30 px-1 align-middle text-[9px] uppercase tracking-wide opacity-80">
            Tab
          </span>
        </m.span>
      )}
    </div>
  );
}
