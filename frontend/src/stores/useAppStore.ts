import { create } from "zustand";

type OllamaStatus = "unknown" | "online" | "offline";

interface AppState {
  ollamaStatus: OllamaStatus;
  setOllamaStatus: (status: OllamaStatus) => void;
}

export const useAppStore = create<AppState>((set) => ({
  ollamaStatus: "unknown",
  setOllamaStatus: (status) => set({ ollamaStatus: status }),
}));
