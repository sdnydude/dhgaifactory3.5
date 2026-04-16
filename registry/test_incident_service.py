"""
Incident Service Tests
======================
Unit tests for incident_service.py: dedup, cascade, CRUD, stats.

Run with: pytest registry/test_incident_service.py -v
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import incident_service as svc


# ── Helpers ─────────────────────────────────────────────────────────────

def make_incident(**overrides):
    """Create a mock Incident object with sensible defaults."""
    now = datetime.now(timezone.utc)
    inc = MagicMock()
    inc.id = overrides.get("id", uuid.uuid4())
    inc.title = overrides.get("title", "Test incident")
    inc.severity = overrides.get("severity", "high")
    inc.status = overrides.get("status", "active")
    inc.category = overrides.get("category", "infrastructure")
    inc.trigger_rule = overrides.get("trigger_rule", "T1")
    inc.affected_services = overrides.get("affected_services", ["svc-a"])
    inc.parent_incident_id = overrides.get("parent_incident_id", None)
    inc.impact_summary = overrides.get("impact_summary", None)
    inc.created_at = overrides.get("created_at", now)
    inc.detected_at = overrides.get("detected_at", now)
    inc.started_at = overrides.get("started_at", None)
    inc.mitigated_at = overrides.get("mitigated_at", None)
    inc.resolved_at = overrides.get("resolved_at", None)
    return inc


def mock_query_chain(db, results):
    """Wire up db.query(...).filter(...).order_by(...).all() → results."""
    q = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.order_by.return_value = q
    q.all.return_value = results
    q.first.return_value = results[0] if results else None
    q.offset.return_value = q
    q.limit.return_value = q
    return q


# ── Deduplication ───────────────────────────────────────────────────────

class TestFindDuplicate:
    def test_returns_none_when_no_trigger_rule(self):
        db = MagicMock()
        result = svc.find_duplicate(db, trigger_rule=None, affected_services=["svc-a"])
        assert result is None
        db.query.assert_not_called()

    def test_returns_none_when_no_matching_incident(self):
        db = MagicMock()
        mock_query_chain(db, [])
        result = svc.find_duplicate(db, trigger_rule="T1", affected_services=["svc-a"])
        assert result is None

    def test_returns_duplicate_when_service_overlaps(self):
        db = MagicMock()
        existing = make_incident(trigger_rule="T1", affected_services=["svc-a", "svc-b"])
        mock_query_chain(db, [existing])
        result = svc.find_duplicate(db, trigger_rule="T1", affected_services=["svc-a"])
        assert result is existing

    def test_returns_none_when_services_dont_overlap(self):
        db = MagicMock()
        existing = make_incident(trigger_rule="T1", affected_services=["svc-b"])
        mock_query_chain(db, [existing])
        result = svc.find_duplicate(db, trigger_rule="T1", affected_services=["svc-a"])
        assert result is None


# ── Cascade Detection ───────────────────────────────────────────────────

class TestFindParentIncident:
    def test_returns_none_when_no_candidates(self):
        db = MagicMock()
        mock_query_chain(db, [])
        result = svc.find_parent_incident(db, affected_services=["svc-a"])
        assert result is None

    def test_returns_parent_with_shared_service(self):
        db = MagicMock()
        parent = make_incident(affected_services=["svc-a", "svc-b"], parent_incident_id=None)
        mock_query_chain(db, [parent])
        result = svc.find_parent_incident(db, affected_services=["svc-a"])
        assert result is parent

    def test_skips_exclude_id(self):
        db = MagicMock()
        q = mock_query_chain(db, [])
        my_id = uuid.uuid4()
        svc.find_parent_incident(db, affected_services=["svc-a"], exclude_id=my_id)
        # Should have called filter at least twice (base filters + exclude)
        assert q.filter.call_count >= 2


# ── Create Incident ─────────────────────────────────────────────────────

class TestCreateIncident:
    @patch("incident_service.find_duplicate", return_value=None)
    @patch("incident_service.capture_system_snapshot", return_value={"host": {}})
    @patch("incident_service.enrich_snapshot_with_db")
    @patch("incident_service.find_parent_incident", return_value=None)
    def test_creates_new_incident(self, _parent, _enrich, _snap, _dedup):
        db = MagicMock()
        db.flush = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()

        svc.create_incident(
            db,
            title="Test crash",
            severity="critical",
            category="infrastructure",
            trigger_rule="T2",
            affected_services=["dhg-agent"],
        )

        db.add.assert_called()
        db.commit.assert_called()
        assert db.add.call_count == 2  # incident + initial event

    @patch("incident_service.find_duplicate")
    def test_dedup_returns_existing_incident(self, mock_dedup):
        db = MagicMock()
        existing = make_incident(title="Existing")
        mock_dedup.return_value = existing

        result = svc.create_incident(
            db,
            title="Duplicate trigger",
            severity="high",
            category="infrastructure",
            trigger_rule="T1",
            affected_services=["svc-a"],
        )

        assert result is existing
        # Should add a dedup event to the existing incident
        db.add.assert_called_once()

    @patch("incident_service.find_duplicate", return_value=None)
    @patch("incident_service.capture_system_snapshot", return_value={})
    @patch("incident_service.enrich_snapshot_with_db")
    @patch("incident_service.find_parent_incident")
    def test_cascade_links_to_parent(self, mock_parent, _enrich, _snap, _dedup):
        db = MagicMock()

        parent = make_incident(title="Parent", impact_summary=None)
        mock_parent.return_value = parent

        svc.create_incident(
            db,
            title="Child crash",
            severity="high",
            category="infrastructure",
            affected_services=["svc-a"],
        )

        # Parent should have impact_summary updated
        assert parent.impact_summary is not None

    @patch("incident_service.find_duplicate", return_value=None)
    @patch("incident_service.capture_system_snapshot", return_value={})
    @patch("incident_service.enrich_snapshot_with_db")
    @patch("incident_service.find_parent_incident", return_value=None)
    def test_skips_snapshot_when_provided(self, _parent, _enrich, mock_snap, _dedup):
        db = MagicMock()

        svc.create_incident(
            db,
            title="Manual incident",
            severity="low",
            category="data",
            system_snapshot={"custom": True},
        )

        mock_snap.assert_not_called()


# ── Update Incident ─────────────────────────────────────────────────────

class TestUpdateIncident:
    def test_returns_none_for_nonexistent(self):
        db = MagicMock()
        mock_query_chain(db, [])
        result = svc.update_incident(db, uuid.uuid4(), status="resolved")
        assert result is None

    def test_auto_transitions_to_resolved(self):
        db = MagicMock()
        inc = make_incident(status="active")
        mock_query_chain(db, [inc])

        now = datetime.now(timezone.utc)
        svc.update_incident(db, inc.id, resolved_at=now)
        assert inc.status == "resolved"

    def test_auto_transitions_to_mitigated(self):
        db = MagicMock()
        inc = make_incident(status="active")
        mock_query_chain(db, [inc])

        now = datetime.now(timezone.utc)
        svc.update_incident(db, inc.id, mitigated_at=now)
        assert inc.status == "mitigated"


# ── Link Child ──────────────────────────────────────────────────────────

class TestLinkChild:
    def test_returns_false_when_child_not_found(self):
        db = MagicMock()
        mock_query_chain(db, [])
        result = svc.link_child(db, uuid.uuid4(), uuid.uuid4())
        assert result is False

    def test_links_child_to_parent(self):
        db = MagicMock()
        child = make_incident()
        mock_query_chain(db, [child])
        parent_id = uuid.uuid4()

        result = svc.link_child(db, parent_id, child.id)
        assert result is True
        assert child.parent_incident_id == parent_id


# ── Compute Stats ───────────────────────────────────────────────────────

class TestComputeStats:
    def test_empty_result(self):
        db = MagicMock()
        mock_query_chain(db, [])

        stats = svc.compute_stats(db)
        assert stats["total"] == 0
        assert stats["by_severity"] == {}
        assert stats["by_status"] == {}
        assert stats["avg_ttd_minutes"] is None
        assert stats["avg_ttm_minutes"] is None
        assert stats["avg_ttr_minutes"] is None
        assert stats["top_triggers"] == []

    def test_counts_by_severity_and_status(self):
        db = MagicMock()

        incidents = [
            make_incident(severity="critical", status="active", category="infrastructure"),
            make_incident(severity="critical", status="resolved", category="pipeline"),
            make_incident(severity="high", status="active", category="infrastructure"),
        ]
        mock_query_chain(db, incidents)

        stats = svc.compute_stats(db)
        assert stats["total"] == 3
        assert stats["by_severity"]["critical"] == 2
        assert stats["by_severity"]["high"] == 1
        assert stats["by_status"]["active"] == 2
        assert stats["by_status"]["resolved"] == 1
        assert stats["by_category"]["infrastructure"] == 2

    def test_sla_metrics_computed(self):
        db = MagicMock()

        now = datetime.now(timezone.utc)
        inc = make_incident(
            started_at=now - timedelta(minutes=10),
            detected_at=now - timedelta(minutes=5),
            mitigated_at=now - timedelta(minutes=2),
            resolved_at=now,
        )
        mock_query_chain(db, [inc])

        stats = svc.compute_stats(db)
        assert stats["avg_ttd_minutes"] == 5.0  # 10min - 5min
        assert stats["avg_ttm_minutes"] == 3.0  # 5min - 2min
        assert stats["avg_ttr_minutes"] == 5.0  # 5min - 0min

    def test_top_triggers_sorted(self):
        db = MagicMock()

        incidents = [
            make_incident(trigger_rule="T2"),
            make_incident(trigger_rule="T2"),
            make_incident(trigger_rule="T2"),
            make_incident(trigger_rule="T1"),
        ]
        mock_query_chain(db, incidents)

        stats = svc.compute_stats(db)
        assert len(stats["top_triggers"]) == 2
        assert stats["top_triggers"][0]["trigger_rule"] == "T2"
        assert stats["top_triggers"][0]["count"] == 3
        assert stats["top_triggers"][1]["trigger_rule"] == "T1"

    def test_null_triggers_excluded(self):
        db = MagicMock()

        incidents = [
            make_incident(trigger_rule=None),
            make_incident(trigger_rule="T1"),
        ]
        mock_query_chain(db, incidents)

        stats = svc.compute_stats(db)
        assert len(stats["top_triggers"]) == 1
        assert stats["top_triggers"][0]["trigger_rule"] == "T1"


# ── Postmortem ──────────────────────────────────────────────────────────

class TestPostmortem:
    def test_creates_new_postmortem(self):
        db = MagicMock()
        inc_id = uuid.uuid4()

        # No existing postmortem
        mock_query_chain(db, [])
        svc.create_or_update_postmortem(db, inc_id, summary="Root cause was config error")

        db.add.assert_called_once()
        db.commit.assert_called()

    def test_transitions_resolved_to_postmortem(self):
        db = MagicMock()
        inc_id = uuid.uuid4()
        incident = make_incident(id=inc_id, status="resolved")

        # First call: get_postmortem returns None, second call: get_incident returns incident
        call_count = [0]
        def side_effect(*args, **kwargs):
            q = MagicMock()
            q.filter.return_value = q
            if call_count[0] == 0:
                q.first.return_value = None  # no existing postmortem
                call_count[0] += 1
            else:
                q.first.return_value = incident  # get_incident
            return q

        db.query.side_effect = side_effect

        svc.create_or_update_postmortem(db, inc_id, summary="RCA complete")
        assert incident.status == "postmortem"
