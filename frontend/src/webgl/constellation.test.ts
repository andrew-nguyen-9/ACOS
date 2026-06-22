import { describe, it, expect } from "vitest";
import { constellationPoints } from "./constellation";

describe("constellationPoints", () => {
  it("returns n xyz triplets", () => {
    expect(constellationPoints(5, 1)).toHaveLength(15);
  });

  it("keeps every node within the radius", () => {
    const r = 2;
    const p = constellationPoints(40, r);
    for (let i = 0; i < p.length; i += 3) {
      expect(Math.hypot(p[i], p[i + 1], p[i + 2])).toBeLessThanOrEqual(r + 1e-6);
    }
  });

  it("is deterministic for the same inputs", () => {
    expect(Array.from(constellationPoints(8, 1))).toEqual(
      Array.from(constellationPoints(8, 1)),
    );
  });
});
