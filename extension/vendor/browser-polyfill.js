/**
 * Minimal WebExtension API shim — single source for Chrome + Firefox (ADR-019 Q7).
 *
 * Firefox exposes the promise-based `browser.*`; Chrome MV3 exposes `chrome.*`,
 * which already returns promises for the APIs this extension uses (storage,
 * scripting, tabs, runtime.sendMessage). So a thin alias is enough — no full
 * webextension-polyfill dependency for this small surface. Swap in the real
 * `webextension-polyfill` here if a callback-only Chrome API is ever needed.
 */
const api = globalThis.browser ?? globalThis.chrome;
export default api;
