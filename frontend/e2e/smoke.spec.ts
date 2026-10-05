// Login -> upload a synthetic video -> see the verdict. Needs E2E_EMAIL, E2E_PASSWORD and
// E2E_VIDEO (a path; CI writes one with backend/tests/fixtures/video_factory.py).
import path from "node:path";
import { expect, test } from "@playwright/test";

const email = process.env.E2E_EMAIL ?? "";
const password = process.env.E2E_PASSWORD ?? "";
const video = process.env.E2E_VIDEO ?? "";

test("login, upload, verdict", async ({ page }) => {
  test.skip(!email || !password || !video, "set E2E_EMAIL, E2E_PASSWORD and E2E_VIDEO");

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/$/);

  await page.goto("/upload");
  await page.getByLabel("Choose video files").setInputFiles(video);

  const name = path.basename(video);
  // Analysis runs in the worker; the badge appears once the job is done.
  const result = page.getByRole("link", { name: `Open inspection for ${name}` });
  await expect(result).toBeVisible({ timeout: 4 * 60_000 });
  await expect(result).toHaveText(/Pass|Review|Fail/);

  await result.click();
  await expect(page).toHaveURL(/\/videos\/\d+$/);
  await expect(page.getByText(/Accepted|Review required|Rejected/).first()).toBeVisible();
});
