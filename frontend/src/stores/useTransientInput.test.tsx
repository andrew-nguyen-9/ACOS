import { afterEach, expect, test } from "vitest";
import { act, cleanup, render } from "@testing-library/react";
import {
  getPointer,
  setPointer,
  subscribePointer,
  usePointerRef,
} from "./useTransientInput";

afterEach(cleanup);

test("setPointer updates the value without re-rendering consumers", () => {
  let renders = 0;
  function Consumer() {
    renders += 1;
    usePointerRef();
    return null;
  }

  render(<Consumer />);
  expect(renders).toBe(1);

  act(() => {
    setPointer(10, 20);
    setPointer(30, 40);
  });

  // High-frequency writes must not trigger React renders (PERF-RP-001).
  expect(renders).toBe(1);
  expect(getPointer()).toEqual({ x: 30, y: 40 });
});

test("usePointerRef exposes the live pointer through a stable ref", () => {
  let captured: { x: number; y: number } | null = null;
  function Consumer() {
    const ref = usePointerRef();
    captured = ref.current;
    return null;
  }

  render(<Consumer />);
  act(() => setPointer(5, 7));
  expect(captured).toEqual({ x: 5, y: 7 });
});

test("subscribePointer notifies imperative listeners and unsubscribes", () => {
  const seen: Array<{ x: number; y: number }> = [];
  const unsub = subscribePointer((p) => seen.push({ ...p }));

  setPointer(1, 2);
  setPointer(3, 4);
  unsub();
  setPointer(9, 9);

  expect(seen).toEqual([
    { x: 1, y: 2 },
    { x: 3, y: 4 },
  ]);
});
