import { apiFetch } from "./api";
import type { CopilotChatRequest, CopilotChatResponse } from "@/types/api";

export const copilotService = {
  chat: (req: CopilotChatRequest) =>
    apiFetch<CopilotChatResponse>("/copilot/chat", {
      method: "POST",
      body: JSON.stringify(req),
    }),
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
