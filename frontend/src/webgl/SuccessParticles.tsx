import { useEffect, useMemo, useRef } from "react";
import { useThree } from "@react-three/fiber";
import {
  AdditiveBlending,
  Color,
  type BufferAttribute,
  type Points,
  type ShaderMaterial,
} from "three";
import { subscribe } from "./clock";
import { constellationPoints } from "./constellation";
import { onCelebrate } from "@/lib/celebrate";
import { success as hapticSuccess } from "@/lib/haptics";
import { PARTICLE_FRAG, PARTICLE_VERT } from "./shaders";

/**
 * "Hired" success choreography (Phase 11.9, HVP-001) — rendered INTO the single
 * 11.7 canvas, never a second context. A pool of points scatters from the center
 * and reassembles into a constellation whose node count = the document's word
 * count (capped). One geometry + one material are allocated once and reused on
 * every trigger (no per-burst allocation → no GC leak on repeat); the morph runs
 * GPU-side via `uProgress`, so each frame the CPU writes a single float.
 *
 * Tiers: Full = full scatter→constellation fling. Reduced = particles fade in/out
 * at the constellation with no motion (scatter == target). Off = this layer is
 * never mounted (the canvas is absent); `CelebrationFallback` covers that tier.
 */
const CAP = 700; // particle pool ceiling
const RADIUS = 2.4; // constellation world radius (fits the default camera)
const DURATION = 2.6; // seconds per burst
const MIN_NODES = 4;
const MAX_NODES = 64;

function accentColor(): Color {
  const raw =
    typeof getComputedStyle !== "undefined"
      ? getComputedStyle(document.documentElement).getPropertyValue("--accent-rgb").trim()
      : "";
  const [r, g, b] = raw.split(/[\s,]+/).map(Number);
  return Number.isFinite(r) ? new Color(r / 255, g / 255, b / 255) : new Color(0.3, 0.55, 1);
}

export default function SuccessParticles({ reduced }: { reduced: boolean }) {
  const pointsRef = useRef<Points>(null);
  const matRef = useRef<ShaderMaterial>(null);
  const { invalidate } = useThree();

  // Animation state lives in a ref — zero React re-renders during a burst.
  const anim = useRef({ active: false, start: 0, elapsed: 0 });

  // Allocated ONCE. `position` = scatter start, `aTarget` = constellation node.
  const { positions, targets } = useMemo(
    () => ({ positions: new Float32Array(CAP * 3), targets: new Float32Array(CAP * 3) }),
    [],
  );
  const uniforms = useMemo(
    () => ({
      uProgress: { value: 1 }, // start "done" → invisible
      uSize: { value: reduced ? 70 : 90 },
      uColor: { value: accentColor() },
    }),
    [], // eslint-disable-line react-hooks/exhaustive-deps -- intentionally stable
  );

  useEffect(() => {
    const off = onCelebrate((words) => {
      const nodeCount = Math.max(MIN_NODES, Math.min(MAX_NODES, words.length || MIN_NODES));
      const nodes = constellationPoints(nodeCount, RADIUS);
      for (let i = 0; i < CAP; i++) {
        const n = (i % nodeCount) * 3;
        // Tight cluster jitter around the assigned node.
        const jx = (Math.random() - 0.5) * 0.25;
        const jy = (Math.random() - 0.5) * 0.25;
        const jz = (Math.random() - 0.5) * 0.25;
        targets[i * 3] = nodes[n] + jx;
        targets[i * 3 + 1] = nodes[n + 1] + jy;
        targets[i * 3 + 2] = nodes[n + 2] + jz;
        if (reduced) {
          // No fling: fade in/out in place at the constellation.
          positions[i * 3] = targets[i * 3];
          positions[i * 3 + 1] = targets[i * 3 + 1];
          positions[i * 3 + 2] = targets[i * 3 + 2];
        } else {
          positions[i * 3] = (Math.random() - 0.5) * 0.4;
          positions[i * 3 + 1] = (Math.random() - 0.5) * 0.4;
          positions[i * 3 + 2] = (Math.random() - 0.5) * 0.4;
        }
      }
      const geom = pointsRef.current?.geometry;
      if (geom) {
        (geom.getAttribute("position") as BufferAttribute).needsUpdate = true;
        (geom.getAttribute("aTarget") as BufferAttribute).needsUpdate = true;
      }
      anim.current = { active: true, start: 0, elapsed: 0 };
      hapticSuccess(); // HVP-002 tactile tick (no-op outside the packaged app)
      invalidate();
    });
    return off;
  }, [positions, targets, reduced, invalidate]);

  // Advance the burst from the shared clock (App-Nap aware). No private rAF.
  useEffect(() => {
    return subscribe((elapsed) => {
      const a = anim.current;
      if (!a.active || !matRef.current) return;
      if (a.start === 0) a.start = elapsed;
      const p = (elapsed - a.start) / DURATION;
      matRef.current.uniforms.uProgress.value = Math.min(p, 1);
      if (p >= 1) {
        a.active = false; // settled → uProgress=1 → vAlpha=0 (invisible, idle)
      }
      invalidate();
    });
  }, [invalidate]);

  return (
    <points ref={pointsRef} frustumCulled={false} renderOrder={2}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-aTarget" args={[targets, 3]} />
      </bufferGeometry>
      <shaderMaterial
        ref={matRef}
        uniforms={uniforms}
        vertexShader={PARTICLE_VERT}
        fragmentShader={PARTICLE_FRAG}
        transparent
        depthTest={false}
        depthWrite={false}
        blending={AdditiveBlending}
      />
    </points>
  );
}
