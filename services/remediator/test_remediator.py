"""
Remediator Tests
================
Covers the three defects that produced 2.6M incident_action rows (page-1-only
polling, no per-incident handled marker, action rows for steps that neither
took nor proposed anything) and the notify-only contract: nothing outside the
command allowlist is ever executed, whatever the runbook says.

Run with: pytest services/remediator -q
"""

import glob
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

sys.path.insert(0, os.path.dirname(__file__))

import remediator as r
from allowlist import check_command

RUNBOOKS_DIR = Path(__file__).resolve().parents[2] / "observability" / "runbooks"


@pytest.fixture(autouse=True)
def clean_state():
    r.processed.clear()
    r.handled_state.clear()
    yield
    r.processed.clear()
    r.handled_state.clear()


def make_incident(inc_id="i1", status="active", trigger="T8", services=None, tags=None):
    return {
        "id": inc_id,
        "status": status,
        "severity": "high",
        "trigger_rule": trigger,
        "affected_services": services if services is not None else ["dhg-api"],
        "tags": tags or [],
    }


RUNBOOK = {
    "trigger_rule": "T8",
    "remediation_mode": "notify",
    "enabled": True,
    "container_allowlist": [],
    "steps": [{"order": 1, "action": "check status", "command": "docker ps"}],
}


# ── Allowlist ───────────────────────────────────────────────────────────


ALLOWLIST_TABLE = [
    # allowed
    ("docker inspect dhg-loki --format '{{.State.Status}}'", True),
    ("docker ps -a --filter status=exited", True),
    ("docker logs --tail 100 dhg-loki", True),
    ("docker stats --no-stream dhg-loki", True),
    ("curl -s http://dhg-loki:3100/ready", True),
    ("curl -s -m 5 -o /dev/null -w '%{http_code}' http://dhg-frontend:3000/", True),
    ('curl -sG http://dhg-prometheus:9090/api/v1/query --data-urlencode \'query=up{job="loki"}\'', True),
    ("wget -qO- http://dhg-loki:3100/ready", True),
    # refused: mutating docker
    ("docker restart dhg-loki", False),
    ("docker stop dhg-loki", False),
    ("docker kill dhg-loki", False),
    ("docker rm -f dhg-loki", False),
    ("docker rmi x", False),
    ("docker image prune -a -f", False),
    ("docker system prune -f", False),
    ("docker volume rm x", False),
    ("docker exec dhg-registry-db psql -c 'SELECT 1'", False),
    ("docker compose down", False),
    # refused: wrong flags on allowed subcommands
    ("docker logs dhg-loki", False),
    ("docker logs -f --tail 10 dhg-loki", False),
    ("docker stats dhg-loki", False),
    # refused: shell operators, even inside an otherwise-allowed command
    ("docker ps | head", False),
    ("docker ps; docker restart x", False),
    ("docker ps && docker restart x", False),
    ("echo 3 > /proc/sys/vm/drop_caches", False),
    ("sync && echo 3 > /proc/sys/vm/drop_caches", False),
    ("docker inspect $(docker ps -q)", False),
    ("docker inspect `docker ps -q`", False),
    ("curl -s http://dhg-loki:3100/ready < /etc/passwd", False),
    # refused: other programs
    ("sh -c 'docker ps'", False),
    ("psql -c 'SELECT 1'", False),
    ("rm -rf /data", False),
    ("echo ok", False),
    ("free -h", False),
    # refused: curl that is not a plain GET to a dhg-* container
    ("curl -s -X POST http://dhg-registry-api:8000/api/incidents", False),
    ("curl -s -d x=1 http://dhg-registry-api:8000/x", False),
    ("curl -s --data-urlencode 'query=up' http://dhg-prometheus:9090/api/v1/query", False),
    ("curl -s http://10.0.0.251:9090/api/v1/targets", False),
    ("curl -s https://dhg-loki:3100/ready", False),
    ("curl -s http://localhost:9090/", False),
    ("curl http://dhg-loki:3100/ready", False),
    ("curl -s -o /tmp/x http://dhg-loki:3100/ready", False),
    ("wget -O /tmp/x http://dhg-loki:3100/ready", False),
    ("wget -qO- http://10.0.0.251:3100/ready", False),
    ("", False),
]


class TestAllowlist:
    @pytest.mark.parametrize("command,expected", ALLOWLIST_TABLE)
    def test_verdict(self, command, expected):
        allowed, _ = check_command(command)
        assert allowed is expected, command

    def test_run_refuses_without_executing(self):
        with patch("allowlist.subprocess.run") as mock_run:
            rc, out = r.run_allowlisted("docker restart dhg-loki")
        mock_run.assert_not_called()
        assert rc == -2 and out.startswith("refused")

    def test_run_never_uses_a_shell(self):
        with patch("allowlist.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "ok"
            mock_run.return_value.stderr = ""
            r.run_allowlisted("docker ps --filter name=dhg-")
        args, kwargs = mock_run.call_args
        assert args[0] == ["docker", "ps", "--filter", "name=dhg-"]
        assert kwargs.get("shell") is False


# ── Placeholders ────────────────────────────────────────────────────────


class TestPlaceholders:
    def test_resolves_from_tags(self):
        inc = make_incident(services=["loki"], tags=[
            "container:dhg-loki", "instance:loki:3100", "job:loki", "service:loki",
        ])
        cmd, missing = r.resolve_placeholders(
            "docker logs --tail 50 {container} {instance} {job} {service}", inc)
        assert cmd == "docker logs --tail 50 dhg-loki loki:3100 loki loki"
        assert missing == []

    def test_falls_back_to_affected_service_for_service_and_dhg_container(self):
        inc = make_incident(services=["dhg-ollama"])
        cmd, missing = r.resolve_placeholders("docker stats --no-stream {container} {service}", inc)
        assert cmd == "docker stats --no-stream dhg-ollama dhg-ollama"
        assert missing == []

    def test_job_label_is_not_treated_as_a_container(self):
        inc = make_incident(services=["cloudflared"])
        cmd, missing = r.resolve_placeholders("docker logs --tail 50 {container}", inc)
        assert cmd == "docker logs --tail 50 {container}"
        assert missing == ["container"]

    def test_go_templates_pass_through(self):
        inc = make_incident(services=["dhg-loki"])
        cmd, missing = r.resolve_placeholders(
            "docker inspect {container} --format '{{.State.Status}}'", inc)
        assert cmd == "docker inspect dhg-loki --format '{{.State.Status}}'"
        assert missing == []

    def test_unresolved_step_is_skipped_with_reason_not_executed(self):
        runbook = dict(RUNBOOK, steps=[
            {"order": 1, "action": "logs", "command": "docker logs --tail 50 {container}"},
        ])
        with patch.object(r, "record_action") as mock_record, \
             patch.object(r, "execute_command") as mock_exec:
            r.process_incident(make_incident(services=["cloudflared"]), runbook)
        mock_exec.assert_not_called()
        assert mock_record.call_count == 1
        assert "skipped" in mock_record.call_args.args[2]
        assert "{container}" in mock_record.call_args.kwargs["result"]

    def test_label_value_cannot_inject_an_operator(self):
        inc = make_incident(services=["dhg-x"], tags=["container:dhg-x; docker restart dhg-x"])
        runbook = dict(RUNBOOK, steps=[
            {"order": 1, "action": "logs", "command": "docker logs --tail 50 {container}"},
        ])
        with patch.object(r, "record_action") as mock_record, \
             patch.object(r, "execute_command") as mock_exec:
            r.process_incident(inc, runbook)
        mock_exec.assert_not_called()
        assert mock_record.call_args.args[1] == "proposed"


# ── Pagination ──────────────────────────────────────────────────────────


class TestFetchActiveIncidents:
    def test_walks_every_page(self):
        """Page-1-only polling meant 1,062 of 1,112 active incidents were invisible."""
        page1 = [make_incident(f"a{i}") for i in range(r.PAGE_SIZE)]
        page2 = [make_incident("tail")]
        calls = []

        def fake_get(path):
            calls.append(path)
            return page1 if "offset=0" in path else page2

        with patch.object(r, "api_get", side_effect=fake_get):
            result = r.fetch_active_incidents()

        assert len(result) == r.PAGE_SIZE + 1
        assert result[-1]["id"] == "tail"
        assert len(calls) == 2
        assert f"offset={r.PAGE_SIZE}" in calls[1]

    def test_stops_on_short_page(self):
        with patch.object(r, "api_get", return_value=[make_incident()]) as mock_get:
            result = r.fetch_active_incidents()
        assert len(result) == 1
        assert mock_get.call_count == 1

    def test_empty_response_stops_cleanly(self):
        with patch.object(r, "api_get", return_value=None):
            assert r.fetch_active_incidents() == []


# ── Once per state change ───────────────────────────────────────────────


class TestOncePerStateChange:
    def test_unchanged_incident_is_processed_once_across_cycles(self):
        """The bug: every 30s cycle re-ran the runbook and wrote fresh rows."""
        incidents = [make_incident()]
        with patch.object(r, "fetch_active_incidents", return_value=incidents), \
             patch.object(r, "fetch_runbooks", return_value={"T8": RUNBOOK}), \
             patch.object(r, "process_incident") as mock_process:
            r.poll_cycle()
            r.poll_cycle()
            r.poll_cycle()

        assert mock_process.call_count == 1

    def test_stale_incidents_are_not_remediated(self):
        """A restart must not stampede the whole open backlog.

        handled_state lives in memory, so on every restart every open
        incident looks new. With 1,114 open incidents that first pass ran
        runbooks against conditions from months ago (observed: 649 action
        rows across 405 incidents in two minutes before it was stopped).
        """
        old = dict(make_incident(),
                   detected_at="2026-04-25T10:00:00+00:00")
        with patch.object(r, "fetch_active_incidents", return_value=[old]), \
             patch.object(r, "fetch_runbooks", return_value={"T8": RUNBOOK}), \
             patch.object(r, "process_incident") as mock_process:
            r.poll_cycle()

        mock_process.assert_not_called()

    def test_key_ignores_service_ordering(self):
        a = r.incident_state_key(make_incident(services=["b", "a"]))
        b = r.incident_state_key(make_incident(services=["a", "b"]))
        assert a == b

    def test_state_change_reprocesses(self):
        with patch.object(r, "fetch_runbooks", return_value={"T8": RUNBOOK}), \
             patch.object(r, "process_incident") as mock_process:
            with patch.object(r, "fetch_active_incidents",
                              return_value=[make_incident(status="active")]):
                r.poll_cycle()
            r.processed.clear()  # cooldown is a separate guard
            with patch.object(r, "fetch_active_incidents",
                              return_value=[make_incident(status="mitigated")]):
                r.poll_cycle()

        assert mock_process.call_count == 2

    def test_cooldown_still_blocks_a_rapid_state_flap(self):
        with patch.object(r, "fetch_runbooks", return_value={"T8": RUNBOOK}), \
             patch.object(r, "process_incident") as mock_process:
            with patch.object(r, "fetch_active_incidents",
                              return_value=[make_incident(status="active")]):
                r.poll_cycle()
            with patch.object(r, "fetch_active_incidents",
                              return_value=[make_incident(status="mitigated")]):
                r.poll_cycle()

        assert mock_process.call_count == 1


# ── Action rows only for real actions ───────────────────────────────────


class TestActionRowDiscipline:
    def test_allowlist_skip_records_no_action(self):
        runbook = dict(RUNBOOK, container_allowlist=["something-else"])
        with patch.object(r, "record_action") as mock_record:
            r.process_incident(make_incident(), runbook)
        mock_record.assert_not_called()

    def test_manual_step_records_no_action(self):
        runbook = dict(RUNBOOK, steps=[{"order": 1, "action": "page a human"}])
        with patch.object(r, "record_action") as mock_record:
            r.process_incident(make_incident(), runbook)
        mock_record.assert_not_called()

    @pytest.mark.parametrize("mode", ["auto", "approval", "notify"])
    def test_non_allowlisted_step_is_proposed_once_and_never_executed(self, mode):
        """Mode no longer matters: restart/stop/prune/psql are never run."""
        runbook = dict(RUNBOOK, remediation_mode=mode, steps=[
            {"order": 1, "action": "restart container", "command": "docker restart x"},
            {"order": 2, "action": "drop caches", "command": "sync && echo 3 > /proc/sys/vm/drop_caches"},
            {"order": 3, "action": "prune", "command": "docker image prune -a -f"},
        ])
        with patch.object(r, "record_action") as mock_record, \
             patch("allowlist.subprocess.run") as mock_run:
            r.process_incident(make_incident(), runbook)
        mock_run.assert_not_called()
        assert mock_record.call_count == 3
        assert {c.args[1] for c in mock_record.call_args_list} == {"proposed"}
        assert "docker restart x" == mock_record.call_args_list[0].kwargs["command"]

    def test_executed_step_records_a_diagnostic(self):
        with patch.object(r, "record_action") as mock_record, \
             patch.object(r, "execute_command", return_value=(0, "ok")) as mock_exec:
            r.process_incident(make_incident(), RUNBOOK)
        mock_exec.assert_called_once_with("docker ps")
        assert mock_record.call_count == 1
        assert mock_record.call_args.args[1] == "diagnostic"

    def test_failed_diagnostic_does_not_stop_the_rest(self):
        runbook = dict(RUNBOOK, steps=[
            {"order": 1, "action": "logs", "command": "docker logs --tail 5 dhg-x"},
            {"order": 2, "action": "ps", "command": "docker ps"},
        ])
        with patch.object(r, "record_action") as mock_record, \
             patch.object(r, "execute_command", side_effect=[(1, "no such container"), (0, "ok")]):
            r.process_incident(make_incident(), runbook)
        assert mock_record.call_count == 2
        assert "failed (exit 1)" in mock_record.call_args_list[0].args[2]


# ── Fixture-driven run over every seeded runbook ────────────────────────


def load_runbook_files() -> list[dict]:
    files = sorted(glob.glob(str(RUNBOOKS_DIR / "*.yml")))
    assert files, f"no runbook YAML found under {RUNBOOKS_DIR}"
    return [yaml.safe_load(open(f)) for f in files]


class TestSeededRunbooks:
    """Every observability/runbooks/*.yml run against a fake incident built
    from its fixture labels: zero refused commands, zero unresolved
    placeholders, and every executed command passes the allowlist."""

    @pytest.mark.parametrize("rb", load_runbook_files(), ids=lambda rb: rb["alert"])
    def test_every_diagnostic_executes_only_allowlisted_commands(self, rb):
        fixture = rb.get("fixture") or {}
        incident = make_incident(
            inc_id=rb["alert"], trigger=rb["trigger_rule"],
            services=[fixture.get("container") or fixture.get("service") or fixture.get("job") or "unknown"],
            tags=[f"{k}:{v}" for k, v in fixture.items()],
        )
        runbook = {
            "trigger_rule": rb["trigger_rule"],
            "remediation_mode": rb["mode"],
            "enabled": True,
            "container_allowlist": [],
            "steps": [{"order": s["order"], "action": s["description"], "command": s["command"]}
                      for s in rb["diagnostics"]],
        }
        executed: list[str] = []
        recorded: list = []

        def fake_exec(cmd):
            allowed, why = check_command(cmd)
            assert allowed, f"{rb['alert']}: executor received a non-allowlisted command: {cmd} ({why})"
            executed.append(cmd)
            return 0, "ok"

        with patch.object(r, "execute_command", side_effect=fake_exec), \
             patch.object(r, "record_action", side_effect=lambda *a, **k: recorded.append((a, k))):
            r.process_incident(incident, runbook)

        kinds = [a[1] for a, _ in recorded]
        assert "proposed" not in kinds, f"{rb['alert']} has a non-allowlisted diagnostic"
        assert not any("skipped" in a[2] for a, _ in recorded), f"{rb['alert']} has an unresolved placeholder"
        assert len(executed) == len(rb["diagnostics"])
        assert all("{" + p + "}" not in cmd for cmd in executed for p in r.PLACEHOLDERS)

    def test_no_human_step_is_a_command(self):
        for rb in load_runbook_files():
            for step in rb.get("human_steps") or []:
                assert isinstance(step, str)

    def test_alert_name_matches_file_name(self):
        for f in sorted(glob.glob(str(RUNBOOKS_DIR / "*.yml"))):
            assert yaml.safe_load(open(f))["alert"] == Path(f).stem


# ── Metrics ─────────────────────────────────────────────────────────────


class TestMetrics:
    def test_expected_series_are_registered(self):
        from prometheus_client import generate_latest

        r.actions_total.labels(kind="diagnostic").inc()
        r.commands_total.labels(verdict="refused").inc()
        r.cycles_total.inc()
        r.incidents_seen.set(3)
        body = generate_latest(r.METRICS_REGISTRY).decode()

        assert "remediator_cycles_total" in body
        assert "remediator_incidents_seen" in body
        assert 'remediator_actions_total{kind="diagnostic"}' in body
        assert 'remediator_commands_total{verdict="refused"}' in body

    def test_cycle_counter_advances(self):
        before = r.cycles_total._value.get()
        with patch.object(r, "fetch_active_incidents", return_value=[]), \
             patch.object(r, "fetch_runbooks", return_value={}):
            r.poll_cycle()
        assert r.cycles_total._value.get() == before + 1

    def test_incidents_seen_reflects_every_page(self):
        incidents = [make_incident(f"x{i}") for i in range(5)]
        with patch.object(r, "fetch_active_incidents", return_value=incidents), \
             patch.object(r, "fetch_runbooks", return_value={}):
            r.poll_cycle()
        assert r.incidents_seen._value.get() == 5

    def test_action_counter_labels_by_kind(self):
        before = r.actions_total.labels(kind="proposed")._value.get()
        with patch.object(r, "api_post"):
            r.record_action("i1", "proposed", "restart container")
        after = r.actions_total.labels(kind="proposed")._value.get()
        assert after == before + 1

    def test_refused_command_counts_as_refused_not_executed(self):
        runbook = dict(RUNBOOK, steps=[
            {"order": 1, "action": "wipe", "command": "rm -rf /data"},
        ])
        refused_before = r.commands_total.labels(verdict="refused")._value.get()
        executed_before = r.commands_total.labels(verdict="executed")._value.get()
        with patch.object(r, "record_action"):
            r.process_incident(make_incident(), runbook)
        assert r.commands_total.labels(verdict="refused")._value.get() == refused_before + 1
        assert r.commands_total.labels(verdict="executed")._value.get() == executed_before
