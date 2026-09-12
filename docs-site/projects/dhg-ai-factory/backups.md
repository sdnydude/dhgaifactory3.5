---
sidebar_position: 8
title: Backups & disaster recovery
---

# Backups & disaster recovery

Every DHG AI Factory data store is dumped nightly, encrypted, verified, kept
locally with a 30-day / 12-week retention, mirrored to the Synology NAS, and
restored into a throwaway container every Sunday to prove the copies are real.
The whole system is two shell scripts, one Prometheus textfile, ten alert rules
and one dashboard. Shipped 2026-09-11 (Langfuse ship AC#53, registry deferred
item `f530537e`).

**What you open:** Grafana → [Backups & NAS](http://10.0.0.251:3001/d/dhg-platform-backups).
Green header means every target has a verified run under 28 h old, the NAS
mirror is fresh and every drill passed inside 8 days.

## Purpose

Database dumps restore *data*; the config layer restores the *ability to start
anything*; the NAS mirror survives the loss of g700data1's NVMe; the drills
turn "we have backups" into "we have restored them". Before this ship no
scheduled backup existed anywhere in the fleet and the NAS had been running on
four of six disks since February with nobody knowing.

## Targets

| id | kind | source | what is captured |
|---|---|---|---|
| `registry-db` | pg | `dhg-registry-db` (pgvector pg15) | `dhg_registry` + `snap2list`, roles (`grafana_ro`) |
| `medkb-db` | pg | `dhg-medkb-db` | `medkb` |
| `eval-db` | pg | `dhg-eval-db` | `evalviewer` + `evalviewer_test` |
| `audio-postgres` | pg | `dhg-audio-postgres` (pg16) | `audio_agent` |
| `transcribe-db` | pg | `dhg-transcribe-db` | `transcribe` |
| `portage-db` | pg | `portage-db` | `portage` |
| `plane-db` | pg | `plane-app-plane-db-1` | `plane` (socket at `/var/run/postgresql`) |
| `langfuse-postgres` | pg | `dhg-langfuse-postgres` on dh40801 | `postgres` |
| `langfuse-clickhouse` | clickhouse | `dhg-langfuse-clickhouse` on dh40801 | DDL of every `default.*` object + one Native stream per table |
| `langfuse-minio` | minio | `dhg-langfuse-minio` on dh40801 | raw xl-single tree `/data` incl. `.minio.sys` |
| `plane-minio` | minio | `plane-app-plane-minio-1` | raw tree `/export` |
| `volumes` | volume | `dhg-grafana`, `dhg-registry-api`, `dhg-open-webui` | `grafana.db`, `/exports`, open-webui data minus `cache/` |
| `config` | files | host filesystem | `observability/scripts/config-layer.list`: `.env` files, `docker-compose.override.yml`, the five Doppler-rendered secret files |

Every Postgres target is dumped with `pg_dump -Fc` under a `pg_export_snapshot()`
taken by one `REPEATABLE READ` session that also counts every user table, so the
manifest's row counts and the archive describe the same instant. ClickHouse
Native streams are self-describing; the drill counts rows in the file itself.
All producers run *inside* the source container through `docker exec`/`docker cp`,
so no database credential ever leaves its container and the backup host needs
none.

### Explicitly not backed up

| what | why |
|---|---|
| Prometheus TSDB (3.7 GB), Loki (2.3 GB) | regenerable telemetry |
| Alertmanager silences | ephemeral |
| Langfuse Redis | queue cache; Langfuse documents it as ephemeral |
| ClickHouse `system` database | internal logs (now capped at 7 days by the config.d drop-in) |
| open-webui `cache/` (1.1 GB) | regenerable model cache |
| transcribe uploads (4 GB), qdrant (1.3 GB), whisper models | owned by the transcribe refactor ship |
| Langfuse environment on dh40801 | lives in Doppler project `langfuse`; there is no `dh40801/.env` |

## Layout, encryption, retention

```
/mnt/4tb/backups/nightly/<target>/<UTC-run>/   e.g. registry-db/20260911T025420Z/
    dhg_registry.dump.gpg   roles.sql.gpg   manifest.json
/mnt/4tb/backups/nightly/.state/<target>/{attempt,success,size_bytes,duration_seconds,drill_success}
```

- Every archive is `gpg --symmetric --cipher-algo AES256`; the passphrase is
  `BACKUP_GPG_PASSPHRASE` in Doppler `dhg-monitoring/dev`, fed on fd 3, never
  in argv. **Escrow:** Stephen keeps a copy in his password manager. A Doppler
  outage or lockout must never mean unreadable backups.
- `manifest.json` is written **last** and is the commit marker: it records the
  source image tag, per-file `sha256` + bytes, per-table counts (pg), member
  counts (tar). Prune and drills ignore run directories without one, so a run
  killed halfway never mirrors a half-written set.
- Retention lives **locally**: nightly runs kept 30 days, Sunday runs 84 days,
  applied only to manifest-bearing run dirs under `nightly/`. The NAS is a pure
  mirror of that tree (`rsync -a --delete --delete-delay --delay-updates`); there
  is no NAS-side logic to break. Snapshot Replication on the NAS folder (daily,
  keep 14) is the undo for a bad mirror.
- Nightly payload ≈ 100 MB; a full retention set ≈ 4 GB.

## Schedule and where it runs

```
30 3 * * *   doppler run --project dhg-monitoring --config dev -- observability/scripts/backup-all.sh       >> ~/.claude/run/backup-all.log
0  4 * * 0   doppler run --project dhg-monitoring --config dev -- observability/scripts/restore-drill.sh --all >> ~/.claude/run/restore-drill.log
```

crontab of `swebber64` on g700data1 (`America/New_York`). Both scripts take
the same `flock` on `/run/user/1000/backup-all.lock`, so a backup and a drill
never overlap; the second instance exits 75 at once.
Guards: the passphrase must be present and `/mnt/4tb` must have 10 GB free or
the run aborts before touching anything. dh40801 gets one 30 s reachability
probe per run; if it fails, its three targets are marked failed and the rest
continue.

Manual use:

```bash
observability/scripts/backup-all.sh --dry-run                    # plan only
doppler run --project dhg-monitoring --config dev -- observability/scripts/backup-all.sh --target registry-db --no-offsite
doppler run --project dhg-monitoring --config dev -- observability/scripts/restore-drill.sh registry-db
```

## Off-host copy: the Synology

Destination `aifactory-backup@10.0.0.250::aifactory-backups/` over the DSM
rsync service in SSH-encrypted mode (port 22, key `~/.ssh/nas-backup_ed25519`).
The `aifactory-backup` user is not an administrator, has `/sbin/nologin`, holds
only the `rsync` application privilege (DSM, SMB, AFP, FTP, SFTP, Drive denied),
R/W on `aifactory-backups` and No Access on every other share **except `homes`**:
a No-Access rule on `homes` makes the user's own home unreadable and sshd can
then no longer read `authorized_keys` (learned the hard way). DSM's SSH-encrypted
rsync mode requires the rsync service to stay enabled, which is why port 873
still lists module names anonymously; data access on 873 is denied
(`account system disabled`). Interactive SSH as that user is refused.

### NAS state and residual risk (read this)

- DS1618+, DSM 7.1.1, one Btrfs volume (21 TB). The storage pool is RAID 6 at
  **5 of 6 disks**: Drive 2 was repaired on 2026-09-10 after the pool had been
  at 4 of 6 since 2026-02-25; **Drive 1 is missing** and needs a replacement
  (SATA HDD ≥ 5.5 TB). Until then the pool tolerates exactly one more failure.
  `NasRaidDegraded` is firing on purpose.
- Immutable snapshots need DSM 7.2 (deferred `8baeab4c`, Stephen's timing;
  the only consideration is Video Station's removal in 7.2.2). Until then the
  NAS copy is deletable by an admin, and by anything holding the backup user's
  key. Snapshot Replication (daily, keep 14) is the interim undo.
- The local copy shares the `/mnt/4tb` NVMe with every Docker volume it
  protects (`DockerRootDir=/mnt/4tb/docker`); it covers logical errors, not
  device loss. The NAS covers device loss.
- The NAS is monitored over SNMPv3 (`dhg-snmp-exporter`, job `nas`,
  `rules.d/nas.yml`). The v1/v2c community `public` that used to answer anyone
  on the LAN is disabled.

## Restore procedures

### One target, one table, one bad deploy

1. Pick the run: `ls /mnt/4tb/backups/nightly/registry-db/` (newest with a
   `manifest.json`; `jq . manifest.json` shows counts and image).
2. Run the drill on it to prove it restores:
   `restore-drill.sh registry-db 20260911T025420Z` — an ephemeral
   `dhg-restore-drill-registry-db` is created, restored, verified and removed.
3. To pull data without touching production, start that container yourself:
   `docker run -d --name scratch -e POSTGRES_PASSWORD=x pgvector/pgvector:pg15`,
   then decrypt and restore: `gpg -d dhg_registry.dump.gpg > /tmp/r.dump` (it
   will prompt for the passphrase) and `docker cp` + `pg_restore` as the drill
   does (`observability/scripts/restore-drill.sh`, function `drill_pg`, is the
   worked example for every kind).
4. Copy what you need across with `psql`/`COPY`, then `docker rm -f scratch`.

### Full disaster (g700data1's NVMe is gone)

1. Rebuild the host and Docker. Pull the mirror back:
   `rsync -a -e 'ssh -p 22 -i ~/.ssh/nas-backup_ed25519' aifactory-backup@10.0.0.250::aifactory-backups/ /mnt/4tb/backups/nightly/`
   (the key is in the config-layer archive too; if both are gone, the NAS admin
   account can read the share directly).
2. Restore the config layer first: `gpg -d config/<run>/config.tar.gpg | tar -C / -x`
   (`.env` files, the override, the rendered secret files). Re-run the
   `render-*.sh` scripts if Doppler is reachable; the archive is the fallback.
3. `docker compose up -d` the databases only, then per database:
   `gpg -d roles.sql.gpg | psql`, `gpg -d <db>.dump.gpg > x && pg_restore -d <db> x`
   (roles before data; drop and recreate the database if the image seeded one).
4. ClickHouse: apply `ddl.sql`, then `INSERT INTO default.<t> FORMAT Native`
   from each gunzipped stream, in the order the drill uses (schema_migrations
   included) **before** starting `dhg-langfuse-worker`. Pin the Langfuse image
   to the version in `manifest.json` (`image`), not the floating `:3` tag.
5. MinIO: untar the archive into the volume, start the server with the same
   `MINIO_ROOT_USER/PASSWORD` the source had (`.minio.sys/config` is encrypted
   with them; they are in Doppler `langfuse/prd` and in `plane.env`).
6. Volumes: untar `grafana.db`, `/exports`, open-webui data into their volumes.
7. Bring the rest up, then run `restore-drill.sh --all` against the restored
   tree and watch the dashboard turn green.

## Drills

`restore-drill.sh` takes the newest manifest-bearing run of a target, starts an
ephemeral `dhg-restore-drill-<target>` container (`--network none`, no ports,
removed by a trap on every exit path, even a failed target inside `--all`) and
checks **exactly** (scratch files live under `/mnt/4tb/backups/.drill`, mode 700,
outside the mirrored tree, and are removed on every exit path):

| kind | restore | equality check |
|---|---|---|
| pg | roles, `CREATE DATABASE`, `pg_restore` from a file copied in | per-table counts == manifest counts (byte-order sorted on both sides) |
| clickhouse | DDL replay, `INSERT … FORMAT Native` | restored count == `clickhouse local` count of the Native file |
| minio | tree untarred into a *created* container (anonymous volume, dropped with the container), then started with the source's root credentials (env-file in scratch, deleted after create) | archive members == manifest; restored tree == archive ∪ the image's pre-restore skeleton, measured before start; server lists buckets |
| volume | — | member count per archive == manifest; `grafana.db` passes `PRAGMA integrity_check` in `dhg-drill-sqlite:3.20` |
| files | — | member count == manifest |

Images the drills need on g700data1: `postgres:17`, `clickhouse/clickhouse-server:25.12`,
`cgr.dev/chainguard/minio`, `dhg-drill-sqlite:3.20` (built locally from
`alpine:3.20` + sqlite). `docker system prune` removes them; `RestoreDrillStale`
is how you find out.

First live `--all` on 2026-09-11: 13/13 pass in 46 s; registry-db alone 9 s
(SLO 30 min).

## Metrics, alerts, dashboard

Textfile `/mnt/4tb/observability/textfile/backups.prom`, rewritten atomically
after **every** target (a run killed halfway still bumps the attempt stamp):

```
backup_last_attempt_timestamp{name}   backup_last_success_timestamp{name}
backup_last_size_bytes{name}          backup_last_duration_seconds{name}
backup_restore_drill_success_timestamp{name}   backup_offsite_last_success_timestamp
```

| alert | condition | severity |
|---|---|---|
| `BackupStale` | no verified run in 28 h, or the textfile is missing (`absent()`) | critical |
| `BackupFailed` | attempt stamp newer than success stamp for 10 min | high |
| `RestoreDrillStale` | no passing drill in 8 d, or missing | high |
| `BackupOffsiteStale` | NAS mirror older than 28 h, or missing | high |
| `NasDown` / `NasRaidCrashed` / `NasDiskUnhealthy` | SNMP unanswered / `raidStatus==12` / SMART critical | critical |
| `NasRaidDegraded` | `raidStatus==11` (pool row) | high, on purpose |
| `NasVolumeHigh` / `NasTempHigh` | volume < 15 % free / drive > 50 °C | warning |

All are human-only (no remediator runbook): the remediator's allowlist cannot
run `gpg` or `rsync`, and a restore is never automated. Per-alert runbooks:
[Backups](runbooks/alerts.md#backups), [NAS](runbooks/alerts.md#nas).
Every backup series carries `name="<target>"` and every rule
`service="backups"`/`"nas"`, which gives one registry incident per target and
keeps Alertmanager grouping separate from node-exporter. `TextfileStale`
excludes `backups.prom` (it is rewritten once a night, not continuously).

## Tests

`observability/tests/*.bats` (bats-core 1.13, 31 tests, CI job **Shell tests**):
the pure functions (retention, textfile, manifest, gpg, target table), the
orchestrator against `docker`/`rsync` shims (dry-run, lock, guards, every
producer, isolation, mirror, mirror failure) and every drill kind against shims.
`observability/tests/bats-tdd-reporter.py` publishes bats results to
tdd-guard so shell reds are visible to the guard.

## Decisions on record

- Storage layer stays bash + gpg + rsync; restic and friends rejected after an
  advisor review (registry decision `ca13da42`): dedup is irrelevant at 100 MB
  a night of already-compressed dumps, and restic would relocate rather than
  remove custom code while adding lock discipline and a restore-time binary.
- The NAS holds full retention only as a mirror; the local tree is the source
  of truth for retention, so the one genuinely fragile piece of the first draft
  (NAS-side pruning) does not exist.
