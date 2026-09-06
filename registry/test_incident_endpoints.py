"""
Incident Endpoints Tests
========================
Tests for incident API routes: CRUD, route ordering, validation, filters.

Run with: pytest registry/test_incident_endpoints.py -v
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


# ── Route Ordering ──────────────────────────────────────────────────────

class TestRouteOrdering:
    """Static paths (/stats, /runbooks) must not be swallowed by /{incident_id}."""

    def test_stats_not_matched_as_uuid(self, client):
        """GET /api/incidents/stats should NOT return a UUID parse error."""
        with patch("incident_service.compute_stats") as mock_stats:
            mock_stats.return_value = {
                "total": 0,
                "by_severity": {},
                "by_status": {},
                "by_category": {},
                "avg_ttd_minutes": None,
                "avg_ttm_minutes": None,
                "avg_ttr_minutes": None,
                "top_triggers": [],
            }
            response = client.get("/api/incidents/stats")
            assert response.status_code == 200
            assert "total" in response.json()

    def test_runbooks_not_matched_as_uuid(self, client, mock_db):
        """GET /api/incidents/runbooks should NOT return a UUID parse error."""
        with patch("incident_service.list_runbooks") as mock_list:
            mock_list.return_value = []
            response = client.get("/api/incidents/runbooks")
            assert response.status_code == 200
            assert response.json() == []


# ── Incident CRUD ───────────────────────────────────────────────────────

class TestIncidentCreate:
    def test_create_requires_body(self, client):
        response = client.post("/api/incidents")
        assert response.status_code == 422

    def test_create_rejects_invalid_severity(self, client):
        response = client.post("/api/incidents", json={
            "title": "Test incident for severity",
            "severity": "apocalyptic",
            "category": "infrastructure",
        })
        assert response.status_code == 422

    def test_create_rejects_invalid_category(self, client):
        response = client.post("/api/incidents", json={
            "title": "Test incident for category",
            "severity": "high",
            "category": "nonexistent",
        })
        assert response.status_code == 422

    def test_create_rejects_short_title(self, client):
        response = client.post("/api/incidents", json={
            "title": "Hi",
            "severity": "low",
            "category": "data",
        })
        assert response.status_code == 422

    def test_create_success(self, client, mock_db):
        with patch("incident_service.create_incident") as mock_create:
            fake_id = uuid.uuid4()
            now = datetime.now(timezone.utc)
            mock_create.return_value = MagicMock(
                id=fake_id,
                title="Container crash loop",
                severity="critical",
                status="active",
                category="infrastructure",
                root_cause=None,
                root_cause_category=None,
                impact_summary=None,
                prevention=None,
                trigger_rule="T2",
                affected_services=["dhg-agent"],
                affected_project_ids=None,
                tags=[],
                parent_incident_id=None,
                pipeline_run_id=None,
                system_snapshot=None,
                created_by=None,
                started_at=None,
                detected_at=now,
                mitigated_at=None,
                resolved_at=None,
                created_at=now,
                updated_at=now,
            )

            response = client.post("/api/incidents", json={
                "title": "Container crash loop",
                "severity": "critical",
                "category": "infrastructure",
                "trigger_rule": "T2",
                "affected_services": ["dhg-agent"],
            })
            assert response.status_code == 201
            data = response.json()
            assert data["title"] == "Container crash loop"
            assert data["severity"] == "critical"


class TestIncidentList:
    def test_list_returns_array(self, client, mock_db):
        with patch("incident_service.list_incidents") as mock_list:
            mock_list.return_value = []
            response = client.get("/api/incidents")
            assert response.status_code == 200
            assert response.json() == []

    def test_list_with_status_filter(self, client, mock_db):
        with patch("incident_service.list_incidents") as mock_list:
            mock_list.return_value = []
            response = client.get("/api/incidents?status=active")
            assert response.status_code == 200
            mock_list.assert_called_once()
            call_kwargs = mock_list.call_args
            assert call_kwargs[1]["status"] == "active"

    def test_list_with_severity_filter(self, client, mock_db):
        with patch("incident_service.list_incidents") as mock_list:
            mock_list.return_value = []
            response = client.get("/api/incidents?severity=critical")
            assert response.status_code == 200

    def test_list_with_limit_and_offset(self, client, mock_db):
        with patch("incident_service.list_incidents") as mock_list:
            mock_list.return_value = []
            response = client.get("/api/incidents?limit=10&offset=5")
            assert response.status_code == 200
            call_kwargs = mock_list.call_args
            assert call_kwargs[1]["limit"] == 10
            assert call_kwargs[1]["offset"] == 5


class TestIncidentDetail:
    def test_get_nonexistent_returns_404(self, client, mock_db):
        with patch("incident_service.get_incident") as mock_get:
            mock_get.return_value = None
            fake_id = str(uuid.uuid4())
            response = client.get(f"/api/incidents/{fake_id}")
            assert response.status_code == 404

    def test_get_invalid_uuid_returns_422(self, client):
        response = client.get("/api/incidents/not-a-uuid")
        assert response.status_code == 422


class TestIncidentUpdate:
    def test_update_nonexistent_returns_404(self, client, mock_db):
        with patch("incident_service.update_incident") as mock_update:
            mock_update.return_value = None
            fake_id = str(uuid.uuid4())
            response = client.patch(
                f"/api/incidents/{fake_id}",
                json={"status": "resolved"},
            )
            assert response.status_code == 404

    def test_update_empty_body_returns_400(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        response = client.patch(
            f"/api/incidents/{fake_id}",
            json={},
        )
        assert response.status_code == 400

    def test_update_rejects_extra_fields(self, client):
        fake_id = str(uuid.uuid4())
        response = client.patch(
            f"/api/incidents/{fake_id}",
            json={"nonexistent_field": "value"},
        )
        assert response.status_code == 422


# ── Events ──────────────────────────────────────────────────────────────

class TestEventEndpoints:
    def test_add_event_to_nonexistent_incident_returns_404(self, client, mock_db):
        with patch("incident_service.get_incident") as mock_get:
            mock_get.return_value = None
            fake_id = str(uuid.uuid4())
            response = client.post(
                f"/api/incidents/{fake_id}/events",
                json={
                    "event_type": "symptom",
                    "description": "CPU spike detected on host",
                },
            )
            assert response.status_code == 404

    def test_add_event_rejects_invalid_type(self, client, mock_db):
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/incidents/{fake_id}/events",
            json={
                "event_type": "invalid_type",
                "description": "This should fail validation",
            },
        )
        assert response.status_code == 422

    def test_add_event_rejects_short_description(self, client):
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/incidents/{fake_id}/events",
            json={
                "event_type": "symptom",
                "description": "Hi",
            },
        )
        assert response.status_code == 422

    def test_list_events_for_nonexistent_incident_returns_404(self, client, mock_db):
        with patch("incident_service.get_incident") as mock_get:
            mock_get.return_value = None
            fake_id = str(uuid.uuid4())
            response = client.get(f"/api/incidents/{fake_id}/events")
            assert response.status_code == 404


# ── Actions ─────────────────────────────────────────────────────────────

class TestActionEndpoints:
    def test_add_action_to_nonexistent_incident_returns_404(self, client, mock_db):
        with patch("incident_service.get_incident") as mock_get:
            mock_get.return_value = None
            fake_id = str(uuid.uuid4())
            response = client.post(
                f"/api/incidents/{fake_id}/actions",
                json={
                    "action_type": "diagnostic",
                    "description": "Checked container logs for errors",
                },
            )
            assert response.status_code == 404

    def test_add_action_rejects_invalid_type(self, client):
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/incidents/{fake_id}/actions",
            json={
                "action_type": "nuke_it",
                "description": "Invalid action type should fail",
            },
        )
        assert response.status_code == 422


# ── Postmortems ─────────────────────────────────────────────────────────

class TestPostmortemEndpoints:
    def test_get_postmortem_not_found(self, client, mock_db):
        with patch("incident_service.get_postmortem") as mock_get:
            mock_get.return_value = None
            fake_id = str(uuid.uuid4())
            response = client.get(f"/api/incidents/{fake_id}/postmortem")
            assert response.status_code == 404

    def test_create_postmortem_for_nonexistent_incident(self, client, mock_db):
        with patch("incident_service.get_incident") as mock_get:
            mock_get.return_value = None
            fake_id = str(uuid.uuid4())
            response = client.post(
                f"/api/incidents/{fake_id}/postmortem",
                json={"summary": "Root cause was config error"},
            )
            assert response.status_code == 404

    def test_update_postmortem_empty_body_returns_400(self, client, mock_db):
        with patch("incident_service.get_postmortem") as mock_get:
            mock_get.return_value = MagicMock()
            fake_id = str(uuid.uuid4())
            response = client.patch(
                f"/api/incidents/{fake_id}/postmortem",
                json={},
            )
            assert response.status_code == 400


# ── Runbooks ────────────────────────────────────────────────────────────

class TestRunbookEndpoints:
    def test_list_runbooks(self, client, mock_db):
        with patch("incident_service.list_runbooks") as mock_list:
            mock_list.return_value = []
            response = client.get("/api/incidents/runbooks")
            assert response.status_code == 200

    def test_create_runbook_requires_body(self, client):
        response = client.post("/api/incidents/runbooks")
        assert response.status_code == 422

    def test_create_runbook_rejects_invalid_severity(self, client):
        response = client.post("/api/incidents/runbooks", json={
            "trigger_rule": "T99",
            "title": "Test runbook",
            "severity": "catastrophic",
        })
        assert response.status_code == 422

    def test_update_runbook_empty_body_returns_400(self, client, mock_db):
        response = client.patch(
            "/api/incidents/runbooks/T1",
            json={},
        )
        assert response.status_code == 400


# ── Stats ───────────────────────────────────────────────────────────────

class TestStatsEndpoint:
    def test_stats_default_params(self, client, mock_db):
        with patch("incident_service.compute_stats") as mock_stats:
            mock_stats.return_value = {
                "total": 5,
                "by_severity": {"critical": 2, "high": 3},
                "by_status": {"active": 3, "resolved": 2},
                "by_category": {"infrastructure": 5},
                "avg_ttd_minutes": 3.5,
                "avg_ttm_minutes": 12.0,
                "avg_ttr_minutes": 45.0,
                "top_triggers": [{"trigger_rule": "T2", "count": 3}],
            }
            response = client.get("/api/incidents/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 5
            assert data["avg_ttd_minutes"] == 3.5
            assert len(data["top_triggers"]) == 1

    def test_stats_with_filters(self, client, mock_db):
        with patch("incident_service.compute_stats") as mock_stats:
            mock_stats.return_value = {
                "total": 0,
                "by_severity": {},
                "by_status": {},
                "by_category": {},
                "avg_ttd_minutes": None,
                "avg_ttm_minutes": None,
                "avg_ttr_minutes": None,
                "top_triggers": [],
            }
            response = client.get("/api/incidents/stats?days=7&severity=critical")
            assert response.status_code == 200
            call_kwargs = mock_stats.call_args[1]
            assert call_kwargs["severity"] == "critical"

    def test_stats_rejects_invalid_days(self, client):
        response = client.get("/api/incidents/stats?days=0")
        assert response.status_code == 422

    def test_stats_rejects_days_over_365(self, client):
        response = client.get("/api/incidents/stats?days=400")
        assert response.status_code == 422


# ── Link Child ──────────────────────────────────────────────────────────

class TestLinkChild:
    def test_link_child_not_found_returns_404(self, client, mock_db):
        with patch("incident_service.link_child") as mock_link:
            mock_link.return_value = False
            parent_id = str(uuid.uuid4())
            child_id = str(uuid.uuid4())
            response = client.post(f"/api/incidents/{parent_id}/link/{child_id}")
            assert response.status_code == 404

    def test_link_child_success_returns_204(self, client, mock_db):
        with patch("incident_service.link_child") as mock_link:
            mock_link.return_value = True
            parent_id = str(uuid.uuid4())
            child_id = str(uuid.uuid4())
            response = client.post(f"/api/incidents/{parent_id}/link/{child_id}")
            assert response.status_code == 204


# ── Pagination limit ────────────────────────────────────────────────────


class TestListLimit:
    """?limit=500 returned nothing because the route capped limit at 200."""

    def test_limit_500_is_accepted(self, client):
        with patch("incident_service.list_incidents", return_value=[]) as mock_list:
            response = client.get("/api/incidents?limit=500")
        assert response.status_code == 200
        assert mock_list.call_args.kwargs["limit"] == 500

    def test_limit_1000_is_accepted(self, client):
        with patch("incident_service.list_incidents", return_value=[]):
            assert client.get("/api/incidents?limit=1000").status_code == 200

    def test_limit_above_cap_is_rejected(self, client):
        assert client.get("/api/incidents?limit=1001").status_code == 422

    def test_days_filter_is_passed_through_as_since(self, client):
        with patch("incident_service.list_incidents", return_value=[]) as mock_list:
            response = client.get("/api/incidents?status=active&days=30")
        assert response.status_code == 200
        assert mock_list.call_args.kwargs["since"] is not None

    def test_list_is_unwindowed_without_days(self, client):
        with patch("incident_service.list_incidents", return_value=[]) as mock_list:
            client.get("/api/incidents?status=active")
        assert mock_list.call_args.kwargs["since"] is None


# ── Alertmanager webhook deduplication ──────────────────────────────────


def _alert_payload(alertname="MemregDLQBacklog", service="memreg", instance="10.0.0.251:8011"):
    return {
        "version": "4",
        "groupKey": "{}:{alertname=\"%s\"}" % alertname,
        "status": "firing",
        "receiver": "registry",
        "alerts": [{
            "status": "firing",
            "labels": {
                "alertname": alertname,
                "severity": "critical",
                "name": service,
                "instance": instance,
            },
            "annotations": {"summary": f"{alertname} is firing"},
            "startsAt": "2026-09-05T00:00:00Z",
        }],
    }


class TestAlertmanagerWebhookDedup:
    def test_fingerprint_is_stable_across_identical_payloads(self, client):
        with patch("incident_service.create_incident") as mock_create:
            mock_create.return_value = MagicMock()
            client.post("/webhooks/alertmanager", json=_alert_payload())
            client.post("/webhooks/alertmanager", json=_alert_payload())

        fingerprints = [c.kwargs["fingerprint"] for c in mock_create.call_args_list]
        assert len(fingerprints) == 2
        assert fingerprints[0] == fingerprints[1]
        assert fingerprints[0] == "MemregDLQBacklog|memreg|10.0.0.251:8011"

    def test_fingerprint_differs_per_instance(self, client):
        with patch("incident_service.create_incident") as mock_create:
            mock_create.return_value = MagicMock()
            client.post("/webhooks/alertmanager", json=_alert_payload(instance="a:1"))
            client.post("/webhooks/alertmanager", json=_alert_payload(instance="b:2"))

        fingerprints = [c.kwargs["fingerprint"] for c in mock_create.call_args_list]
        assert fingerprints[0] != fingerprints[1]

    def test_two_identical_webhooks_create_one_incident(self, client, mock_db):
        """End-to-end through the real create_incident/find_duplicate path.

        MemregDLQBacklog has no entry in ALERT_TRIGGER_MAP, so trigger_rule is
        None — the old trigger-keyed dedup bailed out and created a fresh
        incident on every re-fire (103 of them in production).
        """
        from models import Incident

        open_incidents: list = []

        def query_side_effect(*_args, **_kwargs):
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            q.all.return_value = list(open_incidents)
            q.first.return_value = open_incidents[0] if open_incidents else None
            return q

        def add_side_effect(obj):
            if isinstance(obj, Incident):
                obj.status = "active"
                obj.occurrence_count = 1
                open_incidents.append(obj)

        mock_db.query.side_effect = query_side_effect
        mock_db.add.side_effect = add_side_effect

        with patch("incident_service.capture_system_snapshot", return_value={}), \
             patch("incident_service.enrich_snapshot_with_db"), \
             patch("incident_service.find_parent_incident", return_value=None):
            client.post("/webhooks/alertmanager", json=_alert_payload())
            client.post("/webhooks/alertmanager", json=_alert_payload())

        assert len(open_incidents) == 1
        assert open_incidents[0].occurrence_count == 2
