import { afterEach, describe, expect, test, vi } from "vitest";
import { fadeUp, flattenVariants, prefersReducedMotion, springs } from "./index";

const TRANSFORM_KEYS = ["x", "y", "scale", "rotate"];

describe("motion variants", () => {
  test("fadeUp animates opacity and a y transform", () => {
    expect(fadeUp.hidden).toMatchObject({ opacity: 0 });
    expect(fadeUp.hidden).toHaveProperty("y");
    expect(fadeUp.visible).toMatchObject({ opacity: 1, y: 0 });
  });

  test("springs are physics-based (no fixed duration)", () => {
    expect(springs.gentle.type).toBe("spring");
    expect(springs.snappy.type).toBe("spring");
  });
});

describe("flattenVariants (reduced-motion)", () => {
  test("strips transform props but keeps opacity", () => {
    const flat = flattenVariants(fadeUp);
    for (const state of Object.values(flat)) {
      for (const key of TRANSFORM_KEYS) {
        expect(state).not.toHaveProperty(key);
      }
    }
    expect(flat.hidden).toMatchObject({ opacity: 0 });
    expect(flat.visible).toMatchObject({ opacity: 1 });
  });

  test("collapses every transition to instant", () => {
    const flat = flattenVariants(fadeUp);
    expect(flat.visible).toMatchObject({ transition: { duration: 0 } });
  });
});

describe("prefersReducedMotion", () => {
  afterEach(() => vi.unstubAllGlobals());

  test("true when the OS reduce-motion query matches", () => {
    vi.stubGlobal("matchMedia", () => ({ matches: true }));
    expect(prefersReducedMotion()).toBe(true);
  });

  test("false when it does not match", () => {
    vi.stubGlobal("matchMedia", () => ({ matches: false }));
    expect(prefersReducedMotion()).toBe(false);
  });
});
