"""
CME SLA scheduler toggle tests
==============================
The APScheduler-based SLA scheduler in ``timeout_handler`` is wired into the
registry lifespan behind ``CME_SLA_SCHEDULER_ENABLED`` (default off). These
tests cover the strict flag parser, the startup branch taken for each state,
the ``registry_cme_sla_scheduler_enabled`` gauge, and clean shutdown. No real
timers run: ``start_scheduler`` is monkeypatched.

Run with: pytest registry/test_cme_sla_scheduler.py -v
"""
import logging
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

import timeout_handler
from timeout_handler import SCHEDULER_ENV, parse_scheduler_flag

GAUGE = "registry_cme_sla_scheduler_enabled"


def _gauge():
    return REGISTRY.get_sample_value(GAUGE)


@pytest.mark.parametrize("value", ["true", "TRUE", "True", "1", "yes", "YES", "on", "ON", " true "])
def test_parse_flag_on(value):
    assert parse_scheduler_flag(value) is True


@pytest.mark.parametrize("value", [None, "", " ", "false", "0", "no", "off", "enabled", "2", "truee", "y"])
def test_parse_flag_off(value):
    assert parse_scheduler_flag(value) is False


class TestLifespanToggle:
    @pytest.fixture
    def start_scheduler(self, monkeypatch):
        fake_scheduler = MagicMock(name="AsyncIOScheduler")
        start = MagicMock(name="start_scheduler", return_value=fake_scheduler)
        monkeypatch.setattr(timeout_handler, "start_scheduler", start)
        return start

    def test_off_when_unset(self, monkeypatch, caplog, start_scheduler):
        monkeypatch.delenv(SCHEDULER_ENV, raising=False)
        from api import app

        with caplog.at_level(logging.INFO, logger="dhg.registry"):
            with TestClient(app):
                assert _gauge() == 0.0
        start_scheduler.assert_not_called()
        assert f"CME SLA scheduler disabled ({SCHEDULER_ENV} unset)" in caplog.text

    def test_on_starts_and_stops_scheduler(self, monkeypatch, caplog, start_scheduler):
        monkeypatch.setenv(SCHEDULER_ENV, "true")
        from api import app

        fake_scheduler = start_scheduler.return_value
        with caplog.at_level(logging.INFO, logger="dhg.registry"):
            with TestClient(app):
                start_scheduler.assert_called_once_with()
                assert _gauge() == 1.0
                fake_scheduler.shutdown.assert_not_called()
        fake_scheduler.shutdown.assert_called_once()
        assert f"CME SLA scheduler enabled: {timeout_handler.SCHEDULE_SUMMARY}" in caplog.text

    def test_off_when_set_false_names_the_value(self, monkeypatch, caplog, start_scheduler):
        monkeypatch.setenv(SCHEDULER_ENV, "false")
        from api import app

        with caplog.at_level(logging.INFO, logger="dhg.registry"):
            with TestClient(app):
                assert _gauge() == 0.0
        start_scheduler.assert_not_called()
        assert f"CME SLA scheduler disabled ({SCHEDULER_ENV}=false)" in caplog.text

    def test_on_but_start_returns_none_reports_zero(self, monkeypatch, start_scheduler):
        """start_scheduler returns None when apscheduler is missing; gauge must not lie."""
        monkeypatch.setenv(SCHEDULER_ENV, "true")
        start_scheduler.return_value = None
        from api import app

        with TestClient(app):
            assert _gauge() == 0.0
        start_scheduler.assert_called_once_with()
