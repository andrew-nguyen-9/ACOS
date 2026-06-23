import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { OnboardingSummary } from "@/types/onboarding";

const { ingestDocument, pollIngest, getOnboardingSummary } = vi.hoisted(() => ({
  ingestDocument: vi.fn(),
  pollIngest: vi.fn(),
  getOnboardingSummary: vi.fn(),
}));
vi.mock("@/services/ingestion", () => ({ ingestDocument, pollIngest, getOnboardingSummary }));

import { UploadStep } from "./UploadStep";

function summary(over: Partial<OnboardingSummary> = {}): OnboardingSummary {
  return {
    skills: [
      { label: "Python", confidence: "strong_inference" },
      { label: "SQL", confidence: "weak_inference" },
    ],
    documents: { count: 1 },
    career_voice: {
      tone_descriptors: ["professional"],
      structure_patterns: [],
      sample_sentences: ["I bring proven results."],
      synthetic: false,
    },
    ...over,
  };
}

beforeEach(() => {
  ingestDocument.mockResolvedValue({ job_id: "job1" });
  pollIngest.mockImplementation(async (_id, onUpdate) => {
    const done = { job_id: "job1", status: "done" as const };
    onUpdate(done);
    return done;
  });
  getOnboardingSummary.mockResolvedValue(summary());
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function pick(name = "resume.pdf") {
  const input = screen.getByTestId("onboarding-file-input");
  const file = new File(["x"], name, { type: "application/pdf" });
  fireEvent.change(input, { target: { files: [file] } });
}

test("selecting a file uploads it to the ingestion endpoint", async () => {
  render(<UploadStep />);
  pick();
  await waitFor(() => expect(ingestDocument).toHaveBeenCalledTimes(1));
  expect(ingestDocument.mock.calls[0][0]).toBeInstanceOf(File);
});

test("renders extracted skills with confidence badges after build", async () => {
  render(<UploadStep />);
  pick();
  const chips = await screen.findByTestId("skill-chips");
  expect(chips.textContent).toContain("Python");
  expect(chips.textContent).toContain("Strong");
  expect(chips.textContent).toContain("Weak");
});

test("a synthetic Career-Voice is clearly labeled", async () => {
  getOnboardingSummary.mockResolvedValue(
    summary({ career_voice: { tone_descriptors: ["x"], structure_patterns: [], sample_sentences: [], synthetic: true } }),
  );
  render(<UploadStep />);
  pick();
  expect(await screen.findByTestId("synthetic-label")).toBeTruthy();
});

test("a real Career-Voice shows no synthetic label", async () => {
  getOnboardingSummary.mockResolvedValue(summary()); // synthetic: false
  render(<UploadStep />);
  pick();
  await screen.findByTestId("summary");
  expect(screen.queryByTestId("synthetic-label")).toBeNull();
});

test("a failed upload is shown inline without crashing the step", async () => {
  ingestDocument.mockRejectedValueOnce(new Error("Unsupported file type"));
  render(<UploadStep />);
  pick("bad.exe");
  await waitFor(() => expect(screen.getByTestId("file-list").textContent).toContain("Unsupported file type"));
});
