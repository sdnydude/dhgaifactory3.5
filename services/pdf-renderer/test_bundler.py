import json
import zipfile
from unittest.mock import MagicMock

import pytest

from bundler import assemble_bundle


@pytest.mark.asyncio
async def test_assemble_bundle_writes_md_and_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPORTS_DIR", str(tmp_path))

    fake_docs = [
        MagicMock(
            id="doc-1",
            document_type="needs_assessment",
            title="Needs",
            content_text="# Needs\n\nBody.",
        ),
        MagicMock(
            id="doc-2",
            document_type="research",
            title="Research",
            content_text="# Research\n\nBody.",
        ),
    ]
    fake_project = MagicMock(id="proj-1", pipeline_thread_id="t-1")
    fake_project.name = "Test Project"  # MagicMock reserves name= kwarg for mock display name
    fake_job = MagicMock(
        id="job-1",
        project_id="proj-1",
        selected_document_ids=None,
    )

    import bundler as bundler_mod

    monkeypatch.setattr(
        bundler_mod, "load_project", MagicMock(return_value=fake_project)
    )
    monkeypatch.setattr(
        bundler_mod, "load_current_docs", MagicMock(return_value=fake_docs)
    )
    monkeypatch.setattr(bundler_mod, "update_job_artifact", MagicMock())

    await assemble_bundle(fake_job)

    final = tmp_path / "job-1.zip"
    assert final.exists()
    with zipfile.ZipFile(final) as zf:
        names = set(zf.namelist())
        assert "README.md" in names
        assert "metadata/project.json" in names
        assert "documents/01-needs_assessment.md" in names
        assert "documents/02-research.md" in names
        assert not any(n.endswith(".pdf") for n in names)

        meta = json.loads(zf.read("metadata/project.json"))
        assert meta["project_id"] == "proj-1"
        assert meta["selection_mode"] == "all"
        assert meta["document_count"] == 2
        assert meta["bundle_format_version"] == 2

        readme = zf.read("README.md").decode("utf-8")
        assert "Test Project" in readme
        assert "sha256" in readme
