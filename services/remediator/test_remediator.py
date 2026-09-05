"""
Remediator Tests
================
Covers the three defects that produced 2.6M incident_action rows:
page-1-only polling, no per-incident handled marker, and action rows written
for steps that neither took nor proposed anything.

Run with: pytest services/remediator/test_remediator.py -v
"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import remediator as r


@pytest.fixture(autouse=True)
def clean_state():
    r.processed.clear()
    getattr(r, "handled_state", {}).clear()
    yield
    r.processed.clear()
    getattr(r, "handled_state", {}).clear()


def make_incident(inc_id="i1", status="active", trigger="T8", services=None):
    return {
        "id": inc_id,
        "status": status,
        "severity": "high",
        "trigger_rule": trigger,
        "affected_services": services if services is not None else ["dhg-api"],
    }


RUNBOOK = {
    "trigger_rule": "T8",
    "remediation_mode": "auto",
    "enabled": True,
    "container_allowlist": [],
    "steps": [{"order": 1, "action": "check status", "command": "echo ok"}],
}


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

    def test_pending_approval_records_a_proposal(self):
        runbook = dict(RUNBOOK, remediation_mode="approval", steps=[
            {"order": 1, "action": "restart container", "command": "docker restart x"},
        ])
        with patch.object(r, "record_action") as mock_record:
            r.process_incident(make_incident(), runbook)
        assert mock_record.call_count == 1

    def test_executed_step_records_an_action(self):
        with patch.object(r, "record_action") as mock_record, \
             patch.object(r, "execute_command", return_value=(0, "ok")):
            r.process_incident(make_incident(), RUNBOOK)
        assert mock_record.call_count == 1


# ── Metrics ─────────────────────────────────────────────────────────────


class TestMetrics:
    def test_expected_series_are_registered(self):
        from prometheus_client import generate_latest

        r.actions_total.labels(kind="diagnostic").inc()
        r.cycles_total.inc()
        r.incidents_seen.set(3)
        body = generate_latest(r.METRICS_REGISTRY).decode()

        assert "remediator_cycles_total" in body
        assert "remediator_incidents_seen" in body
        assert 'remediator_actions_total{kind="diagnostic"}' in body

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
        before = r.actions_total.labels(kind="auto_remediation")._value.get()
        with patch.object(r, "api_post"):
            r.record_action("i1", "auto_remediation", "restarted container")
        after = r.actions_total.labels(kind="auto_remediation")._value.get()
        assert after == before + 1

    def test_blocked_command_records_no_action(self):
        runbook = dict(RUNBOOK, steps=[
            {"order": 1, "action": "wipe", "command": "rm -rf /data"},
        ])
        with patch.object(r, "record_action") as mock_record:
            r.process_incident(make_incident(), runbook)
        mock_record.assert_not_called()

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
