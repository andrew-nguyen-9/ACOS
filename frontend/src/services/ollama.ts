import { streamProgress } from "./stream";

export interface PullProgress {
  status?: string;
  completed?: number;
  total?: number;
  error?: string;
  done?: boolean;
}

/**
 * Pull an Ollama model, reporting streamed progress (Phase 13.7). Always
 * user-initiated (a multi-GB download is never silent). Resolves on the terminal
 * `done` frame; throws if the backend reports an error frame.
 */
export async function pullModel(
  model: string,
  onProgress: (p: PullProgress) => void,
  signal?: AbortSignal,
): Promise<void> {
  for await (const frame of streamProgress(
    `/ollama/pull?model=${encodeURIComponent(model)}`,
    signal,
  )) {
    const p = frame as PullProgress;
    if (p.error) throw new Error(p.error);
    onProgress(p);
    if (p.done) return;
  }
}
