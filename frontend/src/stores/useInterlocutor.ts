/**
 * Interlocutor transient state (Phase 11.9, IIS-001).
 *
 * Bridges the interview page's Web Audio analyser to the WebGL interlocutor that
 * lives in the shared 11.7 canvas. Plain module singletons (not React state):
 * the GL loop reads `getInterlocutor()` every clock tick, so routing amplitude
 * through `useState` would re-render the tree dozens of times per second.
 */
let active = false;
let amplitude = 0;

export function setInterlocutorActive(value: boolean): void {
  active = value;
  if (!value) amplitude = 0;
}

export function setInterlocutorAmplitude(value: number): void {
  amplitude = value;
}

export function getInterlocutor(): { active: boolean; amplitude: number } {
  return { active, amplitude };
}

// Dev-only hook for manual testing / perf traces of the interlocutor without a
// live interview backend. Stripped from production builds.
if (import.meta.env.DEV && typeof window !== "undefined") {
  (window as unknown as Record<string, unknown>).__acosInterlocutor = {
    setActive: setInterlocutorActive,
    setAmplitude: setInterlocutorAmplitude,
  };
}
