import { useEffect, useRef } from "react";
import { subscribe } from "@/webgl/clock";
import { prefersReducedMotion } from "@/motion";

/**
 * Real-time cadence/pace waveform (Phase 11.9, IIS-002). A lightweight 2D-canvas
 * line driven by the panel's `AnalyserNode` time-domain data — volume/timing
 * only, NO transcription (§4). Drawn from the shared App-Nap clock, not a private
 * rAF. Reduced motion → a flat, static baseline (no animation).
 */
export function CadenceMeter({ analyser }: { analyser: AnalyserNode | null }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !analyser) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const reduce = prefersReducedMotion();
    const buf = new Uint8Array(analyser.fftSize);

    const draw = () => {
      const { width: w, height: h } = canvas;
      ctx.clearRect(0, 0, w, h);
      ctx.lineWidth = 2;
      ctx.strokeStyle =
        getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() ||
        "#4c8dff";
      ctx.beginPath();
      if (reduce) {
        ctx.moveTo(0, h / 2);
        ctx.lineTo(w, h / 2);
      } else {
        analyser.getByteTimeDomainData(buf);
        const step = w / buf.length;
        for (let i = 0; i < buf.length; i++) {
          const y = (buf[i] / 255) * h;
          i === 0 ? ctx.moveTo(0, y) : ctx.lineTo(i * step, y);
        }
      }
      ctx.stroke();
    };

    draw();
    if (reduce) return; // static baseline; no per-frame work
    return subscribe(draw);
  }, [analyser]);

  return (
    <canvas
      ref={canvasRef}
      width={480}
      height={64}
      className="w-full h-16 rounded-xl bg-white/[0.03] border border-white/10"
      aria-hidden
    />
  );
}
