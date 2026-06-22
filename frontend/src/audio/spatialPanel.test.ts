import { describe, it, expect, vi } from "vitest";
import { amplitudeOf, buildSpatialGraph, speak, teardown } from "./spatialPanel";

// Minimal AudioContext fake — enough to exercise the graph wiring without WebAudio.
function fakeCtx() {
  const make = () => ({ connect: vi.fn(), disconnect: vi.fn() });
  return {
    state: "running",
    currentTime: 0,
    destination: make(),
    createStereoPanner: vi.fn(() => ({ ...make(), pan: { value: 0 } })),
    createAnalyser: vi.fn(() => ({
      ...make(),
      fftSize: 0,
      frequencyBinCount: 4,
      getByteFrequencyData: (a: Uint8Array) => a.fill(128),
    })),
    createGain: vi.fn(() => ({
      ...make(),
      gain: { value: 1, setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() },
    })),
    createOscillator: vi.fn(() => ({
      ...make(),
      type: "sine",
      frequency: { value: 0, setValueAtTime: vi.fn() },
      start: vi.fn(),
      stop: vi.fn(),
    })),
    resume: vi.fn(),
    close: vi.fn(),
  } as unknown as AudioContext;
}

describe("spatialPanel", () => {
  it("builds one panner per panelist, positioned in stereo space", () => {
    const ctx = fakeCtx();
    const g = buildSpatialGraph(ctx, [
      { name: "A", pan: -0.6 },
      { name: "B", pan: 0.6 },
    ]);
    expect(g.sources).toHaveLength(2);
    expect(g.sources[0].panner.pan.value).toBe(-0.6);
    expect(g.sources[1].panner.pan.value).toBe(0.6);
    expect(g.analyser).toBeDefined();
  });

  it("amplitudeOf normalizes analyser bytes to 0..1", () => {
    const ctx = fakeCtx();
    const g = buildSpatialGraph(ctx, [{ name: "A", pan: 0 }]);
    expect(amplitudeOf(g)).toBeCloseTo(128 / 255, 2);
  });

  it("speak() plays a positioned oscillator without throwing", () => {
    const ctx = fakeCtx();
    const g = buildSpatialGraph(ctx, [{ name: "A", pan: 0 }]);
    expect(() => speak(g, 0)).not.toThrow();
    expect(ctx.createOscillator).toHaveBeenCalled();
  });

  it("teardown disconnects nodes and closes the context", () => {
    const ctx = fakeCtx();
    const g = buildSpatialGraph(ctx, [{ name: "A", pan: 0 }]);
    teardown(g);
    expect(ctx.close).toHaveBeenCalled();
  });
});
