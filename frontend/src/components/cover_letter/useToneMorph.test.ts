import { describe, it, expect } from "vitest";
import { toneToType } from "./useToneMorph";

describe("toneToType", () => {
  it("morphs from airy/light (Traditional) to tight/heavy (Bold)", () => {
    const trad = toneToType(0);
    const bold = toneToType(1);
    expect(trad.fontWeight).toBeLessThan(bold.fontWeight);
    expect(trad.letterSpacing).toBeGreaterThan(bold.letterSpacing); // more tracking
    expect(trad.lineHeight).toBeGreaterThan(bold.lineHeight); // airier
  });

  it("interpolates the midpoint between the ends", () => {
    const mid = toneToType(0.5);
    const trad = toneToType(0);
    const bold = toneToType(1);
    expect(mid.fontWeight).toBeGreaterThan(trad.fontWeight);
    expect(mid.fontWeight).toBeLessThan(bold.fontWeight);
  });

  it("clamps out-of-range input", () => {
    expect(toneToType(-1)).toEqual(toneToType(0));
    expect(toneToType(2)).toEqual(toneToType(1));
  });
});
