import { useEffect, useRef, useState } from "react";
import { FpsMeter, measureLongTasks } from "@/utils/perf";

/**
 * Dev-only rolling-FPS overlay (Phase 11.0).
 *
 * Drives an `FpsMeter` from a `requestAnimationFrame` loop via refs, committing
 * to React state only ~2×/sec so the overlay itself costs <1ms/frame and never
 * perturbs the number it reports. Mount only in DEV (see App.tsx).
 */
export default function FpsOverlay() {
  const [fps, setFps] = useState(0);
  const meter = useRef(new FpsMeter());
  const lastCommit = useRef(0);

  useEffect(() => {
    let raf = 0;
    const loop = (now: number) => {
      const current = meter.current.tick(now);
      if (now - lastCommit.current > 500) {
        lastCommit.current = now;
        setFps(current);
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    const stopLongTasks = measureLongTasks();
    return () => {
      cancelAnimationFrame(raf);
      stopLongTasks();
    };
  }, []);

  const color = fps >= 58 ? "#4ade80" : fps >= 30 ? "#facc15" : "#f87171";
  return (
    <div
      style={{
        position: "fixed",
        bottom: 8,
        right: 8,
        zIndex: 99999,
        padding: "2px 8px",
        borderRadius: 6,
        font: "600 12px ui-monospace, monospace",
        background: "rgba(0,0,0,0.7)",
        color,
        pointerEvents: "none",
      }}
    >
      {fps.toFixed(0)} FPS
    </div>
  );
}
