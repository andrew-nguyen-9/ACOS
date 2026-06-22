import { afterEach, expect, test, vi } from "vitest";
import { streamSSE } from "./stream";

afterEach(() => vi.unstubAllGlobals());

function sseResponse(chunks: string[]): Response {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      const enc = new TextEncoder();
      for (const c of chunks) controller.enqueue(enc.encode(c));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "content-type": "text/event-stream" },
  });
}

test("streamSSE yields each delta and concatenates to the full text", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve(
        sseResponse([
          'data: {"delta": "Hel"}\n\n',
          'data: {"delta": "lo"}\n\n',
          'data: {"done": true}\n\n',
        ])
      )
    )
  );

  const out: string[] = [];
  for await (const d of streamSSE("/copilot/chat/stream", { message: "hi" })) {
    out.push(d);
  }

  expect(out).toEqual(["Hel", "lo"]); // incremental: more than one yield
  expect(out.join("")).toBe("Hello"); // final state == concatenated deltas
});

test("streamSSE reassembles events split across read-chunk boundaries", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve(
        sseResponse([
          'data: {"delta": "ab', // event split mid-JSON across chunks
          'c"}\n\ndata: {"de',
          'lta": "d"}\n\ndata: {"done": true}\n\n',
        ])
      )
    )
  );

  const out: string[] = [];
  for await (const d of streamSSE("/x", {})) out.push(d);

  expect(out).toEqual(["abc", "d"]);
});

test("aborting the signal stops further deltas mid-stream", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve(
        sseResponse([
          'data: {"delta": "a"}\n\n',
          'data: {"delta": "b"}\n\n',
          'data: {"delta": "c"}\n\n',
          'data: {"done": true}\n\n',
        ])
      )
    )
  );

  const controller = new AbortController();
  const out: string[] = [];
  for await (const d of streamSSE("/x", {}, controller.signal)) {
    out.push(d);
    controller.abort(); // cancel right after the first delta
  }

  expect(out).toEqual(["a"]); // no "b"/"c" appended after abort
});

test("streamSSE surfaces a leading meta event via onMeta without yielding it", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve(
        sseResponse([
          'data: {"meta": {"confidence": "strong_inference", "citations": []}}\n\n',
          'data: {"delta": "hi"}\n\n',
          'data: {"done": true}\n\n',
        ])
      )
    )
  );

  let meta: unknown;
  const out: string[] = [];
  for await (const d of streamSSE("/x", {}, undefined, (m) => (meta = m))) out.push(d);

  expect(out).toEqual(["hi"]); // meta is not yielded as a token
  expect(meta).toEqual({ confidence: "strong_inference", citations: [] });
});

test("streamSSE throws when the stream sends an error frame mid-flight", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve(
        sseResponse([
          'data: {"delta": "partial"}\n\n',
          'data: {"error": "generation_failed"}\n\n',
        ])
      )
    )
  );

  const out: string[] = [];
  await expect(async () => {
    for await (const d of streamSSE("/x", {})) out.push(d);
  }).rejects.toThrow("generation_failed");
  expect(out).toEqual(["partial"]); // tokens before the error still surfaced
});

test("streamSSE throws ApiError on a non-200 response", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(new Response("nope", { status: 500 })))
  );

  await expect(async () => {
    for await (const _ of streamSSE("/x", {})) void _;
  }).rejects.toThrow();
});
