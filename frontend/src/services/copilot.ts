import { apiFetch } from "./api";
import type { CopilotChatRequest, CopilotChatResponse } from "@/types/api";

export const copilotService = {
  chat: (req: CopilotChatRequest) =>
    apiFetch<CopilotChatResponse>("/copilot/chat", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  intents: () => apiFetch<{ intents: string[] }>("/copilot/intents"),
};
