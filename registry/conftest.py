"""
Shared test fixtures for registry API tests.

Handles:
- Prometheus CollectorRegistry cleanup between test sessions
- FastAPI dependency override for get_db (mock database)
- sys.path setup so registry modules import correctly
"""

import sys
import os
import pytest
from unittest.mock import MagicMock
from prometheus_client import REGISTRY
from prometheus_client.metrics import MetricWrapperBase

sys.path.insert(0, os.path.dirname(__file__))


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


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.__enter__ = MagicMock(return_value=db)
    db.__exit__ = MagicMock(return_value=False)
    return db


@pytest.fixture
def client(mock_db):
    """Create a test client with the database dependency overridden."""
    from database import get_db
    from api import app

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
