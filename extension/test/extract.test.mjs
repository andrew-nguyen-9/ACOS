/**
 * Phase 17.2/17.5 — runnable tests (node --test, no deps): extraction heuristics
 * + the Phase-17 minimal-permission strict rule on the manifest.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { extractFromHtml } from "../src/extract.mjs";

const FIXTURE = `
<html><head><title>Acme — Careers</title>
<meta property="og:site_name" content="Acme Corp"></head>
<body>
  <h1>Senior Product Manager</h1>
  <h2>Responsibilities</h2>
  <ul><li>Own the roadmap</li><li>Work cross-functionally</li></ul>
  <h2>Qualifications</h2>
  <ul><li>5+ years PM experience</li><li>SQL and analytics</li></ul>
  <h2>Benefits</h2>
  <p>Health, 401k</p>
</body></html>`;

test("extracts the four job fields", () => {
  const job = extractFromHtml(FIXTURE);
  assert.equal(job.title, "Senior Product Manager");
  assert.equal(job.company, "Acme Corp");
  assert.match(job.responsibilities, /roadmap/);
  assert.match(job.qualifications, /5\+ years/);
  assert.equal(job.confidence, "high");
});

test("strips scripts and markup", () => {
  const job = extractFromHtml(
    "<h1>Role</h1><script>steal()</script><p>Responsibilities</p>"
  );
  assert.ok(!job.raw_text.includes("steal()"));
  assert.ok(!job.raw_text.includes("<"));
});

test("thin page yields low/none confidence, never fabricated", () => {
  const job = extractFromHtml("<html><body><p>hello</p></body></html>");
  assert.ok(["low", "none"].includes(job.confidence));
  assert.equal(job.responsibilities, "");
});

test("manifest requests only minimal permissions (no tracking)", async () => {
  const manifest = JSON.parse(await readFile(new URL("../manifest.json", import.meta.url)));
  const forbidden = ["history", "tabs", "cookies", "webNavigation", "webRequest", "<all_urls>", "bookmarks"];
  const perms = [...(manifest.permissions || []), ...(manifest.host_permissions || [])];
  for (const f of forbidden) {
    assert.ok(!perms.includes(f), `manifest must not request ${f}`);
  }
  assert.ok(perms.includes("activeTab"), "needs activeTab for explicit capture");
  assert.ok(!manifest.host_permissions, "no broad host permissions allowed");
});
