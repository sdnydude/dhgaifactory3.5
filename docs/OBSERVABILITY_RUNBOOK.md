# DHG AI Factory — Observability Runbook

Operator procedures for the monitoring stack as rebuilt on 2026-09-04. Rationale:
[`observability/AUDIT-2026-09.md`](../observability/AUDIT-2026-09.md) and
[`observability/REBUILD-PLAN-2026-09.md`](../observability/REBUILD-PLAN-2026-09.md).
**Per-alert procedures are not here** — they live at
`http://10.0.0.251:8017/dhg-ai-factory/runbooks/alerts`, which is what every
rule's `runbook_url` points at.

Use `10.0.0.251`, never loopback: several services do not bind it.

## Hosts

**g700data1 (10.0.0.251)** runs Prometheus, Alertmanager, Grafana, Loki, Alloy,
the exporters and the app stack. **dh40801 (10.0.0.179)** runs Langfuse (web,
worker, ClickHouse, MinIO, Postgres) plus its own node-exporter / cAdvisor /
Alloy agent. dh40801 is driven over a remote Docker context —
`docker --context dh40801 ...`, never Ansible (standing decision). Redeploy its
agent with:

```bash
ALLOY_CONFIG="$(cat dh40801/alloy/config.alloy)" \
  docker --context dh40801 compose -f dh40801/docker-compose.observability.yml up -d
```

## Collection

Config lives in `observability/`, bind-mounted live into the containers, so an
edit plus a reload suffices. Service definitions are in
`docker-compose.override.yml`; a `command:` cannot be overridden from
`docker-compose.yml`.

| Container | Port | Role |
|---|---|---|
| dhg-prometheus | 9090 | Metrics, rule evaluation |
| dhg-alertmanager | 9093 | Alert routing |
| dhg-grafana | 3001 → 3000 | Dashboards |
| dhg-loki | 3100 | Log store + ruler |
| dhg-alloy | 12345 internal | Log shipping, g700data1 |
| dhg-cadvisor | 8080 | Container metrics |
| dhg-node-exporter | 9100 host net | Host metrics + textfile collector |
| dhg-postgres-exporter | 9187 | registry-db (the other six via the multi exporter) |
| dhg-blackbox | 9115 loopback | Synthetic probes (separate compose project) |
| dhg-p5-loki-du | — | Writes `loki_store.prom` to the node-exporter textfile dir |

Three more containers are listed in "Ports added 2026-09-04" below.

Scrape jobs are in `observability/prometheus/prometheus.yml`. **Static jobs are
canonical** (AUDIT P1 / decision D-B): `registry-api`, `vs-engine`,
`session-logger` and `memreg` are drop-relabelled out of `docker-sd` so each is
scraped once with a stable instance label. `file_sd` jobs read
`observability/prometheus/targets/*.json` and pick up changes without a restart —
that is how dh40801 is wired. Both hosts' node-exporter and cAdvisor targets carry
a `host` label — `host="g700data1"` on the static jobs, `host="dh40801"` from the
file_sd target files — so `node_*` and `container_*` series can be split by host
without relying on the job name. Blackbox jobs cover surfaces with no `/metrics`.
Logs: Alloy on both hosts ships container logs to the Loki on g700data1;
dh40801's Alloy tags its streams `host="dh40801"`. Keep-all — nothing is deleted
automatically.

Validate, then apply:

```bash
docker run --rm -v "$PWD/observability/prometheus:/p" --entrypoint promtool \
  prom/prometheus:v2.48.0 check rules /p/alerts.yml /p/rules.d/*.yml
docker run --rm -v "$PWD/observability/alertmanager:/a" --entrypoint amtool \
  prom/alertmanager:v0.27.0 check-config /a/alertmanager.yml

docker compose restart prometheus              # no --web.enable-lifecycle on this build
curl -X POST http://10.0.0.251:9093/-/reload   # Alertmanager
docker compose up -d loki                      # Loki config; rules are polled, no restart
docker compose -f observability/blackbox/docker-compose.yml up -d
```

## Alerting

45 rules: 40 in Prometheus (`observability/prometheus/alerts.yml` plus
`rules.d/{dh40801,gpu,postgres,probes,registry}.yml`, loaded by a glob) and 5 in
the Loki ruler (`observability/loki/rules/fake/alerts.yml`).

Three severities only. `critical` and `high` go to the registry webhook **and**
the Telegram alerts chat, and the registry auto-creates an incident. `warning` goes to
Telegram only — the handler (`registry/api.py`, `POST /webhooks/alertmanager`) drops
anything not `critical|high` by design. `medium` is retired.

`observability/alertmanager/alertmanager.yml` is **generated and gitignored** — it
embeds the Telegram bot token, a credential. Edit `alertmanager.yml.tmpl`, run
`observability/scripts/render-alertmanager.sh`, then reload. Without
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in Doppler (`dhg-monitoring`/`dev`) it renders a valid
Telegram-free config and exits 0; alerting still reaches the registry.

Every rule carries `for`, `summary`, `description` and a `runbook_url` of
`http://10.0.0.251:8017/dhg-ai-factory/runbooks/alerts#<alertname lowercased>`.
Renaming an alert means moving its section on that page in the same change.

```bash
curl -s http://10.0.0.251:9090/api/v1/alerts | python3 -m json.tool   # firing
curl -s http://10.0.0.251:9093/api/v2/alerts | python3 -m json.tool   # routed
docker exec dhg-alertmanager amtool --alertmanager.url=http://127.0.0.1:9093 \
  silence add alertname=<Name> --duration=2h --comment="<why>"
```

## Dashboards

`observability/grafana/provisioning/dashboards/json/<folder>/` is the only place
a dashboard lives — one file per board, in git, provisioned through the bind
mount. Folders: `platform`, `services`, `ai`, `alerting`. Dashboard JSON
re-provisions live every ~10s; provider config and datasources are read at
Grafana startup only. The authoring standard is
[`observability/grafana/README.md`](../observability/grafana/README.md);
`dhg-platform-overview.json` is the worked reference. Before shipping a board run
`observability/scripts/verify-dashboard.sh <uid>`: it replays every panel through
`/api/ds/query` and renders a PNG to `observability/verify/<uid>.png`
(gitignored), authenticating with `GRAFANA_SA_TOKEN` from Doppler
`dhg-monitoring/dev`. Legitimately-empty panels are listed by id in
`observability/verify/allow-empty/<uid>.txt` with a reason.

**After every Grafana restart, run `observability/scripts/grant-folder-viewer.sh`.**
A folder created by the dashboard provisioner gets no ACL at all (Grafana applies
default folder permissions only on the UI/API creation path), so a new provider
folder is invisible to every non-Admin identity — including the `dhg-verify`
service account that `verify-dashboard.sh` uses, which then reports a 403 fetch
failure rather than an empty panel. The script is idempotent; folders that already
carry the Viewer/Editor grants are reported `unchanged`. Full explanation in
[`observability/grafana/README.md`](../observability/grafana/README.md).

## Langfuse

All OTLP goes to Langfuse on dh40801 — `http://10.0.0.179:3000/api/public/otel`
(traces at `/v1/traces`), HTTP Basic with a project key pair.
`render-medkb-otel-env.sh` writes the gitignored `services/medkb/.env.otel`
(mode 600) from Doppler; with no keys it warns, exits 0, and medkb starts with
tracing disabled.

`langfuse-canary.sh` is the **silent-drop detector**: Langfuse v3 accepts a trace
(HTTP 207) and hands it to MinIO, so if MinIO is down or the bucket is missing the
POST still succeeds, the trace vanishes, and `/api/public/health` stays 200. Only
a write-then-read round-trip catches that. The canary writes
`langfuse_canary_success_timestamp` to the node-exporter textfile dir;
`LangfuseCanaryStale` alerts on its age, with an `absent()` clause so a deleted
textfile fails closed.

## Retired 2026-09-04

- **Tempo** — never received a span in production. Held out of `docker compose up`
  by a `profiles: ["retired"]` merge stanza; the `dhgaifactory35_tempo_data`
  volume is left in place. Grafana now has two datasources, Prometheus and Loki,
  with no `derivedFields` or exemplar trace links.
- **The pre-Alloy log shipper** — replaced by Grafana Alloy on both hosts; no
  container, config or scrape job for it remains. **LangSmith** — no longer a
  live dependency of the registry.
- **Dead boards** — the core-golden and langgraph-traces dashboards were deleted
  (`dhg-platform-overview` supersedes the first; the second lost its data source
  with Tempo). The old flat dashboard tree under `observability/grafana/` is gone.

## Pending root-only items

Real gaps, each needing root on g700data1 — Stephen's call.

**1. cloudflared metrics.** Both `cloudflared` scrape targets are DOWN by design —
the units bind their metrics servers to loopback, unreachable from a container.
Add to each unit's `ExecStart` (`cloudflared.service`: `--metrics 0.0.0.0:20241`;
`cloudflared-portage.service`: `--metrics 0.0.0.0:20242`) then
`systemctl daemon-reload && systemctl restart cloudflared cloudflared-portage`.

**2. node-exporter thermal_zone.** The g700data1 node-exporter emits ~708K
`thermal_zone` error lines/day, which kept the Loki log alerts permanently firing;
`HighErrorRate` and `ContainerErrorSpike` exclude `dhg-node-exporter` as a
workaround. The fix is `--no-collector.thermal_zone` on its `command:` in
`docker-compose.override.yml` (dh40801's already has it). Remove the exclusion
once it is in place.

**3. LAN exposure (rebuild plan WP9).** The core observability ports answer any
LAN host with no auth. Limit them to loopback and the Mac, leaving Grafana `:3001`
and the frontend `:3000` open. Ports 3200/4317/4318 are moot since Tempo retired.

```bash
for p in 9090 9093 3100 8080; do
  sudo ufw allow from 127.0.0.1    to any port $p proto tcp
  sudo ufw allow from <MAC_LAN_IP> to any port $p proto tcp
  sudo ufw deny to any port $p proto tcp
done
sudo ufw reload && sudo ufw status numbered
```

Verify: from the Mac `curl 10.0.0.251:9090/-/ready` = 200, from any other LAN
host = timeout, frontend `/api/prometheus` still 200.

## Operational scripts (`observability/scripts/`)

| Script | Purpose |
|---|---|
| `render-alertmanager.sh` | Renders the gitignored `alertmanager.yml` from template + Doppler Telegram bot token and chat id |
| `render-medkb-otel-env.sh` | Renders the gitignored `services/medkb/.env.otel` for Langfuse OTLP |
| `verify-dashboard.sh` | Replays every panel of a board and renders a PNG; exit 0 = all panels answer with data |
| `langfuse-canary.sh` | Write-then-read Langfuse round-trip; writes the canary textfile metric |
| `p5-baseline.sh` | Alert-path silence round-trip test + Loki label baseline (`baselines/*.json`) |
| `p5-seeded-secret.sh` | Seeds a known secret shape to prove the Alloy redaction stage works |

## Ports added 2026-09-04

| Port | Container / host | Exposure | Purpose |
|---|---|---|---|
| 8081 | dhg-grafana-renderer | internal | Grafana image renderer for `verify-dashboard.sh` |
| 9835 | dhg-gpu-exporter | internal | `nvidia_gpu_exporter` for the RTX 5080 |
| 9187 | dhg-postgres-exporter-multi | internal | Multi-target postgres_exporter `/probe`, six instances |
| 9100 | dh40801 | LAN, bound 10.0.0.179 | node-exporter on the Langfuse host |
| 8080 | dh40801 | LAN, bound 10.0.0.179 | cAdvisor on the Langfuse host |

Check `memory/reference_port_map.md` before assigning any new port.

## Troubleshooting

- **Target down** — read `lastError` from `/api/v1/targets`, then
  `docker ps --filter name=dhg-`, then try it from inside the network:
  `docker exec dhg-prometheus wget -qO- http://<target>/metrics | head`.
- **No logs in Loki** — `docker logs --tail 100 dhg-alloy`, then
  `curl -s http://10.0.0.251:3100/loki/api/v1/labels`. A running Alloy with a
  broken pipeline looks healthy; confirm by querying a recent window.
- **Dashboard "No data"** — confirm the metric exists before editing the panel:
  `curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=<metric>'`.
- **Grafana will not start** — it refuses to start on a malformed provisioning
  file; the first error line in `docker logs dhg-grafana` names it.
- **Docs site 500s after a build** — Docusaurus replaces the `build/` inode, so
  the `dhg-docs` bind mount goes stale ("internal redirection cycle"):
  `docker compose up -d --force-recreate dhg-docs`.
- **Never** `docker compose down`. Restart only what you changed:
  `docker compose up -d <service>`.
