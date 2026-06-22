/**
 * Tone dial (Phase 11.9, RCL-003). Presentational slider between Traditional and
 * Bold. The morph logic + debounced regeneration live in `useToneMorph`; this is
 * just the control. Keyboard-accessible by virtue of the native range input
 * (a11y: focus ring, arrow keys, labelled).
 */
interface ToneDialProps {
  tone: number;
  setTone: (value: number) => void;
}

export function ToneDial({ tone, setTone }: ToneDialProps) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between text-xs font-medium text-[#a1a1a1]">
        <span>Traditional</span>
        <span className="uppercase tracking-wider text-neutral-500">Tone</span>
        <span>Bold</span>
      </div>
      <input
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={tone}
        onChange={(e) => setTone(Number(e.target.value))}
        aria-label="Cover letter tone: Traditional to Bold"
        className="w-full accent-[var(--accent)] cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]/50 rounded-full"
      />
    </div>
  );
}
