import { afterEach, describe, expect, it } from "vitest";
import { isRunning, pause, resume, subscribe } from "./clock";

// The App-Nap clock (DMI-003): the single pause/resume authority every animation
// loop subscribes to. These cover the contract that matters — it runs while
// observed, and parks itself when the window is hidden/blurred so the canvas
// costs ~0 in the background.

afterEach(() => {
  // Leave the clock parked + unsubscribed between tests.
  resume();
  Object.defineProperty(document, "hidden", { value: false, configurable: true });
});

describe("animation clock", () => {
  it("runs only while it has subscribers", () => {
    expect(isRunning()).toBe(false);
    const off = subscribe(() => {});
    expect(isRunning()).toBe(true);
    off();
    expect(isRunning()).toBe(false);
  });

  it("pauses when the document becomes hidden and resumes when visible", () => {
    const off = subscribe(() => {});
    expect(isRunning()).toBe(true);

    Object.defineProperty(document, "hidden", { value: true, configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));
    expect(isRunning()).toBe(false);

    Object.defineProperty(document, "hidden", { value: false, configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));
    expect(isRunning()).toBe(true);

    off();
  });

  it("pause()/resume() toggle the running state while subscribed", () => {
    const off = subscribe(() => {});
    pause();
    expect(isRunning()).toBe(false);
    resume();
    expect(isRunning()).toBe(true);
    off();
  });

  it("stays parked while any pause source is still active", () => {
    const off = subscribe(() => {});
    // Document hidden parks the clock (one pause source).
    Object.defineProperty(document, "hidden", { value: true, configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));
    expect(isRunning()).toBe(false);

    // A resume from a *different* source (e.g. Tauri focus regained) must NOT
    // override the still-active visibility pause — otherwise the rAF runs in the
    // background, defeating App-Nap (DMI-003).
    resume();
    expect(isRunning()).toBe(false);

    // Clearing the last active source resumes.
    Object.defineProperty(document, "hidden", { value: false, configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));
    expect(isRunning()).toBe(true);

    off();
  });
});
