import { isTauri } from "@/lib/ipc";

export interface PendingUpdate {
  version: string;
  notes: string;
  /** Verify-and-apply, then relaunch. Tauri checks the signature before install. */
  install: () => Promise<void>;
}

/**
 * Phase 13.9 (ADR-011) — check the single signed update channel.
 *
 * No-op in the browser / dev (no Tauri): returns null, so the only environment that
 * ever touches the network is the packaged app. The plugin is dynamically imported
 * inside the guard so a web build never bundles it.
 */
export async function checkForUpdate(): Promise<PendingUpdate | null> {
  if (!isTauri()) return null;
  const { check } = await import("@tauri-apps/plugin-updater");
  const update = await check();
  if (!update?.available) return null;
  return {
    version: update.version,
    notes: update.body ?? "",
    install: async () => {
      // downloadAndInstall verifies the artifact's minisign signature against the
      // bundled pubkey BEFORE applying; a tampered/unsigned artifact throws here and
      // is never installed (ADR-011 §2).
      await update.downloadAndInstall();
      const { relaunch } = await import("@tauri-apps/plugin-process");
      await relaunch();
    },
  };
}
