"""Tests for agent session update (PUT) — idempotent re-capture support.

The Stop hook fires multiple times per session; the second and later
captures must update the existing row instead of dying on 409.
"""
from unittest.mock import MagicMock

import agent_sessions_service as svc
from agent_sessions_schemas import AgentSessionCreate


def _payload(**overrides):
    base = dict(
        session_id="sess-1",
        project="cavemem",
        branch="main",
        source="claude-code",
        model="claude-fable-5",
        summary="did things",
        tldr="things",
        commits=["abc123"],
        files_changed=2,
        ended_at="2026-07-07T21:44:52Z",
    )
    base.update(overrides)
    return AgentSessionCreate(**base)


class TestUpdateAgentSessionService:
    def test_updates_existing_row_fields(self, mock_db):
        row = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = row

        result = svc.update_agent_session(mock_db, "sess-1", _payload())

        assert result is row
        assert row.summary == "did things"
        assert row.commits == ["abc123"]
        mock_db.commit.assert_called_once()

    def test_empty_values_do_not_overwrite(self, mock_db):
        row = MagicMock()
        row.summary = "earlier summary"
        row.commits = ["earlier"]
        mock_db.query.return_value.filter.return_value.first.return_value = row

        svc.update_agent_session(
            mock_db, "sess-1", _payload(summary="", tldr=None, commits=[]),
        )

        assert row.summary == "earlier summary"
        assert row.commits == ["earlier"]

    def test_unknown_session_returns_none(self, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = svc.update_agent_session(mock_db, "nope", _payload())

        assert result is None
        mock_db.commit.assert_not_called()


class TestUpdateAgentSessionEndpoint:
    def test_put_unknown_session_returns_404(self, client, mock_db):
        mock_db.query.return_value.filter.return_value.first.return_value = None

        resp = client.put(
            "/api/agent-sessions/nope", json=_payload().model_dump(mode="json"),
        )

        assert resp.status_code == 404
