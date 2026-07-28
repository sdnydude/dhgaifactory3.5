"""Tests for burndown-items agent tracking fields.

Covers the three columns added for agent-driven walkthroughs:
  - agent_findings (Text)
  - agent_actions  (Text)
  - resolution     (String, enum: open/investigating/fixed/deferred/wont_fix)

Run with:
    pytest registry/test_burndown.py -v
"""
import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from burndown_schemas import BurndownItemUpdate, BurndownItemResponse


def _mock_item_row(**overrides):
    """Build a MagicMock that looks like a BurndownItem ORM row."""
    defaults = dict(
        id=uuid.uuid4(),
        list_id=uuid.uuid4(),
        seq=1,
        feature="Home / Dashboard",
        url="https://example.com/home",
        what_to_check="loads",
        status="not_started",
        severity="none",
        user_comment=None,
        console_errors=None,
        assigned_to=None,
        fixed_in_commit=None,
        checked_at=None,
        agent_findings=None,
        agent_actions=None,
        resolution="open",
        meta_data=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    row = MagicMock()
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


class TestBurndownAgentSchemas:
    def test_update_accepts_agent_fields(self):
        upd = BurndownItemUpdate(
            agent_findings="Porter chat 404s on /porter",
            agent_actions="traced to api.ts:42; filed bug 770aa950",
            resolution="fixed",
        )
        assert upd.agent_findings == "Porter chat 404s on /porter"
        assert upd.agent_actions.startswith("traced")
        assert upd.resolution == "fixed"

    def test_response_exposes_agent_fields(self):
        row = _mock_item_row(
            agent_findings="empty-state only (no inventory)",
            agent_actions="deferred to data-seeded account",
            resolution="deferred",
        )
        resp = BurndownItemResponse.model_validate(row)
        assert resp.agent_findings == "empty-state only (no inventory)"
        assert resp.agent_actions == "deferred to data-seeded account"
        assert resp.resolution == "deferred"


class TestBurndownAgentEndpoint:
    @patch("burndown_endpoints.svc")
    def test_patch_accepts_agent_fields(self, mock_svc, client):
        row = _mock_item_row(agent_findings="f", agent_actions="a", resolution="fixed")
        mock_svc.update_item.return_value = row

        r = client.patch(
            f"/api/burndown-items/{row.id}",
            json={"agent_findings": "f", "agent_actions": "a", "resolution": "fixed"},
        )

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["agent_findings"] == "f"
        assert body["agent_actions"] == "a"
        assert body["resolution"] == "fixed"

    @patch("burndown_endpoints.svc")
    def test_patch_invalid_resolution_returns_422(self, mock_svc, client):
        mock_svc.update_item.return_value = _mock_item_row()

        r = client.patch(
            f"/api/burndown-items/{uuid.uuid4()}",
            json={"resolution": "banana"},
        )

        assert r.status_code == 422
