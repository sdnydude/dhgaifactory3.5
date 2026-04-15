"""Project bundle assembler — MD-only v2.

Reads current versions from cme_documents and writes a zip containing:
  documents/NN-<type>.md    one markdown file per selected document
  metadata/project.json     machine-readable manifest
  README.md                 human-readable index with sha256 per entry

Atomic write: stream to `<job_id>.zip.tmp`, then os.replace to the final
path so a reader never sees a partial archive.

Per-document PDF export is served separately by Phase 1's
`/api/cme/export/document/{thread_id}`. PDF-in-bundle can be added later
behind an `include_pdfs` flag on BundleJobCreate.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _exports_dir() -> Path:
    base = os.getenv("EXPORTS_DIR", "/var/exports")
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_project(project_id: Any) -> Any:
    from db import session_scope
    from registry.models import CMEProject

    with session_scope() as db:
        return db.query(CMEProject).filter(CMEProject.id == project_id).first()


def load_current_docs(project_id: Any, selected_ids: list[str] | None) -> list[Any]:
    from db import session_scope
    from registry.models import CMEDocument

    with session_scope() as db:
        q = db.query(CMEDocument).filter(
            CMEDocument.project_id == project_id,
            CMEDocument.is_current.is_(True),
        )
        if selected_ids:
            q = q.filter(CMEDocument.id.in_(selected_ids))
        return (
            q.order_by(CMEDocument.document_type, CMEDocument.version.desc()).all()
        )


def update_job_artifact(job_id: Any, path: Path, size: int, sha: str) -> None:
    from db import session_scope
    from registry.models import DownloadJob

    with session_scope() as db:
        job = db.query(DownloadJob).filter(DownloadJob.id == job_id).first()
        if job is None:
            return
        job.artifact_path = str(path)
        job.artifact_bytes = size
        job.artifact_sha256 = sha
        db.commit()


def _readme_text(
    project: Any,
    entries: list[tuple[str, str]],
    selection_mode: str,
    generated_at: str,
) -> str:
    lines = [
        f"# Bundle: {project.name}",
        "",
        f"Generated: {generated_at}",
        f"Selection mode: {selection_mode}",
        "",
        "## Files",
        "",
    ]
    for name, sha in entries:
        lines.append(f"- `{name}` — sha256 `{sha}`")
    lines.append("")
    return "\n".join(lines)


async def assemble_bundle(job: Any) -> None:
    exports = _exports_dir()
    tmp = exports / f"{job.id}.zip.tmp"
    final = exports / f"{job.id}.zip"

    project = load_project(job.project_id)
    if project is None:
        raise RuntimeError(f"project {job.project_id} not found")

    selected = list(job.selected_document_ids) if job.selected_document_ids else None
    docs = load_current_docs(job.project_id, selected)
    if not docs:
        raise RuntimeError("no documents matched the selection")

    generated_at = datetime.now(timezone.utc).isoformat()
    entries: list[tuple[str, str]] = []

    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, doc in enumerate(docs, start=1):
            name = f"documents/{i:02d}-{doc.document_type}.md"
            md_bytes = (doc.content_text or "").encode("utf-8")
            zf.writestr(name, md_bytes)
            entries.append((name, hashlib.sha256(md_bytes).hexdigest()))

        metadata = {
            "project_id": str(project.id),
            "project_name": project.name,
            "selection_mode": "subset" if selected else "all",
            "selected_document_ids": [str(x) for x in (selected or [])],
            "generated_at": generated_at,
            "document_count": len(docs),
            "bundle_format_version": 2,
        }
        meta_bytes = json.dumps(metadata, indent=2).encode("utf-8")
        zf.writestr("metadata/project.json", meta_bytes)
        entries.append(
            ("metadata/project.json", hashlib.sha256(meta_bytes).hexdigest())
        )

        readme = _readme_text(project, entries, metadata["selection_mode"], generated_at)
        zf.writestr("README.md", readme.encode("utf-8"))

    os.replace(tmp, final)

    size = final.stat().st_size
    h = hashlib.sha256()
    with final.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    update_job_artifact(job.id, final, size, h.hexdigest())
    logger.info("bundle written", extra={"job_id": str(job.id), "size": size})
