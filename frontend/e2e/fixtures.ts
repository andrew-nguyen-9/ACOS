import { test as base, Page } from "@playwright/test";

// ── Canonical mock payloads ──────────────────────────────────────────────────
export const MOCK_RESUME_RESPONSE = {
  resume_id: "abc123def456abc123def456abc12345",
  content_json: {
    experiences: [
      {
        title: "Data Engineer",
        company: "Acme Corp",
        dates: "2022–2024",
        bullets: [
          {
            text: "Built Python ETL pipeline reducing costs by 40%",
            evidence_id: "b1",
            confidence: "verified",
          },
        ],
      },
    ],
    skills: ["Python", "ETL", "SQL"],
    projects: [],
    education: [],
  },
  ats_score: {
    overall_score: 85,
    keyword_score: 88,
    skill_score: 82,
    experience_score: 80,
    industry_score: 90,
    matched_keywords: ["Python", "ETL"],
    missing_keywords: [],
    explanation: "Strong match for this role.",
  },
  weak_inference_count: 0,
  requires_approval: false,
};

export const MOCK_COVER_LETTER_RESPONSE = {
  cover_letter_id: "cl-uuid-1234",
  content_text:
    "Dear Hiring Manager,\n\nI am excited to apply for the Software Engineer position at Acme Corp.\n\nSincerely,",
  weak_inference_count: 0,
  requires_approval: false,
};

export const MOCK_COPILOT_RESPONSE = {
  response:
    "Based on your experience, you have strong Python and data engineering skills.",
  intent: "resume_help",
  confidence: "verified",
  citations: [
    {
      source: "acos_experiences",
      text: "Built Python ETL pipeline",
      confidence: "verified",
      similarity: 0.92,
    },
  ],
  evidence_count: 1,
};

export const MOCK_APPLICATION = {
  id: "app-uuid-1234-5678-9012-345678901234",
  company: "Acme Corp",
  role: "Software Engineer",
  status: "applied",
  created_at: "2026-06-19T10:00:00",
};

export const MOCK_APPLICATIONS_LIST = [MOCK_APPLICATION];

// ── Fixture type ─────────────────────────────────────────────────────────────
type Fixtures = {
  mockApi: void;
};

// ── Extended test with API mocks ──────────────────────────────────────────────
export const test = base.extend<Fixtures>({
  mockApi: [
    async ({ page }: { page: Page }, use: () => Promise<void>) => {
      // Resume generate — used by both ResumePage and AtsPage
      await page.route("**/api/v1/resume/generate", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(MOCK_RESUME_RESPONSE),
        });
      });

      // Cover letter generate
      await page.route("**/api/v1/cover-letter/generate", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(MOCK_COVER_LETTER_RESPONSE),
        });
      });

      // Copilot chat
      await page.route("**/api/v1/copilot/chat", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(MOCK_COPILOT_RESPONSE),
        });
      });

      // Applications: use a single regex route to distinguish collection vs individual
      // /applications/ (trailing slash only) = collection; /applications/{id}/ = individual
      await page.route(/\/api\/v1\/applications/, async (route) => {
        const url = route.request().url();
        const method = route.request().method();
        const isCollection = /\/api\/v1\/applications\/$/.test(url);

        if (isCollection) {
          if (method === "GET") {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify(MOCK_APPLICATIONS_LIST),
            });
          } else if (method === "POST") {
            await route.fulfill({
              status: 201,
              contentType: "application/json",
              body: JSON.stringify(MOCK_APPLICATION),
            });
          } else {
            await route.continue();
          }
        } else {
          // Individual application CRUD
          if (method === "GET") {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify(MOCK_APPLICATION),
            });
          } else if (method === "PATCH") {
            await route.fulfill({
              status: 200,
              contentType: "application/json",
              body: JSON.stringify({ ...MOCK_APPLICATION, status: "interviewing" }),
            });
          } else if (method === "DELETE") {
            await route.fulfill({ status: 204, body: "" });
          } else {
            await route.continue();
          }
        }
      });

      // Health check
      await page.route("**/api/v1/health", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ status: "healthy", ollama: { available: true } }),
        });
      });

      await use();
    },
    { auto: true },
  ],
});

export { expect } from "@playwright/test";
