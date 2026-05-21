"""Tests for cme_pipeline_service — direct service-layer coverage."""
import os
import sys
import uuid
from datetime import datetime
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cme_pipeline_service as svc
from schemas import PipelineRunRead


# ── Helpers ─────────────────────────────────────────────────────────────


def make_run(**overrides):
    """Create a mock CMEPipelineRun with sensible defaults."""
    run = MagicMock()
    run.run_id = overrides.get("run_id", uuid.uuid4())
    run.project_id = overrides.get("project_id", uuid.uuid4())
    run.run_number = overrides.get("run_number", 1)
    run.thread_id = overrides.get("thread_id", "thread-abc")
    run.langgraph_run_id = overrides.get("langgraph_run_id", "lg-run-123")
    run.intake_version_used = overrides.get("intake_version_used", 1)
    run.triggered_by = overrides.get("triggered_by", None)
    run.trigger_reason = overrides.get("trigger_reason", "initial")
    run.triggered_at = overrides.get("triggered_at", datetime(2026, 5, 1, 12, 0, 0))
    run.completed_at = overrides.get("completed_at", None)
    run.status = overrides.get("status", "processing")
    run.error_message = overrides.get("error_message", None)
    run.final_agent = overrides.get("final_agent", None)
    run.reason = overrides.get("reason", None)
    return run


def make_project(**overrides):
    """Create a mock CMEProject with sensible defaults."""
    proj = MagicMock()
    proj.id = overrides.get("id", uuid.uuid4())
    proj.name = overrides.get("name", "Test Project")
    proj.status = overrides.get("status", "intake")
    proj.intake_version = overrides.get("intake_version", 1)
    proj.current_agent = overrides.get("current_agent", None)
    proj.pipeline_thread_id = overrides.get("pipeline_thread_id", None)
    proj.current_run_id = overrides.get("current_run_id", None)
    proj.started_at = overrides.get("started_at", None)
    proj.completed_at = overrides.get("completed_at", None)
    proj.agents_completed = overrides.get("agents_completed", [])
    proj.errors = overrides.get("errors", [])
    return proj


def mock_scalar_chain(db, scalar_value):
    """Wire db.query(...).filter(...).scalar() to return scalar_value."""
    q = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.scalar.return_value = scalar_value
    return q


def mock_query_chain(db, results):
    """Wire db.query(...).filter(...).order_by(...).all() to return results."""
    q = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.order_by.return_value = q
    q.all.return_value = results
    q.first.return_value = results[0] if results else None
    return q


# ── pipeline_run_to_read ───────────────────────────────────────────────


class TestPipelineRunToRead:
    def test_converts_run_with_no_completion(self):
        run = make_run()
        result = svc.pipeline_run_to_read(run)

        assert isinstance(result, PipelineRunRead)
        assert result.run_id == run.run_id
        assert result.project_id == run.project_id
        assert result.run_number == 1
        assert result.thread_id == "thread-abc"
        assert result.status == "processing"
        assert result.duration_seconds is None

    def test_computes_duration_when_completed(self):
        triggered = datetime(2026, 5, 1, 12, 0, 0)
        completed = datetime(2026, 5, 1, 12, 3, 30)
        run = make_run(triggered_at=triggered, completed_at=completed)

        result = svc.pipeline_run_to_read(run)
        assert result.duration_seconds == 210.0

    def test_preserves_all_fields(self):
        run = make_run(
            triggered_by="stephen",
            trigger_reason="manual",
            error_message="timeout",
            final_agent="research",
            reason="manual rerun",
        )
        result = svc.pipeline_run_to_read(run)

        assert result.triggered_by == "stephen"
        assert result.trigger_reason == "manual"
        assert result.error_message == "timeout"
        assert result.final_agent == "research"
        assert result.reason == "manual rerun"


# ── start_pipeline ─────────────────────────────────────────────────────


class TestStartPipeline:
    def test_creates_run_and_updates_project(self, mock_db):
        project = make_project()
        mock_scalar_chain(mock_db, 0)  # no previous runs

        run = svc.start_pipeline(mock_db, project, "thread-1", "run-1")

        assert project.status == "processing"
        assert project.current_agent == "research"
        assert project.pipeline_thread_id == "thread-1"
        assert project.current_run_id == run.run_id
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.flush.assert_called_once()
        assert mock_db.refresh.call_count == 2

    def test_first_run_is_initial_trigger(self, mock_db):
        project = make_project()
        mock_scalar_chain(mock_db, 0)

        run = svc.start_pipeline(mock_db, project, "t", "r")
        assert run.trigger_reason == "initial"
        assert run.run_number == 1

    def test_subsequent_run_is_retry_trigger(self, mock_db):
        project = make_project()
        mock_scalar_chain(mock_db, 2)  # already had 2 runs

        run = svc.start_pipeline(mock_db, project, "t", "r")
        assert run.trigger_reason == "retry"
        assert run.run_number == 3

    def test_uses_intake_version_from_project(self, mock_db):
        project = make_project(intake_version=3)
        mock_scalar_chain(mock_db, 0)

        run = svc.start_pipeline(mock_db, project, "t", "r")
        assert run.intake_version_used == 3

    def test_defaults_intake_version_when_none(self, mock_db):
        project = make_project(intake_version=None)
        mock_scalar_chain(mock_db, 0)

        run = svc.start_pipeline(mock_db, project, "t", "r")
        assert run.intake_version_used == 1


# ── cancel_pipeline ────────────────────────────────────────────────────


class TestCancelPipeline:
    def test_cancels_run_and_updates_project(self, mock_db):
        project = make_project(status="processing", current_agent="gap_analysis")
        run = make_run(status="processing")

        result = svc.cancel_pipeline(mock_db, project, run)

        assert result.status == "cancelled"
        assert result.completed_at is not None
        assert result.final_agent == "gap_analysis"
        assert project.status == "cancelled"
        assert project.completed_at is not None
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(run)


# ── rerun_pipeline ─────────────────────────────────────────────────────


class TestRerunPipeline:
    def test_creates_new_run_with_manual_trigger(self, mock_db):
        project = make_project(intake_version=2)
        mock_scalar_chain(mock_db, 1)

        run = svc.rerun_pipeline(mock_db, project, "thread-2", "run-2", reason="data updated")

        assert run.trigger_reason == "manual"
        assert run.run_number == 2
        assert run.reason == "data updated"
        assert run.intake_version_used == 2

    def test_resets_project_state(self, mock_db):
        project = make_project(
            status="failed",
            agents_completed=["research", "clinical"],
            errors=[{"msg": "timeout"}],
            completed_at=datetime(2026, 5, 1),
        )
        mock_scalar_chain(mock_db, 1)

        svc.rerun_pipeline(mock_db, project, "thread-2", "run-2")

        assert project.status == "processing"
        assert project.current_agent == "research"
        assert project.pipeline_thread_id == "thread-2"
        assert project.completed_at is None
        assert project.agents_completed == []
        assert project.errors == []
        assert project.current_run_id is not None

    def test_cancels_active_prev_run(self, mock_db):
        prev = make_run(status="processing")
        project = make_project()
        mock_scalar_chain(mock_db, 1)

        svc.rerun_pipeline(mock_db, project, "t", "r", prev_run=prev)

        assert prev.status == "cancelled"
        assert prev.completed_at is not None
        assert prev.reason == "superseded by rerun"

    def test_does_not_cancel_completed_prev_run(self, mock_db):
        prev = make_run(status="success")
        project = make_project()
        mock_scalar_chain(mock_db, 1)

        svc.rerun_pipeline(mock_db, project, "t", "r", prev_run=prev)

        assert prev.status == "success"  # unchanged

    def test_no_prev_run_does_not_error(self, mock_db):
        project = make_project()
        mock_scalar_chain(mock_db, 0)

        run = svc.rerun_pipeline(mock_db, project, "t", "r", prev_run=None)
        assert run.status == "processing"


# ── get_active_run ─────────────────────────────────────────────────────


class TestGetActiveRun:
    def test_returns_none_when_no_current_run_id(self, mock_db):
        project = make_project(current_run_id=None)
        result = svc.get_active_run(mock_db, project)
        assert result is None
        mock_db.query.assert_not_called()

    def test_returns_run_when_found(self, mock_db):
        run_id = uuid.uuid4()
        run = make_run(run_id=run_id)
        project = make_project(current_run_id=run_id)
        mock_query_chain(mock_db, [run])

        result = svc.get_active_run(mock_db, project)
        assert result is run

    def test_returns_none_when_run_not_in_db(self, mock_db):
        project = make_project(current_run_id=uuid.uuid4())
        mock_query_chain(mock_db, [])

        result = svc.get_active_run(mock_db, project)
        assert result is None


# ── list_runs ──────────────────────────────────────────────────────────


class TestListRuns:
    def test_returns_runs_for_project(self, mock_db):
        project_id = uuid.uuid4()
        runs = [make_run(run_number=2), make_run(run_number=1)]
        mock_query_chain(mock_db, runs)

        result = svc.list_runs(mock_db, str(project_id))
        assert result == runs
        assert len(result) == 2

    def test_returns_empty_list_when_no_runs(self, mock_db):
        mock_query_chain(mock_db, [])
        result = svc.list_runs(mock_db, str(uuid.uuid4()))
        assert result == []
