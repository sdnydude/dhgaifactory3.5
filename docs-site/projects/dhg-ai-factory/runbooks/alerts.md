---
sidebar_position: 1
title: Alert runbooks
---

# Alert runbooks

Every alert rule in the DHG AI Factory observability stack carries a
`runbook_url` annotation pointing at a section on this page. The anchor is the
contract: the URL is
`http://10.0.0.251:8017/dhg-ai-factory/runbooks/alerts#<alertname lowercased>`,
and the heading text below is the alert name verbatim so Docusaurus generates
that anchor. **Renaming an alert means moving its section here in the same
change.**

Source files: `observability/prometheus/alerts.yml`,
`observability/prometheus/rules.d/*.yml` (40 Prometheus rules) and
`observability/loki/rules/fake/alerts.yml` (5 Loki ruler rules) — 45 rules total.

## Severity taxonomy

Only three values are legal. Anything else is a bug in the rule file.

| Severity | Meaning | Where it goes |
|---|---|---|
| `critical` | Page-worthy. A service is down, or data / security is at risk. | Registry webhook **and** Slack. The registry auto-creates an incident. |
| `high` | Degraded or actively failing; needs same-day attention. | Registry webhook **and** Slack. Also creates an incident. |
| `warning` | Informational or a trend. Not an incident. | Slack only. |

`medium` is retired. The registry webhook handler
(`registry/api.py`, `POST /webhooks/alertmanager`) explicitly skips any severity
that is not `critical` or `high`, so a `warning` can never become an incident —
that is intentional, not a dropped alert.

## Where alerts go

```
Prometheus (10.0.0.251:9090) ─┐
                              ├─> Alertmanager (10.0.0.251:9093) ─┬─> Slack #dhg-alerts
Loki ruler (10.0.0.251:3100) ─┘                                   └─> POST http://dhg-registry-api:8000/webhooks/alertmanager
```

Routing lives in `observability/alertmanager/alertmanager.yml`, which is
**generated** — it embeds the Slack incoming-webhook URL, which is a credential,
so the rendered file is gitignored. Edit `alertmanager.yml.tmpl`, then:

```bash
observability/scripts/render-alertmanager.sh
curl -X POST http://10.0.0.251:9093/-/reload
```

If `SLACK_ALERT_WEBHOOK_URL` is absent from Doppler (`dhg-monitoring` / `dev`)
the script still renders a valid config and exits 0 — alerting keeps working
through the registry webhook, with no Slack leg. Until that secret is set,
"goes to Slack" below means "will go to Slack once the webhook is configured".

Three inhibition rules suppress consequential noise: a `critical` suppresses
`high`/`warning` for the same `service`; `RegistryApiDown` suppresses everything
labelled `service=registry-api`; `PrometheusTargetDown` suppresses every other
`*Down` alert on the same `instance`.

## How to silence an alert

```bash
# List what is firing right now
curl -s http://10.0.0.251:9093/api/v2/alerts | python3 -m json.tool

# Silence one alert for 2 hours
docker exec dhg-alertmanager amtool --alertmanager.url=http://localhost:9093 \
  silence add alertname=HostMemoryHigh --duration=2h \
  --comment="ollama model load, tracked in <ticket>"

# List and expire silences
docker exec dhg-alertmanager amtool --alertmanager.url=http://localhost:9093 silence query
docker exec dhg-alertmanager amtool --alertmanager.url=http://localhost:9093 silence expire <silence-id>
```

The Alertmanager UI at `http://10.0.0.251:9093` does the same thing with a form.
Always set a `--comment` — an unexplained silence is how a real outage gets
missed. Silences are stored in the Alertmanager data volume and survive restart.

## Standing checks

Useful at the top of any investigation:

```bash
curl -s http://10.0.0.251:9090/api/v1/alerts | python3 -m json.tool     # firing rules
curl -s http://10.0.0.251:9090/api/v1/targets | python3 -m json.tool    # scrape health
docker ps --filter name=dhg- --format '{{.Names}}\t{{.Status}}'
```

Grafana is at `http://10.0.0.251:3001`; every dashboard link below is
`/d/<uid>`.

---

## Infrastructure

Rules from `observability/prometheus/alerts.yml`, group `dhg-infrastructure`.
These cover the g700data1 host and its containers.

### ContainerCrashLoop

```promql
changes(container_start_time_seconds{name=~"dhg-.*"}[15m]) > 3
```

**Means:** a `dhg-*` container restarted more than three times in fifteen
minutes. `container_start_time_seconds` changes value on every start, so the
count of changes is the count of restarts. Severity `high`, not `critical`: a
restart loop is degradation, and the outage case is already covered by
`RegistryApiDown` / `PrometheusTargetDown`.

**First three checks:**

```bash
docker logs --tail 200 <container>
docker inspect <container> --format '{{.State.ExitCode}} {{.State.OOMKilled}} {{.RestartCount}}'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=changes(container_start_time_seconds{name=~"dhg-.*"}[15m]) > 3'
```

**Likely causes:** a bad config or missing env var after an edit (the container
starts, fails validation, exits); OOM kill against a `mem_limit`; a dependency
that is not up yet and no `depends_on` healthcheck; an image pulled with a
changed entrypoint.

**Resolve:** read the exit reason *before* restarting anything — a restart
destroys the evidence. `OOMKilled: true` means raise `mem_limit` or fix the
consumer (see `ContainerHighMemory`). A non-zero exit with a config error means
fix the config and `docker compose up -d <service>`. Never `docker compose down`.

**Dashboard:** [Docker Overview](http://10.0.0.251:3001/d/docker-overview)

### HostMemoryHigh

```promql
(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) > 0.9
```

**Means:** g700data1 has under 10% of its 64 GB available. The OOM killer is
close, and it does not choose politely — it can take registry-api or Postgres.

**First three checks:**

```bash
ssh 10.0.0.251 'free -h && ps -eo pid,rss,comm --sort=-rss | head -15'
docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' | sort -k2 -h -r | head -15
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=topk(10, container_memory_usage_bytes{name=~"dhg-.*"})'
```

**Likely causes:** Ollama model residency (a loaded model holds host RAM as well
as VRAM, and multiple models stay resident); cAdvisor working-set growth; an
unbounded container leaking (see `ContainerMemoryLeak`).

**Resolve:** identify the top consumer first. For Ollama, unload idle models
(`curl http://10.0.0.251:11434/api/generate -d '{"model":"<m>","keep_alive":0}'`)
rather than restarting the container mid-inference. `vm.swappiness` is 10 on
this host, so swap will not absorb the spike for you — treat `HostSwapHigh` as
the same incident.

**Dashboard:** [DHG Platform Overview](http://10.0.0.251:3001/d/dhg-platform-overview)

### HostSwapHigh

```promql
(1 - node_memory_SwapFree_bytes / node_memory_SwapTotal_bytes) > 0.8 and node_memory_SwapTotal_bytes > 0
```

**Means:** swap is over 80% used. With `vm.swappiness=10` the kernel only swaps
under genuine pressure, so this is not lazy paging — it is a precursor to
`HostMemoryHigh`.

**First three checks:**

```bash
ssh 10.0.0.251 'free -h && swapon --show'
ssh 10.0.0.251 'for p in /proc/[0-9]*; do awk -v p=$p "/VmSwap/{print \$2, p}" \$p/status 2>/dev/null; done | sort -rn | head -10'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=node_memory_SwapFree_bytes'
```

**Likely causes:** the same consumers as `HostMemoryHigh`, an hour earlier. A
long-idle container that was swapped out and never touched again is benign; a
process actively faulting is not.

**Resolve:** free real memory (see `HostMemoryHigh`). Do not add swap as the
fix — more swap on this host buys latency, not headroom. If swap stays high
after memory recovers, the pages are cold and can be left alone.

**Dashboard:** [DHG Platform Overview](http://10.0.0.251:3001/d/dhg-platform-overview)

### RootDiskHigh

```promql
(1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) > 0.85
```

**Means:** the root filesystem is over 85% full. Docker's data root is
`/mnt/4tb/docker`, so root filling is usually *not* images — it is logs,
journald, or an apt/build cache.

**First three checks:**

```bash
ssh 10.0.0.251 'df -h / && du -xh --max-depth=2 / 2>/dev/null | sort -rh | head -20'
ssh 10.0.0.251 'journalctl --disk-usage'
docker system df
```

**Likely causes:** journald growth; an apt cache after a kernel/nvidia install;
a stray large file in `/home` or `/var/tmp`; a container writing to a
non-volume path.

**Resolve:** `journalctl --vacuum-size=500M` first (safe and usually enough),
then `apt clean`. Prune **dangling** images only —
`docker image prune` without `-a`; `-a` removes images that are not currently
running and will cost a long re-pull. Never prune volumes.

**Dashboard:** [DHG Platform Overview](http://10.0.0.251:3001/d/dhg-platform-overview)

### DataDiskHigh

```promql
(1 - node_filesystem_avail_bytes{mountpoint="/mnt/4tb"} / node_filesystem_size_bytes{mountpoint="/mnt/4tb"}) > 0.8
```

**Means:** the 4 TB data volume is over 80% full. It holds the Docker data root,
the Loki store, backups and model caches. `warning` — this is a trend signal, and
nothing is deleted automatically.

**First three checks:**

```bash
ssh 10.0.0.251 'df -h /mnt/4tb && du -xh --max-depth=2 /mnt/4tb | sort -rh | head -20'
ssh 10.0.0.251 'du -sh /mnt/4tb/backups /mnt/4tb/docker /mnt/4tb/observability 2>/dev/null'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=loki_store_bytes'
```

**Likely causes:** Ollama model files; old backups; Docker image layers; Loki
chunk growth (cross-check `LokiStoreGrowth` — at ~11 MB/day Loki is not the
driver at this size).

**Resolve:** review `/mnt/4tb/backups` first, then unused Ollama models
(`ollama list` / `ollama rm`). This is an operator decision, not an automated
cleanup.

**Dashboard:** [DHG Platform Overview](http://10.0.0.251:3001/d/dhg-platform-overview)

### PrometheusTargetDown

```promql
up == 0
```

**Means:** any scrape target has been unreachable for 2 minutes. This is the
generic liveness net under every job; it inhibits the per-service `*Down` alerts
for the same `instance`, so when it fires alongside them, this is the one to
work.

**First three checks:**

```bash
curl -s http://10.0.0.251:9090/api/v1/targets | python3 -c "import json,sys; [print(t['labels']['job'], t['labels']['instance'], t['health'], t['lastError']) for t in json.load(sys.stdin)['data']['activeTargets'] if t['health']!='up']"
docker ps --filter name=dhg- --format '{{.Names}}\t{{.Status}}' | grep -v Up
docker exec dhg-prometheus wget -qO- http://<target-host>:<port>/metrics | head -5
```

**Likely causes:** the container is down or restarting; the exporter is up but
its `/metrics` handler is failing; a network mismatch (a container on a compose
project not joined to `dhgaifactory35_dhg-network`); a published host port
that was lost on recreate.

**Known and expected:** both `cloudflared` targets are DOWN by design. The two
`cloudflared` systemd units bind their metrics servers to `127.0.0.1`, which a
container cannot reach. The fix is root-only — see "Pending root-only items" in
`docs/OBSERVABILITY_RUNBOOK.md`. Silence these two instances rather than
chasing them.

**Resolve:** fix the target, not the rule. If a target is permanently gone,
delete its scrape job from `observability/prometheus/prometheus.yml` and
`docker compose restart prometheus`.

**Dashboard:** [DHG Platform Overview](http://10.0.0.251:3001/d/dhg-platform-overview)

### OllamaDown

```promql
probe_success{job="blackbox-http", service="ollama"} == 0
```

**Means:** the blackbox probe of Ollama failed. Ollama is probed on two paths —
`container` (`http://dhg-ollama:11434/api/tags`) and `lan`
(`http://10.0.0.251:11434/api/tags`). The `path` label says which one failed.
This costs money: Portage's Porter falls back to paid cloud inference silently.

**First three checks:**

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://10.0.0.251:11434/api/tags
docker exec dhg-blackbox wget -qO- 'http://localhost:9115/probe?target=http://dhg-ollama:11434/api/tags&module=http_2xx' | grep probe_success
docker logs --tail 100 dhg-ollama
```

**Likely causes:** **LAN path down while container path is up = the host port
mapping was lost** (this happened on 2026-08-15, bug-fix `ef492f28`). Both paths
down = the container is down or the model load wedged it. A host `ollama.service`
stealing port 11434 is the other historical cause.

**Resolve:** for the lost port mapping,
`docker compose up -d --force-recreate --no-deps ollama`. Verify both probe
paths return `probe_success 1` before closing. Every minute down is billable
cloud inference.

**Dashboard:** [DHG Platform Overview](http://10.0.0.251:3001/d/dhg-platform-overview)

### PortageApiDown

```promql
up{job="portage-api"} == 0 or probe_success{job="blackbox-https", service="portage-api"} == 0
```

**Means:** either the direct scrape of `portage-api:8016` or the HTTPS probe of
its `/health` endpoint has been failing for 2 minutes.

**First three checks:**

```bash
curl -sk -o /dev/null -w '%{http_code}\n' https://10.0.0.251:8016/health
docker ps --filter name=portage --format '{{.Names}}\t{{.Status}}'
docker logs --tail 200 dhg-portage-api 2>/dev/null || docker logs --tail 200 portage-api
```

**Likely causes:** the Portage container is down or restarting; its self-signed
TLS cert expired or was regenerated (the scrape uses `insecure_skip_verify`, so
this shows as a connection failure, not a verify failure); the Portage database
is unreachable and the health check fails closed.

**Resolve:** if only the *public* HTTPS probe fails and the container is
healthy, suspect the Cloudflare tunnel, not Portage — that is a separate signal.
Check `PostgresDown{service="portage-db"}` before restarting the API.

**Dashboard:** [DHG Platform Overview](http://10.0.0.251:3001/d/dhg-platform-overview)

### RegistryApiDown

```promql
up{job="registry-api"} == 0
```

**Means:** the registry API is down. `critical`, and it is the first thing to
fix in any multi-alert incident: the registry is the incident sink for this
whole pipeline. While it is down, no alert creates an incident and every memreg
capture dead-letters. This alert inhibits everything labelled
`service=registry-api`.

**First three checks:**

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://10.0.0.251:8011/healthz
docker logs --tail 200 dhg-registry-api
docker inspect dhg-registry-api --format '{{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}}'
```

**Likely causes:** a failed migration or import error on startup; `dhg-registry-db`
unreachable (check `PostgresDown{service="registry-db"}` first — the API fails
closed on a dead database); connection-pool exhaustion wedging the event loop.

**Resolve:** restore the database before the API. Then
`docker compose up -d registry-api`. Confirm `/healthz` is 200 and that the
memreg DLQ drains (`MemregDLQBacklog` should clear on its own within 15 minutes;
if it does not, that is a second incident).

**Dashboard:** [DHG Registry API](http://10.0.0.251:3001/d/dhg-registry-api)

### ContainerMemoryLeak

```promql
container_memory_usage_bytes{name=~"dhg-.*"} > 17179869184 and container_spec_memory_limit_bytes{name=~"dhg-.*"} == 0
```

**Means:** an unbounded container (no `mem_limit`) is holding more than 16 GB on
a 64 GB host. It either leaks, or it needs a limit so its failure is contained.

**First three checks:**

```bash
docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}' | sort -k2 -h -r | head -10
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=topk(5, container_memory_usage_bytes{name=~"dhg-.*"} and container_spec_memory_limit_bytes == 0)'
curl -sG http://10.0.0.251:9090/api/v1/query_range --data-urlencode 'query=container_memory_usage_bytes{name="<container>"}' --data-urlencode 'start='$(date -d '24 hours ago' +%s) --data-urlencode 'end='$(date +%s) --data-urlencode 'step=300' | head -c 400
```

**Likely causes:** Ollama holding multiple resident models — usually legitimate,
and the reason this alert is `high` and not `critical`. Anything else at 16 GB
is a leak: an unbounded cache, an ever-growing in-process queue, or a model
loaded per request instead of once.

**Resolve:** a 24h range query separates "loaded once and flat" (fine) from
"monotonically rising" (leak). For a genuine leak, add a `mem_limit` stanza in
`docker-compose.yml` so it is OOM-killed in isolation instead of taking the host
down, then fix the consumer.

**Dashboard:** [Docker Overview](http://10.0.0.251:3001/d/docker-overview)

### ContainerHighCPU

```promql
rate(container_cpu_usage_seconds_total{name=~"dhg-.*"}[5m]) > 0.9
```

**Means:** a container has saturated a full core for 10 minutes. `warning` and
informational — inference, indexing and embedding workloads do this legitimately.

**First three checks:**

```bash
docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}' | sort -k2 -h -r | head -10
docker logs --tail 100 <container>
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=topk(5, rate(container_cpu_usage_seconds_total{name=~"dhg-.*"}[5m]))'
```

**Likely causes:** expected for `dhg-ollama`, `dhg-medkb-api` during ingest, and
transcription workers. Unexpected for anything that should be idle — a hot retry
loop, a runaway scheduler, or a poll with no backoff.

**Resolve:** only act if it is a service that should be idle. Find the loop in
the logs. Do not add CPU limits reflexively; they turn a busy service into a
slow one.

**Dashboard:** [Docker Overview](http://10.0.0.251:3001/d/docker-overview)

### ContainerHighMemory

```promql
(container_memory_usage_bytes{name=~"dhg-.*"} / container_spec_memory_limit_bytes{name=~"dhg-.*"}) > 0.9 and container_spec_memory_limit_bytes{name=~"dhg-.*"} > 0
```

**Means:** a container with a configured `mem_limit` is within 10% of it and
will be OOM-killed if it crosses. The counterpart to `ContainerMemoryLeak`,
which covers containers with no limit at all.

**First three checks:**

```bash
docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}' | sort -k3 -h -r | head -10
docker inspect <container> --format '{{.HostConfig.Memory}}'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=container_memory_usage_bytes{name="<container>"} / container_spec_memory_limit_bytes{name="<container>"}'
```

**Likely causes:** the limit was set for a smaller workload; a cache with no
eviction; a legitimate growth in working set after a data volume increase.

**Resolve:** decide whether the limit is wrong or the consumer is. Raising the
limit in `docker-compose.yml` is correct when the workload genuinely grew;
otherwise fix the consumer. Either way, expect a restart of that service.

**Dashboard:** [Docker Overview](http://10.0.0.251:3001/d/docker-overview)

---

## Alerting pipeline

Rules from `observability/prometheus/alerts.yml`, group `dhg-alerting-pipeline`.
Without these, every other rule on this page fails open: a dead Alertmanager or
a broken evaluation produces silence that is indistinguishable from health.
**When one of these fires, assume every other alert is unreliable until it clears.**

### AlertmanagerDown

```promql
up{job="alertmanager"} == 0
```

**Means:** Alertmanager is unreachable. Prometheus still evaluates rules, but
nothing reaches Slack or the registry webhook. Every alert in the estate is
silently ineffective. `critical`.

**First three checks:**

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://10.0.0.251:9093/-/healthy
docker logs --tail 100 dhg-alertmanager
docker inspect dhg-alertmanager --format '{{.State.Status}} {{.State.ExitCode}}'
```

**Likely causes:** an invalid rendered `alertmanager.yml` after a template edit
(Alertmanager refuses to start on a bad config); the container stopped; a port
conflict on 9093.

**Resolve:** validate before restarting —

```bash
docker run --rm -v "$PWD/observability/alertmanager:/a" --entrypoint amtool \
  prom/alertmanager:v0.27.0 check-config /a/alertmanager.yml
docker compose up -d alertmanager
```

If the rendered file is missing or corrupt, re-run
`observability/scripts/render-alertmanager.sh`.

**Dashboard:** [DHG Alerting Pipeline](http://10.0.0.251:3001/d/dhg-alerting-pipeline)

### PrometheusRuleEvalFailures

```promql
increase(prometheus_rule_evaluation_failures_total[15m]) > 0
```

**Means:** one or more rules in the named `rule_group` raised an evaluation
error, so the alerts in that group are not being computed at all. The group is
dark, not healthy.

**First three checks:**

```bash
curl -s http://10.0.0.251:9090/api/v1/rules | python3 -c "import json,sys; [print(g['name'], r['name'], r.get('health'), r.get('lastError')) for g in json.load(sys.stdin)['data']['groups'] for r in g['rules'] if r.get('health')!='ok']"
docker logs --tail 100 dhg-prometheus | grep -i 'rule\|eval'
docker run --rm -v "$PWD/observability/prometheus:/p" --entrypoint promtool prom/prometheus:v2.48.0 check rules /p/alerts.yml /p/rules.d/*.yml
```

**Likely causes:** a PromQL error introduced in a recent rule edit (a bare `+`
between two counters with disjoint labels returns empty, but a type error
raises); a query that exceeds `query.max-samples`; a `histogram_quantile` over a
non-histogram metric.

**Resolve:** fix the expression in the rule file, `promtool check rules`, then
`docker compose restart prometheus`. Confirm every rule reports `health: ok`
before closing.

**Dashboard:** [DHG Alerting Pipeline](http://10.0.0.251:3001/d/dhg-alerting-pipeline)

### PrometheusNotificationsDropped

```promql
increase(prometheus_notifications_dropped_total[15m]) > 0
```

**Means:** Prometheus could not hand alerts to Alertmanager and gave up on them.
Those alerts were never delivered anywhere and will not be retried.

**First three checks:**

```bash
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=prometheus_notifications_queue_length / prometheus_notifications_queue_capacity'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=up{job="alertmanager"}'
docker logs --tail 100 dhg-prometheus | grep -i notif
```

**Likely causes:** Alertmanager unreachable (expect `AlertmanagerDown`
alongside); the notification queue full because Alertmanager is slow; a DNS
failure resolving `dhg-alertmanager` on the compose network.

**Resolve:** restore Alertmanager. Drops are unrecoverable — after the pipeline
is healthy, re-check `/api/v1/alerts` on Prometheus for anything still firing
that never reached Slack, and handle it by hand.

**Dashboard:** [DHG Alerting Pipeline](http://10.0.0.251:3001/d/dhg-alerting-pipeline)

### AlertmanagerNotificationsFailing

```promql
increase(alertmanager_notifications_failed_total[15m]) > 0
```

**Means:** Alertmanager accepted alerts but the named `integration` could not
deliver them. Alerts are being lost at the last hop.

**First three checks:**

```bash
docker logs --tail 100 dhg-alertmanager | grep -i 'notify\|error'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=sum by (integration) (increase(alertmanager_notifications_failed_total[1h]))'
curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: application/json' -d '{"alerts":[]}' http://10.0.0.251:8011/webhooks/alertmanager
```

**Likely causes:** `integration="slack"` — a revoked, rotated or malformed
incoming-webhook URL. `integration="webhook"` — the registry returning non-2xx,
usually because `dhg-registry-api` is down (expect `RegistryApiDown`) or the
webhook secret does not match.

**Resolve:** for Slack, re-mint the webhook, `doppler secrets set
SLACK_ALERT_WEBHOOK_URL --project dhg-monitoring --config dev`, re-run
`observability/scripts/render-alertmanager.sh`, then reload. Never paste the URL
into a file in the repo. For the registry leg, fix the registry.

**Dashboard:** [DHG Alerting Pipeline](http://10.0.0.251:3001/d/dhg-alerting-pipeline)

### LokiRulerErrors

```promql
increase(loki_prometheus_notifications_errors_total[15m]) > 0
```

**Means:** the Loki ruler evaluated the log-based alerts but could not push them
to Alertmanager. Every rule in `observability/loki/rules/**` is currently
undelivered — including `SecretLeakDetected` and `PostgresFatalError`.

**First three checks:**

```bash
docker logs --tail 100 dhg-loki | grep -i 'ruler\|alertmanager'
curl -s http://10.0.0.251:3100/loki/api/v1/rules | head -40
docker exec dhg-loki wget -qO- http://dhg-alertmanager:9093/-/healthy 2>&1 | head -3
```

**Likely causes:** a wrong or stale `alertmanager_url` in
`observability/loki/loki-config.yml`; Alertmanager down; the ruler unable to
resolve the Alertmanager container name.

**Resolve:** fix the URL in the Loki config and `docker compose up -d loki`.
Note the Loki ruler polls its rule directory, so *rule* edits do not need a
restart — only config changes do.

**Dashboard:** [DHG Alerting Pipeline](http://10.0.0.251:3001/d/dhg-alerting-pipeline)

### TextfileStale

```promql
time() - node_textfile_mtime_seconds > 900
```

**Means:** a node-exporter textfile under
`/mnt/4tb/observability/textfile` has not been rewritten in 15 minutes, so its
writer has stopped. Any alert reading a metric from that file is evaluating a
frozen value and will not fire on new conditions.

**First three checks:**

```bash
ssh 10.0.0.251 'ls -la /mnt/4tb/observability/textfile/'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=time() - node_textfile_mtime_seconds'
systemctl list-timers --all | grep -i 'loki-du\|canary'
```

**Likely causes:** the `dhg-p5-loki-du` container (writer of `loki_store.prom`,
feeding `LokiStoreGrowth`) stopped or is erroring; a cron/timer for a future
backup marker failing; the textfile directory permissions changed.

**Resolve:** restart the writer (`docker compose up -d p5-loki-du`) and confirm
the mtime advances within one write interval. Note the companion failure mode:
if a textfile is *deleted*, `node_textfile_mtime_seconds` disappears with it and
this alert cannot fire — that is why `LangfuseCanaryStale` carries its own
`absent()` clause.

**Dashboard:** [DHG Alerting Pipeline](http://10.0.0.251:3001/d/dhg-alerting-pipeline)

---

## Services

Symptom-level alerts for Portage (`dhg-portage-symptoms`), the memreg capture
daemon (`dhg-memreg`), and the registry API RED signals
(`rules.d/registry.yml`).

### PortageHighErrorRate

```promql
sum(rate(portage_http_requests_total{status_code=~"5..", route!~"/metrics|/health"}[10m]))
  /
sum(rate(portage_http_requests_total{route!~"/metrics|/health"}[10m]))
  > 0.05
```

**Means:** more than 1 in 20 non-health Portage requests returned a server error
over the last 10 minutes. This is a user-visible symptom, not a proxy for one.
Deliberately aggregate: `route` carries raw ids, so a `by (route)` alert would be
unbounded cardinality. `/metrics` and `/health` are excluded because they are a
third of all traffic, always 200, and would dilute the ratio.

**First three checks:**

```bash
docker logs --tail 200 dhg-portage-api 2>/dev/null || docker logs --tail 200 portage-api
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=sum by (status_code) (rate(portage_http_requests_total[10m]))'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=pg_up{service="portage-db"}'
```

**Likely causes:** an upstream marketplace adapter (eBay especially) returning
errors or rate-limiting; the Portage database down or connection-starved; an AI
tool loop hitting its cap; Ollama down and the fallback path also failing.

**Resolve:** classify by status code first — a wall of 502/504 points upstream,
a wall of 500 points at Portage itself. Check `OllamaDown` and
`PostgresDown{service="portage-db"}` before touching Portage.

**Dashboard:** [DHG Platform Overview](http://10.0.0.251:3001/d/dhg-platform-overview)

### PortageHighLatency

```promql
histogram_quantile(0.95, sum by (le) (rate(portage_http_request_duration_seconds_bucket{route!~"/metrics|/health"}[10m]))) > 2
```

**Means:** p95 request latency has been over 2 seconds for 10 minutes. `warning`
— slow, not broken. Note the `sum by (le)`: without it the quantile silently
splits per instance the day a second replica appears.

**First three checks:**

```bash
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=histogram_quantile(0.95, sum by (le) (rate(portage_http_request_duration_seconds_bucket[10m])))'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=probe_success{service="ollama"}'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=sum by (service) (pg_stat_database_numbackends) / max by (service) (pg_settings_max_connections)'
```

**Likely causes:** an eBay or other marketplace adapter timing out and being
retried; Ollama down, so inference fell back to a slower cloud model; Postgres
connection-pool contention; a large image upload path.

**Resolve:** correlate with `OllamaDown` first — the fallback is the most common
cause and is also costing money. Then check adapter timeouts in the Portage
logs.

**Dashboard:** [DHG Platform Overview](http://10.0.0.251:3001/d/dhg-platform-overview)

### MemregDLQBacklog

```promql
max_over_time(memreg_dlq_depth[15m]) > 0
```

**Means:** the memreg capture dead-letter queue has been non-empty for 15
minutes and the daemon retry loop is not draining it. Registry captures are
failing and **session knowledge is being lost** — the whole point of the capture
rules. `max_over_time` is used so a queue that briefly drains between scrapes
still counts.

**First three checks:**

```bash
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=memreg_dlq_depth'
docker logs --tail 200 dhg-memreg-agent
curl -s -o /dev/null -w '%{http_code}\n' http://10.0.0.251:8011/healthz
```

**Likely causes:** `dhg-registry-api` down or 5xx-ing (expect `RegistryApiDown`
or `RegistryHighErrorRate`); a schema mismatch causing 422s on a capture
endpoint, which retry will never fix; the daemon's retry loop wedged.

**Resolve:** restore the registry first; the DLQ should then drain on its own
within one retry cycle. If depth stays flat while the registry is healthy, the
entries are being rejected, not dropped — read the daemon log for the status
code and fix the payload schema.

**Dashboard:** [Memreg Daemon](http://10.0.0.251:3001/d/memreg-daemon)

### MemregDLQMetricMissing

```promql
absent(memreg_dlq_depth)
```

**Means:** the DLQ depth gauge is not being exported at all. This is the
fail-closed companion to `MemregDLQBacklog`: a gauge that stops being exported
looks exactly like a healthy DLQ, so without this alert a growing queue would go
unnoticed forever.

**First three checks:**

```bash
docker exec dhg-prometheus wget -qO- http://dhg-memreg-agent:8020/metrics | grep memreg_dlq_depth
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=up{job="memreg"}'
docker logs --tail 100 dhg-memreg-agent
```

**Likely causes:** `dhg-memreg-agent` down (then `PrometheusTargetDown` fires
too); the gauge is lazily created and has never been touched since the last
restart — a known property of labelled gauges in the daemon; the metrics port
changed.

**Resolve:** if the container is up and the metric is genuinely absent from
`/metrics`, the daemon needs to initialise the gauge at startup rather than on
first use. Do not "fix" this by deleting the alert — absence is the failure
mode it exists to catch.

**Dashboard:** [Memreg Daemon](http://10.0.0.251:3001/d/memreg-daemon)

### RegistryHighErrorRate

```promql
sum(rate(http_requests_total{job="registry-api",status=~"5.."}[10m]))
/
sum(rate(http_requests_total{job="registry-api"}[10m]))
> 0.05
```

**Means:** over 5% of registry-api requests have returned 5xx for 10 minutes.
Capture POSTs, KB search and the frontend all depend on this API. A ratio rather
than an absolute rate, because the registry serves bursty capture traffic and a
fixed 5xx/s threshold would fire on any quiet period. `/metrics` and `/healthz`
are excluded from instrumentation, so scrape traffic never dilutes it.

**First three checks:**

```bash
docker logs --tail 200 dhg-registry-api
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=sum by (handler, status) (rate(http_requests_total{job="registry-api", status=~"5.."}[10m]))'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=pg_up{service="registry-db"}'
```

**Likely causes:** `dhg-registry-db` down or connection-starved; an unhandled
null in a service layer (the classic serializer-drift 500); a pgvector KB query
timing out; an Anthropic call failing on a request path.

**Resolve:** the per-`handler` breakdown localises it immediately — one handler
means a code bug, all handlers means the database. Check `PostgresDown` and
`PostgresConnectionsHigh` for `service=registry-db` before reading code.

**Dashboard:** [DHG Registry API](http://10.0.0.251:3001/d/dhg-registry-api)

### RegistryHighLatency

```promql
histogram_quantile(
  0.95,
  sum by (le) (rate(http_request_duration_seconds_bucket{job="registry-api"}[10m]))
)
> 2
```

**Means:** registry-api p95 latency has been over 2 seconds for 10 minutes.
`warning`. KB search is the slowest legitimate route and sits well under 2s, so
a sustained p95 above that is a real regression.

**First three checks:**

```bash
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=histogram_quantile(0.95, sum by (handler, le) (rate(http_request_duration_seconds_bucket{job="registry-api"}[10m])))'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=sum by (service) (pg_stat_database_numbackends) / max by (service) (pg_settings_max_connections)'
docker logs --tail 200 dhg-registry-api | grep -i 'slow\|timeout'
```

**Likely causes:** a slow pgvector KB query (a missing or unused index after an
ingest); connection-pool saturation on `dhg-registry-db`; an Anthropic call
blocking a synchronous request path.

**Resolve:** the per-handler quantile names the route. For KB search, check the
pgvector index; for capture endpoints, check pool size against
`pg_stat_database_numbackends`.

**Dashboard:** [DHG Registry API](http://10.0.0.251:3001/d/dhg-registry-api)

---

## Postgres

Rules from `observability/prometheus/rules.d/postgres.yml`. Two scrape jobs feed
them and both export `pg_up` and `pg_settings_*`: `job="postgres"` (registry-db,
via `dhg-postgres-exporter`) and `job="postgres-multi"` (the other six, via
`/probe` on `dhg-postgres-exporter-multi`). Every target carries a `service`
label, so both rules generalize over `service` instead of being written out per
instance.

### PostgresDown

```promql
pg_up == 0
```

**Means:** the exporter could not connect to the named Postgres instance for 2
minutes. Anything backed by that database is down or about to be. `critical`.

**First three checks:**

```bash
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=pg_up' | python3 -m json.tool
docker ps --filter name=db --format '{{.Names}}\t{{.Status}}'
docker logs --tail 100 dhg-postgres-exporter-multi   # or dhg-postgres-exporter for registry-db
```

**Likely causes:** the database container is down or restarting; it hit
`max_connections` and refused the exporter's connection (cross-check
`PostgresConnectionsHigh` for the same `service`); credentials rotated without
re-rendering `observability/postgres-exporter/postgres_exporter.yml`; disk full
so Postgres refuses writes.

**Resolve:** distinguish "database down" from "exporter cannot connect" —
`docker exec <db-container> pg_isready` answers that in one command. If it is a
credential drift, re-render the gitignored exporter config from Doppler and
`docker compose up -d postgres-exporter-multi`.

**Dashboard:** [DHG PostgreSQL Fleet](http://10.0.0.251:3001/d/dhg-platform-postgres)

### PostgresConnectionsHigh

```promql
sum by (service) (pg_stat_database_numbackends)
/
max by (service) (pg_settings_max_connections)
> 0.8
```

**Means:** the named instance has held over 80% of its connection slots for 10
minutes. New connections will start being refused. `numbackends` is
per-database and `max_connections` is per-server (and carries an extra `server`
label), so both sides are aggregated down to `service` — this is why the rule
covers all seven instances including `registry-db` with one expression.

**First three checks:**

```bash
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=sum by (service) (pg_stat_database_numbackends) / max by (service) (pg_settings_max_connections)'
docker exec dhg-registry-db psql -U postgres -c "SELECT state, count(*), max(now()-state_change) AS oldest FROM pg_stat_activity GROUP BY state ORDER BY 2 DESC;"
docker exec dhg-registry-db psql -U postgres -c "SELECT application_name, count(*) FROM pg_stat_activity GROUP BY 1 ORDER BY 2 DESC LIMIT 10;"
```

**Likely causes:** a client leaking pool connections — a SQLAlchemy session not
returned, which shows up as a growing pile of `idle in transaction`; a service
restarted repeatedly, each instance opening a fresh pool; too many services
pointed at one database.

**Resolve:** find the leaking client before raising `max_connections`. A large
`idle in transaction` count with a long `oldest` age is the signature of an
un-closed session and is a code bug, not a capacity problem. Raising the limit
converts a fast failure into a slow, memory-hungry one.

**Dashboard:** [DHG PostgreSQL Fleet](http://10.0.0.251:3001/d/dhg-platform-postgres)

---

## GPU

Rules from `observability/prometheus/rules.d/gpu.yml`, fed by
`nvidia_gpu_exporter` (job `gpu`, container `dhg-gpu-exporter`, internal port
9835). Metrics are keyed by `uuid`; the RTX 5080 is the only GPU on g700data1.

### GpuVramHigh

```promql
nvidia_smi_memory_used_bytes / nvidia_smi_memory_total_bytes > 0.92
```

**Means:** over 92% of the card's 16 GB VRAM has been in use for 10 minutes.
Further model loads will fail or spill to host RAM, which is 10–50x slower.
`warning` — on a single-GPU inference host, high VRAM is often the working state.

**First three checks:**

```bash
ssh 10.0.0.251 'nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv'
curl -s http://10.0.0.251:11434/api/ps
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=nvidia_smi_memory_used_bytes / nvidia_smi_memory_total_bytes'
```

**Likely causes:** multiple Ollama models resident at once; a large model loaded
for a one-off request and still held by `keep_alive`; a leaked CUDA context from
a crashed process.

**Resolve:** `/api/ps` lists resident Ollama models with their expiry. Unload the
ones you do not need with a `keep_alive: 0` request rather than restarting
Ollama mid-inference. A process holding VRAM that is not in `nvidia-smi`'s
compute-apps list is a leaked context and needs the owning container restarted.

**Dashboard:** [DHG GPU](http://10.0.0.251:3001/d/dhg-platform-gpu)

### GpuTempHigh

```promql
nvidia_smi_temperature_gpu > 85
```

**Means:** the card has been at or above 85 °C for 5 minutes. It will
thermal-throttle (so inference gets slower, not just hotter) and sustained heat
shortens the card's life. `high`.

**First three checks:**

```bash
ssh 10.0.0.251 'nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,power.draw,clocks_throttle_reasons.active --format=csv'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=nvidia_smi_temperature_gpu'
ssh 10.0.0.251 'sensors 2>/dev/null | head -20'
```

**Likely causes:** sustained inference load (check GPU utilisation alongside —
85 °C at 100% util is the card working, 85 °C at low util is a cooling problem);
chassis airflow blocked or dust; ambient room temperature; a failing fan.

**Resolve:** if utilisation is low and temperature is high, it is physical —
check airflow and fans, and treat it as urgent. If utilisation is high, decide
whether the workload is worth the thermal budget; the throttle reasons field
tells you whether the card is already derating.

**Dashboard:** [DHG GPU](http://10.0.0.251:3001/d/dhg-platform-gpu)

---

## Probes

Rules from `observability/prometheus/rules.d/probes.yml`. Blackbox uptime probes
for the surfaces that expose no `/metrics` of their own. Targets are defined in
the `blackbox-http` / `blackbox-public` jobs in `prometheus.yml` and each carries
a `service` label.

### FrontendDown

```promql
probe_success{service="frontend"} == 0
```

**Means:** `http://dhg-frontend:3000/` has failed its probe for 3 minutes. This
is the chat/inbox UI — the primary human surface. The root path answers 307 to
`/projects`; the `http_2xx` module follows redirects, so the probe sees the final
200.

**First three checks:**

```bash
curl -s -o /dev/null -w '%{http_code} -> %{url_effective}\n' -L http://10.0.0.251:3000/
docker logs --tail 100 dhg-frontend
docker exec dhg-blackbox wget -qO- 'http://localhost:9115/probe?target=http://dhg-frontend:3000/&module=http_2xx' | grep -E 'probe_success|probe_http_status_code'
```

**Likely causes:** the Next.js container crashed or is mid-rebuild; a build
error left it serving 500s; the registry API it proxies is down, and a server
component throws during render.

**Resolve:** `docker compose up -d frontend` after reading the log. Note the
frontend emits almost no logs to Loki, so `docker logs` is the primary source
here, not Grafana.

**Dashboard:** [DHG Platform Overview](http://10.0.0.251:3001/d/dhg-platform-overview)

### OpenWebUIDown

```promql
probe_success{service="open-webui"} == 0
```

**Means:** `http://dhg-open-webui:8080/` has failed its probe for 3 minutes. The
local-model chat UI is unreachable. Published on the host as `:3080`.

**First three checks:**

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://10.0.0.251:3080/
docker logs --tail 100 dhg-open-webui
curl -s -o /dev/null -w '%{http_code}\n' http://10.0.0.251:11434/api/tags
```

**Likely causes:** the container is down; its SQLite/state volume is locked or
full; Ollama unreachable, so the UI starts but its model list fails (check
`OllamaDown` — they usually fire together).

**Resolve:** fix Ollama first if both are firing. Otherwise
`docker compose up -d open-webui` and confirm the probe returns
`probe_success 1`.

**Dashboard:** [DHG Platform Overview](http://10.0.0.251:3001/d/dhg-platform-overview)

### GrafanaDown

```promql
probe_success{service="grafana"} == 0
```

**Means:** `http://dhg-grafana:3000/api/health` has failed its probe for 3
minutes. Every dashboard is dark — and this alert is the only remaining signal
that observability itself is broken, since you cannot look at a dashboard to
diagnose it.

**First three checks:**

```bash
curl -s http://10.0.0.251:3001/api/health
docker logs --tail 100 dhg-grafana
docker inspect dhg-grafana --format '{{.State.Status}} {{.State.ExitCode}}'
```

**Likely causes:** an invalid provisioning file — Grafana reads
`dashboards/dashboards.yml` and the datasource provisioning at **startup only**
and refuses to start on a malformed one; the Grafana database (SQLite) locked or
corrupt; a plugin failing to load (the image renderer).

**Resolve:** the startup log names the offending file on the first error line.
Fix it and `docker compose up -d grafana`. Remember dashboard JSON re-provisions
live every 10s, but provider config and datasources need the restart.

**Dashboard:** [DHG Platform Overview](http://10.0.0.251:3001/d/dhg-platform-overview) — reachable only if Grafana is back.

### RegistryPublicDown

```promql
probe_success{service="registry-public"} == 0
```

**Means:** `https://registry.digitalharmonyai.com/health` has failed its probe
for 3 minutes. `warning`, deliberately — this probe is answered at the
**Cloudflare edge** by the Access policy (302, redirect not followed). A success
proves the edge answers for the hostname and the Access application is attached;
it proves nothing about the tunnel or the registry app, because Access rejects
the unauthenticated request before it reaches the origin.

**First three checks:**

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://registry.digitalharmonyai.com/health
dig +short registry.digitalharmonyai.com
systemctl status cloudflared --no-pager | head -15
```

**Likely causes:** DNS record removed or changed; the Cloudflare Access
application for the hostname deleted or misconfigured; a Cloudflare incident. It
is **not** evidence that the registry is down — `RegistryApiDown` is the origin
signal.

**Resolve:** confirm origin health first (`RegistryApiDown` clear = the app is
fine). Then work the Cloudflare side: DNS record, tunnel route, Access policy.
Tunnel config on this host is root-owned; see
`docs/OBSERVABILITY_RUNBOOK.md`.

**Dashboard:** [DHG Platform Overview](http://10.0.0.251:3001/d/dhg-platform-overview)

---

## dh40801 / Langfuse

Rules from `observability/prometheus/rules.d/dh40801.yml`. dh40801 is
`10.0.0.179` and runs the Langfuse stack. Reach it with
`docker --context dh40801 ...`; its agent (node-exporter, cAdvisor, Alloy) is
defined in `dh40801/docker-compose.observability.yml` and scraped over the LAN
via the `file_sd` targets in `observability/prometheus/targets/dh40801-*.json`.

### Dh40801Down

```promql
up{job="node-exporter-dh40801"} == 0
```

**Means:** Prometheus cannot scrape `10.0.0.179:9100`. Either dh40801 is down or
its observability agent stopped, and with it every host and container metric for
the Langfuse stack. `critical`.

**First three checks:**

```bash
docker --context dh40801 ps
ping -c 3 10.0.0.179
curl -s -m 5 http://10.0.0.179:9100/metrics | head -3
```

**Likely causes:** the host is down or rebooted; the observability compose
project was not brought back up after a reboot (it uses `restart: unless-stopped`,
so an explicit `stop` persists); a firewall change closed 9100.

**Resolve:** if the Docker context itself fails, the host is gone — that is a
hardware/network problem, not a container one. If the context works, redeploy the
agent:

```bash
ALLOY_CONFIG="$(cat dh40801/alloy/config.alloy)" \
  docker --context dh40801 compose -f dh40801/docker-compose.observability.yml up -d
```

**Dashboard:** [Langfuse — dh40801](http://10.0.0.251:3001/d/dhg-ai-langfuse)

### Dh40801DiskHigh

```promql
(1 - node_filesystem_avail_bytes{job="node-exporter-dh40801", mountpoint="/"} / node_filesystem_size_bytes{job="node-exporter-dh40801", mountpoint="/"}) > 0.85
```

**Means:** the dh40801 root volume is over 85% full. When it fills, Langfuse
stops persisting traces — and does so quietly, because the web tier keeps
answering 200.

**First three checks:**

```bash
docker --context dh40801 system df -v | head -30
docker --context dh40801 exec dhg-langfuse-clickhouse df -h / 2>/dev/null || true
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=node_filesystem_avail_bytes{job="node-exporter-dh40801", mountpoint="/"}'
```

**Likely causes:** ClickHouse trace tables growing; MinIO object storage holding
undrained trace batches; Docker image layers from repeated Langfuse upgrades.

**Resolve:** ClickHouse and MinIO under the Langfuse stack are the growth
drivers. Check the Langfuse named volumes before pruning anything, and prune
dangling images only. Do not delete MinIO objects by hand — undrained batches
are unwritten traces.

**Dashboard:** [Langfuse — dh40801](http://10.0.0.251:3001/d/dhg-ai-langfuse)

### LangfuseUnhealthy

```promql
probe_success{job="blackbox-langfuse"} == 0
```

**Means:** the blackbox probe of `http://10.0.0.179:3000/api/public/health` has
not returned 2xx for 3 minutes. Langfuse is not accepting traces; every agent
that traces to it is losing observability. `critical`.

**First three checks:**

```bash
curl -s -m 5 -o /dev/null -w '%{http_code}\n' http://10.0.0.179:3000/api/public/health
docker --context dh40801 logs --tail 200 dhg-langfuse-web
docker --context dh40801 ps --filter name=langfuse --format '{{.Names}}\t{{.Status}}'
```

**Likely causes:** the web container is down or restarting; its Postgres or
ClickHouse dependency is unreachable, so the health endpoint fails closed; the
host is out of disk (check `Dh40801DiskHigh`).

**Resolve:** restore dependencies before the web tier. A healthy `/health` is a
necessary but **not sufficient** condition — `LangfuseCanaryStale` is what proves
traces actually land. Do not close this until the canary is green too.

**Dashboard:** [Langfuse — dh40801](http://10.0.0.251:3001/d/dhg-ai-langfuse)

### LangfuseCanaryStale

```promql
(time() - langfuse_canary_success_timestamp > 900) or absent(langfuse_canary_success_timestamp)
```

**Means:** the write-then-read trace round-trip has not completed in over 15
minutes, or its metric is missing entirely. **This is the MinIO silent-drop
detector.** Langfuse v3 accepts a trace (HTTP 207) and hands it to MinIO for the
worker to drain into ClickHouse; if MinIO is down or the bucket is gone, the POST
still succeeds, the trace vanishes, `/api/public/health` stays 200 and
`LangfuseUnhealthy` never fires. Only a round-trip catches it. The `absent()`
clause is deliberate: if the canary's textfile is deleted, a bare age comparison
would evaluate over an empty vector and stay silent forever — the exact failure
this alert exists to prevent. `TextfileStale` cannot cover it either, because
`node_textfile_mtime_seconds` disappears with the file.

**First three checks:**

```bash
doppler run --project dhg-monitoring --config dev -- observability/scripts/langfuse-canary.sh
docker --context dh40801 logs --tail 200 dhg-langfuse-minio
docker --context dh40801 logs --tail 200 dhg-langfuse-worker
```

**Likely causes:** MinIO down or its `langfuse` bucket missing; the worker not
draining batches into ClickHouse; expired or rotated canary API keys; the canary
script's cron/timer stopped, so the textfile went stale without Langfuse being
at fault.

**Resolve:** run the canary by hand — it fails at the specific step and names it.
If it succeeds by hand but the metric is stale, the *scheduler* is the problem,
not Langfuse. Never delete the textfile to "clear" this alert.

**Dashboard:** [Langfuse — dh40801](http://10.0.0.251:3001/d/dhg-ai-langfuse)

### LangfuseContainerRestart

```promql
changes(container_start_time_seconds{host="dh40801", name=~"dhg-langfuse-.*"}[15m]) > 1
```

**Means:** a Langfuse container on dh40801 restarted more than once in 15
minutes. Tighter than the estate-wide `ContainerCrashLoop` (>3 restarts)
because the Langfuse stack is a fixed set of long-lived containers — a second
start inside 15 minutes is already abnormal.

**First three checks:**

```bash
docker --context dh40801 logs --tail 200 <container>
docker --context dh40801 inspect <container> --format '{{.State.ExitCode}} {{.State.OOMKilled}} {{.RestartCount}}'
docker --context dh40801 ps -a --filter name=langfuse --format '{{.Names}}\t{{.Status}}'
```

**Likely causes:** ClickHouse OOM on a large ingest; MinIO failing on a full
disk (check `Dh40801DiskHigh`); a version mismatch after a partial upgrade.

**Resolve:** ClickHouse and MinIO restarts **drop in-flight trace batches even
while the web tier keeps answering 200**, so treat this as data loss, not just
noise. After the restart loop stops, confirm `LangfuseCanaryStale` is clear
before closing.

**Dashboard:** [Langfuse — dh40801](http://10.0.0.251:3001/d/dhg-ai-langfuse)

---

## Logs

Three Prometheus rules (`alerts.yml`, group `dhg-logs`) covering the log
pipeline itself, plus the five Loki ruler rules in
`observability/loki/rules/fake/alerts.yml` that alert on log **content**.

Log collection is Grafana Alloy → Loki on both hosts. The keep-all directive
applies: nothing is deleted automatically, ever.

### LokiStoreGrowth

```promql
loki_store_bytes > 21474836480
```

**Means:** the keep-all log store has crossed 20 GB — roughly 10x the 2026-08
store, about two years of headroom at the observed ~11 MB/day. This is an
operator decision point, **not** an instruction to delete anything.

**First three checks:**

```bash
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=loki_store_bytes'
ssh 10.0.0.251 'du -sh /mnt/4tb/loki 2>/dev/null; df -h /mnt/4tb'
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=topk(10, sum by (container) (count_over_time({job="dhg-ai-factory"}[24h])))'
```

**Likely causes:** a container that started emitting high-volume logs (the
node-exporter `thermal_zone` collector produced ~708K error lines/day before it
was excluded); ephemeral e2e containers being ingested; a genuine increase in
traffic.

**Resolve:** find the top talker first — a single noisy container is almost
always the cause, and fixing it at the source is better than expanding storage.
Cross-check `TextfileStale`: `loki_store_bytes` comes from a textfile written by
`dhg-p5-loki-du`, so a frozen value can masquerade as either health or growth.
Expansion or the documented operator-only deletion procedure is Stephen's call.

**Dashboard:** [DHG Log Analytics](http://10.0.0.251:3001/d/dhg-log-analytics)

### LokiDown

```promql
up{job="loki"} == 0
```

**Means:** the log store is unreachable. `critical`. Note that a container
healthcheck is impossible on the shell-less Loki 3.x image — **this alert is the
liveness probe**.

**First three checks:**

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://10.0.0.251:3100/ready
docker logs --tail 200 dhg-loki
docker inspect dhg-loki --format '{{.State.Status}} {{.State.ExitCode}}'
```

**Likely causes:** a bad `loki-config.yml` after an edit; the store path on
`/mnt/4tb` unavailable or full; a WAL replay taking longer than the alert window
after an unclean shutdown (this resolves itself — check the log before acting).

**Resolve:** ingestion buffers in Alloy and the Docker json-file driver while
Loki is down, so short outages lose nothing; a multi-day outage does. Restart
with `docker compose up -d loki` and confirm `/ready` returns 200. If it is
replaying a WAL, wait rather than restarting again.

**Dashboard:** [DHG Log Analytics](http://10.0.0.251:3001/d/dhg-log-analytics)

### AlloyDown

```promql
up{job="alloy"} == 0
```

**Means:** the Grafana Alloy log shipper is not being scraped. Container logs are
buffering in the Docker json-file driver (10 MB x 3 files per container) and will
be lost once those rotate.

**First three checks:**

```bash
docker logs --tail 100 dhg-alloy
curl -s http://10.0.0.251:3100/loki/api/v1/labels
docker exec dhg-prometheus wget -qO- http://alloy:12345/metrics | head -3
```

**Likely causes:** a bad `observability/alloy/config.alloy` after an edit; Loki
unreachable so Alloy wedged on send (check `LokiDown`); the Docker socket mount
lost on recreate.

**Resolve:** fix Loki first if both are down. Then
`docker compose up -d alloy`. Verify ingestion actually resumed by querying a
recent window in Loki, not just by seeing the container as `Up` — a running
Alloy with a broken pipeline looks healthy. The dh40801 Alloy is a separate
deployment; see `Dh40801Down` for its redeploy command.

**Dashboard:** [DHG Log Analytics](http://10.0.0.251:3001/d/dhg-log-analytics)

### HighErrorRate

```promql
sum(count_over_time({job="dhg-ai-factory", level=~"error|fatal|critical|ERROR|FATAL|CRITICAL", container!="dhg-node-exporter"}[5m])) > 50
```

**Means:** more than 50 error-level log lines across all containers in 5
minutes. Loki ruler rule, `warning`.

`dhg-node-exporter` is excluded: its `thermal_zone` collector emits ~708K error
lines/day, which on its own kept this alert permanently firing and made the whole
log-alert group worthless. **The exclusion is a workaround, not the fix** — the
real fix is `--no-collector.thermal_zone` on the node-exporter command, which
lives in `docker-compose.override.yml` and needs Stephen. Remove the exclusion
once that flag is in place.

**First three checks:**

```bash
curl -sG http://10.0.0.251:3100/loki/api/v1/query --data-urlencode 'query=topk(10, sum by (container) (count_over_time({job="dhg-ai-factory", level=~"error|ERROR"}[15m])))'
docker logs --tail 200 <top-talking-container>
curl -s http://10.0.0.251:9090/api/v1/alerts | python3 -m json.tool | grep -i alertname
```

**Likely causes:** a single container in a retry loop (then `ContainerErrorSpike`
fires too and names it); a dependency outage producing errors across many
services; a new container with a noisy default log level.

**Resolve:** find the top talker by container and fix the source. Raising the
threshold masks everything; excluding another container masks that container.
Neither is a fix.

**Dashboard:** [DHG Log Analytics](http://10.0.0.251:3001/d/dhg-log-analytics)

### ContainerErrorSpike

```promql
sum by (container) (count_over_time({job="dhg-ai-factory", level=~"error|fatal|critical|ERROR|FATAL|CRITICAL", container!="dhg-node-exporter"}[5m])) > 20
```

**Means:** a *single* container produced more than 20 errors in 5 minutes. The
per-container companion to `HighErrorRate`, and the more actionable of the two
because it names the culprit in the alert label. Same `dhg-node-exporter`
exclusion and same pending real fix.

**First three checks:**

```bash
docker logs --tail 200 <container>
curl -sG http://10.0.0.251:3100/loki/api/v1/query_range --data-urlencode 'query={container="<container>"} |= "error"' --data-urlencode 'limit=50'
docker inspect <container> --format '{{.State.Status}} {{.RestartCount}}'
```

**Likely causes:** a crash loop (cross-check `ContainerCrashLoop`); an upstream
dependency down and a retry with no backoff; a bad deploy.

**Resolve:** read the actual lines — 20 identical retry errors and 20 distinct
errors are entirely different incidents. Fix the source; do not raise the
threshold.

**Dashboard:** [DHG Log Analytics](http://10.0.0.251:3001/d/dhg-log-analytics)

### PostgresFatalError

```promql
count_over_time({job="dhg-ai-factory", container="dhg-registry-db", level=~"fatal|panic|FATAL|PANIC"}[5m]) > 0
```

**Means:** the registry database logged a FATAL or PANIC. `critical`, `for: 0m`
— it fires on the first occurrence, deliberately.

**First three checks:**

```bash
docker logs --tail 200 dhg-registry-db
docker exec dhg-registry-db pg_isready
curl -sG http://10.0.0.251:9090/api/v1/query --data-urlencode 'query=pg_up{service="registry-db"}'
```

**Likely causes:** authentication failures (FATAL, and usually benign — a client
with stale credentials retrying); `max_connections` reached (FATAL "sorry, too
many clients", cross-check `PostgresConnectionsHigh`); disk full; genuine
corruption (PANIC — rare and serious).

**Resolve:** read the message. A repeated auth FATAL is a misconfigured client,
not a database problem. A PANIC means stop and assess before restarting: an
unclean restart after a PANIC can compound corruption. There are currently no
backups on either host — treat any PANIC as a potential data-loss event and
escalate to Stephen before acting.

**Dashboard:** [DHG PostgreSQL Fleet](http://10.0.0.251:3001/d/dhg-platform-postgres)

### NoLogsFromRegistryApi

```promql
absent_over_time({job="dhg-ai-factory", container="dhg-registry-api"}[10m])
```

**Means:** the registry API container has emitted no logs for 10+ minutes. Either
it is down, or the log pipeline between it and Loki is broken. `warning`,
because the ambiguity means it is not on its own an incident.

**First three checks:**

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://10.0.0.251:8011/healthz
docker logs --tail 20 dhg-registry-api
curl -sG http://10.0.0.251:3100/loki/api/v1/query --data-urlencode 'query=count_over_time({container="dhg-registry-api"}[15m])'
```

**Likely causes:** the container is down (then `RegistryApiDown` fires too, and
that is the real alert); Alloy lost connectivity to Loki (check `AlloyDown` and
`LokiDown`); genuinely no traffic at a quiet hour — the registry does log
periodically, so this is unusual but possible.

**Resolve:** the discriminator is `docker logs` — if the container is producing
lines locally but Loki has none, the problem is the shipper, not the service.
Fix Alloy in that case.

**Dashboard:** [DHG Log Analytics](http://10.0.0.251:3001/d/dhg-log-analytics)

### SecretLeakDetected

```promql
sum by (container) (count_over_time({job="dhg-ai-factory"} |~ `eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|dp\.(?:st|ct|pt)\.[A-Za-z0-9_-]{10,}` [5m])) > 0
```

**Means:** a JWT or Doppler token shape reached the **stored** log lines
unredacted — that is, it survived the redaction stage. `critical`, `for: 0m`. The
pattern matches raw secret shapes only and never matches the `[REDACTED*]`
markers themselves, so a hit is a redaction failure by construction.

**First three checks:**

Order matters here.

1. **Rotate the credential first.** Identify which secret shape leaked from the
   `container` label alone. Do **not** query the matching log line, and do not
   paste it anywhere — reading it to "confirm" spreads the exposure.
2. Fix the redaction stage in `observability/alloy/config.alloy` for that
   container's log format.
3. Prove the fix with the seeded-secret harness:
   `observability/scripts/p5-seeded-secret.sh`.

```bash
# Which container, and how many lines — no line content.
curl -sG http://10.0.0.251:3100/loki/api/v1/query --data-urlencode 'query=sum by (container) (count_over_time({job="dhg-ai-factory"} |~ `dp\.(st|ct|pt)\.` [1h]))'
```

**Likely causes:** a new container whose log format the Alloy redaction stage
does not parse; a service logging a full request or environment dump on error; a
secret embedded in a URL query string, which many redaction rules miss.

**Resolve:** rotation is the fix; the redaction repair is the prevention. Report
the exposure to Stephen — GitHub and Doppler auto-revoke some detected key
shapes, which makes rotation urgent rather than optional. The keep-all log
directive means the leaked line is not deleted by retention on its own.

**Dashboard:** [DHG Log Analytics](http://10.0.0.251:3001/d/dhg-log-analytics)
