import { ApiError } from "./api";
import type {
  ResumeGenerateRequest,
  ResumeGenerateResponse,
} from "@/types/api";

const BASE_URL = "http://localhost:8000/api/v1";

export const resumeService = {
  generate: async (req: ResumeGenerateRequest): Promise<ResumeGenerateResponse> => {
    const res = await fetch(`${BASE_URL}/resume/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new ApiError(res.status, body || res.statusText);
    }
    return res.json() as Promise<ResumeGenerateResponse>;
  },

  exportDocx: async (req: ResumeGenerateRequest): Promise<Blob> => {
    const res = await fetch(`${BASE_URL}/resume/generate/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new ApiError(res.status, "Export failed");
    return res.blob();
  },
};
