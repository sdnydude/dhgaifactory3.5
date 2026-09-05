# Runbooks as code

One YAML per alert whose diagnostics can run unattended. These files are the
source; the `incident_runbooks` table is a cache of them (`registry/seed_runbooks.py`
loads this directory, `POST /api/incidents/runbooks/seed` refreshes it), and the
"Automation" block under each alert's section in
`docs-site/projects/dhg-ai-factory/runbooks/alerts.md` is generated from them by
`observability/scripts/gen-runbooks.py`. Human-only alerts have no YAML here; they
are listed in the "Automation coverage" table on that page.

Schema:

```yaml
alert: PrometheusTargetDown      # alertname, verbatim from the rule file
trigger_rule: T8                 # incident_runbooks.trigger_rule / ALERT_TRIGGER_MAP
severity: high                   # critical | high | warning (warning never opens an incident)
mode: notify                     # the only mode; diagnostics are read-only
title: ...
description: ...
fixture:                         # label values used by tests and verify-runbooks.sh
  job: prometheus
diagnostics:                     # every command must pass services/remediator/allowlist.py
  - order: 1
    description: ...
    command: docker logs --tail 100 {container}
human_steps:                     # what a person does; never executed
  - ...
notes: ...
```

Placeholders `{container}` `{instance}` `{service}` `{job}` resolve from the
alert labels the registry webhook stores as incident tags; a step whose
placeholder cannot be resolved is skipped with the reason recorded.
`observability/scripts/verify-runbooks.sh` runs every diagnostic live inside the
remediator image with the fixture values.
