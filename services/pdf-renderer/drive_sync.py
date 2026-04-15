"""Google Drive sync for project documents — MD-only.

Reconciliation model: manifest.json in the Drive project folder holds the
desired state; on each run we diff current cme_documents against persisted
drive_md5 values and only upload documents whose content hash changed.
Upload format is markdown (.md) — Drive previews it natively and it matches
the v2 bundler. All Google SDK calls are sync — wrapped with asyncio.to_thread.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from googleapiclient.http import MediaIoBaseUpload

from bundler import load_current_docs, load_project
from drive_client import build_drive_client

logger = logging.getLogger(__name__)

MANIFEST_NAME = "manifest.json"
FOLDER_MIME = "application/vnd.google-apps.folder"
MD_MIME = "text/markdown"


def persist_project_updates(
    project_id: Any, drive_folder_id: str, status: str
) -> None:
    from db import session_scope
    from registry.models import CMEProject

    with session_scope() as db:
        p = db.query(CMEProject).filter(CMEProject.id == project_id).first()
        if p is None:
            return
        p.drive_folder_id = drive_folder_id
        p.drive_last_synced_at = datetime.now(timezone.utc)
        p.drive_sync_status = status
        db.commit()


def persist_document_sync(
    document_id: Any, drive_file_id: str, md5: str
) -> None:
    from db import session_scope
    from registry.models import CMEDocument

    with session_scope() as db:
        d = (
            db.query(CMEDocument)
            .filter(CMEDocument.id == document_id)
            .first()
        )
        if d is None:
            return
        d.drive_file_id = drive_file_id
        d.drive_md5 = md5
        d.drive_synced_at = datetime.now(timezone.utc)
        db.commit()


async def sync_project_to_drive(job: Any) -> None:
    root_folder_id = os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID")
    if not root_folder_id:
        raise RuntimeError("GOOGLE_DRIVE_ROOT_FOLDER_ID not configured")

    drive = build_drive_client()
    project = load_project(job.project_id)
    if project is None:
        raise RuntimeError(f"project {job.project_id} not found")

    folder_id = project.drive_folder_id
    if not folder_id:
        meta = await asyncio.to_thread(
            lambda: drive.files()
            .create(
                body={
                    "name": f"{project.name} ({project.id})",
                    "mimeType": FOLDER_MIME,
                    "parents": [root_folder_id],
                },
                fields="id",
            )
            .execute()
        )
        folder_id = meta["id"]

    existing = await asyncio.to_thread(
        lambda: drive.files()
        .list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, md5Checksum)",
        )
        .execute()
    )
    existing_by_name = {f["name"]: f for f in existing.get("files", [])}

    docs = load_current_docs(job.project_id, None)
    manifest_entries = []

    for i, doc in enumerate(docs, start=1):
        md_name = f"{i:02d}-{doc.document_type}.md"
        md_bytes = (doc.content_text or "").encode("utf-8")
        md_md5 = hashlib.md5(md_bytes).hexdigest()

        manifest_entries.append(
            {
                "document_id": str(doc.id),
                "name": md_name,
                "md5": md_md5,
            }
        )

        if doc.drive_md5 == md_md5 and doc.drive_file_id:
            continue

        media = MediaIoBaseUpload(
            io.BytesIO(md_bytes),
            mimetype=MD_MIME,
            resumable=False,
        )
        if md_name in existing_by_name:
            file_id = existing_by_name[md_name]["id"]
            await asyncio.to_thread(
                lambda fid=file_id, m=media: drive.files()
                .update(fileId=fid, media_body=m)
                .execute()
            )
        else:
            res = await asyncio.to_thread(
                lambda m=media: drive.files()
                .create(
                    body={"name": md_name, "parents": [folder_id]},
                    media_body=m,
                    fields="id",
                )
                .execute()
            )
            file_id = res["id"]
        persist_document_sync(doc.id, file_id, md_md5)

    manifest = {
        "project_id": str(project.id),
        "project_name": project.name,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "documents": manifest_entries,
    }
    manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
    manifest_media = MediaIoBaseUpload(
        io.BytesIO(manifest_bytes),
        mimetype="application/json",
        resumable=False,
    )
    if MANIFEST_NAME in existing_by_name:
        await asyncio.to_thread(
            lambda: drive.files()
            .update(
                fileId=existing_by_name[MANIFEST_NAME]["id"],
                media_body=manifest_media,
            )
            .execute()
        )
    else:
        await asyncio.to_thread(
            lambda: drive.files()
            .create(
                body={"name": MANIFEST_NAME, "parents": [folder_id]},
                media_body=manifest_media,
                fields="id",
            )
            .execute()
        )

    persist_project_updates(project.id, folder_id, "ok")
    logger.info(
        "drive sync done",
        extra={
            "project_id": str(project.id),
            "document_count": len(docs),
            "folder_id": folder_id,
        },
    )
