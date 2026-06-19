import { apiFetch } from "./api";

interface CoverLetterRequest {
  job_description: string;
  application_id?: string;
}

interface CoverLetterResponse {
  cover_letter_id: string;
  content_text: string;
  weak_inference_count: number;
  requires_approval: boolean;
}

export const coverLetterService = {
  generate: (req: CoverLetterRequest) =>
    apiFetch<CoverLetterResponse>("/cover-letter/generate", {
      method: "POST",
      body: JSON.stringify(req),
    }),
};
