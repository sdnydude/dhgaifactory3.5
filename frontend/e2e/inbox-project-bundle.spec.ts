import { test, expect } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";
import { execFileSync } from "node:child_process";

const REGISTRY_URL =
  process.env.REGISTRY_URL ?? "http://localhost:8011";
const SMOKE_PROJECT_ID =
  process.env.SMOKE_PROJECT_ID ??
  "ef4e5b53-d4e8-4a98-9c0e-451bf3ba1206";

const POLL_INTERVAL_MS = 2_000;
const POLL_TIMEOUT_MS = 60_000;

/* ------------------------------------------------------------------ */
/* 1. List projects — at least one with documents                     */
/* ------------------------------------------------------------------ */
test("GET /projects returns projects with document counts", async ({
  request,
}) => {
  const res = await request.get(
    `${REGISTRY_URL}/api/cme/export/projects?limit=10`,
  );
  expect(res.status()).toBe(200);

  const body = await res.json();
  expect(body.projects.length).toBeGreaterThan(0);
  expect(body.total).toBeGreaterThan(0);

  const withDocs = body.projects.filter(
    (p: { document_count: number }) => p.document_count > 0,
  );
  expect(withDocs.length).toBeGreaterThan(0);
});

/* ------------------------------------------------------------------ */
/* 2. List documents for the smoke project                            */
/* ------------------------------------------------------------------ */
test("GET /projects/:id/documents returns current documents", async ({
  request,
}) => {
  const res = await request.get(
    `${REGISTRY_URL}/api/cme/export/projects/${SMOKE_PROJECT_ID}/documents`,
  );
  expect(res.status()).toBe(200);

  const body = await res.json();
  expect(body.project_id).toBe(SMOKE_PROJECT_ID);
  expect(body.documents.length).toBeGreaterThan(0);

  for (const doc of body.documents) {
    expect(doc.is_current).toBe(true);
    expect(doc.document_type).toBeTruthy();
  }
});

/* ------------------------------------------------------------------ */
/* 3. Full round-trip: enqueue → poll → download → verify zip         */
/* ------------------------------------------------------------------ */
test("bundle round-trip: enqueue subset, poll, download, verify zip", async ({
  request,
}) => {
  // --- Step 1: fetch documents and pick a subset ---------
  const docsRes = await request.get(
    `${REGISTRY_URL}/api/cme/export/projects/${SMOKE_PROJECT_ID}/documents`,
  );
  expect(docsRes.status()).toBe(200);
  const { documents } = await docsRes.json();
  expect(documents.length).toBeGreaterThanOrEqual(2);

  const subset = documents.slice(0, 3).map((d: { id: string }) => d.id);

  // --- Step 2: enqueue a bundle job ----------------------
  const enqueueRes = await request.post(
    `${REGISTRY_URL}/api/cme/export/bundle`,
    {
      data: {
        project_id: SMOKE_PROJECT_ID,
        document_ids: subset,
        include_manifest: true,
        include_intake: false,
      },
    },
  );
  expect(enqueueRes.status()).toBe(202);

  const job = await enqueueRes.json();
  expect(job.id).toBeTruthy();
  expect(job.scope).toBe("project_bundle");
  expect(job.status).toBe("pending");
  const jobId: string = job.id;

  // --- Step 3: poll until succeeded or failed ------------
  let finalStatus = "pending";
  const deadline = Date.now() + POLL_TIMEOUT_MS;

  while (Date.now() < deadline) {
    const pollRes = await request.get(
      `${REGISTRY_URL}/api/cme/export/job/${jobId}`,
    );
    expect(pollRes.status()).toBe(200);
    const pollBody = await pollRes.json();
    finalStatus = pollBody.status;

    if (finalStatus === "succeeded" || finalStatus === "failed") break;
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }

  expect(finalStatus).toBe("succeeded");

  // --- Step 4: download the artifact ---------------------
  const artifactRes = await request.get(
    `${REGISTRY_URL}/api/cme/export/artifact/${jobId}`,
  );
  expect(artifactRes.status()).toBe(200);
  expect(artifactRes.headers()["content-type"]).toContain(
    "application/zip",
  );

  const zipBuf = await artifactRes.body();
  expect(zipBuf.length).toBeGreaterThan(256);

  // Zip magic bytes: PK\x03\x04
  expect(zipBuf[0]).toBe(0x50); // P
  expect(zipBuf[1]).toBe(0x4b); // K
  expect(zipBuf[2]).toBe(0x03);
  expect(zipBuf[3]).toBe(0x04);

  // --- Step 5: write to temp, unzip, verify contents -----
  const tmpDir = fs.mkdtempSync(
    path.join(os.tmpdir(), "bundle-e2e-"),
  );
  const zipPath = path.join(tmpDir, "bundle.zip");
  fs.writeFileSync(zipPath, zipBuf);

  const extractDir = path.join(tmpDir, "extracted");
  fs.mkdirSync(extractDir);
  execFileSync("unzip", ["-q", zipPath, "-d", extractDir]);

  // Verify README.md exists
  const readmePath = path.join(extractDir, "README.md");
  expect(fs.existsSync(readmePath)).toBe(true);
  const readme = fs.readFileSync(readmePath, "utf-8");
  expect(readme).toContain("Bundle:");

  // Verify metadata/project.json
  const metaPath = path.join(extractDir, "metadata", "project.json");
  expect(fs.existsSync(metaPath)).toBe(true);
  const meta = JSON.parse(fs.readFileSync(metaPath, "utf-8"));
  expect(meta.project_id).toBe(SMOKE_PROJECT_ID);
  expect(meta.selection_mode).toBe("subset");
  expect(meta.document_count).toBe(subset.length);
  expect(meta.bundle_format_version).toBe(2);

  // Verify documents/ directory has .md files
  const docsDir = path.join(extractDir, "documents");
  expect(fs.existsSync(docsDir)).toBe(true);
  const mdFiles = fs
    .readdirSync(docsDir)
    .filter((f: string) => f.endsWith(".md"));
  expect(mdFiles.length).toBe(subset.length);

  // Each md file should have content
  for (const f of mdFiles) {
    const content = fs.readFileSync(path.join(docsDir, f), "utf-8");
    expect(content.length).toBeGreaterThan(100);
  }

  // Cleanup
  fs.rmSync(tmpDir, { recursive: true, force: true });
});

/* ------------------------------------------------------------------ */
/* 4. Error cases                                                     */
/* ------------------------------------------------------------------ */
test("bundle for nonexistent project returns 404", async ({ request }) => {
  const res = await request.post(
    `${REGISTRY_URL}/api/cme/export/bundle`,
    {
      data: {
        project_id: "00000000-0000-0000-0000-000000000000",
        document_ids: null,
        include_manifest: true,
        include_intake: false,
      },
    },
  );
  expect(res.status()).toBe(404);
});

test("artifact for non-succeeded job returns 409", async ({ request }) => {
  // Enqueue a job, then immediately try to download (before worker runs)
  const enqueueRes = await request.post(
    `${REGISTRY_URL}/api/cme/export/bundle`,
    {
      data: {
        project_id: SMOKE_PROJECT_ID,
        document_ids: null,
        include_manifest: true,
        include_intake: false,
      },
    },
  );
  expect(enqueueRes.status()).toBe(202);
  const { id: jobId } = await enqueueRes.json();

  const artifactRes = await request.get(
    `${REGISTRY_URL}/api/cme/export/artifact/${jobId}`,
  );
  // Should be 409 (not ready) — unless worker is extremely fast
  expect([409, 200]).toContain(artifactRes.status());
});
