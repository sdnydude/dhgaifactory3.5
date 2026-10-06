# Trouble-Ticket System — Implementation Design & Plan

**Date:** 2026-07-18
**Status:** Design draft — awaiting approval before any build (per standing production rules)
**Owner:** Stephen Webber
**Builds on:** `2026-07-18-oss-customer-support-platform-research.md` (research + recommendation, decisions locked there)
**Scope:** Implementation design for the trouble-ticket system whose platform decisions were settled in the research pass. Resolves the 5 open questions that research deferred, defines the registry schema + webhook/queue mechanics + LangGraph triage graph, and sequences the build so the registry-side pieces **bundle into the current registry deploy** (the same rebuild shipping the new `assets` table).

---

## 0. Locked upstream decisions (do not re-litigate)

From the research doc, already decided:
- **Chatwoot CE (MIT)** = intake channel, self-hosted `dhg-chatwoot` on `dhgaifactory35_dhg-network`.
- **Twenty CRM (MIT)** = companion CRM, `dhg-twenty`.
- **Registry + a new LangGraph triage graph = the ticket system of record.** Chatwoot is the channel, not the DB of record. No second OSS ticketing product.
- **Auth** = Cloudflare Access perimeter only for the pilot; no full JWT/RBAC wiring yet.
- **Beta reports = first ticket type** (pilot). Portage already POSTs beta reports to the registry (`beta_reports` table, PR #226) — that is the live pilot source.

## 1. Open questions — resolved here (recommendations; override any)

| # | Question | Decision | Why |
|---|----------|----------|-----|
| 1 | DB placement | **Dedicated `dhg-chatwoot-db` + dedicated `dhg-twenty-db`; `support_tickets` (system of record) stays in `dhg-registry-db`.** | Chatwoot/Twenty own Rails/their-own migrations — must not co-own the registry's Alembic-managed schema. The ticket-of-record is registry data, lives with the registry. |
| 2 | Ticket schema | **Single `support_tickets` table with a `ticket_type` enum discriminator** (`beta_report` \| `support` \| `question` \| `bug` \| `other`), separate from the Incident Record Library. Plus `ticket_ingest_queue` for the webhook buffer. | Ops-incident lifecycle ≠ tester-feedback lifecycle. Enum discriminator (not free text) keeps types queryable. |
| 3 | Webhook mechanics | **`POST /api/support/chatwoot-webhook` → validate HMAC → insert `ticket_ingest_queue` row (dedupe key = hash(conversation_id, message_id)) → return 200 immediately. Async worker claims rows `FOR UPDATE SKIP LOCKED`, invokes the triage graph, writes `support_tickets`.** | Chatwoot webhooks are fire-and-forget with sender-side retries; a 5-min LangGraph run behind a sync handler would double-invoke. Mirrors the proven `services/pdf-renderer/worker.py` claim pattern; reuses `registry_agent.py._generate_idempotency_key()` + dead-letter. |
| 4 | Frontend surface | **A third "Support" tab in the existing Inbox master-detail shell** (same pattern as the Files tab); agents work in DHG's native Inbox against Chatwoot's API, not the Chatwoot console. Phase 4. | Reuses the built + proven CME Inbox review UX. `decision-bar` action set parameterized beyond CME's approve/revise/escalate. |
| 5 | Backup/DR | **Nightly `pg_dump` of `dhg-chatwoot-db` + `dhg-registry-db`; documented restore-together runbook. Low priority — after pilot.** | Cross-DB restore-timestamp mismatch is a real but non-blocking risk for a pilot. |

## 2. Registry schema (new — migration 032)

**`support_tickets`** (system of record, `dhg-registry-db`):
`id` (uuid pk) · `ticket_type` (varchar, enum-checked) · `project_name` · `source_channel` (`chatwoot` \| `beta_report` \| `internal`) · `external_ref` (Chatwoot conversation id / beta_report id) · `reporter_email` · `reporter_user_id` · `subject` · `body` (text) · `page` · `area` · `severity` (low/medium/high/critical) · `status` (open→triaged→in_progress→resolved→wont_fix) · `category` · `duplicate_of` (uuid, self-fk) · `confidence` (real, triage) · `routing_decision` (text) · `assignee` · `screenshot_url` · `tags` (text[]) · `embedding` (vector 768) · `search_vector` (tsvector) · `meta_data` (jsonb) · `created_at` / `updated_at`.
Unique: `(project_name, source_channel, external_ref)` for idempotency.

**`ticket_ingest_queue`** (webhook buffer, `dhg-registry-db`):
`id` · `dedupe_key` (unique) · `raw_payload` (jsonb) · `source_channel` · `status` (`queued`→`claimed`→`done`→`dead`) · `claimed_at` · `attempts` · `last_error` · `created_at`.

## 3. LangGraph triage graph (new — `support_triage_agent.py`)

New dedicated graph (17 → 18 graphs). State: `ticket_id, category, severity, duplicate_of, confidence, auto_closeable, routing_decision`.
Nodes: `classify → dedupe (embedding similarity vs. open tickets) → decide_route → registry_write` — delegating idempotency/dead-letter to `registry_agent.py`, **not** reinventing it. Auto-close biased toward escalation (never silently close on low confidence).

## 4. Beta-reports pilot bridge

Portage's live `beta_reports` POST is the pilot ingest source. Two options considered:
- **A. Dual-write:** keep `beta_reports` as-is; also enqueue each into `ticket_ingest_queue` (`source_channel=beta_report`) so it flows through triage into `support_tickets`.
- **B. Migrate:** fold `beta_reports` into `support_tickets` (`ticket_type=beta_report`), retire the old table.

**Recommend A for the pilot** — non-destructive, `beta_reports` keeps working while the triage loop is proven, migrate later if desired. Prove the Chatwoot→registry→triage→human-review loop on beta reports before generalizing.

## 5. Phased plan — and how it "bundles here"

| Phase | Work | Bundles with |
|-------|------|--------------|
| **P0** | `support_tickets` + `ticket_ingest_queue` tables (**migration 032**), `/api/support` ingest endpoints (`chatwoot-webhook` + internal beta-report enqueue), queue-worker skeleton (`FOR UPDATE SKIP LOCKED`). **Registry-only, additive.** | **The current registry rebuild** — one deploy ships `assets` (031) + tickets (032). This is the concrete "bundle here." |
| **P1** | `support_triage_agent.py` LangGraph graph (classify/dedupe/route); wire `beta_reports` dual-write → triage → `support_tickets`. Prove the loop end-to-end. | Standalone (LangGraph stack) |
| **P2** | Deploy `dhg-chatwoot` + `dhg-chatwoot-db` containers; configure Chatwoot webhook → `/api/support/chatwoot-webhook`; HMAC secret. | Compose / infra |
| **P3** | Deploy `dhg-twenty` + `dhg-twenty-db` (CRM); link ticket reporters → CRM contacts. | Compose / infra |
| **P4** | "Support" tab in the Inbox master-detail shell; parameterize `decision-bar`. | aifactory frontend |

## 6. Approval gate

This is the implementation-design pass the research doc required. **No build starts until approved.** The only piece proposed for immediate action is **P0**, bundled into the in-flight registry rebuild (assets). P1–P4 are sequenced, each its own build with its own verification. Production rules apply — the registry rebuild is a shared-service restart.

## Version History
- v1 (2026-07-18): Initial implementation design; resolves the 5 research open questions; P0 bundled into the assets registry deploy.
