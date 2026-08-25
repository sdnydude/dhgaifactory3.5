"""P5 T8 — ALERT_TRIGGER_MAP carries the log-program alerts (SecretLeakDetected,
LokiStoreGrowth, AlloyDown) with the right categories and unique triggers."""
from api import ALERT_TRIGGER_MAP


def test_secret_leak_maps_to_security_trigger():
    assert ALERT_TRIGGER_MAP["SecretLeakDetected"] == {"trigger": "T14", "category": "security"}


def test_loki_store_growth_maps_to_infrastructure():
    assert ALERT_TRIGGER_MAP["LokiStoreGrowth"] == {"trigger": "T15", "category": "infrastructure"}


def test_alloy_down_maps_to_infrastructure():
    assert ALERT_TRIGGER_MAP["AlloyDown"] == {"trigger": "T16", "category": "infrastructure"}


def test_loki_down_maps_to_infrastructure():
    assert ALERT_TRIGGER_MAP["LokiDown"] == {"trigger": "T17", "category": "infrastructure"}


def test_new_triggers_do_not_collide_with_existing():
    triggers = [v["trigger"] for v in ALERT_TRIGGER_MAP.values()]
    for t in ("T14", "T15", "T16", "T17"):
        assert triggers.count(t) == 1
