import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { __resetPrefetch, warm } from "./prefetch";

beforeEach(() => {
  __resetPrefetch();
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("{}"))));
  // jsdom default visibilityState is "visible".
});

afterEach(() => vi.unstubAllGlobals());

test("warm() fires one GET for an endpoint", () => {
  warm("/applications/");
  expect(fetch).toHaveBeenCalledTimes(1);
  const [url, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
  expect(String(url)).toContain("/api/v1/applications/");
  expect(init?.method ?? "GET").toBe("GET");
});

test("warm() dedups repeat calls for the same endpoint", () => {
  warm("/applications/");
  warm("/applications/");
  warm("/applications/");
  expect(fetch).toHaveBeenCalledTimes(1);
});

test("warm() does not fetch when the document is hidden", () => {
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
  warm("/learning/report");
  expect(fetch).not.toHaveBeenCalled();
});
