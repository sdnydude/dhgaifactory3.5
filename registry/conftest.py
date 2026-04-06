"""
Shared test fixtures for registry API tests.

Handles Prometheus CollectorRegistry cleanup between test sessions
to avoid 'Duplicated timeseries' errors when api.py is re-imported.
"""

import pytest
from prometheus_client import REGISTRY
from prometheus_client.metrics import MetricWrapperBase


@pytest.fixture(autouse=True, scope="session")
def clean_prometheus_registry():
    """Clear any previously registered Prometheus metrics before tests run."""
    collectors_to_remove = []
    for collector in REGISTRY._names_to_collectors.values():
        if isinstance(collector, MetricWrapperBase):
            collectors_to_remove.append(collector)
    for collector in collectors_to_remove:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass
    yield
