# Inbox Document & Project Download Feature — Design v2

**Date:** 2026-04-14 (v2 amended)
**Status:** Approved (brainstorming phase) — Phase 1 shipped; Phase 2+ redesigned
**Owner:** Stephen Webber
**Supersedes:** `_v1.md` (archived)
**Next step:** Writing-plans skill → amended Phase 2 implementation plan

---

## Why v2

The v1 spec shipped Phase 1 (sync document download) successfully. While scoping Phase 2, three requirements surfaced that v1 did not cover:

1. **Projects persist all their documents** (10+ PDFs per project typical), and reviewers need to **find a project** and zip it to share — projects outlive any individual pipeline run.
2. **Reviewers need to pick specific documents** from a project (not just "everything") via a file-tree tab in the inbox left-side panel, with multi-select.
3. **All agent-generated project docs must mirror to Google Drive** in per-project folders, so non-platform users can access them through Drive's native sharing.

v2 also corrects three v1 assumptions that turned out to be wrong once we started Phase 2 implementation:

- v1 assumed bundler fetches documents from LangGraph thread state. **In reality**, `cme_documents` is the authoritative store (Phase 1 already reads from it; see `cme_endpoints.py:2892`). Bundler enumerates `cme_documents WHERE project_id=? AND is_current=true`.
- v1 assumed `SELECT FOR UPDATE SKIP LOCKED` for worker claims. **In reality**, DHG runs a single renderer replica — plain `FOR UPDATE` is correct; `SKIP LOCKED` adds surface area we don't need.
- v1 assumed async SQLAlchemy in the registry. **In reality**, `registry/database.py` only exposes sync `SessionLocal` / `get_db`; any worker code must either use sync sessions or wrap DB calls in `asyncio.to_thread`.

---

## 1. Problem (amended)

The inbox at `/inbox` lets a reviewer approve, revise, or reject in-flight LangGraph review threads. Today it has:

- A sync document download button (Phase 1, shipped) — grabs the currently-visible manuscript as MD + PDF in a zip.

It does not yet have:

- A way to see **every document** associated with a project, because the current review-panel view only shows the document under review.
- A way to **select a subset** of documents for download.
- A way to share a bundle with someone outside the platform without passing around a signed URL.
- A way to find projects by anything other than "still in an interrupted review state."
- A way for non-platform stakeholders (medical directors, compliance officers) to see project artifacts without a DHG account.

v2 ships these in four user-visible capabilities:

| # | Capability | User action | Shape |
|---|---|---|---|
| 1 | **Files tab** on inbox left sidebar | Click "Files" tab → see tree of project → file checkboxes | New tab next to the existing reviews list |
| 2 | **Project bundle download** | Select 1+ files → click "Download zip" → wait for job → download | Async job, downloads tray |
| 3 | **Google Drive sync** | Automatic on pipeline milestones | Drive folder per project, managed by service account |
| 4 | ~~Admin-configurable storage path~~ | **Deferred** to a follow-up phase | Env-var paths for Phase 2 v2; admin UI for runtime changes later |

Phase 1 (sync document download from the review panel) is **unchanged** and remains the fast path for "just give me this one PDF."

---

## 2. Decisions (v2 — new and amended)

### 2.1 Still valid from v1

| # | Question | Decision |
|---|---|---|
| Q2 | File format | Markdown + PDF, bundled in a zip |
| Q5 | Frontend vs backend export | Backend (registry endpoint + sibling renderer) |
| Q6 | PDF rendering stack | Playwright + Next.js print routes (`dhg-pdf-renderer`) |
| Q7 | Sync vs async | Document sync, project async |
| Q8 | In-app permissions | Any authenticated inbox user can download |

### 2.2 Amended

| # | Question | v1 Decision | v2 Decision | Why |
|---|---|---|---|---|
| Q1 | Scope | Document + "full project" | Document + **user-selected subset or full project** | Reviewers need to pick what goes in the bundle |
| Q3 | Bundle contents | Fixed audit trail | **User-selected files + optional audit-trail extras** | Flexibility; audit trail is now an opt-in include |
| Q4 | UI placement | Button in page header | **Files tab on left sidebar with multi-select** | Requires a browser, not just a button |
| Q9 | Bundle shape | Numeric-prefix structure + README + project.json | **Same structure, but contents filtered to selected files**; README always lists selection + checksums | Compliance-friendly structure preserved |

### 2.3 New

| # | Question | Decision | Rationale |
|---|---|---|---|
| Q10 | What is the primary identifier? | `project_id`, not `thread_id` | Projects outlive any individual pipeline run; thread_id is a transient LangGraph artifact |
| Q11 | How do reviewers find projects? | **Files tab searches/filters all projects**, not just interrupted-review threads | Must work after a project ships |
| Q12 | Share mechanism | **Google Drive native sharing** replaces v1's signed URL | Drive permissions + audit trail are already what Stephen's clients use |
| Q13 | Drive sync trigger | **Pipeline milestones** (after each agent pass, after human review decision, after compliance pass) | Write-triggered sync would exceed Drive's 1000 writes / 100s quota during a burst |
| Q14 | Drive auth | **Service account** shared across projects | One set of credentials, no per-user OAuth flow |
| Q15 | Drive reconciliation | `manifest.json` at root of each Drive project folder | Source of truth for "what should be here vs what's there" |
| Q16 | Worker claim primitive | **Plain `FOR UPDATE`** (no `SKIP LOCKED`) | Single-replica deployment |
| Q17 | Bundle source of truth | **`cme_documents` table** (`is_current=true`) | Already the authoritative store; Phase 1 reads from it |
| Q18 | Storage path configurability | **Env vars for Phase 2 v2** (`EXPORTS_DIR`, `GOOGLE_DRIVE_ROOT_FOLDER_ID`); admin UI deferred to a follow-up phase | Ship the core feature first; runtime reconfigurability is valuable but not blocking |

---

## 3. Architecture (v2)

```
                                ┌──────────────────────┐
                                │   Google Drive       │
                                │   (service account)  │
                                │                      │
                                │   /DHG Projects/     │
                                │     {project_name}/  │
                                │       manifest.json  │
                                │       01-needs.pdf   │
                                │       02-research.pdf│
                                │       ...            │
                                └──────────▲───────────┘
                                           │ drive_sync job
                                           │ (service account writes)
                                           │
┌─────────────────┐       ┌─────────────────────────────────┐
│  dhg-frontend   │       │   dhg-registry-api (FastAPI)    │
│  (Next.js)      │       │                                 │
│                 │       │   /api/cme/export/*             │
│  /inbox         │ ───── │   /api/cme/projects/*           │
│    ├ Reviews    │       │   /api/admin/settings/*         │
│    │   tab      │       │                                 │
│    └ Files tab  │       │   [download_jobs]               │
│        ├ tree   │       │   [system_settings]             │
│        ├ select │       │   [cme_projects]                │
│        └ dl btn │       │   [cme_documents]               │
│                 │       └─────────────┬───────────────────┘
│  Downloads tray │                     │
│  (polls)        │                     │ claim (FOR UPDATE)
└─────────────────┘                     ▼
                                ┌─────────────────────────┐
                                │   dhg-pdf-renderer       │
                                │                          │
                                │   FastAPI /render-sync   │
                                │   Worker loop (single)   │
                                │     ├ job.scope=document │
                                │     ├ job.scope=bundle   │
                                │     └ job.scope=drive_sync
                                │                          │
                                │   Playwright Chromium    │
                                │   Google Drive SDK       │
                                │   (google-api-python-    │
                                │    client via            │
                                │    asyncio.to_thread)    │
                                └───────────┬──────────────┘
                                            │
                                            ▼
                                   ┌───────────────────┐
                                   │  dhg_exports vol  │
                                   │  (admin-configur- │
                                   │   able via system │
                                   │   _settings)      │
                                   └───────────────────┘
```

### 3.1 Components (v2 — new and changed)

| Component | v1 | v2 |
|---|---|---|
| `download_jobs` table | `(thread_id, scope)` keyed | **Adds** `project_id`, `selected_document_ids JSONB`, `scope IN ('document','project_bundle','drive_sync')` |
| `system_settings` table | — | **Deferred** to follow-up phase (admin filepath UI) |
| `cme_projects` | — | **Adds** `drive_folder_id`, `drive_last_synced_at`, `drive_sync_status` |
| `cme_documents` | — | **Adds** `drive_file_id`, `drive_synced_at`, `drive_md5` |
| `dhg-pdf-renderer` | document + project renderer | **Adds** `drive_sync` scope to worker loop |
| Inbox left sidebar | Reviews list only | **Adds** `Files` tab alongside `Reviews` |
| Admin page | — | **NEW** `/admin/storage` page with exports path + Drive folder ID fields |

### 3.2 Data flow — Files tab + bundle download

1. User opens `/inbox`, clicks **Files** tab.
2. Files tab calls `GET /api/cme/projects?search=&status=&limit=50` → project list.
3. User clicks a project row → `GET /api/cme/projects/{project_id}/documents` → file tree under the project.
4. User checks 3 of 8 files → state held in `files-tab-store.ts`.
5. User clicks **Download selected** → `POST /api/cme/export/bundle` with `{ project_id, document_ids: [...], include_manifest: true }` → 202 `{ job_id }`.
6. Downloads tray polls `GET /api/cme/export/job/{job_id}` every 3s.
7. Worker claims job (plain `FOR UPDATE`), calls `assemble_bundle(job)`:
   - Reads each `document_id` from `cme_documents` (already has `content_text`).
   - Renders MD directly from `content_text` field.
   - Renders PDF via Playwright against `/print/document/{document_id}?token=...`.
   - Writes README.md with manifest + SHA256s.
   - Writes `project.json` with project metadata + selection info.
   - Zips into `{exports_base_path}/{job_id}.zip.tmp`, `os.replace` to final.
8. Worker updates job row → `completed`, stores `artifact_path`, `artifact_sha256`, `artifact_bytes`.
9. Tray sees `completed` → shows download link → `GET /api/cme/export/artifact/{job_id}` → registry streams zip.

### 3.3 Data flow — Google Drive sync

1. **Milestone trigger** fires at one of: agent completion, review decision, compliance pass. The orchestrator inserts a `download_jobs` row with `scope='drive_sync'` and `project_id=X`.
2. Worker claims the job. For Drive sync, the worker:
   - Loads `project.drive_folder_id` (creates the folder under `drive_root_folder_id` if null, stores the new ID).
   - Lists current files in the Drive folder via `files.list`.
   - Reads `cme_documents WHERE project_id=X AND is_current=true`.
   - Diffs current-vs-desired using MD5 of each document's rendered PDF bytes.
   - For each document needing upload: renders PDF via Playwright (or reuses cached bytes), uploads via `files.create` or `files.update`, stores returned `drive_file_id` + `drive_md5` on the `cme_documents` row.
   - Writes/updates `manifest.json` at Drive folder root with full file index, sync timestamp, per-file MD5s.
   - Updates `project.drive_last_synced_at` and `drive_sync_status='ok'`.
3. On any Drive API error, job → `failed` with error text; next milestone retries.
4. `google-api-python-client` is sync-only; worker wraps all calls in `asyncio.to_thread` to avoid blocking the event loop.

### 3.4 Key design choices (v2)

- **project_id is primary.** Every job and every Drive folder keys on `project_id`. `thread_id` is a column, not a key, and is nullable on `drive_sync` jobs.
- **One worker, one queue primitive.** `FOR UPDATE` is sufficient; `SKIP LOCKED` gets added only if we ever scale to multiple renderer replicas.
- **Milestone-triggered sync, not write-triggered.** Orchestrator enqueues `drive_sync` at a small number of well-defined points; avoids Drive quota exhaustion during rapid document writes.
- **Manifest.json is Drive's source of truth.** The next sync reconciles what's there against what should be there — no naive "upload everything every time."
- **Admin can change storage paths without redeploy.** `system_settings` seeds from env but admin edits win.
- **Reuse `cme_documents`**, don't re-render from LangGraph. Phase 1 already proved this path works.
- **Drive permissions replace signed URLs**. The v1 share-via-signed-URL concept is dropped; Drive does it natively.
- **No behavior change for Phase 1.** The existing `GET /api/cme/export/document/{thread_id}` endpoint remains (by `thread_id`) so the review-panel Download button keeps working unchanged.

---

## 4. Backend detail (v2)

### 4.1 Migration `010_download_feature_v2.py`

One migration covers all v2 schema changes. Uses repo convention short numeric ID.

```python
revision = "010"
down_revision = "009"

def upgrade() -> None:
    # 1) download_jobs: add project_id, selected_document_ids; widen scope CHECK
    op.add_column("download_jobs",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("download_jobs",
        sa.Column("selected_document_ids", postgresql.JSONB, nullable=True))
    op.create_index("ix_download_jobs_project_id_status",
                    "download_jobs", ["project_id", "status"])
    op.drop_constraint("download_jobs_scope_check", "download_jobs", type_="check")
    op.create_check_constraint(
        "download_jobs_scope_check",
        "download_jobs",
        "scope IN ('document','project_bundle','drive_sync')",
    )
    op.create_foreign_key(
        "fk_download_jobs_project",
        "download_jobs", "cme_projects",
        ["project_id"], ["id"], ondelete="SET NULL",
    )

    # 3) cme_projects: Drive tracking columns
    op.add_column("cme_projects", sa.Column("drive_folder_id", sa.Text(), nullable=True))
    op.add_column("cme_projects",
        sa.Column("drive_last_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cme_projects",
        sa.Column("drive_sync_status", sa.Text(), nullable=True))  # 'pending'|'ok'|'error'

    # 4) cme_documents: Drive tracking columns
    op.add_column("cme_documents", sa.Column("drive_file_id", sa.Text(), nullable=True))
    op.add_column("cme_documents",
        sa.Column("drive_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cme_documents", sa.Column("drive_md5", sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column("cme_documents", "drive_md5")
    op.drop_column("cme_documents", "drive_synced_at")
    op.drop_column("cme_documents", "drive_file_id")
    op.drop_column("cme_projects", "drive_sync_status")
    op.drop_column("cme_projects", "drive_last_synced_at")
    op.drop_column("cme_projects", "drive_folder_id")
    op.drop_constraint("fk_download_jobs_project", "download_jobs", type_="foreignkey")
    op.drop_constraint("download_jobs_scope_check", "download_jobs", type_="check")
    op.create_check_constraint(
        "download_jobs_scope_check",
        "download_jobs",
        "scope IN ('document','project')",
    )
    op.drop_index("ix_download_jobs_project_id_status", table_name="download_jobs")
    op.drop_column("download_jobs", "selected_document_ids")
    op.drop_column("download_jobs", "project_id")
```

Note: `download_jobs` already exists from migration 009. Migration 010 augments it. `system_settings` is **deferred** to the follow-up admin-filepath phase.

### 4.2 SQLAlchemy model additions

```python
# registry/models.py additions

# DownloadJob additions:
class DownloadJob(Base):
    # ... existing columns from migration 009 ...
    project_id = Column(UUID(as_uuid=True),
                        ForeignKey("cme_projects.id", ondelete="SET NULL"),
                        nullable=True)
    selected_document_ids = Column(JSONB, nullable=True)  # list[str UUIDs] or None = all
    # scope values: 'document' | 'project_bundle' | 'drive_sync'

# CMEProject additions:
class CMEProject(Base):
    # ... existing ...
    drive_folder_id = Column(Text, nullable=True)
    drive_last_synced_at = Column(DateTime(timezone=True), nullable=True)
    drive_sync_status = Column(Text, nullable=True)

# CMEDocument additions:
class CMEDocument(Base):
    # ... existing ...
    drive_file_id = Column(Text, nullable=True)
    drive_synced_at = Column(DateTime(timezone=True), nullable=True)
    drive_md5 = Column(Text, nullable=True)
```

### 4.3 Registry endpoints (v2)

```
# Existing (Phase 1, unchanged)
GET  /api/cme/export/document/{thread_id}      → sync zip

# New — project discovery
GET  /api/cme/projects?search=&status=&limit=&offset=
     → { projects: [{ id, name, status, kind, document_count,
                      last_activity_at, drive_folder_id }], total }
GET  /api/cme/projects/{project_id}
     → full project detail
GET  /api/cme/projects/{project_id}/documents
     → { documents: [{ id, document_type, title, word_count, version,
                       is_current, updated_at, drive_file_id }] }

# New — async bundle
POST /api/cme/export/bundle
     body: { project_id: UUID, document_ids: UUID[] | null,
             include_manifest: bool, include_intake: bool }
     → 202 { job_id, status: 'pending', poll_url }

GET  /api/cme/export/job/{job_id}              → status + artifact_url
GET  /api/cme/export/artifact/{job_id}         → streams zip (author-gated)
GET  /api/cme/export/jobs?limit=20             → recent jobs for user
```

All Pydantic schemas in `registry/export_schemas.py` use `model_config = ConfigDict(extra='forbid')`.

### 4.4 Storage path configuration (Phase 2 v2 — env var only)

For Phase 2 v2, storage paths are controlled by environment variables only:

| Env var | Default | Used by |
|---|---|---|
| `EXPORTS_DIR` | `/var/exports` | `assemble_bundle()` to resolve artifact write path |
| `GOOGLE_DRIVE_ROOT_FOLDER_ID` | (required) | `sync_project_to_drive()` to resolve Drive parent folder |

The worker reads these at process start. Changing them requires a container restart.

**Runtime admin reconfiguration is deferred** to a follow-up phase (see §12 Deferred Work). The deferred design includes a `system_settings` DB table with admin UI at `/admin/storage`, path validation, Drive folder reachability test, and an explicit "migrate artifacts" action. Phase 2 v2 is structured so that introducing it later is additive (swap env-var reads for a `get_exports_base_path()` helper that falls back to env var when the DB setting is null).

### 4.5 Worker loop (v2)

```python
# services/pdf-renderer/src/worker.py

async def claim_next_job(db_session) -> DownloadJob | None:
    # Plain FOR UPDATE — single-replica, so no SKIP LOCKED
    return await asyncio.to_thread(
        lambda: db_session.execute(
            text("""
                SELECT * FROM download_jobs
                 WHERE status = 'pending'
                 ORDER BY created_at
                 LIMIT 1
                 FOR UPDATE
            """)
        ).fetchone()
    )

async def run_worker():
    while True:
        async with session_scope() as db:
            job = await claim_next_job(db)
            if not job:
                await db.rollback()
                await asyncio.sleep(2)
                continue
            await asyncio.to_thread(mark_running, db, job.id)
        try:
            if job.scope == "document":
                # Legacy path from Phase 1 — still sync via /render-sync,
                # no async job row should reach here under normal operation
                raise RuntimeError("document scope is sync; not a worker job")
            elif job.scope == "project_bundle":
                await assemble_bundle(job)
            elif job.scope == "drive_sync":
                await sync_project_to_drive(job)
            await asyncio.to_thread(mark_completed, job.id)
        except Exception as e:
            await asyncio.to_thread(mark_failed, job.id, str(e)[:2000])
```

### 4.6 `assemble_bundle(job)` (v2)

```python
async def assemble_bundle(job):
    base_path = os.getenv("EXPORTS_DIR", "/var/exports")
    tmp = Path(base_path) / f"{job.id}.zip.tmp"
    final = Path(base_path) / f"{job.id}.zip"

    # 1) Resolve selection
    with SessionLocal() as db:
        project = db.query(CMEProject).get(job.project_id)
        if job.selected_document_ids:
            docs = db.query(CMEDocument).filter(
                CMEDocument.id.in_(job.selected_document_ids),
                CMEDocument.project_id == project.id,
                CMEDocument.is_current == True,
            ).all()
        else:
            docs = db.query(CMEDocument).filter(
                CMEDocument.project_id == project.id,
                CMEDocument.is_current == True,
            ).all()

    # 2) Build zip
    manifest_entries = []
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, doc in enumerate(docs, start=1):
            prefix = f"{i:02d}-{doc.document_type}"
            # MD from DB content_text
            md_bytes = doc.content_text.encode("utf-8")
            zf.writestr(f"01-documents/{prefix}.md", md_bytes)
            manifest_entries.append((f"01-documents/{prefix}.md",
                                     hashlib.sha256(md_bytes).hexdigest()))
            # PDF via Playwright
            pdf_bytes = await render_document_pdf(doc.id)
            zf.writestr(f"01-documents/{prefix}.pdf", pdf_bytes)
            manifest_entries.append((f"01-documents/{prefix}.pdf",
                                     hashlib.sha256(pdf_bytes).hexdigest()))

        if job.include_intake:
            intake_md = render_intake_md(project)
            zf.writestr("00-intake/intake.md", intake_md.encode("utf-8"))
            # ... intake.pdf ...

        # project.json
        zf.writestr(
            "04-metadata/project.json",
            json.dumps(build_project_metadata(project, docs, job), indent=2),
        )

        # README.md with manifest
        readme = render_readme(project, manifest_entries, job)
        zf.writestr("README.md", readme)

    # 3) atomic rename
    tmp.replace(final)

    # 4) update job row
    with SessionLocal() as db:
        db_job = db.query(DownloadJob).get(job.id)
        db_job.artifact_path = str(final)
        db_job.artifact_bytes = final.stat().st_size
        db_job.artifact_sha256 = sha256_file(final)
        db.commit()
```

### 4.7 `sync_project_to_drive(job)` — new

```python
async def sync_project_to_drive(job):
    drive = build_drive_client()  # service account creds from env
    root_folder_id = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID")
    if not root_folder_id:
        raise RuntimeError("GOOGLE_DRIVE_ROOT_FOLDER_ID not configured")

    with SessionLocal() as db:
        project = db.query(CMEProject).get(job.project_id)
        docs = db.query(CMEDocument).filter(
            CMEDocument.project_id == project.id,
            CMEDocument.is_current == True,
        ).all()

        # 1) Ensure project folder exists in Drive
        if not project.drive_folder_id:
            folder_meta = await asyncio.to_thread(
                lambda: drive.files().create(
                    body={
                        "name": f"{project.name} ({project.id})",
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [root_folder_id],
                    },
                    fields="id",
                ).execute()
            )
            project.drive_folder_id = folder_meta["id"]
            db.commit()

        # 2) Load existing Drive state
        existing = await asyncio.to_thread(
            lambda: drive.files().list(
                q=f"'{project.drive_folder_id}' in parents and trashed = false",
                fields="files(id, name, md5Checksum)",
            ).execute()
        )
        existing_by_name = {f["name"]: f for f in existing.get("files", [])}

        # 3) For each doc: render PDF, diff MD5, upload if changed
        for i, doc in enumerate(docs, start=1):
            pdf_name = f"{i:02d}-{doc.document_type}.pdf"
            pdf_bytes = await render_document_pdf(doc.id)
            pdf_md5 = hashlib.md5(pdf_bytes).hexdigest()

            if doc.drive_md5 == pdf_md5 and doc.drive_file_id:
                continue  # unchanged

            media = MediaIoBaseUpload(io.BytesIO(pdf_bytes),
                                     mimetype="application/pdf")
            if pdf_name in existing_by_name:
                file_id = existing_by_name[pdf_name]["id"]
                await asyncio.to_thread(
                    lambda: drive.files().update(
                        fileId=file_id, media_body=media
                    ).execute()
                )
            else:
                result = await asyncio.to_thread(
                    lambda: drive.files().create(
                        body={"name": pdf_name,
                              "parents": [project.drive_folder_id]},
                        media_body=media,
                        fields="id",
                    ).execute()
                )
                file_id = result["id"]
            doc.drive_file_id = file_id
            doc.drive_md5 = pdf_md5
            doc.drive_synced_at = datetime.now(timezone.utc)
            db.commit()

        # 4) Write manifest.json to Drive folder root
        manifest = build_drive_manifest(project, docs)
        manifest_media = MediaIoBaseUpload(
            io.BytesIO(json.dumps(manifest, indent=2).encode("utf-8")),
            mimetype="application/json",
        )
        # ... upsert manifest.json ...

        project.drive_last_synced_at = datetime.now(timezone.utc)
        project.drive_sync_status = "ok"
        db.commit()
```

### 4.8 Milestone triggers

The orchestrator (`langgraph_workflows/dhg-agents-cloud/src/orchestrator.py`) enqueues `drive_sync` at these three points only, via a new helper `enqueue_drive_sync(project_id)` that inserts a `download_jobs` row with `scope='drive_sync'`:

1. After each content-agent node successfully writes to `cme_documents` (grouped — one sync per agent pass, not one per document).
2. After a human review decision is resumed (approved / needs_revision / rejected).
3. After `compliance_review_agent` completes a successful pass.

Dedup: if an existing `pending` or `running` `drive_sync` job exists for the same `project_id`, insert is skipped. This absorbs burst milestones (e.g., parallel research + clinical finishing within ms of each other) into a single sync.

---

## 5. Frontend detail (v2)

### 5.1 Inbox left-sidebar tabs

Current: `inbox-master-detail.tsx` renders a single reviews list on the left.

v2: the left panel gets a shadcn `Tabs` (underline variant) with two tabs:

```
┌────────────────────────────────┐
│  [ Reviews ]  [ Files ]        │  ← underline Tabs
├────────────────────────────────┤
│                                │
│  (tab content)                 │
│                                │
└────────────────────────────────┘
```

**Reviews tab:** unchanged from Phase 1.

**Files tab:** new. Layout:

```
┌────────────────────────────────┐
│  [ Reviews ]  [ Files ]        │
├────────────────────────────────┤
│  🔍 Search projects...         │
│                                │
│  ▼ Project A (8 docs)          │
│    ☐ 01 Needs Assessment  1.2k │
│    ☐ 02 Research          2.4k │
│    ☑ 03 Gap Analysis       890 │
│    ☐ 04 Learning Obj       640 │
│    ...                         │
│  ▶ Project B (6 docs)          │
│  ▶ Project C (10 docs)         │
│                                │
├────────────────────────────────┤
│  3 selected                    │
│  [ Download zip ]              │
└────────────────────────────────┘
```

Interaction model (two-click pattern borrowed from Gmail/Linear/Superhuman):

- **Click row** → preview document in the right panel (reuses existing `DocumentViewer`).
- **Click checkbox** → add/remove from selection, does NOT preview.
- **Click Download zip** (enabled when `selection.length > 0`) → POST to `/api/cme/export/bundle` with `project_id` (the project of the most recently touched selection) and `document_ids` (the selected docs). If the selection spans multiple projects, the button is disabled and a tooltip says "select files from one project at a time."

### 5.2 Components

```
frontend/src/components/inbox/
├── inbox-master-detail.tsx        # adds left-side Tabs
├── reviews-tab.tsx                # existing list moved here
├── files-tab.tsx                  # NEW — search + project tree + selection bar
├── files-tree.tsx                 # NEW — expandable project/doc tree
├── files-selection-bar.tsx        # NEW — bottom bar with count + download button
└── ...
```

### 5.3 Store

```ts
// frontend/src/stores/files-tab-store.ts
interface FilesTabState {
  projects: ProjectListItem[];
  expandedProjectIds: Set<string>;
  selectedDocumentIds: Set<string>;
  selectedProjectId: string | null;  // derived from last selection
  searchQuery: string;
  previewDocumentId: string | null;  // row-click sets this

  setProjects: (projects: ProjectListItem[]) => void;
  toggleProject: (id: string) => void;
  toggleDocument: (projectId: string, documentId: string) => void;
  clearSelection: () => void;
  setPreview: (id: string | null) => void;
  setSearch: (q: string) => void;
}
```

Zustand with `persist` on `expandedProjectIds` only (selection and preview are ephemeral).

### 5.4 API client

```ts
// frontend/src/lib/filesApi.ts
export async function listProjects(params: {
  search?: string; status?: string; limit?: number; offset?: number;
}): Promise<ProjectListResponse> { ... }

export async function listProjectDocuments(projectId: string)
  : Promise<ProjectDocumentsResponse> { ... }

export async function createBundleJob(body: {
  project_id: string;
  document_ids: string[] | null;
  include_manifest: boolean;
  include_intake: boolean;
}): Promise<{ job_id: string; status: string }> { ... }
```

### 5.5 Downloads tray (unchanged shape, adds drive_sync)

The downloads tray from v1 is kept. New scope `drive_sync` shows a slightly different row:

```
┌─────────────────────────────────────────┐
│ ☁️ Drive sync — Grant Package           │
│    10 docs · 2 uploaded, 8 unchanged    │
│    ✓ 30s ago                            │
└─────────────────────────────────────────┘
```

Drive-sync jobs are not user-downloadable (no artifact link) — they show only status and summary.

---

## 6. Bundle structure (v2)

```
{job_id}.zip
├── README.md                         # manifest + SHA256s + selection list
├── 00-intake/                        # only if include_intake=true
│   ├── intake.md
│   └── intake.pdf
├── 01-documents/                     # the user's selection, or all if none
│   ├── 01-needs_assessment.md
│   ├── 01-needs_assessment.pdf
│   ├── 02-research.md
│   ├── 02-research.pdf
│   └── ...
└── 04-metadata/
    └── project.json                  # project metadata + selection info
```

- Numeric prefixes preserve ordering even when the selection is sparse.
- `project.json` includes `selection_mode: "all" | "subset"`, `selected_document_ids`, `include_intake`, exporter, timestamps.
- README always enumerates **every file in the zip** with a SHA256, so compliance tooling can verify integrity.
- Phase 3 additions (quality, review history, citations) are **not** in v2 scope — they remain deferred per v1.

---

## 7. Phase breakdown (v2 — Phase 2 only)

Phase 1 shipped unchanged. Phases 3–5 from v1 are still the follow-on but may be re-scoped after Phase 2 lands. This doc defines **Phase 2 v2** only.

### Phase 2 v2 — Files tab, bundles, Drive sync, admin settings

**Goal:** Reviewer opens `/inbox` Files tab, finds any project, picks 1+ files, downloads a zip. All agent output also mirrors to a Drive folder automatically. Admin can change storage paths at runtime.

**Deliverables (high level, details go into the plan doc):**

- Alembic migration `010_download_feature_v2.py` (DownloadJob extensions, CMEProject/CMEDocument Drive fields)
- SQLAlchemy model additions (DownloadJob extensions, CMEProject/CMEDocument Drive fields)
- `registry/projects_endpoints.py` project list + project documents
- `registry/export_endpoints.py` bundle POST + amended job/artifact
- `services/pdf-renderer/src/bundler.py` assemble_bundle from cme_documents
- `services/pdf-renderer/src/drive_sync.py` sync_project_to_drive with service account
- `services/pdf-renderer/src/worker.py` amended with plain FOR UPDATE + three scopes
- `langgraph_workflows/.../orchestrator.py` `enqueue_drive_sync()` at milestones
- Frontend: `files-tab.tsx`, `files-tree.tsx`, `files-selection-bar.tsx`, tabs in inbox master-detail
- Frontend: `files-tab-store.ts`, `filesApi.ts`
- Frontend: downloads tray extended for `drive_sync` rows
- E2E: Playwright scenarios for Files tab selection + download + Drive manifest check (using a test Drive folder)

**Acceptance:**

1. Files tab renders projects from `cme_projects`; search filters by name/status.
2. Selecting 3 of 8 docs and clicking Download produces a zip containing exactly those 6 files (3 MD + 3 PDF) plus README + project.json.
3. README lists every zip entry with SHA256; all SHA256s verify.
4. A pipeline run end-to-end produces files in the Drive project folder matching `cme_documents` state; `manifest.json` is present and current.
5. Two milestones firing within 50ms for the same project → one `drive_sync` job, not two (dedup).
6. User A can't fetch user B's bundle artifact (403).
7. Worker restart mid-render leaves no `.zip` at the final path (only `.zip.tmp`).

**Out of scope for Phase 2 v2:**

- Phase 3 compliance add-ons (quality/history/citations bundles).
- Per-user Drive auth (service account only).
- Drive folder permission management from the admin UI (set once in the Drive console).
- Full-text search over document content (search is name/status only).
- Bundling across projects (selection must be within a single project).

**Estimate:** 7–9 engineering days.

---

## 8. Security considerations

- **Drive service account key** lives in `.env` as a path to a JSON file, mounted into the renderer container only. Never committed. Never surfaced to frontend.
- **Drive folder permissions** are managed in Drive's native UI — the service account writes the files; sharing is a separate action the project owner takes in Drive.
- **Artifact auth** unchanged from v1: job creator or admin only.
- **Bundle content**: selection is validated server-side — if `document_ids` contains an ID not belonging to `project_id`, the job fails before any work runs.

## 9. Testing approach

- **Unit**: settings_service env/DB precedence; dedup logic for drive_sync; path allowlist; Drive client mocking.
- **Integration (real DB)**: full bundle job lifecycle; Drive sync against a test folder; admin settings CRUD + validation; migration 010 up/down round-trip.
- **Playwright e2e**: Files tab navigation, selection, download, zip inspection in the test harness.
- **Chaos**: kill renderer mid-bundle → `.tmp` only, no final artifact; kill mid-drive-sync → partial Drive state, next milestone reconciles via manifest diff.

## 10. Out of scope (explicit non-goals)

- **S3 / object storage** — shared volume is fine, configurability covers path migration.
- **WebSocket push** of job status — polling remains.
- **Cross-project bundles** — must pick from one project at a time.
- **Drive per-user auth** — service account only.
- **Drive sharing UI inside DHG** — do that in Drive.
- **Document content search** — Files tab searches names/status, not body text.
- **Round-by-round diffs** — Phase 4 still.
- **TTL cleanup** — Phase 5 still (artifacts accumulate until then; 14-day GC recommended but not yet built).

## 11. Deferred Work (follow-up phases)

Features that were considered for Phase 2 v2 but deferred to keep scope shippable. Each is designed so the Phase 2 v2 code is a compatible starting point — these are additive changes, not rewrites.

### 12.1 Admin-configurable storage paths

**Why deferred:** Ship the core download + Drive-sync feature first. Runtime path reconfiguration is valuable but not blocking.

**Intent:** Let an admin change `exports_base_path` and `drive_root_folder_id` at runtime via `/admin/storage` without a container restart.

**Approach (sketch — formalize in a follow-up spec):**

- New migration: `system_settings` key/value table (`key PK`, `value`, `updated_by`, `updated_at`).
- New `registry/settings_service.py` with `get_setting(key, env_fallback)` — env var is the seed default, DB value wins when non-null.
- Swap direct `os.getenv(...)` calls in `bundler.py` and `drive_sync.py` for `get_exports_base_path()` / `get_drive_root_folder_id()` helpers. **Call these at job-start time**, not process-start, so admin edits apply to the next job without restart.
- New endpoints:
  - `GET /api/admin/settings`
  - `PUT /api/admin/settings` with validation: path must exist and be writable (`os.access(path, W_OK)`); Drive folder ID must be reachable by the service account (`drive.files().get(fileId).execute()`).
  - `POST /api/admin/settings/migrate-artifacts` — enqueues a background job that **copies** (not moves) pending artifacts from old path to new path with SHA256 verification. Old artifacts remain at the old path until 14-day GC sweeps them.
- New admin UI at `frontend/src/app/admin/storage/page.tsx`: two fields, `Test` button per field with status badges (`unchecked`/`valid`/`invalid: {reason}`), `Save` disabled until both tests pass, separate `Migrate existing artifacts` button that only appears after a successful path change.
- RBAC: new `admin:settings` permission, seeded to the `admin` role.
- Path allowlist: reject admin input outside a configurable allowlist (`/var/exports`, `/mnt/*`, `/data/*`) to prevent writes to system directories. Allowlist is itself an env var so ops controls it, not admins.
- **Never auto-move artifacts on save.** Explicit action only.

**Acceptance criteria for the deferred phase:**

1. Admin changes `exports_base_path` to a new valid directory; next bundle job writes there; old artifacts remain.
2. Invalid path → Test fails, Save disabled.
3. Unreachable Drive folder → Test fails, Save disabled.
4. Migrate button copies artifacts, verifies SHA256, leaves old copies in place.
5. Path outside allowlist → 400 on save.
6. Non-admin user hitting `/api/admin/settings` → 403.

### 12.2 Other deferred items

Carried forward from the v1 spec:

- **Phase 3** — quality signals, review history, citations bundle sections.
- **Phase 4** — round-by-round diffs.
- **Phase 5** — TTL cleanup, rate limiting, retry UX, memory watchdog, signing key rotation, Grafana/Alertmanager coverage.

## 12. Open design decisions

- **Drive folder naming**: `{project.name} ({project.id})` may be long. Alternative: `{short_id}-{slug}`. Defer to implementation, either works.
- **Milestone granularity**: one `drive_sync` per agent pass vs one per document. Defaulting to per-agent-pass in the plan; revisit if sync latency hurts reviewer workflow.
- **Manifest.json format**: include full checksum tree or just file index? Defaulting to full checksum tree for reconciliation.
- **Admin path allowlist default**: need to confirm with ops what paths are safe writeable on the host.
