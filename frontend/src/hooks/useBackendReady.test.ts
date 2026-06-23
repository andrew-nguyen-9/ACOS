import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useBackendReady } from "./useBackendReady";

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

type FetchImpl = () => Promise<{ ok: boolean }>;

function mockFetch(...impls: FetchImpl[]) {
  const fn = vi.fn();
  impls.forEach((impl) => fn.mockImplementationOnce(impl));
  vi.stubGlobal("fetch", fn);
  return fn;
}

const ok: FetchImpl = async () => ({ ok: true });
const down: FetchImpl = async () => {
  throw new Error("backend unreachable");
};

test("reaches 'ready' when /health responds ok", async () => {
  mockFetch(ok);
  const { result } = renderHook(() =>
    useBackendReady("/health", { maxAttempts: 3, baseDelay: 100 }),
  );
  expect(result.current).toBe("loading");

  await act(async () => void (await vi.advanceTimersByTimeAsync(0)));
  expect(result.current).toBe("ready");
});

test("stays 'loading' through the retry budget, then 'error'", async () => {
  mockFetch(down, down, down);
  const { result } = renderHook(() =>
    useBackendReady("/health", { maxAttempts: 3, baseDelay: 100, maxDelay: 1000 }),
  );

  await act(async () => void (await vi.advanceTimersByTimeAsync(0))); // attempt 1
  expect(result.current).toBe("loading");

  await act(async () => void (await vi.advanceTimersByTimeAsync(100))); // attempt 2
  expect(result.current).toBe("loading");

  await act(async () => void (await vi.advanceTimersByTimeAsync(200))); // attempt 3 == max
  expect(result.current).toBe("error");
});

test("recovers to 'ready' if a later poll succeeds after erroring", async () => {
  mockFetch(down, ok);
  const { result } = renderHook(() =>
    useBackendReady("/health", { maxAttempts: 1, baseDelay: 100 }),
  );

  await act(async () => void (await vi.advanceTimersByTimeAsync(0))); // attempt 1 == max -> error
  expect(result.current).toBe("error");

  await act(async () => void (await vi.advanceTimersByTimeAsync(100))); // retry succeeds
  expect(result.current).toBe("ready");
});

test("stops polling once ready (no further fetches)", async () => {
  const fn = mockFetch(ok);
  renderHook(() => useBackendReady("/health", { maxAttempts: 3, baseDelay: 100 }));

  await act(async () => void (await vi.advanceTimersByTimeAsync(0)));
  await act(async () => void (await vi.advanceTimersByTimeAsync(5000)));
  expect(fn).toHaveBeenCalledTimes(1);
});
