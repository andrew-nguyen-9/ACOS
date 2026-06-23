import { ApiError } from "./api";

const BASE = "http://localhost:8000/api/v1";

/**
 * POST `body` to an SSE endpoint and yield each `{delta}` token as it arrives
 * (Phase 12.4). Stops on the terminal `{done:true}` event, on stream end, or
 * when `signal` aborts — the abort also tears down the fetch, which closes the
 * socket and frees the Ollama GPU job on the backend.
 *
 * Buffers across read-chunk boundaries so an SSE event split mid-JSON between
 * two TCP reads is still parsed once whole.
 */
export async function* streamSSE(
  path: string,
  body: unknown,
  signal?: AbortSignal,
  onMeta?: (meta: unknown) => void
): AsyncGenerator<string> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    const text = res.ok ? "missing response body" : await res.text().catch(() => "");
    throw new ApiError(res.status, text || res.statusText);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      if (signal?.aborted) return;
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        if (signal?.aborted) return;
        const event = buffer.slice(0, sep).trim();
        buffer = buffer.slice(sep + 2);
        if (!event.startsWith("data:")) continue;
        let payload;
        try {
          payload = JSON.parse(event.slice("data:".length).trim());
        } catch {
          continue; // tolerate a malformed line, like the backend's NDJSON parser
        }
        if (payload.error) throw new ApiError(500, payload.error);
        if (payload.meta !== undefined) {
          onMeta?.(payload.meta); // leading non-token event (e.g. citations)
          continue;
        }
        if (payload.done) return;
        if (typeof payload.delta === "string") yield payload.delta;
      }
    }
  } finally {
    // Best-effort: release the lock / cancel the body if we exit early (abort).
    reader.cancel().catch(() => {});
  }
}

/**
 * GET an SSE endpoint and yield each `data: {json}` frame as a parsed object
 * (Phase 13.7). Same `data: {…}\n\n` framing + chunk-boundary buffering as
 * {@link streamSSE}, but for progress streams whose frames are arbitrary objects
 * (status/completed/total) rather than token deltas. Aborting tears down the
 * fetch, which cancels the underlying pull on the backend.
 */
export async function* streamProgress(
  path: string,
  signal?: AbortSignal
): AsyncGenerator<Record<string, unknown>> {
  const res = await fetch(`${BASE}${path}`, { signal });
  if (!res.ok || !res.body) {
    const text = res.ok ? "missing response body" : await res.text().catch(() => "");
    throw new ApiError(res.status, text || res.statusText);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      if (signal?.aborted) return;
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        if (signal?.aborted) return;
        const event = buffer.slice(0, sep).trim();
        buffer = buffer.slice(sep + 2);
        if (!event.startsWith("data:")) continue;
        try {
          yield JSON.parse(event.slice("data:".length).trim());
        } catch {
          continue;
        }
      }
    }
  } finally {
    reader.cancel().catch(() => {});
  }
}
