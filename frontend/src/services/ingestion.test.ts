import { afterEach, expect, test, vi } from "vitest";
import { ingestDocument, getOnboardingSummary } from "./ingestion";

afterEach(() => vi.restoreAllMocks());

test("ingestDocument POSTs multipart form-data to /ingest (no JSON content-type)", async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ job_id: "abc", status: "queued" }), { status: 202 }),
  );
  vi.stubGlobal("fetch", fetchMock);

  const file = new File(["resume text"], "resume.pdf", { type: "application/pdf" });
  const res = await ingestDocument(file);

  expect(res.job_id).toBe("abc");
  const [url, init] = fetchMock.mock.calls[0];
  expect(url).toMatch(/\/ingest$/);
  expect(init.method).toBe("POST");
  expect(init.body).toBeInstanceOf(FormData);
  // Must NOT force application/json — the browser sets the multipart boundary.
  expect(init.headers?.["Content-Type"]).toBeUndefined();
});

test("ingestDocument surfaces a rejected upload as an error", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response("too large", { status: 422 })),
  );
  const file = new File(["x"], "huge.pdf");
  await expect(ingestDocument(file)).rejects.toThrow();
});

test("getOnboardingSummary fetches the summary endpoint", async () => {
  const payload = { skills: [], documents: { count: 0 }, career_voice: { synthetic: true } };
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 })),
  );
  const summary = await getOnboardingSummary();
  expect(summary.career_voice.synthetic).toBe(true);
});
