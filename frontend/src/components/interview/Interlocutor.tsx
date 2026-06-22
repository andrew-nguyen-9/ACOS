import { useEffect, useMemo, useRef } from "react";
import { useThree } from "@react-three/fiber";
import { Color, type Mesh, type MeshBasicMaterial } from "three";
import { subscribe } from "@/webgl/clock";
import { getInterlocutor } from "@/stores/useInterlocutor";

/**
 * Abstract WebGL interlocutor (Phase 11.9, IIS-001) — an icosahedron that lives
 * in the shared 11.7 canvas and pulses with the interview panel's speech
 * amplitude (fed via `useInterlocutor` from the Web Audio analyser). It is
 * invisible until the interview page activates it, so it costs nothing on other
 * routes. No second GL context, no private rAF — it reads the App-Nap clock.
 */
function accentColor(): Color {
  const raw =
    typeof getComputedStyle !== "undefined"
      ? getComputedStyle(document.documentElement).getPropertyValue("--accent-rgb").trim()
      : "";
  const [r, g, b] = raw.split(/[\s,]+/).map(Number);
  return Number.isFinite(r) ? new Color(r / 255, g / 255, b / 255) : new Color(0.3, 0.55, 1);
}

export default function Interlocutor() {
  const meshRef = useRef<Mesh>(null);
  const { invalidate } = useThree();
  const color = useMemo(accentColor, []);
  // Smoothed amplitude so the pulse settles instead of strobing on each sample.
  const eased = useRef(0);

  useEffect(() => {
    return subscribe((elapsed) => {
      const mesh = meshRef.current;
      if (!mesh) return;
      const { active, amplitude } = getInterlocutor();
      mesh.visible = active;
      if (!active) return;
      eased.current += (amplitude - eased.current) * 0.2;
      const s = 1 + eased.current * 0.45;
      mesh.scale.setScalar(s);
      mesh.rotation.y = elapsed * 0.25;
      mesh.rotation.x = elapsed * 0.12;
      (mesh.material as MeshBasicMaterial).opacity = 0.25 + eased.current * 0.5;
      invalidate();
    });
  }, [invalidate]);

  return (
    <mesh ref={meshRef} visible={false} position={[0, 0, -0.5]} renderOrder={1}>
      <icosahedronGeometry args={[1.1, 1]} />
      <meshBasicMaterial color={color} wireframe transparent opacity={0.3} depthWrite={false} />
    </mesh>
  );
}
