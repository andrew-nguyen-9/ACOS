import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// jsdom path: isTauri() is false, so the token persists to sessionStorage.
import { enroll, getToken, login, logout, restoreSession } from "@/services/auth";
import { apiFetch, setAuthToken } from "@/services/api";

vi.mock("@/services/api", async () => {
  const actual = await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return { ...actual, apiFetch: vi.fn() };
});

const mockFetch = apiFetch as unknown as ReturnType<typeof vi.fn>;

describe("auth service", () => {
  beforeEach(() => {
    sessionStorage.clear();
    setAuthToken(null);
    mockFetch.mockReset();
  });
  afterEach(() => sessionStorage.clear());

  it("enroll stores the returned token (memory + sessionStorage)", async () => {
    mockFetch.mockResolvedValueOnce({ token: "tok-123" });
    await enroll("hunter2");
    expect(getToken()).toBe("tok-123");
    expect(sessionStorage.getItem("session-token")).toBe("tok-123");
  });

  it("login stores the token", async () => {
    mockFetch.mockResolvedValueOnce({ token: "tok-login" });
    await login("hunter2");
    expect(getToken()).toBe("tok-login");
  });

  it("restoreSession rehydrates token from persistence", async () => {
    sessionStorage.setItem("session-token", "persisted");
    const t = await restoreSession();
    expect(t).toBe("persisted");
    expect(getToken()).toBe("persisted");
  });

  it("logout clears the token even if the request fails", async () => {
    mockFetch.mockResolvedValueOnce({ token: "tok" });
    await login("pw");
    mockFetch.mockRejectedValueOnce(new Error("network"));
    await logout();
    expect(getToken()).toBeNull();
    expect(sessionStorage.getItem("session-token")).toBeNull();
  });
});
