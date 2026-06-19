import { apiFetch } from "./api";
import type { Application, ApplicationCreate } from "@/types/api";

export const applicationsService = {
  list: () => apiFetch<Application[]>("/applications/"),
  get: (id: string) => apiFetch<Application>(`/applications/${id}`),
  create: (data: ApplicationCreate) =>
    apiFetch<Application>("/applications/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<ApplicationCreate>) =>
    apiFetch<Application>(`/applications/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    apiFetch<void>(`/applications/${id}`, { method: "DELETE" }),
};
