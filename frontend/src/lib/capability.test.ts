import { describe, expect, it } from "vitest";
import { pickTier } from "./capability";

// The effort tier is min(user preference, what the device can honestly do).
// No WebGL or OS reduced-motion forces the cheap static fallback (Off), where
// the app renders fully via the 11.5 aurora proxy — effects are never required
// for function.

describe("pickTier", () => {
  it("forces Off when WebGL is unavailable, whatever the preference", () => {
    expect(pickTier({ pref: "full", webgl: false, reducedMotion: false })).toBe("off");
  });

  it("forces Off under OS reduced-motion", () => {
    expect(pickTier({ pref: "full", webgl: true, reducedMotion: true })).toBe("off");
  });

  it("honors a capable Full preference", () => {
    expect(pickTier({ pref: "full", webgl: true, reducedMotion: false })).toBe("full");
  });

  it("honors a capable Reduced preference", () => {
    expect(pickTier({ pref: "reduced", webgl: true, reducedMotion: false })).toBe("reduced");
  });

  it("respects an explicit Off preference even when capable", () => {
    expect(pickTier({ pref: "off", webgl: true, reducedMotion: false })).toBe("off");
  });
});
