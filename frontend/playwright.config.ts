import { defineConfig, devices } from "@playwright/test";

// Smoke test against a running stack (`docker compose up`). Not part of `npm test`.
export default defineConfig({
  testDir: "e2e",
  timeout: 5 * 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
