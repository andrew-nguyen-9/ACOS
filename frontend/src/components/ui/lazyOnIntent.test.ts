import { expect, test, vi } from "vitest";
import { lazyOnIntent } from "./lazyOnIntent";

test("prefetch starts the import once, even if called repeatedly", () => {
  const importer = vi.fn(() => Promise.resolve({ default: () => null }));
  const { prefetch } = lazyOnIntent(importer);

  // React.lazy defers; constructing lazyOnIntent must not import yet.
  expect(importer).toHaveBeenCalledTimes(0);

  prefetch();
  prefetch();
  prefetch();

  expect(importer).toHaveBeenCalledTimes(1);
});

test("returns a renderable lazy component", () => {
  const importer = () => Promise.resolve({ default: () => null });
  const { Component } = lazyOnIntent(importer);
  expect(typeof Component).toBe("object"); // React.lazy exotic component
});
