/**
 * Phase 16.1 (ADR-014) — auth gate.
 *
 * Renders children only once a session token is held. Otherwise prompts: enroll
 * (set the account passphrase on first run) or unlock (login). Local-first — there
 * is no password reset (ADR-001/014): the warning text says so honestly.
 */
import { useEffect, useState, type ReactNode } from "react";
import { enroll, getAuthStatus, getToken, login, restoreSession } from "@/services/auth";
import { ApiError } from "@/services/api";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

type Phase = "checking" | "enroll" | "login" | "authed";

export default function AuthGate({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<Phase>("checking");
  const [secret, setSecret] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      await restoreSession();
      if (getToken()) {
        setPhase("authed");
        return;
      }
      try {
        const { enrolled } = await getAuthStatus();
        setPhase(enrolled ? "login" : "enroll");
      } catch {
        // Backend not reachable yet — App's own backend-error screen handles it.
        setPhase("enroll");
      }
    })();
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (phase === "enroll") await enroll(secret);
      else await login(secret);
      setSecret("");
      setPhase("authed");
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "Incorrect passphrase."
          : "Something went wrong. Try again.",
      );
    } finally {
      setBusy(false);
    }
  };

  if (phase === "authed") return <>{children}</>;
  if (phase === "checking")
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );

  const enrolling = phase === "enroll";
  return (
    <div className="min-h-screen bg-[#09090b] text-white flex items-center justify-center">
      <form onSubmit={submit} className="w-80 space-y-4">
        <h1 className="text-xl font-semibold">
          {enrolling ? "Set your passphrase" : "Unlock ACOS"}
        </h1>
        <input
          type="password"
          autoFocus
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          placeholder="Passphrase"
          aria-label="Passphrase"
          className="w-full rounded bg-gray-900 border border-gray-700 px-3 py-2 text-sm outline-none focus:border-gray-400"
        />
        {error && <p className="text-sm text-red-400">{error}</p>}
        {enrolling && (
          <p className="text-xs text-gray-500">
            Stored only on this device. There is no reset — if you forget it, and
            encryption is on, that data is unrecoverable.
          </p>
        )}
        <button
          type="submit"
          disabled={busy || !secret}
          className="w-full rounded bg-white text-black py-2 text-sm font-medium disabled:opacity-40"
        >
          {busy ? "…" : enrolling ? "Create" : "Unlock"}
        </button>
      </form>
    </div>
  );
}
