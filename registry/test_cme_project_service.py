"""Tests for cme_project_service — direct service-layer coverage.

Run with:
    pytest registry/test_cme_project_service.py -v
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cme_project_service as svc
from models import CMEProject, CMEDocument


# ── Helpers ─────────────────────────────────────────────────────────────


def _mock_project(**overrides):
    """Build a MagicMock that looks like a CMEProject ORM row."""
    defaults = dict(
        id=uuid.uuid4(),
        name="Test CME Project",
        status="intake",
        intake={"disease_area": "oncology", "target_audience": "physicians"},
        current_agent=None,
        progress_percent=0,
        agents_completed=[],
        agents_pending=list(svc.INITIAL_AGENTS_PENDING),
        pipeline_thread_id=None,
        langsmith_run_id=None,
        outputs={},
        errors=[],
        human_review_status=None,
        human_review_notes=None,
        reviewed_by=None,
        reviewed_at=None,
        intake_version=1,
        current_run_id=None,
        drive_folder_id=None,
        drive_last_synced_at=None,
        drive_sync_status=None,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        started_at=None,
        completed_at=None,
    )
    defaults.update(overrides)
    row = MagicMock(spec=CMEProject)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _mock_document(**overrides):
    """Build a MagicMock that looks like a CMEDocument ORM row."""
    defaults = dict(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        document_type="needs_assessment",
        version=1,
        is_current=True,
        title="Needs Assessment Document",
        content_text="Full document content here.",
        content_html=None,
        content_json=None,
        word_count=500,
        quality_score=0.85,
        quality_passed=True,
        quality_details={"review_round": 2},
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    row = MagicMock(spec=CMEDocument)
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


def _mock_query_chain(db, results):
    """Wire up db.query(...).filter(...).order_by(...).offset(...).limit(...).all()."""
    q = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.all.return_value = results
    q.first.return_value = results[0] if results else None
    q.delete.return_value = len(results)
    return q


# ── create_project ──────────────────────────────────────────────────────


class TestCreateProject:
    def test_creates_and_commits(self, mock_db):
        result = svc.create_project(
            mock_db,
            name="Oncology Grant 2026",
            intake_dict={"disease_area": "oncology"},
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        added_project = mock_db.add.call_args[0][0]
        assert isinstance(added_project, CMEProject)
        assert added_project.name == "Oncology Grant 2026"
        assert added_project.status == "intake"
        assert added_project.intake == {"disease_area": "oncology"}

    def test_sets_initial_agents_pending(self, mock_db):
        svc.create_project(mock_db, name="Test", intake_dict={})

        added_project = mock_db.add.call_args[0][0]
        assert added_project.agents_pending == list(svc.INITIAL_AGENTS_PENDING)
        assert len(added_project.agents_pending) == 12

    def test_initializes_empty_collections(self, mock_db):
        svc.create_project(mock_db, name="Test", intake_dict={})

        added_project = mock_db.add.call_args[0][0]
        assert added_project.agents_completed == []
        assert added_project.outputs == {}
        assert added_project.errors == []
        assert added_project.progress_percent == 0
        assert added_project.current_agent is None
        assert added_project.human_review_status is None
        assert added_project.pipeline_thread_id is None


# ── list_projects ───────────────────────────────────────────────────────


class TestListProjects:
    def test_returns_all_non_archived(self, mock_db):
        projects = [_mock_project(status="intake"), _mock_project(status="processing")]
        _mock_query_chain(mock_db, projects)

        result = svc.list_projects(mock_db)
        assert result == projects
        assert len(result) == 2

    def test_with_status_filter(self, mock_db):
        project = _mock_project(status="review")
        _mock_query_chain(mock_db, [project])

        result = svc.list_projects(mock_db, status_filter="review")
        assert result == [project]

    def test_empty_list(self, mock_db):
        _mock_query_chain(mock_db, [])

        result = svc.list_projects(mock_db)
        assert result == []

    def test_pagination_skip_and_limit(self, mock_db):
        q = _mock_query_chain(mock_db, [])

        svc.list_projects(mock_db, skip=10, limit=5)

        q.offset.assert_called_once_with(10)
        q.limit.assert_called_once_with(5)

    def test_default_pagination(self, mock_db):
        q = _mock_query_chain(mock_db, [])

        svc.list_projects(mock_db)

        q.offset.assert_called_once_with(0)
        q.limit.assert_called_once_with(100)


# ── get_project ─────────────────────────────────────────────────────────


class TestGetProject:
    def test_found(self, mock_db):
        project = _mock_project()
        _mock_query_chain(mock_db, [project])

        result = svc.get_project(mock_db, str(project.id))
        assert result is project

    def test_not_found_returns_none(self, mock_db):
        _mock_query_chain(mock_db, [])

        result = svc.get_project(mock_db, str(uuid.uuid4()))
        assert result is None


# ── update_project_intake ───────────────────────────────────────────────


class TestUpdateProjectIntake:
    def test_updates_name_and_intake(self, mock_db):
        project = _mock_project(name="Old Name", intake={"old": True})

        result = svc.update_project_intake(
            mock_db,
            project,
            name="New Name",
            intake_dict={"new": True},
        )

        assert project.name == "New Name"
        assert project.intake == {"new": True}
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_does_not_bump_version_when_status_is_intake(self, mock_db):
        project = _mock_project(status="intake", intake_version=1)

        svc.update_project_intake(
            mock_db, project, name="Updated", intake_dict={"v": 1}
        )

        assert project.intake_version == 1

    def test_bumps_version_when_status_is_not_intake(self, mock_db):
        project = _mock_project(status="processing", intake_version=1)

        svc.update_project_intake(
            mock_db, project, name="Updated", intake_dict={"v": 2}
        )

        assert project.intake_version == 2

    def test_bumps_version_from_none(self, mock_db):
        project = _mock_project(status="review", intake_version=None)

        svc.update_project_intake(
            mock_db, project, name="Updated", intake_dict={}
        )

        assert project.intake_version == 2

    def test_calls_extract_intake_fields_fn_when_provided(self, mock_db):
        project = _mock_project()
        extract_fn = MagicMock()
        q = _mock_query_chain(mock_db, [])

        svc.update_project_intake(
            mock_db,
            project,
            name="With Fields",
            intake_dict={"disease_area": "cardiology"},
            extract_intake_fields_fn=extract_fn,
        )

        extract_fn.assert_called_once_with(
            project.id,
            {"disease_area": "cardiology"},
            mock_db,
        )

    def test_deletes_old_intake_fields_before_extract(self, mock_db):
        project = _mock_project()
        extract_fn = MagicMock()
        q = _mock_query_chain(mock_db, [])

        svc.update_project_intake(
            mock_db,
            project,
            name="Refresh Fields",
            intake_dict={},
            extract_intake_fields_fn=extract_fn,
        )

        # The delete call happens on the query chain for CMEIntakeField
        mock_db.query.assert_called()
        q.delete.assert_called_once()

    def test_skips_extract_when_fn_is_none(self, mock_db):
        project = _mock_project()

        svc.update_project_intake(
            mock_db, project, name="No Extract", intake_dict={}
        )

        # db.query should not be called (no CMEIntakeField delete)
        mock_db.query.assert_not_called()


# ── archive_project ─────────────────────────────────────────────────────


class TestArchiveProject:
    def test_sets_status_to_archived(self, mock_db):
        project = _mock_project(status="complete")

        result = svc.archive_project(mock_db, project)

        assert project.status == "archived"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_archives_intake_project(self, mock_db):
        project = _mock_project(status="intake")

        svc.archive_project(mock_db, project)

        assert project.status == "archived"


# ── set_project_status ──────────────────────────────────────────────────


class TestSetProjectStatus:
    def test_changes_status(self, mock_db):
        project = _mock_project(status="intake")

        result = svc.set_project_status(mock_db, project, "processing")

        assert project.status == "processing"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_sets_to_review(self, mock_db):
        project = _mock_project(status="processing")

        svc.set_project_status(mock_db, project, "review")

        assert project.status == "review"

    def test_sets_to_failed(self, mock_db):
        project = _mock_project(status="processing")

        svc.set_project_status(mock_db, project, "failed")

        assert project.status == "failed"


# ── fetch_latest_document_for_thread ────────────────────────────────────


class TestFetchLatestDocumentForThread:
    @patch("database.SessionLocal")
    def test_returns_document_dict(self, mock_session_local):
        project = _mock_project(name="Cardiology Grant")
        doc = _mock_document(
            document_type="needs_assessment",
            content_text="Document body text.",
            quality_details={"review_round": 3},
        )

        mock_session = MagicMock()
        mock_session_local.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_local.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.first.return_value = (doc, project)
        mock_session.execute.return_value = mock_result

        result = svc.fetch_latest_document_for_thread("thread-abc-123")

        assert result is not None
        assert result["title"] == "Cardiology Grant"
        assert result["graph_label"] == "needs_assessment"
        assert result["review_round"] == 3
        assert result["document_text"] == "Document body text."

    @patch("database.SessionLocal")
    def test_returns_none_when_no_document(self, mock_session_local):
        mock_session = MagicMock()
        mock_session_local.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_local.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result

        result = svc.fetch_latest_document_for_thread("nonexistent-thread")

        assert result is None

    @patch("database.SessionLocal")
    def test_handles_null_quality_details(self, mock_session_local):
        project = _mock_project(name="Null QD Project")
        doc = _mock_document(quality_details=None, document_type="grant_writer")

        mock_session = MagicMock()
        mock_session_local.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_local.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.first.return_value = (doc, project)
        mock_session.execute.return_value = mock_result

        result = svc.fetch_latest_document_for_thread("thread-null-qd")

        assert result is not None
        assert result["review_round"] == 0
        assert result["graph_label"] == "grant_writer"

    @patch("database.SessionLocal")
    def test_handles_empty_quality_details_dict(self, mock_session_local):
        project = _mock_project(name="Empty QD")
        doc = _mock_document(quality_details={}, content_text="")

        mock_session = MagicMock()
        mock_session_local.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_local.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.first.return_value = (doc, project)
        mock_session.execute.return_value = mock_result

        result = svc.fetch_latest_document_for_thread("thread-empty-qd")

        assert result is not None
        assert result["review_round"] == 0
        assert result["document_text"] == ""

    @patch("database.SessionLocal")
    def test_handles_non_integer_review_round(self, mock_session_local):
        project = _mock_project(name="Bad Round")
        doc = _mock_document(quality_details={"review_round": "not-a-number"})

        mock_session = MagicMock()
        mock_session_local.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_local.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.first.return_value = (doc, project)
        mock_session.execute.return_value = mock_result

        result = svc.fetch_latest_document_for_thread("thread-bad-round")

        assert result is not None
        assert result["review_round"] == 0

    @patch("database.SessionLocal")
    def test_handles_null_document_type(self, mock_session_local):
        project = _mock_project(name="No Doc Type")
        doc = _mock_document(document_type=None, content_text="Some text")

        mock_session = MagicMock()
        mock_session_local.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_local.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.first.return_value = (doc, project)
        mock_session.execute.return_value = mock_result

        result = svc.fetch_latest_document_for_thread("thread-no-type")

        assert result is not None
        assert result["graph_label"] == "CME Document"

    @patch("database.SessionLocal")
    def test_handles_null_content_text(self, mock_session_local):
        project = _mock_project(name="No Content")
        doc = _mock_document(content_text=None)

        mock_session = MagicMock()
        mock_session_local.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_local.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.first.return_value = (doc, project)
        mock_session.execute.return_value = mock_result

        result = svc.fetch_latest_document_for_thread("thread-no-content")

        assert result is not None
        assert result["document_text"] == ""
