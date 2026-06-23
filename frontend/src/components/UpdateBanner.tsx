import { useEffect, useState } from "react";
import { Download, Loader2, AlertTriangle } from "lucide-react";
import { checkForUpdate, type PendingUpdate } from "@/services/updater";

/**
 * 13.9 release-notes surface. Checks the signed update channel on mount; when an
 * update is available, shows the new version + notes and a user-triggered Update
 * button. Silent in the browser/dev (checkForUpdate returns null off-Tauri).
 */
export function UpdateBanner() {
  const [pending, setPending] = useState<PendingUpdate | null>(null);
  const [installing, setInstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    checkForUpdate()
      .then(setPending)
      .catch(() => {}); // a failed check must never disrupt the app (ADR-011 §5)
  }, []);

  if (!pending) return null;

  async function update() {
    setInstalling(true);
    setError(null);
    try {
      await pending!.install();
    } catch (e) {
      // verification/download failure leaves the current version intact (atomicity)
      setInstalling(false);
      setError(e instanceof Error ? e.message : "Update failed — still on the current version.");
    }
  }

  return (
    <div
      data-testid="update-banner"
      className="mx-6 mt-4 flex items-start gap-3 rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-4 py-3"
    >
      <Download className="size-4 text-indigo-300 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-neutral-100">
          Update available — v{pending.version}
        </p>
        {pending.notes && (
          <p className="text-xs text-neutral-400 mt-0.5 whitespace-pre-line" data-testid="update-notes">
            {pending.notes}
          </p>
        )}
        {error && (
          <p className="flex items-center gap-1.5 text-xs text-red-400 mt-1">
            <AlertTriangle className="size-3.5" /> {error}
          </p>
        )}
      </div>
      <button
        onClick={() => void update()}
        disabled={installing}
        data-testid="update-install"
        className="inline-flex items-center gap-1.5 py-1.5 px-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition disabled:opacity-50"
      >
        {installing ? <Loader2 className="size-3.5 animate-spin" /> : null}
        {installing ? "Updating…" : "Update & Relaunch"}
      </button>
    </div>
  );
}
