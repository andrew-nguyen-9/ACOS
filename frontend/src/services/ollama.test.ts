import { afterEach, expect, test, vi } from "vitest";

const { streamProgress } = vi.hoisted(() => ({ streamProgress: vi.fn() }));
vi.mock("./stream", () => ({ streamProgress }));

import { pullModel } from "./ollama";

afterEach(() => vi.clearAllMocks());

async function* frames(...fs: Record<string, unknown>[]) {
  for (const f of fs) yield f;
}

test("pullModel reports progress and resolves on the done frame", async () => {
  streamProgress.mockReturnValue(
    frames(
      { status: "pulling manifest" },
      { status: "downloading", completed: 25, total: 100 },
      { status: "done", done: true },
    ),
  );
  const seen: number[] = [];
  await pullModel("qwen3:8b", (p) => {
    if (p.total && p.completed != null) seen.push(Math.round((p.completed / p.total) * 100));
  });
  expect(seen).toContain(25);
});

test("pullModel throws on an error frame (degraded, surfaced to the UI)", async () => {
  streamProgress.mockReturnValue(frames({ error: "ollama unreachable" }));
  await expect(pullModel("x", () => {})).rejects.toThrow("ollama unreachable");
});
