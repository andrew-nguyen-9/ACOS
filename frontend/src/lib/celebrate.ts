/**
 * Celebration event bus (Phase 11.9, HVP-001).
 *
 * A dependency-free pub/sub so any page can fire the "hired"/milestone success
 * choreography (`emitCelebrate(words)`) and the WebGL particle layer — or the
 * Off-tier CSS flourish — can react, without either side importing the other.
 * Same shape as the 11.7 clock and 11.5 transient store: one `Set`, no deps.
 */
type CelebrateCallback = (words: string[]) => void;

const subscribers = new Set<CelebrateCallback>();

/** Fire a celebration with the document's words to disperse into a constellation. */
export function emitCelebrate(words: string[]): void {
  for (const cb of subscribers) cb(words);
}

/** Subscribe to celebrations; returns an unsubscribe fn. */
export function onCelebrate(cb: CelebrateCallback): () => void {
  subscribers.add(cb);
  return () => subscribers.delete(cb);
}

// Dev-only hook so the celebration can be driven from a console / perf trace
// (the dev DB has no ingested evidence, so generation produces no words to
// disperse). Stripped from production builds.
if (import.meta.env.DEV && typeof window !== "undefined") {
  (window as unknown as { __acosCelebrate?: typeof emitCelebrate }).__acosCelebrate =
    emitCelebrate;
}
