// Shader source for the WebGL background material (Phase 11.7, HAM-001).
// Inlined as strings rather than .glsl files so no vite-plugin-glsl is needed and
// the whole webgl module stays in one lazy chunk. GLSL ES 1.00 (build target is
// safari13 → WebGL1), so: `varying`, `gl_FragColor`, highp precision.
// ponytail: inline strings; move to .glsl + vite-plugin-glsl only if a third
// shader shows up and the imports earn their keep.

// Full-screen triangle/quad in clip space — ignores the camera entirely so the
// plane always covers the viewport regardless of R3F's default camera.
export const VERT = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;

// Aesthetic (frontend-design): a true-dark base (#0a0a0a) with three very slow
// "breathing" light pools placed to echo the static 11.5 aurora, lifted only a
// few percent toward the P3 accent. The signature is an ambient *focus glow*
// (catalog #90) that follows the cursor and softly refracts the field toward it,
// plus value-noise grain (#82 sub-pixel shimmer) that kills banding and reads as
// material, not gradient. Restrained on purpose — this sits behind glass and must
// never look like a screensaver. `uReduced` drops the cursor work for the
// Reduced tier.
export const FRAG = /* glsl */ `
  precision highp float;
  varying vec2 vUv;
  uniform float uTime;
  uniform vec2  uResolution;
  uniform vec2  uPointer;   // 0..1, y-down (screen space)
  uniform vec3  uAccent;    // 0..1 sRGB channels
  uniform vec3  uStrong;
  uniform float uReduced;   // 1.0 = reduced tier

  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
  }
  float vnoise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
  }
  float fbm(vec2 p) {
    return 0.6 * vnoise(p) + 0.4 * vnoise(p * 2.03 + 7.0);
  }
  // Soft aspect-correct radial falloff.
  float pool(vec2 uv, vec2 c, float r) {
    float d = length((uv - c) * vec2(uResolution.x / uResolution.y, 1.0));
    return smoothstep(r, 0.0, d);
  }

  void main() {
    vec2 uv = vUv;
    float t = uTime * 0.04; // very slow breathing

    // Ambient focus glow + soft refraction toward the cursor (skipped if reduced).
    vec2 ptr = vec2(uPointer.x, 1.0 - uPointer.y);
    float focus = pool(uv, ptr, 0.45) * (1.0 - uReduced);
    uv += (ptr - uv) * focus * 0.04;

    float p1 = pool(uv, vec2(0.12 + 0.03 * sin(t),        -0.05 + 0.02 * cos(t * 0.8)), 0.85);
    float p2 = pool(uv, vec2(1.05 + 0.03 * cos(t * 0.9),   0.10 + 0.02 * sin(t * 1.1)), 0.80);
    float p3 = pool(uv, vec2(0.50,                          1.10 + 0.03 * sin(t * 0.7)), 0.85);

    vec3 col = vec3(0.039); // #0a0a0a
    col += uAccent * p1 * 0.16;
    col += uStrong * p2 * 0.09;
    col += uAccent * p3 * 0.07;
    col += uAccent * focus * 0.10;

    float grain = fbm(uv * vec2(uResolution.x / uResolution.y, 1.0) * 3.0 + t * 0.5);
    col += (grain - 0.5) * 0.015;

    gl_FragColor = vec4(col, 1.0);
  }
`;

// ── Success particle choreography (Phase 11.9, HVP-001) ──────────────────────
// Each particle morphs from its scatter `position` to `aTarget` (a constellation
// node) as `uProgress` goes 0→1, all on the GPU. The CPU only writes uProgress
// per frame. Soft round points, additive-blended, fade in fast / out at the end.
export const PARTICLE_VERT = /* glsl */ `
  attribute vec3 aTarget;
  uniform float uProgress;
  uniform float uSize;
  varying float vAlpha;
  void main() {
    float e = smoothstep(0.0, 1.0, uProgress);
    vec3 p = mix(position, aTarget, e);
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    gl_PointSize = uSize / max(-mv.z, 0.1);
    // Fade in over the first 12%, hold, fade out over the last 30%.
    vAlpha = smoothstep(0.0, 0.12, uProgress) * (1.0 - smoothstep(0.7, 1.0, uProgress));
  }
`;

export const PARTICLE_FRAG = /* glsl */ `
  precision highp float;
  uniform vec3 uColor;
  varying float vAlpha;
  void main() {
    float d = length(gl_PointCoord - vec2(0.5));
    float mask = smoothstep(0.5, 0.0, d);
    gl_FragColor = vec4(uColor, mask * vAlpha);
  }
`;
