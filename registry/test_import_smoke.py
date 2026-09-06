"""Import smoke tests for the CME SLA notification modules.

Regression guard: notification_service and timeout_handler imported
``langsmith``, which is not in registry/requirements.txt and is not installed
in the dhg-registry-api image. Both modules therefore raised
ModuleNotFoundError at import time, so every CME SLA timeout, escalation and
HOLD notification was dead. LangSmith is deprecated here — the dependency must
not come back.
"""
import importlib

import pytest

SLA_MODULES = ["notification_service", "timeout_handler"]


@pytest.mark.parametrize("module_name", SLA_MODULES)
def test_sla_module_imports(module_name):
    """The module must import cleanly with only requirements.txt installed."""
    assert importlib.import_module(module_name) is not None
