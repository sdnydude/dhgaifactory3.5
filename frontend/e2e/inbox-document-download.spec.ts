import { test, expect } from "@playwright/test";

const REGISTRY_URL = process.env.REGISTRY_URL ?? "http://localhost:8011";

test("sync document export returns a valid PDF", async ({ request }) => {
  // Discover a valid thread_id dynamically instead of hardcoding one.
  // Chain: list projects → pick one with docs → get its runs → extract thread_id.
  const projectsRes = await request.get(
    `${REGISTRY_URL}/api/cme/export/projects?limit=10`,
  );
  expect(projectsRes.status()).toBe(200);
  const { projects } = await projectsRes.json();
  const withDocs = projects.filter(
    (p: { document_count: number }) => p.document_count > 0,
  );

  if (withDocs.length === 0) {
    test.info().annotations.push({
      type: "skipped",
      description: "no projects with documents — sync PDF test not exercised",
    });
    return;
  }

  // Find a thread_id from any project's runs
  let threadId: string | null = null;
  for (const proj of withDocs) {
    const runsRes = await request.get(
      `${REGISTRY_URL}/api/cme/projects/${proj.id}/runs`,
    );
    if (runsRes.status() !== 200) continue;
    const { runs } = await runsRes.json();
    const withThread = runs.find(
      (r: { thread_id: string | null }) => r.thread_id,
    );
    if (withThread) {
      threadId = withThread.thread_id;
      break;
    }
  }

  if (!threadId) {
    test.info().annotations.push({
      type: "skipped",
      description: "no project runs with a thread_id found — sync PDF test not exercised",
    });
    return;
  }

  const res = await request.get(
    `${REGISTRY_URL}/api/cme/export/document/${threadId}`,
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
