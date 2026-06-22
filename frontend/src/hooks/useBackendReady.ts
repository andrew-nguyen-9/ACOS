import { useEffect, useState } from "react";

/**
 * Sidecar warmup gate (Phase 12.3, UI-002).
 *
 * Polls the backend `/health` endpoint until it answers, so the shell can show a
 * skeleton during the Python cold-start window and swap to live UI the moment the
 * port binds. `error` is non-terminal: it only surfaces after `maxAttempts`
 * failures (so a normal warmup never flashes an error), and polling continues —
 * a late boot still recovers to `ready`.
 */
export type BackendStatus = "loading" | "ready" | "error";

const HEALTH_URL = "http://localhost:8000/api/v1/health";

interface Options {
  maxAttempts?: number;
  baseDelay?: number;
  maxDelay?: number;
}

export function useBackendReady(
  url: string = HEALTH_URL,
  { maxAttempts = 5, baseDelay = 300, maxDelay = 3000 }: Options = {},
): BackendStatus {
  const [status, setStatus] = useState<BackendStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let attempt = 0;

    const poll = async () => {
      try {
        const res = await fetch(url);
        if (cancelled) return;
        if (res.ok) {
          setStatus("ready");
          return; // bound — stop polling
        }
        throw new Error(`health ${res.status}`);
      } catch {
        if (cancelled) return;
        attempt += 1;
        // Hold "loading" through the warmup budget; only call it an error once
        // the backend has stayed unreachable past maxAttempts.
        setStatus(attempt >= maxAttempts ? "error" : "loading");
        const delay = Math.min(baseDelay * 2 ** (attempt - 1), maxDelay);
        timer = setTimeout(poll, delay);
      }
    };

    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [url, maxAttempts, baseDelay, maxDelay]);

  return status;
}
