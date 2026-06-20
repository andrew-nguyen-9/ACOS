import { apiFetch } from "./api";

export async function getSettings(): Promise<Record<string, string>> {
  const data = await apiFetch<{ settings: Record<string, string> }>("/settings");
  return data.settings;
}

export async function updateSetting(key: string, value: string): Promise<void> {
  await apiFetch<{ key: string; value: string }>(`/settings/${key}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  });
}

export async function getOnboardingStatus(): Promise<boolean> {
  const data = await apiFetch<{ completed: boolean }>("/settings/onboarding");
  return data.completed;
}

export async function completeOnboarding(): Promise<void> {
  await apiFetch<{ completed: boolean }>("/settings/onboarding/complete", {
    method: "POST",
  });
}
