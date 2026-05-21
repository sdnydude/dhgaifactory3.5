"""
CME Review Service Tests
========================
Unit tests for cme_review_service.py: reviewer CRUD, assignment workflow,
review submission, and query helpers.

Run with: pytest registry/test_cme_review_service.py -v
"""

import os
import sys
import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cme_review_service as svc


# ── Helpers ─────────────────────────────────────────────────────────────


def make_reviewer(**overrides):
    """Create a mock CMEReviewerConfig with sensible defaults."""
    r = MagicMock()
    r.id = overrides.get("id", uuid.uuid4())
    r.email = overrides.get("email", "reviewer@example.com")
    r.display_name = overrides.get("display_name", "Test Reviewer")
    r.is_active = overrides.get("is_active", True)
    r.notify_email = overrides.get("notify_email", True)
    r.notify_google_chat = overrides.get("notify_google_chat", False)
    r.google_chat_webhook_url = overrides.get("google_chat_webhook_url", None)
    r.max_concurrent_reviews = overrides.get("max_concurrent_reviews", 5)
    return r


def make_assignment(**overrides):
    """Create a mock CMEReviewAssignment with sensible defaults."""
    a = MagicMock()
    a.id = overrides.get("id", uuid.uuid4())
    a.project_id = overrides.get("project_id", uuid.uuid4())
    a.reviewer_id = overrides.get("reviewer_id", uuid.uuid4())
    a.reviewer_order = overrides.get("reviewer_order", 1)
    a.status = overrides.get("status", "active")
    a.assigned_at = overrides.get("assigned_at", datetime(2026, 5, 21, 12, 0, 0))
    a.sla_deadline = overrides.get("sla_deadline", datetime(2026, 5, 22, 12, 0, 0))
    a.completed_at = overrides.get("completed_at", None)
    a.decision = overrides.get("decision", None)
    a.notes = overrides.get("notes", None)
    a.annotations = overrides.get("annotations", [])
    return a


def make_project(**overrides):
    """Create a mock CMEProject with sensible defaults."""
    p = MagicMock()
    p.id = overrides.get("id", uuid.uuid4())
    p.name = overrides.get("name", "Test Grant Project")
    p.status = overrides.get("status", "processing")
    p.human_review_status = overrides.get("human_review_status", None)
    p.human_review_notes = overrides.get("human_review_notes", None)
    p.reviewed_at = overrides.get("reviewed_at", None)
    p.completed_at = overrides.get("completed_at", None)
    return p


def mock_query_chain(db, results):
    """Wire up db.query(...).filter(...).order_by(...).all() -> results."""
    q = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.join.return_value = q
    q.order_by.return_value = q
    q.all.return_value = results
    q.first.return_value = results[0] if results else None
    return q


# ── list_reviewers ─────────────────────────────────────────────────────


class TestListReviewers:
    def test_active_only_true_applies_filter(self):
        db = MagicMock()
        reviewers = [make_reviewer(), make_reviewer(email="r2@example.com")]
        q = mock_query_chain(db, reviewers)

        result = svc.list_reviewers(db, active_only=True)

        assert result == reviewers
        q.filter.assert_called_once()

    def test_active_only_false_returns_all(self):
        db = MagicMock()
        active = make_reviewer(email="a@x.com", is_active=True)
        inactive = make_reviewer(email="b@x.com", is_active=False)
        q = mock_query_chain(db, [active, inactive])

        result = svc.list_reviewers(db, active_only=False)

        assert len(result) == 2
        q.filter.assert_not_called()

    def test_empty_list_returns_empty(self):
        db = MagicMock()
        mock_query_chain(db, [])

        result = svc.list_reviewers(db, active_only=True)

        assert result == []


# ── create_reviewer ────────────────────────────────────────────────────


class TestCreateReviewer:
    def test_creates_new_reviewer(self):
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = None  # No existing reviewer

        svc.create_reviewer(
            db,
            email="new@example.com",
            display_name="New Reviewer",
            notify_email=True,
            notify_google_chat=True,
            google_chat_webhook_url="https://chat.google.com/hook",
            max_concurrent_reviews=3,
        )

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()
        added_obj = db.add.call_args[0][0]
        assert added_obj.email == "new@example.com"
        assert added_obj.display_name == "New Reviewer"
        assert added_obj.max_concurrent_reviews == 3
        assert added_obj.notify_google_chat is True

    def test_duplicate_email_returns_none(self):
        db = MagicMock()
        existing = make_reviewer(email="dup@example.com")
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = existing

        result = svc.create_reviewer(db, email="dup@example.com", display_name="Dup")

        assert result is None
        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_default_parameters(self):
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = None

        svc.create_reviewer(db, email="default@example.com", display_name="Default")

        added_obj = db.add.call_args[0][0]
        assert added_obj.notify_email is True
        assert added_obj.notify_google_chat is False
        assert added_obj.google_chat_webhook_url is None
        assert added_obj.max_concurrent_reviews == 5


# ── deactivate_reviewer ───────────────────────────────────────────────


class TestDeactivateReviewer:
    def test_deactivates_existing_reviewer(self):
        db = MagicMock()
        reviewer = make_reviewer(is_active=True)
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = reviewer

        result = svc.deactivate_reviewer(db, str(reviewer.id))

        assert result is reviewer
        assert reviewer.is_active is False
        db.commit.assert_called_once()

    def test_returns_none_when_not_found(self):
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = None

        result = svc.deactivate_reviewer(db, str(uuid.uuid4()))

        assert result is None
        db.commit.assert_not_called()


# ── submit_for_review ──────────────────────────────────────────────────


class TestSubmitForReview:
    def test_creates_assignments_for_all_reviewers(self):
        db = MagicMock()
        project = make_project()
        r1 = make_reviewer(email="r1@example.com")
        r2 = make_reviewer(email="r2@example.com")

        # Each db.query(...).filter(...).first() call returns a different reviewer
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.side_effect = [r1, r2]

        result = svc.submit_for_review(db, project, ["r1@example.com", "r2@example.com"])

        assert len(result) == 2
        assert result[0]["email"] == "r1@example.com"
        assert result[0]["order"] == 1
        assert result[0]["status"] == "active"
        assert result[1]["email"] == "r2@example.com"
        assert result[1]["order"] == 2
        assert result[1]["status"] == "pending"
        assert db.add.call_count == 2
        db.commit.assert_called_once()

    def test_sets_project_to_review_status(self):
        db = MagicMock()
        project = make_project(status="processing")
        r1 = make_reviewer(email="r1@example.com")
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = r1

        svc.submit_for_review(db, project, ["r1@example.com"])

        assert project.status == "review"
        assert project.human_review_status == "pending"

    def test_raises_for_unknown_reviewer(self):
        db = MagicMock()
        project = make_project()
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = None  # Not found

        with pytest.raises(ValueError, match="Reviewer not found or inactive"):
            svc.submit_for_review(db, project, ["ghost@example.com"])

        db.commit.assert_not_called()

    def test_raises_for_inactive_reviewer(self):
        """An inactive reviewer should not be found by the active filter."""
        db = MagicMock()
        project = make_project()
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = None  # Filter includes is_active==True, so inactive returns None

        with pytest.raises(ValueError, match="Reviewer not found or inactive"):
            svc.submit_for_review(db, project, ["inactive@example.com"])

    def test_single_reviewer_is_active_immediately(self):
        db = MagicMock()
        project = make_project()
        r1 = make_reviewer(email="solo@example.com")
        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.first.return_value = r1

        result = svc.submit_for_review(db, project, ["solo@example.com"])

        assert len(result) == 1
        assert result[0]["status"] == "active"
        assert result[0]["order"] == 1


# ── get_review_status ──────────────────────────────────────────────────


class TestGetReviewStatus:
    def test_returns_assignments_ordered(self):
        db = MagicMock()
        pid = uuid.uuid4()
        a1 = make_assignment(project_id=pid, reviewer_order=1)
        a2 = make_assignment(project_id=pid, reviewer_order=2)
        mock_query_chain(db, [a1, a2])

        result = svc.get_review_status(db, str(pid))

        assert result == [a1, a2]
        assert len(result) == 2

    def test_returns_empty_for_unknown_project(self):
        db = MagicMock()
        mock_query_chain(db, [])

        result = svc.get_review_status(db, str(uuid.uuid4()))

        assert result == []


# ── submit_review ──────────────────────────────────────────────────────


class TestSubmitReview:
    def _setup_submit(self, db, assignment, next_assignment=None):
        """Configure the mock DB for submit_review calls.

        submit_review calls db.query(...).join(...).filter(...).first() for the
        active assignment, then optionally a second query chain for the next
        pending assignment.
        """
        q1 = MagicMock()
        q2 = MagicMock()

        # Track which query call we're on
        call_count = {"n": 0}

        def side_effect_query(*_a):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return q1
            return q2

        db.query.side_effect = side_effect_query

        # First query chain: find the active assignment
        q1.join.return_value = q1
        q1.filter.return_value = q1
        q1.first.return_value = assignment

        # Second query chain: find next pending assignment
        q2.filter.return_value = q2
        q2.order_by.return_value = q2
        q2.first.return_value = next_assignment

        return q1, q2

    def test_approved_with_next_reviewer(self):
        db = MagicMock()
        project = make_project(status="review")
        assignment = make_assignment(status="active")
        next_asgn = make_assignment(status="pending", reviewer_order=2)
        self._setup_submit(db, assignment, next_assignment=next_asgn)

        result = svc.submit_review(db, project, "reviewer@example.com", "approved")

        assert result is not None
        assert assignment.status == "approved"
        assert assignment.decision == "approved"
        assert assignment.completed_at is not None
        assert next_asgn.status == "active"
        assert next_asgn.assigned_at is not None
        assert next_asgn.sla_deadline is not None
        # Project stays in review when there's a next reviewer
        assert project.status == "review"
        db.commit.assert_called_once()

    def test_approved_final_reviewer_completes_project(self):
        db = MagicMock()
        project = make_project(status="review")
        assignment = make_assignment(status="active")
        self._setup_submit(db, assignment, next_assignment=None)

        result = svc.submit_review(db, project, "reviewer@example.com", "approved")

        assert result is not None
        assert project.human_review_status == "approved"
        assert project.status == "complete"
        assert project.reviewed_at is not None
        assert project.completed_at is not None
        db.commit.assert_called_once()

    def test_revision_requested_sets_project_status(self):
        db = MagicMock()
        project = make_project(status="review")
        assignment = make_assignment(status="active")
        # For revision_requested, only the first query chain is used
        q = MagicMock()
        db.query.return_value = q
        q.join.return_value = q
        q.filter.return_value = q
        q.first.return_value = assignment

        result = svc.submit_review(
            db, project, "reviewer@example.com",
            "revision_requested", notes="Section 3 needs citations",
        )

        assert result is not None
        assert assignment.status == "revision_requested"
        assert assignment.decision == "revision_requested"
        assert assignment.notes == "Section 3 needs citations"
        assert project.human_review_status == "revision_requested"
        assert project.human_review_notes == "Section 3 needs citations"
        assert project.status == "review"
        db.commit.assert_called_once()

    def test_returns_none_when_no_active_assignment(self):
        db = MagicMock()
        project = make_project()
        q = MagicMock()
        db.query.return_value = q
        q.join.return_value = q
        q.filter.return_value = q
        q.first.return_value = None

        result = svc.submit_review(db, project, "nobody@example.com", "approved")

        assert result is None
        db.commit.assert_not_called()

    def test_stores_annotations(self):
        db = MagicMock()
        project = make_project(status="review")
        assignment = make_assignment(status="active")
        q = MagicMock()
        db.query.return_value = q
        q.join.return_value = q
        q.filter.return_value = q
        q.first.return_value = assignment

        annotations = [{"node": "p1", "text": "Fix typo"}]
        svc.submit_review(
            db, project, "reviewer@example.com",
            "revision_requested", annotations=annotations,
        )

        assert assignment.annotations == annotations

    def test_empty_annotations_default(self):
        db = MagicMock()
        project = make_project(status="review")
        assignment = make_assignment(status="active")
        q = MagicMock()
        db.query.return_value = q
        q.join.return_value = q
        q.filter.return_value = q
        q.first.return_value = assignment

        svc.submit_review(db, project, "reviewer@example.com", "revision_requested")

        assert assignment.annotations == []

    def test_result_contains_assignment_and_project_status(self):
        db = MagicMock()
        project = make_project(status="review")
        aid = uuid.uuid4()
        assignment = make_assignment(id=aid, status="active")
        self._setup_submit(db, assignment, next_assignment=None)

        final_result = svc.submit_review(db, project, "reviewer@example.com", "approved")

        assert final_result is not None
        assert final_result["assignment_id"] == str(aid)
        assert final_result["project_status"] == "complete"


# ── get_my_reviews ─────────────────────────────────────────────────────


class TestGetMyReviews:
    def _setup_my_reviews(self, db, assignments, projects_by_id):
        """Configure mock DB for get_my_reviews.

        get_my_reviews does:
        1. db.query(Assignment).join(Reviewer).options(joinedload).filter(email).filter(status).order_by().all()
        2. Uses a.project (eagerly loaded) for project name
        """
        for a in assignments:
            a.project = projects_by_id.get(a.project_id)

        q = MagicMock()
        q.join.return_value = q
        q.options.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.all.return_value = assignments

        db.query.return_value = q

    def test_returns_reviews_for_email(self):
        db = MagicMock()
        pid = uuid.uuid4()
        a1 = make_assignment(
            project_id=pid,
            reviewer_order=1,
            status="active",
            assigned_at=datetime(2026, 5, 21, 12, 0, 0),
            sla_deadline=datetime(2026, 5, 22, 12, 0, 0),
        )
        project = make_project(id=pid, name="Grant Alpha")
        self._setup_my_reviews(db, [a1], {pid: project})

        result = svc.get_my_reviews(db, "reviewer@example.com")

        assert len(result) == 1
        assert result[0]["project_name"] == "Grant Alpha"
        assert result[0]["order"] == 1
        assert result[0]["status"] == "active"
        assert result[0]["assigned_at"] is not None

    def test_with_status_filter_none_returns_all(self):
        db = MagicMock()
        pid1, pid2 = uuid.uuid4(), uuid.uuid4()
        a1 = make_assignment(project_id=pid1, status="active")
        a2 = make_assignment(project_id=pid2, status="approved")
        p1 = make_project(id=pid1, name="P1")
        p2 = make_project(id=pid2, name="P2")
        self._setup_my_reviews(db, [a1, a2], {pid1: p1, pid2: p2})

        result = svc.get_my_reviews(db, "reviewer@example.com", status_filter=None)

        assert len(result) == 2

    def test_empty_reviews(self):
        db = MagicMock()
        self._setup_my_reviews(db, [], {})

        result = svc.get_my_reviews(db, "nobody@example.com")

        assert result == []

    def test_unknown_project_shows_unknown_name(self):
        db = MagicMock()
        pid = uuid.uuid4()
        a1 = make_assignment(project_id=pid, status="active")
        self._setup_my_reviews(db, [a1], {})  # No matching project

        result = svc.get_my_reviews(db, "reviewer@example.com")

        assert len(result) == 1
        assert result[0]["project_name"] == "Unknown"

    def test_hours_remaining_present_when_sla_set(self):
        db = MagicMock()
        pid = uuid.uuid4()
        a1 = make_assignment(
            project_id=pid,
            sla_deadline=datetime(2099, 12, 31, 23, 59, 59),
        )
        p1 = make_project(id=pid)
        self._setup_my_reviews(db, [a1], {pid: p1})

        result = svc.get_my_reviews(db, "reviewer@example.com")

        assert result[0]["hours_remaining"] is not None
        assert result[0]["hours_remaining"] > 0

    def test_hours_remaining_none_when_no_sla(self):
        db = MagicMock()
        pid = uuid.uuid4()
        a1 = make_assignment(project_id=pid, sla_deadline=None, assigned_at=None)
        p1 = make_project(id=pid)
        self._setup_my_reviews(db, [a1], {pid: p1})

        result = svc.get_my_reviews(db, "reviewer@example.com")

        assert result[0]["hours_remaining"] is None
        assert result[0]["assigned_at"] is None
        assert result[0]["sla_deadline"] is None
