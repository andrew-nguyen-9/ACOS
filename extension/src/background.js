/**
 * Phase 17 (ADR-019) — background service worker: the bridge client.
 *
 * Holds the one-time pairing token (in extension storage) and talks to the
 * app-gated localhost bridge. App closed → bridge unreachable → the capture is
 * queued (storage) and the popup shows "open ACOS to sync". NO background reads,
 * NO history/tab/cookie access — it only acts on a message from the content script
 * which itself only runs on an explicit click.
 */
import browser from "../vendor/browser-polyfill.js";

const BRIDGE = "http://localhost:8000/api/v1/bridge";

async function getToken() {
  const { pairingToken } = await browser.storage.local.get("pairingToken");
  return pairingToken || null;
}

async function postCapture(payload) {
  const token = await getToken();
  if (!token) return { ok: false, error: "not_paired" };
  try {
    const res = await fetch(`${BRIDGE}/capture`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Bridge-Token": token },
      body: JSON.stringify(payload),
    });
    if (!res.ok) return { ok: false, error: `http_${res.status}` };
    return { ok: true, result: await res.json() };
  } catch {
    // App closed / bridge down (ADR-019 §2): queue and tell the user to open ACOS.
    const { queued = [] } = await browser.storage.local.get("queued");
    queued.push(payload);
    await browser.storage.local.set({ queued });
    return { ok: false, error: "app_closed_queued" };
  }
}

browser.runtime.onMessage.addListener((msg) => {
  if (msg?.type === "acos:capture") return postCapture(msg.payload);
  if (msg?.type === "acos:setToken") return browser.storage.local.set({ pairingToken: msg.token });
  return undefined;
});
