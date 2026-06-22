import { describe, it, expect } from "vitest";
import { createBatchedInvoke } from "./ipc";

describe("createBatchedInvoke (PERF-IPC-001)", () => {
  it("defers invokes until the frame flushes", () => {
    const calls: Array<[string, unknown]> = [];
    let flush: (() => void) | null = null;
    const batched = createBatchedInvoke(
      (c, a) => calls.push([c, a]),
      (cb) => {
        flush = cb;
      },
    );

    batched("resize", { w: 1 });
    expect(calls).toEqual([]);

    flush!();
    expect(calls).toEqual([["resize", { w: 1 }]]);
  });

  it("coalesces N same-command calls in a frame into one with the last payload", () => {
    const calls: Array<[string, unknown]> = [];
    let flush: (() => void) | null = null;
    const batched = createBatchedInvoke(
      (c, a) => calls.push([c, a]),
      (cb) => {
        flush = cb;
      },
    );

    batched("resize", { w: 1 });
    batched("resize", { w: 2 });
    batched("resize", { w: 3 });
    flush!();

    expect(calls).toEqual([["resize", { w: 3 }]]);
  });

  it("keeps distinct commands separate, one call each per frame", () => {
    const calls: Array<[string, unknown]> = [];
    let flush: (() => void) | null = null;
    const batched = createBatchedInvoke(
      (c, a) => calls.push([c, a]),
      (cb) => {
        flush = cb;
      },
    );

    batched("resize", { w: 1 });
    batched("scroll", { y: 9 });
    flush!();

    expect(calls).toEqual([
      ["resize", { w: 1 }],
      ["scroll", { y: 9 }],
    ]);
  });

  it("reschedules after a flush so the next frame's calls also fire", () => {
    const calls: Array<[string, unknown]> = [];
    const flushes: Array<() => void> = [];
    const batched = createBatchedInvoke(
      (c, a) => calls.push([c, a]),
      (cb) => flushes.push(cb),
    );

    batched("resize", { w: 1 });
    flushes[0]();
    batched("resize", { w: 2 });
    expect(flushes).toHaveLength(2);
    flushes[1]();

    expect(calls).toEqual([
      ["resize", { w: 1 }],
      ["resize", { w: 2 }],
    ]);
  });
});
