---
title: "Backups and disaster recovery: nightly encrypted dumps, Synology mirror, restore drills, NAS monitoring"
sidebar_label: "003 Backups & DR"
sidebar_position: 3
---

# Backups and disaster recovery: nightly encrypted dumps, Synology mirror, restore drills, NAS monitoring

| Field | Value |
|-------|-------|
| **Status** | complete |
| **Complexity** | complex |
| **TDD** | Yes (bats on pure functions and shimmed orchestration; live runs for the rest) |
| **PR** | https://github.com/sdnydude/dhgaifactory3.5/pull/30 (stacked on #29) |
| **Completed** | 2026-09-12 |
| **Model** | Claude Fable 5.1 (`claude-fable-5-1`) |

## Approach

One bash orchestrator on g700data1 streams every data store out of its own
container (`docker exec`/`docker cp`, local or the `dh40801` context), encrypts
each archive with gpg, writes a manifest last as the commit marker, keeps the
full retention locally and mirrors the tree to the Synology over rsync-in-SSH
mode with a dedicated non-admin user and key. A second script restores every
target into a throwaway container and checks exact counts. Storage tooling
(restic, pgBackRest, Kopia) was rejected after an advisor review: at ~100 MB a
night of already-compressed dumps it relocates custom code rather than removing
it. The NAS itself is now monitored over SNMPv3, because it had been running on
four of six disks since February with nobody knowing.

## Spec

13 targets (7 Postgres on g700data1, Langfuse Postgres/ClickHouse/MinIO on
dh40801, plane MinIO, Grafana/exports/open-webui volumes, the config/secrets
layer), nightly 03:30 ET, gpg AES256 with a Doppler passphrase (escrowed),
manifest-last, local retention 30 nightly + 84 d Sundays, NAS mirror
`rsync -a --delete --delete-delay --delay-updates`, Sunday restore drills into
ephemeral containers with exact equality, textfile metrics, four backup alerts
and six NAS alerts (human-only), a `dhg-platform-backups` dashboard, docs, and a
ClickHouse system-log diet on dh40801. Explicit exclusions documented. Full
spec and residual-risk statement: [Backups & disaster recovery](../backups.md).

## Exploration findings

- `node_textfile_mtime_seconds{file}` carries the full host path, so the
  TextfileStale exclusion had to be a regex.
- The registry webhook fingerprints `alertname|service|instance` from
  `name`/`job`; without a per-target `name` label all 13 targets collapse into
  one incident.
- 88 % of the nightly payload was open-webui's regenerable model cache;
  excluded at the source.
- No `sqlite3` anywhere locally: grafana.db integrity is checked in a prebuilt
  alpine+sqlite drill image; drills run `--network none`, so images are
  pre-pulled and pre-built.
- Langfuse secrets live in Doppler `langfuse/prd`, not `dev`; a compose recreate
  under the wrong config would have started ClickHouse with a blank password.
- Prometheus has no lifecycle endpoint; reload is `docker kill -s HUP`.
- The Synology: DSM 7.1.1 (immutable snapshots need 7.2), rsync-over-SSH needs
  the rsync service on (873 keeps listing module names), a No-Access rule on
  `homes` breaks the backup user's key auth, SNMPv1/2c community `public` was
  answering the whole LAN.

## Commits

- `d43db56` fix(langfuse): ClickHouse system-log diet via config.d drop-in (9.6 GiB → 172 KiB)
- `ca89d13` feat(backups): backup-lib.sh pure functions + bats suite + Shell tests CI job
- `99f39e5` feat(backups): backup-all.sh nightly orchestrator + 13 bats tests
- `7b90e62` feat(backups): restore-drill.sh ephemeral restore verification + 8 bats tests
- `f15b679` fix(backups): keep manifest ints/objects typed; exclude .state from the NAS mirror
- `57db845` feat(observability): backup + NAS alert rules, runbook docs, human-only trigger map entries
- `78773e8` feat(observability): Synology NAS monitoring over SNMPv3 (dhg-snmp-exporter, job nas)
- `283d4af` fix(backups): restore drill defects found by the first live --all run
- `cfd1656` feat(observability): Backups & NAS dashboard (dhg-platform-backups) + crontab
- `af14b8e` docs(backups): backups.md page, runbook pointer, CLAUDE.md; remove legacy backup scripts
- `daeddf5` fix(backups): Phase 6 review fixes — exit codes, success gating, alert blind spot, plaintext scratch, drill contracts

## Verification

- **tests:** bats 40/40 (`observability/tests`, CI job *Shell tests*), promtool unit tests for the backup rules (in CI), registry pytest 708 passed / 0 failed, rule-map test 12/12.
- **live:** three unattended nightly runs (03:30 ET 2026-09-11 and 2026-09-12) 13/13 ok with mirror; `restore-drill.sh --all` 13/13 (46 s; registry-db 9 s vs the 30-min SLO); isolation check with a stopped source container; NAS mirror dry-run empty; no scratch, plaintext, containers or volumes left behind.
- **health checks:** registry-api healthy after rebuild, ClickHouse healthy after recreate (Langfuse counts unchanged, canary green), `dhg-snmp-exporter` up, Prometheus 36/36 targets, 50 rules live.
- **alerts:** only `NasRaidDegraded` firing, on purpose (pool at 5 of 6), with its registry incident; TextfileStale silent.
- **AgentShield:** 0 new findings against the refreshed baseline, gate passed.
- **performance baselines:** nightly backup 30 s wall (~100 MB); full drill 46 s; NAS scrape 60 s interval.
- **dashboard:** `verify-dashboard.sh dhg-platform-backups` 17/17 panels, PNG rendered and inspected.

## Review findings

Six-agent panel plus a classification audit. Critical: unknown `--target` exited 0 as "all targets ok"; a manifest/rename failure still stamped success; a ClickHouse decrypt failure passed as an empty table; drill plaintext scratch inside the mirrored tree with no lock (audited up to Critical as a security issue). Important: never-succeeded targets invisible to BackupFailed/RestoreDrillStale (fixed with `unless on(name)` + promtool unit tests), roles-restore error swallowing, tar pipeline status, doppler error masking, reporter exit codes, numeric state guard, manifest key guard, several doc inaccuracies (flock claim, fifth rendered secret file, unscoped NAS runbook queries). All fixed test-first; a further live-only defect (the chainguard MinIO image seeds `/data/.minio.sys`) fixed during re-verification.

## Deferred Items

- DSM 7.2 upgrade + immutable snapshots on `aifactory-backups` — after Drive 1 and at Stephen's timing (Video Station's removal in 7.2.2 is the only consideration) — high — registry `8baeab4c`.
- ContainerCrashLoop's description text in `alerts.yml` is a copy of ContainerMemoryLeak's (pre-existing) — low — needs approval to record.

## Park List

- CI red baseline (POSTGRES_PASSWORD default in Validate Docker Compose; CLAUDE.md container-name drift; ruff 62; uuid-ossp in CI Postgres) — separate small ship.
- Remediator deployed-image parity with source — verified in review: image postdates the fix; closed.
- Pre-existing NAS user `claude` with rsync/DSM/AFP/SMB/Drive allow rules — Stephen to confirm.
- `produce_pg` fifo plumbing could be a coproc; bats setup dedup into a helper — style, works, not touched.

**Tags:** `backups` `disaster-recovery` `synology` `snmp` `prometheus` `grafana` `clickhouse` `gpg` `rsync` `bats` `tdd-guard`
