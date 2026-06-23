import { apiFetch } from "./api";

/** Phase 17 (ADR-019): mint a one-time pairing token to paste into the extension. */
export async function generatePairingToken(): Promise<string> {
  const data = await apiFetch<{ pairing_token: string }>("/bridge/pairing-token", {
    method: "POST",
  });
  return data.pairing_token;
}
