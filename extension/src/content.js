/**
 * Phase 17.2 — content script. Runs ONLY when injected by the popup's explicit
 * click (via chrome.scripting on the activeTab) — there is no MutationObserver, no
 * auto-capture, no background read. It extracts the current page's job posting and
 * hands it to the background worker.
 */
import { extractFromHtml } from "./extract.mjs";

(async () => {
  const job = extractFromHtml(document.documentElement.outerHTML);
  job.job_url = location.href;
  const browser = (await import("../vendor/browser-polyfill.js")).default;
  await browser.runtime.sendMessage({ type: "acos:capture", payload: job });
})();
