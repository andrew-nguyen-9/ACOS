/**
 * Phase 17 popup — pairing + the explicit capture trigger. Capture injects the
 * content script into the ACTIVE TAB only, after a user click (activeTab perm).
 */
import browser from "../vendor/browser-polyfill.js";

const $ = (id) => document.getElementById(id);

function setStatus(text, cls = "") {
  const el = $("status");
  el.textContent = text;
  el.className = "status " + cls;
}

$("pair").addEventListener("click", async () => {
  const token = $("token").value.trim();
  if (!token) return;
  await browser.runtime.sendMessage({ type: "acos:setToken", token });
  $("token").value = "";
  setStatus("Paired with ACOS.", "ok");
});

$("capture").addEventListener("click", async () => {
  setStatus("Capturing…");
  $("capture").disabled = true;
  try {
    const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
    // Inject the content script into the active tab only — explicit, user-gestured.
    const results = await browser.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["src/content.js"],
    });
    void results;
    setStatus("Sent to ACOS — review the draft in the app.", "ok");
  } catch (e) {
    setStatus("Capture failed. Is ACOS open?", "err");
  } finally {
    $("capture").disabled = false;
  }
});
