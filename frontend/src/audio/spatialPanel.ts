/**
 * Spatial-audio mock interview panel (Phase 11.9, IIS-001).
 *
 * A small Web Audio graph that places each virtual interviewer at a fixed
 * stereo position (a `StereoPannerNode`) so a panel "surrounds" the user. Voices
 * (placeholder oscillator beeps until real TTS exists — no new ML, per §4) play
 * from their positioned source; a shared `AnalyserNode` taps the master so the
 * WebGL interlocutor can pulse with speech amplitude.
 *
 * Autoplay policy: the AudioContext must be created/resumed from a user gesture
 * (the "Generate questions" / start button) — see `InterviewPrepPage`.
 * Everything tears down on unmount; nothing leaks across sessions.
 */
export interface Panelist {
  name: string;
  /** Stereo position, -1 (hard left) .. 1 (hard right). */
  pan: number;
}

export interface SpatialSource {
  name: string;
  panner: StereoPannerNode;
}

export interface SpatialGraph {
  ctx: AudioContext;
  master: GainNode;
  analyser: AnalyserNode;
  sources: SpatialSource[];
  bins: Uint8Array<ArrayBuffer>;
}

/** Wire master → analyser → destination, with one positioned panner per panelist. */
export function buildSpatialGraph(ctx: AudioContext, panelists: Panelist[]): SpatialGraph {
  const master = ctx.createGain();
  master.gain.value = 0.6;
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 256;
  master.connect(analyser);
  analyser.connect(ctx.destination);

  const sources = panelists.map((p) => {
    const panner = ctx.createStereoPanner();
    panner.pan.value = p.pan;
    panner.connect(master);
    return { name: p.name, panner };
  });

  return { ctx, master, analyser, sources, bins: new Uint8Array(analyser.frequencyBinCount) };
}

/** Mean speech amplitude, normalized 0..1 — drives the interlocutor + cadence meter. */
export function amplitudeOf(graph: SpatialGraph): number {
  graph.analyser.getByteFrequencyData(graph.bins);
  if (graph.bins.length === 0) return 0;
  let sum = 0;
  for (const v of graph.bins) sum += v;
  return sum / graph.bins.length / 255;
}

/** Play a short positioned beep from panelist `idx` (placeholder for TTS). */
export function speak(graph: SpatialGraph, idx: number, durationMs = 280): void {
  const src = graph.sources[idx];
  if (!src) return;
  const { ctx } = graph;
  const t = ctx.currentTime;
  const dur = durationMs / 1000;

  const osc = ctx.createOscillator();
  osc.type = "sine";
  osc.frequency.setValueAtTime(200 + idx * 60, t);

  const env = ctx.createGain();
  env.gain.setValueAtTime(0.0001, t);
  env.gain.exponentialRampToValueAtTime(0.5, t + 0.02);
  env.gain.exponentialRampToValueAtTime(0.0001, t + dur);

  osc.connect(env);
  env.connect(src.panner);
  osc.start(t);
  osc.stop(t + dur);
}

/** Disconnect every node and close the context. Idempotent enough for unmount. */
export function teardown(graph: SpatialGraph): void {
  for (const s of graph.sources) {
    try {
      s.panner.disconnect();
    } catch {
      /* already disconnected */
    }
  }
  try {
    graph.master.disconnect();
    graph.analyser.disconnect();
  } catch {
    /* already disconnected */
  }
  if (graph.ctx.state !== "closed") void graph.ctx.close();
}
