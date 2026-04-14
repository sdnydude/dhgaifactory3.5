import { test, expect } from "@playwright/test";

const REGISTRY_URL = process.env.REGISTRY_URL ?? "http://localhost:8011";
const SMOKE_THREAD_ID = process.env.SMOKE_THREAD_ID ?? "6878b142-a4f2-44d0-983d-4e545637fdea";

test("sync document export returns a valid PDF", async ({ request }) => {
  const res = await request.get(
    `${REGISTRY_URL}/api/cme/export/document/${SMOKE_THREAD_ID}`,
    { timeout: 120_000 },
  );
  expect(res.status()).toBe(200);
  expect(res.headers()["content-type"]).toContain("application/pdf");
  expect(res.headers()["content-disposition"]).toContain("attachment");

  const buf = await res.body();
  expect(buf.subarray(0, 5).toString()).toBe("%PDF-");
  expect(buf.length).toBeGreaterThan(2048);
});

test("inbox page renders and exposes the download button in the masthead when a review is selected", async ({
  page,
}) => {
  const reviewsResponse = page.waitForResponse(
    (r) => r.url().includes("/inbox") || r.url().includes("/threads"),
    { timeout: 15_000 },
  ).catch(() => null);

  await page.goto("/inbox");
  await reviewsResponse;

  const reviewCard = page.locator('[data-testid="review-card"], button:has-text("Grant"), button:has-text("Needs")').first();
  const hasPending = await reviewCard.isVisible({ timeout: 5_000 }).catch(() => false);

  if (!hasPending) {
    test.info().annotations.push({
      type: "skipped",
      description: "no pending interrupted threads in LangGraph cloud — UI click path not exercised (API path already covered by the first test)",
    });
    return;
  }

  await reviewCard.click();
  const downloadButton = page.getByRole("button", { name: /download document/i });
  await expect(downloadButton).toBeVisible();
  await expect(downloadButton).toBeEnabled();

  const downloadPromise = page.waitForEvent("download", { timeout: 120_000 });
  await downloadButton.click();
  const download = await downloadPromise;

  const path = await download.path();
  expect(path).toBeTruthy();
  const fs = await import("node:fs");
  const buf = fs.readFileSync(path!);
  expect(buf.subarray(0, 5).toString()).toBe("%PDF-");
  expect(buf.length).toBeGreaterThan(2048);
});
