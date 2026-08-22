status: complete
phase: 7
completed_at: 2026-07-29T08:36Z
feature: Self-hosted Langfuse v3 on dh40801 — replace LangSmith/Langfuse Cloud, repoint Portage before beta
approach: Approach D — remote Docker context from g700data1; own compose file in-repo; reuse existing cloudflared tunnel; LAN transport
complexity: complex
explore_scope: full (3-agent divergent explore — targeted was proposed and rejected)
branch: feat/langfuse-selfhost
phase2_complete: true — 3 divergent agents + advisor + 3 Fable-5 specialist reviews (infra/tracing/security) + Langfuse official docs (WebFetch + Context7)
scope_locked: Part A (install Langfuse) + Part B (repoint Portage); PARKED — medkb (c60008ba), agent tracing (d571a7d6), feedback_loop project_name (146c8096)
approved: "approved" 2026-07-26T20:07:47Z
kb_findings: Prior decisions — "Custom shouldExportSpan filter + MaskingSpanProcessor wrapper" (Portage Langfuse export gotcha); "Trace context propagates via OpenTelemetry, not threaded through lib signatures"; "Hosted Doppler SaaS over Infisical/Vault self-hosted; CEO can't ops infrastructure" (tension, disavowed in handoff for non-secrets-manager cases); "Standardize project_name to dhg-ai-factory across all capture rules and registry records"; "cloudflare-ops full-capability scope C". Related open deferred items — "[high] Resolve docs.digitalharmonyai.com Cloudflare Access gate (perceived as down)"; "[med] rehearsal:3004 ingress delete + :8018 landing awaiting go". Active correction patterns — workflow-violation INCREASING and repeated scope-cutting (three instances this session): do NOT cut scope.
codegraph_scan: `from tracing import traced_node` in exactly 14 modules under langgraph_workflows/dhg-agents-cloud/src/ — the LangSmith->Langfuse agent migration is wide-but-shallow. IN SCOPE as Workstream D.
advisor: 7 reviews — systems-architect, config-safety-reviewer, security-auditor (stack), security-auditor (service account), performance-tuner, plus 2 Fable-5 (60-claim fact verification; efficiency/critical-path). All returned "not ready as-is"; objections were mechanism, not direction. Findings folded in below.

---

# Spec — Self-hosted Langfuse on dh40801

## What it does

Stands up a self-hosted Langfuse v3 stack on dh40801 (10.0.0.179), relocates medkb to the same host, integrates both with the AI Factory on g700data1 (10.0.0.251), fixes a live public-exposure defect in Cloudflare Access, and repoints the Portage app off Langfuse Cloud US before beta opens.

## Full scope — nothing deferred

Per `feedback_no_deferrals.md`: within scope, nothing is deferred.

**A — Langfuse stack.** Six containers, disks, secrets, monitoring, backups.
**B — Cloudflare Access remediation.** Fix the `*.digitalharmonyai.com` `bypass/everyone` policy and gate the 8 ungated hostnames. Prerequisite for exposing Langfuse and for Workstream H.
**C — Portage: DEPLOY the tracing branch, then point it at self-hosted.** NOT a repoint — nothing is deployed.

**CRITICAL CORRECTION (2026-07-21).** `LANGFUSE_SELFHOST_HANDOFF.md:29` claims prod is running Langfuse tracing against Cloud US with "traces verified flowing." **That is false.** Verified against the running container:
1. `portage-api`'s image has no `dist/instrumentation.js` (only app, index, lib, routes, middleware, db, marketplace)
2. `@langfuse` packages are absent from its `node_modules` entirely
3. No `"Langfuse tracing enabled"` log line exists — the code isn't there to emit it

Mechanism: the Portage repo is on `main` (b2a6db1); `feat/langfuse-tracing` is NOT merged; `docker-compose.yml` builds `portage-api` from `context: .` (the working tree). Building while on `main` yields an image with no tracing code. The `LANGFUSE_*` env vars are present only because Doppler injects them; nothing reads them.

Consequences that change this ship:
- The export-filter fix (`shouldExportSpan`) and the image-masking wrapper were validated in DEV ONLY. They have never run against production traffic.
- `df272d0` (conditionNotes save bug) is stranded on the same unmerged branch — that is why the bug is still live in prod.
- AC-25 (masking regression check) is now MANDATORY, not precautionary: the first production traces will be the first time that code path meets real user photos.
- Sequence is: merge/deploy the branch -> verify tracing works AT ALL -> then point at self-hosted. Two verification points, not one.
**D — LangSmith -> Langfuse agent migration.** Swap `@traceable` for Langfuse `CallbackHandler` across the **14** modules importing `tracing`; set `LANGFUSE_*`, drop `LANGSMITH_*`/`LANGCHAIN_TRACING_V2`. Decide the fate of the parallel OTel->Tempo export.
**E — User-level attribution.** Langfuse user id = `req.user.email`, plus `tier` + internal UUID as metadata, across all 5 Portage AI features. TDD per tdd-guard. Also set OTel `service.name = portage-api` (currently `unknown_service`).
**F — Dashboards.** Langfuse user + cost dashboards; Grafana panels for the dh40801 host and the Langfuse stack.
**G — KB (reframed).** medkb built the read side (retrieval, CRAG, corpora, auth, metrics — 51 commits, 46 tests) and never built ingestion; the dh40801 SOP is an ingestion pipeline needing a GPU. They are two halves of one system:
- **Move medkb to dh40801** — `dhg-medkb-api`, `dhg-medkb-db`, `dhg-medkb-cache`. Verified safe: ZERO consumers in the codebase, 8 MB of data (sample seed `dhg_cme_sample` only).
- **Build ingestion on dh40801**, writing through **medkb's own models/migrations** — never Haystack's `PgvectorDocumentStore`, which creates its own tables and would produce write-side/read-side schema drift.
- **CANCELLED: `dhg-kb-db`.** No sixth vector store. Port 5433 is RELEASED, not reserved.
- **CANCELLED: Haystack.** medkb already defines retrieval; a second RAG framework serves no consumer.
- **CANCELLED: a third transcription path.** `dhg-transcribe` already runs faster-whisper (WhisperX's own backend) in 10 containers. Reuse it, containerized onto dh40801's GPU. Add WhisperX only if diarization/alignment is a stated requirement.
- **Ollama as a container, not a host install** — `curl | sh` needs sudo and duplicates `dhg-ollama`, which already serves nomic-embed-text.
**H — memreg integration.**
- **H1 attribution:** `langfuse` and `medkb` **tags** on captures. NOT new `project_name` values — the standardization decision stands.
- **H2 ingestion:** memreg pulls FROM Langfuse and medkb into the registry KB. **Blocked on B** — the registry API is public today; ingesting trace-derived data before that is fixed would publish user prompts and (after E) customer emails.
  - Langfuse -> registry: **curated signals only** (error patterns, cost rollups, latency outliers, eval scores). Never prompt bodies, completions, media, or user identifiers.
  - medkb -> registry: **federate, do not copy.** Registry KB search queries medkb `/v1/query` and merges results.

**Also in scope:** cherry-pick Portage `df272d0` (conditionNotes cap 500->2000) to Portage `main`, independently of the tracing branch.

## Decisions locked

| Decision | Choice | Why |
|---|---|---|
| Host | dh40801 | .251 takes beta load; dh40801 idle, 24C/62.5GiB, GPU unused by Langfuse |
| Deploy mechanism | Remote Docker context (`docker --context dh40801`) | Verified: client 29.5.2 -> server 29.3.0, no sudo, no secrets at rest on dh40801, no repo clone |
| Ansible | NOT used to deploy | Fleet layer has never executed on any host (ufw `ENABLED=no`, untouched `sshd_config` on .251); `become` undefined fleet-wide; `docker-compose-deploy.yml` has no `-f`/`-p` and would deploy the entire AI Factory onto dh40801 |
| Transport | LAN (10.0.0.179), not tailnet | `tailscale ping` -> "peer's node key has expired"; LAN 0.2-0.3ms, 0% loss |
| Public hostname | `labs.digitalharmonyai.com` via the EXISTING tunnel (one ingress line, `service: http://10.0.0.179:3000`) | No new tunnel, no cloudflared container, no tunnel token to leak. **CONSTRAINT: `/etc/cloudflared/config.yml` on .251 is ROOT-OWNED and sudo needs a password — this edit + `systemctl reload cloudflared` is a STEPHEN-run step, not a Claude step. Sequence AFTER the `labs.` Access app (AC-18) exists, so labs never resolves under the still-open wildcard bypass.** |
| UI path vs data path | Split: UI via tunnel+Access; ingestion LAN-direct | Keeps the highest-PII-density flow off the internet and off Cloudflare's edge; removes the Access-exemption problem; decouples C from B |
| Postgres/Redis/MinIO | Dedicated, not shared | Prisma migrations run on every upgrade; Redis is a BullMQ queue needing `noeviction`; MinIO holds raw prompts + media |
| Langfuse projects | TWO — Portage, factory agents | Independent key rotation; separate retention; customer PII isolated |
| Data disk | `/data` on sda4 (3.4TB xfs, mounted) | DB volumes off the OS disk |
| Access policy, 8 ungated hostnames | Strict email allowlist on all 8 | All 8 are operator surfaces. Portage beta runs on `portage.`/`portage-api.`, already gated with an allowlist containing the testers. No tester locked out. |
| medkb location | Moves to dh40801 | Zero consumers; 8 MB; colocates store with the GPU generating its embeddings; frees .251 for beta |
| 990 PRO reformat | NO | `/data` is 2% used of 3.4TB. Serves nothing this ship needs. RESOLVED, not parked. |
| Service account | Skipped | docker-group membership is already root-equivalent, so it buys attribution + revocation only |

## Acceptance criteria

### A — Langfuse stack
1. Six containers on dh40801, compose project `dhg-langfuse`, all `dhg-` prefixed, all `restart: unless-stopped`
2. All image tags pinned exactly (no `:latest`, no major-only floats); web and worker on the SAME patch version
3. Every container sets `TZ=UTC`; ClickHouse also sets server-side `timezone: UTC`
4. `DATABASE_URL` sets an explicit `connection_limit`. Prisma v6 confirmed (`prisma: ^6.19.3`): default is 24x2+1 = 49/process x2 processes = 98 against 97 usable — a real startup failure without this
5. Postgres healthcheck uses `$${POSTGRES_USER}` — HYGIENE ONLY. (An earlier draft claimed a non-default user breaks the stack; that is FALSE — `pg_isready` exits 0 regardless of user validity.)
6. Redis runs `--maxmemory <N> --maxmemory-policy noeviction --appendonly yes`; `mem_limit` exceeds maxmemory by >=30%
7. ClickHouse has BOTH a cgroup `mem_limit` AND explicit `max_server_memory_usage`, `mark_cache_size`, `uncompressed_cache_size`
8. Healthchecks on `langfuse-web` and `langfuse-worker` (upstream has none); ClickHouse `start_period` >= 30s
9. ONLY the web port published; ClickHouse, Postgres, Redis, MinIO unpublished
10. Secrets generated via `openssl rand`, stored in a NEW Doppler project `langfuse`; nothing secret in the repo; nothing under `/home` (Samba-exported, writable)
11. ClickHouse + MinIO data volumes on `/data`
12. **`scripts/lint-langfuse-compose.sh` committed and passing** — asserts AC 1,2,3,4,6,7,8,9 mechanically. Re-runnable on every future edit.
13. Langfuse org + 2 projects created; keys minted per project
14. MinIO lifecycle expiry + ClickHouse retention configured (retention management is enterprise-gated, so manual)
15. Sampling at 1.0 for beta, with a documented trip-wire (drop to 0.25 if >50k traces/day or MinIO events bucket >100GB)

### B — Cloudflare Access
16. `*.digitalharmonyai.com` wildcard no longer `bypass`/`everyone`
17. Dedicated Access app for each of the **8** ungated hostnames (registry, knowledge, app, chat, grafana, docs, dhgdocs, rehearsal): `decision: allow`, explicit email allowlist, 24h session, existing OAuth IdP
18. `labs.digitalharmonyai.com` Access app created BEFORE its DNS record exists
19. **`scripts/check-public-exposure.sh` committed** — curls every tunnel hostname and asserts each redirects to Access or returns 401/403. This is the pass/fail gate (supersedes verifying config by inspection)
20. `otel.` keeps its working `non_identity` service-token policy — DO NOT touch
21. `portage-api/billing/webhook`, `portage-images.`, `c2l.` bypass apps confirmed intentional before any change

### C — Portage deploy + repoint
22a. `feat/langfuse-tracing` merged to Portage `main` (or deployed from the branch by explicit decision) — WITHOUT this, no tracing exists at all
22b. Rebuilt `portage-api` image VERIFIED to contain `dist/instrumentation.js` and `node_modules/@langfuse` — the check that would have caught this
22. Doppler `dev` pointed at self-hosted, rebuilt, trace verified via the Langfuse API/CLI
23. Doppler `prd` in a quiet window BEFORE beta users; `"Langfuse tracing enabled"` in logs AND a real trace present
23b. `LANGFUSE_SELFHOST_HANDOFF.md:29` corrected — it currently asserts prod is tracing successfully, which is false and misled this ship's planning
24. **Rollback documented and rehearsed:** revert 3 Doppler values (`LANGFUSE_BASE_URL` + 2 keys), rebuild `portage-api`. Rollback success is verified by TRACE ARRIVAL, not container health — a partial Doppler state silently disables tracing
25. **Masking regression check:** a scanned-item trace in self-hosted Langfuse contains no base64 image data (API-checked, not eyeballed)
26. **SIGTERM flush bounded** by an explicit timeout in `shutdownTracing()`, OR a recorded decision to accept slower deploys

### D — agent migration
27. All **14** modules importing `tracing` migrated to Langfuse `CallbackHandler`; `LANGSMITH_*` and `LANGCHAIN_TRACING_V2` removed
28. Explicit decision recorded on the parallel OTel->Tempo export (keep, or consolidate)
29. A real agent run produces a trace in the factory Langfuse project

### E — user-level attribution
30. Langfuse user id = `req.user.email` across all 5 Portage AI features; `tier` + internal UUID as metadata; TDD, one test at a time
31. OTel `service.name = portage-api`
32. A trace is attributable to a real user and the Langfuse Users view populates

### F — dashboards
33. Langfuse cost + user dashboards created
34. Grafana dashboard covering dh40801 host metrics and the Langfuse container set

### G — medkb relocation + ingestion
35. **GATE, do first:** medkb's configured embedding model/dimension verified to match nomic-embed-text (768). Mismatch means re-embedding everything.
36. `dhg-medkb-api`, `dhg-medkb-db`, `dhg-medkb-cache` running on dh40801; 8 MB volume migrated; `/v1/healthz` green from .251; `dhg_cme_sample` corpus still queryable
36b. **medkb is NOT zero-consumer — the monitoring plane references it.** `registry/patchbay_service.py:34` hardcodes `"medkb": 8015` probed at `PROBE_HOST=10.0.0.251` (line 16), keyed to match frontend `services.ts`. Moving medkb to 10.0.0.179 turns the patchbay tile red unless the probe target is updated. Update `patchbay_service.py` (and the matching `services.ts` entry) to point the medkb probe at 10.0.0.179; verify the tile is green after the move. (An earlier draft claimed "ZERO consumers" — false; corrected 2026-07-21 by the session audit.)
37. medkb removed from the .251 compose stack, no orphaned volumes
38. Ingestion pipeline on dh40801: Docling parse -> transcribe (reusing `dhg-transcribe`'s faster-whisper) -> embed (Ollama container) -> write **through medkb's models/migrations**
39. End-to-end smoke test: a real document lands in a new corpus and is retrievable via `/v1/query`
40. `dhg-kb-db` NOT created; port 5433 released; Haystack NOT installed — verified by absence
41. Resource caps set BOTH directions so neither Langfuse nor the KB workload can starve the other
42. `dh40801` added to `ansible/inventory.yml` for asset truth ONLY — NOT joined to `docker_hosts` until `docker-compose-deploy.yml` is parameterized with `compose_file`/`compose_project`/`repo_path`
43. SOP Phase 1 leftovers applied on dh40801: `vm.swappiness=10`, unattended-upgrades kernel/nvidia blacklist

### H — memreg integration
44. `langfuse` and `medkb` tags added to the `auto-*-capture.md` rules; `project_name` stays `dhg-ai-factory`
45. A capture from Langfuse or medkb work lands in the registry with the correct tag — verified by querying for it
46. Langfuse -> registry ingestion carries ONLY curated signals. Verified: no prompt body, no completion body, no media reference, no user identifier in any ingested record
47. Registry KB search federates to medkb `/v1/query`; one query returns merged results
48. Both ingestion paths idempotent — running twice creates no duplicates (verified by row count)
49. Workstream B COMPLETE before any Langfuse ingestion runs

### Monitoring, backup, docs
50. node-exporter + cadvisor + promtail on dh40801; Prometheus static job on .251; disk alerts at 75%/85%
51. Blackbox probe from .251 to the Langfuse health endpoint — the only detector of a dead collector, since the client fails silently by design
52. Nightly `pg_dump` of the Langfuse Postgres to .251 (holds orgs, projects, and the API keys prod authenticates with)
53. **FIX EXISTING GAP: `scripts/backup.sh` is not in any crontab — registry backups are not running today.** Schedule it alongside the Langfuse backup
54. `reference_port_map.md` extended with a dh40801 section (5433 released, not reserved)
55. `LANGFUSE_SELFHOST_HANDOFF.md` corrected — it currently names g700data1 as the target
56. Portage `df272d0` cherry-picked to Portage `main`

## Edge cases / failure modes

- **Collector unreachable:** verified from code — `BatchSpanProcessor`, no `forceFlush` at any request call site, drops on queue overflow. User requests never blocked. Failures are therefore SILENT — hence AC-51.
- **Half-finished Doppler repoint:** `tracingEnabled` requires BOTH keys; a partial rollout silently disables tracing. Verify by trace arrival (AC-24).
- **Portage SIGTERM flush:** `shutdownTracing()` has no timeout; an unreachable collector delays shutdown to Docker's grace period (AC-26).
- **Masking regression:** client-side masking is the only masking (server-side is enterprise-only). A library writing images as non-string attributes bypasses `scrubSpanAttributes` — this is how photos leaked before. AC-25 checks it; the MinIO quota is the second line of defence.
- **Co-tenancy:** memory breaks first, then disk. GPU is not contended by Langfuse.

## Workstream B detail — exposure PARTIALLY REMEDIATED 2026-07-21

**Original finding:** `*.digitalharmonyai.com` was `bypass/everyone`, 168h session; 8 of 12 tunnel hostnames had no Access gate (app, grafana, registry, chat, knowledge, dhgdocs, rehearsal inherited the wildcard; docs had its own bypass/everyone app). `registry.` served live API data + a public Swagger UI.

**DONE (Stephen ratified):** created dedicated `allow`+allowlist Access apps for registry, knowledge, app, chat, grafana, dhgdocs, rehearsal (all 24h session, 4-email allowlist); converted docs. from bypass to allow. Verified from the public edge: all 12 hostnames now 302->Access or 401. `otel.` non_identity service-token app untouched. **AC-17 is COMPLETE.**

**STILL OPEN:**
- **AC-16** — the `*.digitalharmonyai.com` wildcard is STILL `bypass/everyone`. It no longer matters for the 12 known hostnames (each has a more-specific app that wins), but any NEW hostname is public-by-default until this is flipped to allow+allowlist. This is the standing landmine — highest-priority remaining B item. Reversible in one API call; the three intentional bypasses (portage-api/billing/webhook, portage-images., c2l.) have dedicated apps and survive the flip.
- **AC-18** — `labs.` Access app, before its DNS record.
- **AC-19** — commit `scripts/check-public-exposure.sh`.
- **AC-21** — confirm the intentional bypasses (note c2l. is vestigial — no live ingress).

## Open items carried into Phase 3

- Exact port block for dh40801 (advisors disagreed; one proposal used 3100, which collides with Loki's fleet convention)
- ClickHouse `mem_limit` (10g vs 16g) and Redis `maxmemory` (768mb vs 3gb) — reconcile against measured beta volume
- Whether Langfuse media upload is enabled (decides whether MinIO can stay unpublished)

## === SESSION HANDOFF #2 (2026-07-21 late) — READ FIRST, urgent git-recovery pending ===

**IMMEDIATE STATE — Portage tracing is LIVE but git main does NOT reflect it. Recover before any rebuild.**

Where things are (all verified minutes ago, in `~/DHG/portage`):
- **Running `portage-api` container IS tracing** — `instrumentation.js` PRESENT, log shows `Langfuse tracing enabled` env=production sampleRate=1. Built from merge `2fa0be8`. Health 200.
- **Langfuse Cloud still shows 11 traces** (newest 7-20). No NEW trace yet — nobody has triggered a scan/Porter action since the deploy. To confirm end-to-end: do ONE scan or Porter message in the app, then `curl -u pk:sk https://us.cloud.langfuse.com/api/public/traces?limit=1` → expect totalItems=12, today's date. (keys: `doppler secrets get LANGFUSE_PUBLIC_KEY -p portage -c prd --plain`, same for SECRET.)
- **THE PROBLEM:** a `git reset --hard origin/main` ran in this session (reflog `HEAD@{0}: reset: moving to origin/main`) and threw away the merge. HEAD is now `93087e7` (origin/main, GitHub PR history); **the Langfuse merge `2fa0be8` is dangling off main.** So the DEPLOYED image has tracing, but git main (93087e7) does NOT — a rebuild from main re-loses tracing (the exact regression we just fixed). The recovery below re-establishes it AND pushes so it is durable.

**RECOVERY PLAN (do this first in the new session):**
1. `cd ~/DHG/portage` — confirm HEAD still `93087e7`, `git cat-file -t 2fa0be8` = commit (recoverable).
2. Re-merge onto current origin/main: `git merge --no-ff feat/langfuse-tracing`. ONE conflict recurs in `apps/api/src/routes/prepare-listing.ts` — resolution: keep the `traceRequest(...)` wrapper AND the `reverbCategories,` field inside `generateListingFields({...})`. (The exact resolved region: `reverbCategories,` then `        }),` then `      );`.)
3. **After merge, REVERT the compose binding:** the branch changes `portage-db` to `"10.0.0.251:5436:5432"` (LAN-exposes Postgres with default `portage:portage` creds). Set it back to `"127.0.0.1:5436:5432"`. The app uses the internal network (`portage-db:5432`) and needs no host binding; only host-run migration/seed tooling uses 5436, works on loopback.
4. `npm --prefix apps/api run typecheck` (was clean before), commit the merge.
5. **PUSH it so the reset can't kill it again:** `git push origin main` (or open a PR per the repo's PR convention #251/#252 — repo uses GitHub PR merges). `feat/langfuse-tracing` exists ONLY on local disk — also `git push -u origin feat/langfuse-tracing`.
6. No rebuild needed — running image already has identical tracing code. If you do rebuild: `docker compose build portage-api && docker compose up -d --no-deps portage-api` (`--no-deps` avoids DB recreate).
7. Rollback if needed: image `portage-api-rollback:2026-07-21` retagged to `portage-portage-api:latest` + `docker compose up -d --no-deps portage-api`.

**Bonus already achieved:** `df272d0` (conditionNotes cap 500→2000, a live prod save-bug fix) is in the same merge — lands with it.

---

## === SESSION HANDOFF (2026-07-21) — Langfuse self-host /ship, still Phase 1 ===

**Next action Stephen chose: the CLOUD-FIRST TEST, before building any self-hosted infra.**

Verified live via the Langfuse Cloud API (portage/prd keys, read-only): keys authenticate; project "My Project" / org "Stephen's Organization" exists at https://us.cloud.langfuse.com; **11 traces exist, the 4 newest are `env: production` from 2026-07-20 (scan-refine / scan-item / porter-chat-turn), real user id.** Monitor URL: https://us.cloud.langfuse.com/project/cmrs907u20h8zad0jzu2xm2b4/traces

**Reconciled truth (two of Claude's claims this session were wrong, opposite directions):**
- The handoff doc's "traces verified flowing" was TRUE when written (7-20).
- Claude's "tracing never ran in prod" was FALSE — it checked the running container (empty image) but never the Cloud API.
- Actual: tracing WAS live & emitting production traces on 7-20, then a later `docker compose build` while the Portage repo sat on `main` (branch `feat/langfuse-tracing` unmerged) replaced the running image with one that has no `dist/instrumentation.js` and no `@langfuse`. That is why the live container looks un-instrumented.

**The test:** in `~/DHG/portage` (currently on `main` b2a6db1) merge/deploy `feat/langfuse-tracing` (commits 6f0c78f tracing + df272d0 conditionNotes save-bug fix — the latter is a LIVE prod bug, land it on main regardless), rebuild `portage-api` (build context is `.`), trigger one AI action, confirm a NEW production trace via `curl -u pk:sk https://us.cloud.langfuse.com/api/public/traces?limit=1` (totalItems > 11). If it works → instrumentation proven, self-host is a pure backend swap. If not → fix instrumentation before touching infra.

**State changes made this session, Stephen-ratified:** (1) Cloudflare Access — created allow+allowlist apps for registry/knowledge/app/chat/grafana/dhgdocs/rehearsal + converted docs. bypass→allow; all 12 tunnel hostnames now gated; `otel.` untouched; **wildcard `*.digitalharmonyai.com` STILL bypass/everyone = AC-16, the #1 open Cloudflare item.** (2) `/data` mounted on dh40801. (3) killed 18 orphaned Claude session trees on .251 (~28GB freed); reaper at `~/.claude/scripts/reap-orphan-sessions.sh` — MANUAL ONLY, never cron.

**Open:** AC-16 wildcard flip; correct handoff doc line 29 (untracked at repo root); AC-36b patchbay medkb probe repoint; `scripts/backup.sh` not in cron. Dormant unused keypair `~/.ssh/dhg-agent_ed25519`.

**Behavioral standing correction:** before claiming verified/working/done/flowing — run the read or command in the SAME turn. Three document-trusted claims this session (Access pattern, traces flowing, medkb zero-consumers) were all wrong and caught only by looking.

**Phase status:** Phase 1 complete, audit-cleared. After the Cloud-first test, resume at Phase 2 (full 3-agent divergent explore). Prior versions: `_v9` (deferred Debug Ops), `_v10` (spec v1).

## Version history

- v1 (2026-07-21) — initial spec after 5 specialist advisor reviews. Snapshot: `ship-state_v10.md`
- v2 (2026-07-21) — 12 defects fixed: cancelled `dhg-kb-db`/Haystack/WhisperX ACs that contradicted Workstream G; added the 9 missing G ACs for the medkb move and ingestion; added rollback (AC-24), masking check (AC-25), SIGTERM bound (AC-26), lint script (AC-12), exposure sweep script (AC-19), backup cron gap (AC-53); corrected 12->14 modules, 9->8 ungated hostnames, 5->7 advisors; removed the stale "agent migration out of scope" line; renumbered all ACs 1-56 contiguously by workstream

---

# PHASE 2 SYNTHESIS + CORRECTIONS (2026-07-26)

**The original spec's core premises were refuted by verification. Corrections (each cited):**

1. **Workstream C REFUTED — Portage tracing is already LIVE, pointed at Langfuse Cloud US.** The spec's "CRITICAL CORRECTION" (prod has no tracing, feat/langfuse-tracing unmerged) is stale. Verified: `portage-api` container has `@langfuse` 5.9.1 (`docker exec ls node_modules/@langfuse`), `LANGFUSE_BASE_URL=https://us.cloud.langfuse.com` (`docker exec env`), feat/langfuse-tracing MERGED to main. Real action = repoint env + **`docker compose up -d portage-api` (RECREATE, not `docker restart`)** (vars baked from env_file at create — F-INFRA). No rebuild, no branch deploy.

2. **Langfuse v3 topology corrected to 6 containers** (LF-COMPOSE authoritative, github.com/langfuse/langfuse): langfuse-web (langfuse:3), langfuse-worker (langfuse-worker:3), postgres:17, clickhouse-server:25.12, redis:7, minio (chainguard). NOT medkb's 4-container clone. Secrets (# CHANGEME): POSTGRES_PASSWORD, DATABASE_URL, SALT, ENCRYPTION_KEY, NEXTAUTH_SECRET, CLICKHOUSE_PASSWORD, REDIS_AUTH, MINIO_ROOT_PASSWORD, 3x S3 keys + NEXTAUTH_URL + LANGFUSE_INIT_*.

3. **Registry-public premise REFUTED for THIS ship's purpose.** All 12 tunnel hostnames challenge anon requests (302→cloudflareaccess), incl registry. (F-SEC curl). Whether each Access POLICY restricts identity vs bypass/everyone = UNVERIFIED (dashboard-only). Cloudflare Access remediation is de-scoped from this ship unless policy audit shows a bypass.

4. **Infra corrections (F-INFRA):** external `dhgaifactory35_dhg-network` does NOT exist on dh40801 → use stack-local network. Named volumes land in `/var/lib/docker` not `/data` → bind-mount to `/data/langfuse/*`. Stock compose exposes minio `9090:9000` + web `3000:3000` on ALL interfaces → bind non-web ports to 127.0.0.1.

5. **Agent tracing (15 registered modules / 18 files real @traceable, langgraph.json) PARKED** (d571a7d6) — not beta-blocking; strategy unresolved (OTLP-exporter+LANGSMITH_OTEL_ENABLED=true vs handoff:94 CallbackHandler swap).

**Divergent yield (park list):** eval-driven capture, PostHog×Langfuse email join, `_extract_langfuse_trace` KB source, GPU colocation — all post-beta.

**Full plan artifact:** scratchpad/langfuse-ship-plan.md (3 architecture diagrams + source-tagged facts + 5 verification gates G1-G5).

---

# PHASE 3 PLAN — TASK LIST (scope: Part A install + Part B repoint)

**Legend:** [CLAUDE] I execute · [STEPHEN] genuinely gated (root sudo password / Cloudflare Access dashboard — not offloadable) · verify/rollback per task.

## Part A — Install Langfuse on dh40801

- **A1 [CLAUDE] Pre-flight verify.** `docker --context dh40801 ps -a` (empty), `network ls`, `ssh dh40801 'df -h /data && ls -ld /data'`. Verify: state matches F-INFRA. Risk: low (read-only).
- **A2 [CLAUDE] Provision /data dirs + Doppler.** `ssh dh40801 mkdir -p /data/langfuse/{postgres,clickhouse,clickhouse_logs,minio,redis}` + chown store UIDs (pg 999, ch 101). `doppler projects create langfuse`; generate every CHANGEME secret via openssl into config prd. Verify: dirs exist w/ correct owner; `doppler secrets --project langfuse` lists all; none in repo. Risk: low. Rollback: `rm -rf /data/langfuse`, delete Doppler project.
- **A3 [CLAUDE] Author `dh40801/docker-compose.langfuse.yml`.** Base LF-COMPOSE; deltas: dhg- prefix, stack-local network, bind-mounts /data/langfuse/*, NEXTAUTH_URL=https://labs.digitalharmonyai.com, minio+all non-web ports→127.0.0.1, exact image pins. Verify: `docker --context dh40801 compose -f ... config` parses; grep no `:latest`, no `external:`. Risk: low (file only). Rollback: rm file.
- **A4 [CLAUDE] Deploy stack.** `doppler run -p langfuse -c prd -- docker --context dh40801 compose -f dh40801/docker-compose.langfuse.yml -p dhg-langfuse up -d`. [VERIFY] Doppler interpolation into remote-context run; fallback `doppler secrets download --format env` → `--env-file`. Verify: 6 containers Up(healthy). Risk: MEDIUM (service, new host). Rollback: `docker --context dh40801 compose -p dhg-langfuse down` (keep volumes).
- **A5 [CLAUDE] First-boot + keys.** ClickHouse migrations in web logs; `curl 10.0.0.179:3000/api/public/health` from .251 → 200; org/project/user bootstrapped; capture project public/secret keys → Doppler. Verify: health 200, keys captured. Risk: low.
- **A6 [CLAUDE] Exposure gate G1.** From .251 `nc -zv 10.0.0.179` for 9090/8123/9000/6379/5432 → all REFUSE; 3000 → accept. Verify: only 3000 open. Risk: low (read). If a store port is open → fix A3 bind, redeploy.

## Part B — Repoint Portage

- **B1 [STEPHEN] Access app `labs.` before DNS.** Cloudflare Access dashboard/API — Claude is classifier-blocked from Access API (not offloadable). Email allowlist, created before DNS record. Verify: app exists.
- **B2 [STEPHEN] Tunnel ingress.** `/etc/cloudflared/config.yml` is root-owned + sudo needs password (F-INFRA) — genuinely a Stephen step. Add `labs.digitalharmonyai.com → http://10.0.0.179:3000` above 404 catch-all; `cloudflared tunnel route dns`; `systemctl reload cloudflared`. Verify G2: `curl -I https://labs.` → 302 cloudflareaccess.
- **B3 [CLAUDE] Repoint Portage.** Portage Doppler: `LANGFUSE_BASE_URL=http://10.0.0.179:3000` (LAN ingest), keys = A5 project keys. `docker compose up -d portage-api` from /home/swebber64/DHG/portage (RECREATE). Verify: `docker exec portage-api env | grep LANGFUSE_BASE_URL` = new URL. Risk: MEDIUM (prod Portage). Rollback G5: revert Doppler to us.cloud + recreate; confirm by trace arrival.
- **B4 [CLAUDE] E2E trace + masking gate G3.** Drive one real Portage AI action; confirm trace in self-hosted UI; **API-verify trace has ZERO base64 image data** (F-SEC: masker is base64-only). Risk: low (read).
- **B5 [CLAUDE] Reporting gate G4.** Confirm cost + usage populate in Langfuse project dashboard. Risk: low.

## Deploy order
A1→A6 (Langfuse healthy + hardened) BEFORE B. Within B: B1→B2 (edge gated) BEFORE B3 (repoint), so labs never resolves ungated. B3→B5 after.

## HARD GATE
Awaiting Stephen: **go / approved / build it / ship it** to enter Phase 4.

---
# PHASE 4 PROGRESS (2026-07-26)

## PART A — COMPLETE + VERIFIED
- A1 pre-flight: dh40801 clean, ports free, /data writable no-sudo but sudo needs pw -> switched to NAMED VOLUMES (789G OS disk).
- A2: Doppler project `langfuse` prd, 16 secrets set via openssl (ENCRYPTION_KEY 64 hex verified), none in repo.
- A3: dh40801/docker-compose.langfuse.yml authored (commit 1383ebf) — 6 services, stack-local net, named volumes, all non-web ports 127.0.0.1. config parses, Doppler interpolation verified.
- A4/A5: deployed (doppler run + remote context); web crash-looped on ClickHouse ON CLUSTER/Zookeeper -> FIXED CLICKHOUSE_CLUSTER_ENABLED=false (commit ae6049c, bug 41690df7, cited Langfuse docs). Health 200 v3.224.1, all 6 up.
- A6 GATE G1: PASSED — only :3000 LAN-open; postgres/clickhouse/redis/minio/worker all refused.

Langfuse UI live at http://10.0.0.179:3000 (LAN). INIT project keys in Doppler langfuse/prd (LANGFUSE_INIT_PROJECT_PUBLIC_KEY / _SECRET_KEY).

## PART B — COMPLETE (2026-07-29). SHIP DONE.
- B1 DONE [STEPHEN 2026-07-28]: Cloudflare Access app labs. created.
- B2 DONE [STEPHEN 2026-07-28] + GATE G2 PASSED (verified 2026-07-29): `curl -I https://labs.digitalharmonyai.com` -> 302 digitalharmonyai.cloudflareaccess.com login. Edge gated, never resolved ungated.
- B3 DONE: prod portage-api recreated, LANGFUSE_BASE_URL=http://10.0.0.179:3000 verified in container env + "Langfuse tracing enabled" log (sampleRate 1). Also fixed: prod was on Doppler dev config (prior session).
- B4 GATE G3 PASSED (2026-07-29): 4 real scan-refine traces (real user traffic 07-27, user-attributed) in self-hosted instance. Newest trace (0be9b9e8eb77a7b2c5175e4b2060121c, 5 obs) API-verified: ZERO raw base64 — both image_url fields read "[image redacted: 293228 base64 chars]", no base64 runs >500 chars anywhere in 71KB trace JSON. Masker confirmed against PROD traffic (was dev-only validated).
- B5 GATE G4 PASSED (2026-07-29): /api/public/metrics/daily — 2026-07-27: 4 traces, 17 obs, $0.0273 total; per-model usage populated (gemini-2.5-flash 41806 in / 5896 out @ $0.0273; qwen3:4b local 259/2048 @ $0 — expected zero for local model).
