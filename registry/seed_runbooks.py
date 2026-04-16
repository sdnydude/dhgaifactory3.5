"""
Seed the 14 deterministic incident trigger rules (T1–T14).

Usage:
    python seed_runbooks.py          # standalone
    POST /api/incidents/runbooks/seed # via API (see incident_endpoints.py)
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from models import IncidentRunbook

logger = logging.getLogger("seed_runbooks")

RUNBOOKS: list[dict] = [
    {
        "trigger_rule": "T1",
        "title": "Container unhealthy > 10 minutes",
        "description": "A container has been in unhealthy state for more than 10 minutes according to Docker healthcheck.",
        "severity": "high",
        "remediation_mode": "approval",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Check container logs", "command": "docker logs --tail 100 {container}"},
            {"order": 2, "action": "Check healthcheck endpoint", "command": "docker inspect --format='{{{{.State.Health}}}}' {container}"},
            {"order": 3, "action": "Restart container (if approved)", "command": "docker restart {container}"},
        ],
    },
    {
        "trigger_rule": "T2",
        "title": "Container crash loop (>3 restarts in 15 min)",
        "description": "Container has restarted more than 3 times in 15 minutes. Indicates a persistent failure that restart won't fix.",
        "severity": "critical",
        "remediation_mode": "none",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Check recent logs for crash cause", "command": "docker logs --tail 200 {container}"},
            {"order": 2, "action": "Check resource usage", "command": "docker stats --no-stream {container}"},
            {"order": 3, "action": "Stop container to prevent further damage", "command": "docker stop {container}"},
            {"order": 4, "action": "Investigate root cause in code/config before restarting"},
        ],
    },
    {
        "trigger_rule": "T3",
        "title": "Host memory > 90%",
        "description": "Host memory usage exceeds 90%. Risk of OOM killer, swap thrashing, and cascading service failures.",
        "severity": "critical",
        "remediation_mode": "approval",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Identify top memory consumers", "command": "docker stats --no-stream --format 'table {{{{.Name}}}}\\t{{{{.MemUsage}}}}' | sort -k2 -h -r | head -10"},
            {"order": 2, "action": "Check for memory leaks (containers using >16GB)", "command": "docker stats --no-stream --format '{{{{.Name}}}} {{{{.MemUsage}}}}' | awk '{if ($2+0 > 16000) print}'"},
            {"order": 3, "action": "Stop top non-essential consumer (if approved)", "command": "docker stop {container}"},
            {"order": 4, "action": "Clear page cache if needed", "command": "sync && echo 3 > /proc/sys/vm/drop_caches"},
        ],
    },
    {
        "trigger_rule": "T4",
        "title": "Host swap > 80%",
        "description": "Host swap usage exceeds 80%. System is memory-constrained and may be thrashing.",
        "severity": "high",
        "remediation_mode": "approval",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Check memory and swap usage", "command": "free -h"},
            {"order": 2, "action": "Identify swap-heavy processes", "command": "for pid in /proc/[0-9]*; do echo \"$(cat $pid/status 2>/dev/null | grep VmSwap | awk '{print $2}') $(cat $pid/cmdline 2>/dev/null | tr '\\0' ' ')\"; done | sort -rn | head -10"},
            {"order": 3, "action": "Stop top non-essential consumer (if approved)", "command": "docker stop {container}"},
        ],
    },
    {
        "trigger_rule": "T5",
        "title": "Root disk > 85%",
        "description": "Root filesystem usage exceeds 85%. Critical system operations may fail.",
        "severity": "high",
        "remediation_mode": "none",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Check disk usage breakdown", "command": "df -h / && du -sh /var/log/* /tmp/* 2>/dev/null | sort -rh | head -10"},
            {"order": 2, "action": "Clean Docker resources", "command": "docker system prune -f"},
            {"order": 3, "action": "Check for large log files", "command": "find /var/log -type f -size +100M -exec ls -lh {} \\;"},
        ],
    },
    {
        "trigger_rule": "T6",
        "title": "Data disk > 80%",
        "description": "Data disk (/mnt/4tb) usage exceeds 80%. Docker images, volumes, and database storage at risk.",
        "severity": "medium",
        "remediation_mode": "none",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Check data disk usage", "command": "df -h /mnt/4tb && du -sh /mnt/4tb/docker/* 2>/dev/null | sort -rh | head -10"},
            {"order": 2, "action": "Check Docker image sizes", "command": "docker image ls --format 'table {{{{.Repository}}}}\\t{{{{.Size}}}}' | sort -k2 -h -r | head -20"},
            {"order": 3, "action": "Prune unused images", "command": "docker image prune -a -f --filter 'until=168h'"},
        ],
    },
    {
        "trigger_rule": "T7",
        "title": "Pipeline agent failure",
        "description": "A LangGraph pipeline agent threw an unhandled exception during execution. Application-level bug requiring code fix.",
        "severity": "high",
        "remediation_mode": "none",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Check orchestrator error details in pipeline_run record"},
            {"order": 2, "action": "Check LangSmith trace for the failed run"},
            {"order": 3, "action": "Review agent source code for the failing node"},
            {"order": 4, "action": "Fix bug and redeploy agent"},
        ],
    },
    {
        "trigger_rule": "T8",
        "title": "Prometheus scrape target DOWN",
        "description": "A Prometheus scrape target is unreachable. The monitored service may be down or network-partitioned.",
        "severity": "high",
        "remediation_mode": "approval",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Check target container status", "command": "docker ps -a --filter name={container}"},
            {"order": 2, "action": "Check Prometheus targets page", "command": "curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool"},
            {"order": 3, "action": "Restart target container (if approved)", "command": "docker restart {container}"},
        ],
    },
    {
        "trigger_rule": "T9",
        "title": "DB connection pool > 80% of max_connections",
        "description": "PostgreSQL connection count exceeds 80% of max_connections. New connections may be refused.",
        "severity": "high",
        "remediation_mode": "none",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Check current connections", "command": "docker exec dhg-registry-db psql -U dhg -d dhg_registry -c \"SELECT count(*), state FROM pg_stat_activity GROUP BY state;\""},
            {"order": 2, "action": "Identify connection-heavy clients", "command": "docker exec dhg-registry-db psql -U dhg -d dhg_registry -c \"SELECT client_addr, count(*) FROM pg_stat_activity GROUP BY client_addr ORDER BY count DESC;\""},
            {"order": 3, "action": "Check for connection leaks in application code"},
        ],
    },
    {
        "trigger_rule": "T10",
        "title": "DB queries running > 30 minutes",
        "description": "One or more database queries have been running for over 30 minutes. Likely stuck or deadlocked.",
        "severity": "medium",
        "remediation_mode": "auto",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Identify long-running queries", "command": "docker exec dhg-registry-db psql -U dhg -d dhg_registry -c \"SELECT pid, now()-query_start AS duration, state, left(query,80) FROM pg_stat_activity WHERE state != 'idle' AND (now()-query_start) > interval '30 minutes' ORDER BY duration DESC;\""},
            {"order": 2, "action": "Terminate stuck queries", "command": "docker exec dhg-registry-db psql -U dhg -d dhg_registry -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state != 'idle' AND (now()-query_start) > interval '30 minutes';\""},
        ],
    },
    {
        "trigger_rule": "T11",
        "title": "DB idle-in-transaction > 5 minutes",
        "description": "Connections stuck in 'idle in transaction' for over 5 minutes. Holds locks and blocks other queries.",
        "severity": "high",
        "remediation_mode": "auto",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Identify idle-in-transaction connections", "command": "docker exec dhg-registry-db psql -U dhg -d dhg_registry -c \"SELECT pid, now()-query_start AS duration, left(query,80) FROM pg_stat_activity WHERE state = 'idle in transaction' AND (now()-query_start) > interval '5 minutes';\""},
            {"order": 2, "action": "Terminate idle-in-transaction backends", "command": "docker exec dhg-registry-db psql -U dhg -d dhg_registry -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND (now()-query_start) > interval '5 minutes';\""},
        ],
    },
    {
        "trigger_rule": "T12",
        "title": "Zombie processes > 50",
        "description": "More than 50 zombie processes detected on the host. Indicates process cleanup failures.",
        "severity": "medium",
        "remediation_mode": "none",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Count zombie processes", "command": "ps aux | grep -c '[Zz]'"},
            {"order": 2, "action": "Identify zombie parent processes", "command": "ps -eo ppid,pid,stat,comm | grep Z | awk '{print $1}' | sort | uniq -c | sort -rn | head -10"},
            {"order": 3, "action": "Restart parent process or container that is spawning zombies"},
        ],
    },
    {
        "trigger_rule": "T13",
        "title": "Container memory > 16GB (no limit)",
        "description": "A container is using more than 16GB of memory without a configured limit. Likely a memory leak.",
        "severity": "high",
        "remediation_mode": "approval",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Check container memory usage", "command": "docker stats --no-stream {container}"},
            {"order": 2, "action": "Check if memory limit is configured", "command": "docker inspect {container} --format='{{{{.HostConfig.Memory}}}}'"},
            {"order": 3, "action": "Stop container (if approved)", "command": "docker stop {container}"},
            {"order": 4, "action": "Add memory limit to docker-compose.yml and rebuild"},
        ],
    },
    {
        "trigger_rule": "T14",
        "title": "External 5xx rate > 10 in 5 min",
        "description": "More than 10 HTTP 5xx responses in a 5-minute window from the registry API.",
        "severity": "medium",
        "remediation_mode": "none",
        "container_allowlist": [],
        "steps": [
            {"order": 1, "action": "Check registry API logs", "command": "docker logs --tail 200 dhg-registry-api"},
            {"order": 2, "action": "Check Prometheus error counter", "command": "curl -s 'http://localhost:9090/api/v1/query?query=registry_errors_total' | python3 -m json.tool"},
            {"order": 3, "action": "Check database connectivity"},
            {"order": 4, "action": "Check dependent services (Ollama, LangGraph Cloud)"},
        ],
    },
]


def seed_all(db: Session) -> dict[str, int]:
    """Upsert all 14 runbooks. Returns {"created": N, "updated": M}."""
    created = 0
    updated = 0

    for rb_data in RUNBOOKS:
        trigger = rb_data["trigger_rule"]
        existing = db.query(IncidentRunbook).filter(IncidentRunbook.trigger_rule == trigger).first()

        if existing:
            for key, value in rb_data.items():
                setattr(existing, key, value)
            updated += 1
        else:
            db.add(IncidentRunbook(**rb_data))
            created += 1

    db.commit()
    logger.info("Runbook seed complete: %d created, %d updated", created, updated)
    return {"created": created, "updated": updated}


if __name__ == "__main__":
    import sys
    from database import SessionLocal

    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        result = seed_all(db)
        print(f"Seeded runbooks: {result}")
    finally:
        db.close()
    sys.exit(0)
