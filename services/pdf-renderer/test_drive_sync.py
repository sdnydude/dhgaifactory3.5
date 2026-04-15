import hashlib
from unittest.mock import MagicMock

import pytest

from drive_sync import sync_project_to_drive


@pytest.mark.asyncio
async def test_drive_sync_creates_folder_and_uploads_changed_docs(
    monkeypatch,
):
    monkeypatch.setenv("GOOGLE_DRIVE_ROOT_FOLDER_ID", "root-folder")

    fake_project = MagicMock(
        id="proj-1",
        drive_folder_id=None,
    )
    fake_project.name = "Test Project"  # MagicMock reserves name= kwarg

    unchanged_body = "# Needs\n\nUnchanged body."
    fake_doc_unchanged = MagicMock(
        id="d-1",
        document_type="needs_assessment",
        content_text=unchanged_body,
        drive_file_id="existing-file-id",
        drive_md5=hashlib.md5(unchanged_body.encode("utf-8")).hexdigest(),
    )
    fake_doc_new = MagicMock(
        id="d-2",
        document_type="research",
        content_text="# Research\n\nNew body.",
        drive_file_id=None,
        drive_md5=None,
    )

    mock_drive = MagicMock()
    mock_drive.files().create().execute.side_effect = [
        {"id": "folder-123"},        # project folder create
        {"id": "file-new-id"},       # doc d-2 create
        {"id": "manifest-file-id"},  # manifest create
    ]
    mock_drive.files().list().execute.return_value = {"files": []}

    import drive_sync as ds

    monkeypatch.setattr(ds, "build_drive_client", lambda: mock_drive)
    monkeypatch.setattr(
        ds, "load_project", MagicMock(return_value=fake_project)
    )
    monkeypatch.setattr(
        ds,
        "load_current_docs",
        MagicMock(return_value=[fake_doc_unchanged, fake_doc_new]),
    )
    monkeypatch.setattr(ds, "persist_project_updates", MagicMock())
    monkeypatch.setattr(ds, "persist_document_sync", MagicMock())

    job = MagicMock(id="job-1", project_id="proj-1")

    await sync_project_to_drive(job)

    # Unchanged doc must not be re-uploaded
    ds.persist_document_sync.assert_called_once()
    doc_args = ds.persist_document_sync.call_args[0]
    assert doc_args[0] == "d-2"
    assert doc_args[1] == "file-new-id"

    # Folder was created and project state was persisted with status=ok
    ds.persist_project_updates.assert_called_once_with(
        "proj-1", "folder-123", "ok"
    )

    # Manifest was written — total of 3 .create().execute() calls
    # (folder + doc d-2 + manifest) matches the side_effect list length.
    assert mock_drive.files().create().execute.call_count == 3
