/**
 * Constellation geometry for the success-particle choreography (Phase 11.9, HVP-001).
 *
 * Pure math (no `three`, no React) so it unit-tests without a GPU. Particles
 * disperse from the center then reassemble onto these node positions — one node
 * per document word (capped). A golden-angle spiral gives an even, organic spread
 * that is fully deterministic (no RNG), so targets are reproducible and testable.
 */
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

/**
 * `n` constellation node positions packed as a flat [x,y,z,...] Float32Array,
 * every node within `radius` of the origin (a sunflower disk, slight z jitter
 * for depth parallax).
 */
export function constellationPoints(n: number, radius: number): Float32Array {
  const out = new Float32Array(Math.max(0, n) * 3);
  for (let i = 0; i < n; i++) {
    // Even radial packing: r grows as sqrt(i/n) so area per node is constant.
    // Planar radius is held to 0.95R so the depth wobble below never pushes a
    // node's 3D distance past R (the unit-tested invariant).
    const r = radius * 0.95 * Math.sqrt((i + 0.5) / n);
    const theta = i * GOLDEN_ANGLE;
    out[i * 3] = r * Math.cos(theta);
    out[i * 3 + 1] = r * Math.sin(theta);
    // Deterministic depth wobble for parallax, bounded so hypot(r, z) ≤ R.
    out[i * 3 + 2] = Math.sin(i * 1.7) * radius * 0.12;
  }
  return out;
}
