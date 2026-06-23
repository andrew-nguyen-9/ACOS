import { afterEach, expect, test, vi } from "vitest";

const { isTauri } = vi.hoisted(() => ({ isTauri: vi.fn() }));
vi.mock("@/lib/ipc", () => ({ isTauri }));

const { check } = vi.hoisted(() => ({ check: vi.fn() }));
vi.mock("@tauri-apps/plugin-updater", () => ({ check }));

const { relaunch } = vi.hoisted(() => ({ relaunch: vi.fn() }));
vi.mock("@tauri-apps/plugin-process", () => ({ relaunch }));

import { checkForUpdate } from "./updater";

afterEach(() => vi.clearAllMocks());

test("off-Tauri (browser/dev) makes no network call and returns null", async () => {
  isTauri.mockReturnValue(false);
  expect(await checkForUpdate()).toBeNull();
  expect(check).not.toHaveBeenCalled(); // the only env that hits the network is the packaged app
});

test("no update available returns null", async () => {
  isTauri.mockReturnValue(true);
  check.mockResolvedValue({ available: false });
  expect(await checkForUpdate()).toBeNull();
});

test("available update surfaces version + notes and installs verify-then-relaunch", async () => {
  isTauri.mockReturnValue(true);
  const downloadAndInstall = vi.fn().mockResolvedValue(undefined);
  check.mockResolvedValue({ available: true, version: "0.2.0", body: "Bug fixes", downloadAndInstall });

  const pending = await checkForUpdate();
  expect(pending).toEqual(expect.objectContaining({ version: "0.2.0", notes: "Bug fixes" }));

  await pending!.install();
  expect(downloadAndInstall).toHaveBeenCalledTimes(1); // verifies signature before applying
  expect(relaunch).toHaveBeenCalledTimes(1);
});

test("a tampered/failed artifact propagates the error (never silently installs)", async () => {
  isTauri.mockReturnValue(true);
  const downloadAndInstall = vi.fn().mockRejectedValue(new Error("signature verification failed"));
  check.mockResolvedValue({ available: true, version: "0.2.0", body: "", downloadAndInstall });

  const pending = await checkForUpdate();
  await expect(pending!.install()).rejects.toThrow("signature verification failed");
  expect(relaunch).not.toHaveBeenCalled(); // failed verify ⇒ no relaunch, app intact
});
