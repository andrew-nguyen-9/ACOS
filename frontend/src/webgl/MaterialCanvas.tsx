import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { Vector2, Vector3, type ShaderMaterial } from "three";
import { subscribe } from "./clock";
import { getPointer } from "@/stores/useTransientInput";
import { FRAG, VERT } from "./shaders";

/**
 * The single WebGL background material (Phase 11.7, HAM-001 / PERF-AC-002).
 *
 * One full-screen shader plane behind the app shell — no per-component contexts.
 * `frameloop="demand"`: nothing renders until the App-Nap clock ticks and calls
 * `invalidate()`, so when the window is hidden/blurred the clock parks and the
 * GPU cost drops to ~0 (DMI-003). Pointer comes from the 11.5 transient store —
 * zero React re-renders drive the cursor uniform (PERF-RP-001).
 *
 * This module statically imports `three` + R3F (~150 kB gz). It is loaded only
 * via `React.lazy` from MaterialBackground, so it never lands in the entry chunk
 * (PERF-IL-001).
 */

/** Parse a `--x-rgb: "76 141 255"` token into a 0..1 Vector3. */
function cssVarRGB(name: string, fallback: [number, number, number]): Vector3 {
  const raw =
    typeof getComputedStyle !== "undefined"
      ? getComputedStyle(document.documentElement).getPropertyValue(name).trim()
      : "";
  const parts = raw.split(/[\s,]+/).map(Number).filter((n) => !Number.isNaN(n));
  const [r, g, b] = parts.length === 3 ? parts : fallback;
  return new Vector3(r / 255, g / 255, b / 255);
}

function Material({ reduced }: { reduced: boolean }) {
  const matRef = useRef<ShaderMaterial>(null);
  const { invalidate, size } = useThree();

  // Stable uniform object — mutated in place, never reallocated (R3F merges it
  // into the material once; mutating the same reference is what updates the GPU).
  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uResolution: { value: new Vector2(1, 1) },
      uPointer: { value: new Vector2(0.5, 0.5) },
      uAccent: { value: cssVarRGB("--accent-rgb", [76, 141, 255]) },
      uStrong: { value: cssVarRGB("--strong-rgb", [90, 200, 250]) },
      uReduced: { value: reduced ? 1 : 0 },
    }),
    [], // eslint-disable-line react-hooks/exhaustive-deps -- intentionally stable
  );

  useEffect(() => {
    uniforms.uResolution.value.set(size.width, size.height);
    invalidate();
  }, [size, uniforms, invalidate]);

  useEffect(() => {
    uniforms.uReduced.value = reduced ? 1 : 0;
    invalidate();
  }, [reduced, uniforms, invalidate]);

  // Drive time + cursor from the shared clock. One subscription, no re-renders.
  useEffect(() => {
    const ptr = uniforms.uPointer.value;
    return subscribe((elapsed) => {
      if (!matRef.current) return;
      uniforms.uTime.value = elapsed;
      const p = getPointer();
      const tx = p.x / window.innerWidth;
      const ty = p.y / window.innerHeight;
      // Critically-damped follow so the focus glow trails the cursor softly.
      ptr.x += (tx - ptr.x) * 0.08;
      ptr.y += (ty - ptr.y) * 0.08;
      invalidate();
    });
  }, [uniforms, invalidate]);

  return (
    <mesh frustumCulled={false}>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        ref={matRef}
        uniforms={uniforms}
        vertexShader={VERT}
        fragmentShader={FRAG}
        depthTest={false}
        depthWrite={false}
      />
    </mesh>
  );
}

export default function MaterialCanvas({ reduced }: { reduced: boolean }) {
  const [lost, setLost] = useState(false);
  // Context loss → unmount; the static aurora behind us becomes the material.
  if (lost) return null;

  return (
    <Canvas
      aria-hidden
      frameloop="demand"
      dpr={reduced ? [1, 1] : [1, 2]}
      gl={{
        antialias: false,
        alpha: false,
        depth: false,
        powerPreference: "high-performance",
      }}
      style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
      onCreated={({ gl }) => {
        gl.domElement.addEventListener(
          "webglcontextlost",
          (e) => {
            e.preventDefault();
            setLost(true);
          },
          { once: true },
        );
      }}
    >
      <Material reduced={reduced} />
    </Canvas>
  );
}
