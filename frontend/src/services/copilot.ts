import { apiFetch } from "./api";
import { streamSSE } from "./stream";
import type { CopilotChatRequest, CopilotChatResponse } from "@/types/api";

/** Streamed answers carry everything but `response` (which arrives as tokens). */
export type CopilotChatMeta = Omit<CopilotChatResponse, "response">;

export const copilotService = {
  chat: (req: CopilotChatRequest) =>
    apiFetch<CopilotChatResponse>("/copilot/chat", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  /**
   * Streaming chat (12.4): yields answer tokens as they arrive. `onMeta` fires
   * once with citations/confidence before the first token; pass an AbortController
   * signal and abort it to cancel — that frees the backend Ollama job.
   */
  chatStream: (
    req: CopilotChatRequest,
    signal?: AbortSignal,
    onMeta?: (meta: CopilotChatMeta) => void
  ): AsyncGenerator<string> =>
    streamSSE(
      "/copilot/chat/stream",
      req,
      signal,
      onMeta as ((m: unknown) => void) | undefined
    ),

  intents: () => apiFetch<{ intents: string[] }>("/copilot/intents"),

  /**
   * Inline ghost completion (COP-003): reuse the existing chat endpoint to get a
   * short continuation for the partial input. No new backend — we trim the reply
   * to a single leading clause so it reads as a suggested completion, not an essay.
   */
  complete: async (partial: string): Promise<string> => {
    const res = await copilotService.chat({ message: partial });
    return res.response.split(/(?<=[.!?])\s/)[0]?.trim() ?? "";
  },
};
