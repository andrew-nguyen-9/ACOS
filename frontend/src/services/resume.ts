import { apiFetch } from "./api";
import type {
  ResumeGenerateRequest,
  ResumeGenerateResponse,
} from "@/types/api";

export const resumeService = {
  generate: (req: ResumeGenerateRequest) =>
    apiFetch<ResumeGenerateResponse>("/resume/generate", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  exportDocx: async (resumeId: string): Promise<Blob> => {
    const res = await fetch(
      `http://localhost:8000/api/v1/resume/${resumeId}/export`,
      { method: "GET" }
    );
    if (!res.ok) throw new Error("Export failed");
    return res.blob();
  },
};
