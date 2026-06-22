/// <reference types="vitest/config" />
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

// Unit-test config (Phase 11.5). Playwright owns e2e; vitest owns the pure
// logic (motion flattening, transient store no-rerender). jsdom for the few
// tests that mount React.
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
