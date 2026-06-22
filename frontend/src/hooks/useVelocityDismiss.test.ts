import { expect, test } from "vitest";
import { dismissTransition, shouldDismiss, MAX_DISMISS_VELOCITY } from "./useVelocityDismiss";

test("shouldDismiss triggers on a fast fling even with small offset", () => {
  expect(shouldDismiss(20, 1200, { offset: 120, velocity: 500 })).toBe(true);
});

test("shouldDismiss triggers on a large slow drag", () => {
  expect(shouldDismiss(160, 50, { offset: 120, velocity: 500 })).toBe(true);
});

test("shouldDismiss stays put for a small slow drag", () => {
  expect(shouldDismiss(40, 100, { offset: 120, velocity: 500 })).toBe(false);
});

test("dismissTransition carries the release velocity into the spring", () => {
  const t = dismissTransition(900);
  expect(t.type).toBe("spring");
  expect(t.velocity).toBe(900);
});

test("dismissTransition clamps absurd velocities both directions", () => {
  expect(dismissTransition(99999).velocity).toBe(MAX_DISMISS_VELOCITY);
  expect(dismissTransition(-99999).velocity).toBe(-MAX_DISMISS_VELOCITY);
});
