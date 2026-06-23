/**
 * Phase 16.1 (ADR-014) — client auth.
 *
 * The bearer token is held in memory and persisted to the OS Keychain via the
 * Tauri `keychain_*` commands (web/dev/jsdom falls back to sessionStorage). The
 * long-lived account *secret* the user types is never stored here — it's exchanged
 * for a token at enroll/login and only the token is kept.
 */
import { apiFetch, setAuthToken } from "@/services/api";
import { isTauri } from "@/lib/ipc";

const ACCOUNT = "session-token";

let token: string | null = null;

async function persist(value: string | null): Promise<void> {
  if (isTauri()) {
    const { invoke } = await import("@tauri-apps/api/core");
    if (value === null) await invoke("keychain_delete", { account: ACCOUNT });
    else await invoke("keychain_set", { account: ACCOUNT, secret: value });
    return;
  }
  if (value === null) sessionStorage.removeItem(ACCOUNT);
  else sessionStorage.setItem(ACCOUNT, value);
}

async function loadPersisted(): Promise<string | null> {
  if (isTauri()) {
    const { invoke } = await import("@tauri-apps/api/core");
    return (await invoke<string | null>("keychain_get", { account: ACCOUNT })) ?? null;
  }
  return sessionStorage.getItem(ACCOUNT);
}

export function getToken(): string | null {
  return token;
}

async function setToken(value: string | null): Promise<void> {
  token = value;
  setAuthToken(value);
  await persist(value);
}

/** Re-hydrate the in-memory token from the Keychain on app start. */
export async function restoreSession(): Promise<string | null> {
  token = await loadPersisted();
  setAuthToken(token);
  return token;
}

export async function getAuthStatus(): Promise<{ enrolled: boolean }> {
  return apiFetch<{ enrolled: boolean }>("/auth/status");
}

export async function enroll(secret: string): Promise<void> {
  const { token: t } = await apiFetch<{ token: string }>("/auth/enroll", {
    method: "POST",
    body: JSON.stringify({ secret }),
  });
  await setToken(t);
}

export async function login(secret: string): Promise<void> {
  const { token: t } = await apiFetch<{ token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ secret }),
  });
  await setToken(t);
}

export async function logout(): Promise<void> {
  // Best-effort server-side invalidation; clearing the local token is what matters,
  // so a failed request never blocks logout.
  try {
    await apiFetch("/auth/logout", { method: "POST" });
  } catch {
    /* ignore */
  }
  await setToken(null);
}
