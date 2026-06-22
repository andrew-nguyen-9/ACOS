import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useDeferredLoading } from "./useDeferredLoading";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

test("stays false before the delay elapses (no spinner flash <200ms)", () => {
  const { result } = renderHook(() => useDeferredLoading(true, 200));
  expect(result.current).toBe(false);

  act(() => void vi.advanceTimersByTime(199));
  expect(result.current).toBe(false);
});

test("becomes true once the delay elapses while still loading", () => {
  const { result } = renderHook(() => useDeferredLoading(true, 200));
  act(() => void vi.advanceTimersByTime(200));
  expect(result.current).toBe(true);
});

test("a load that finishes under the delay never shows the skeleton", () => {
  const { result, rerender } = renderHook(
    ({ loading }) => useDeferredLoading(loading, 200),
    { initialProps: { loading: true } },
  );
  act(() => void vi.advanceTimersByTime(150));
  rerender({ loading: false });
  act(() => void vi.advanceTimersByTime(500));
  expect(result.current).toBe(false);
});
