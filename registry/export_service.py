from __future__ import annotations

import logging
import os
import time
from typing import Any
from urllib.parse import quote
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from export_signing import PrintTokenPayload, sign_print_token
from models import CMEDocument, CMEProject, DownloadJob

logger = logging.getLogger(__name__)


def _secret() -> str:
    secret = os.environ.get("EXPORT_SIGNING_SECRET")
    if not secret:
        raise RuntimeError("EXPORT_SIGNING_SECRET not set")
    return secret


def _frontend_internal_url() -> str:
    return os.environ.get("FRONTEND_INTERNAL_URL", "http://dhg-frontend:3000")


def _renderer_url() -> str:
    return os.environ.get("PDF_RENDERER_URL", "http://dhg-pdf-renderer:8014")


def build_print_url(
    subject: str,
    resource_id: str,
    path_prefix: str,
    ttl_seconds: int = 300,
) -> str:
    token = sign_print_token(
        PrintTokenPayload(
            subject=subject,
            resource_id=resource_id,
            expires_at=int(time.time()) + ttl_seconds,
        ),
        secret=_secret(),
    )
    return f"{_frontend_internal_url()}{path_prefix}{quote(resource_id)}?t={token}"


async def load_document_for_thread(thread_id: str) -> dict[str, Any] | None:
    """Fetch the data the print route needs for a single document.

    Thin wrapper so tests can monkey-patch. Real impl reads the latest
    CMEDocument row joined to CMEProject via pipeline_thread_id.
    """
    from cme_endpoints import fetch_latest_document_for_thread

    return await fetch_latest_document_for_thread(thread_id)


async def render_via_renderer(
    url: str,
    wait_for_selectors: list[str] | None = None,
) -> bytes:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{_renderer_url()}/render-sync",
            json={
                "url": url,
                "wait_for_selectors": wait_for_selectors or ["[data-print-ready=true]"],
            },
        )
        resp.raise_for_status()
        return resp.content


def get_project(db: Session, project_id: UUID) -> CMEProject | None:
    return db.query(CMEProject).filter(CMEProject.id == project_id).first()


def validate_document_ids(
    db: Session, project_id: UUID, document_ids: list[UUID],
) -> int:
    """Return the count of valid current documents matching the given IDs."""
    return (
        db.query(CMEDocument)
        .filter(
            CMEDocument.id.in_(document_ids),
            CMEDocument.project_id == project_id,
            CMEDocument.is_current.is_(True),
        )
        .count()
    )


def create_bundle_job(
    db: Session, project: CMEProject, document_ids: list[UUID] | None,
) -> DownloadJob:
    job = DownloadJob(
        thread_id=project.pipeline_thread_id or "",
        graph_id="bundle",
        scope="project_bundle",
        status="pending",
        project_id=project.id,
        selected_document_ids=(
            [str(x) for x in document_ids] if document_ids else None
        ),
        created_by=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: UUID) -> DownloadJob | None:
    return db.query(DownloadJob).filter(DownloadJob.id == job_id).first()


def list_jobs(db: Session, *, limit: int = 20) -> list[DownloadJob]:
    return (
        db.query(DownloadJob)
        .order_by(DownloadJob.created_at.desc())
        .limit(limit)
        .all()
    )
