from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from export_schemas import (
    BundleJobCreate,
    BundleJobResponse,
    DocumentPrintPayload,
)
from export_service import (
    build_print_url,
    load_document_for_thread,
    render_via_renderer,
)
from export_signing import (
    PrintTokenExpired,
    PrintTokenInvalid,
    verify_print_token,
)
from models import CMEDocument, CMEProject, DownloadJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cme/export", tags=["cme-export"])


def _sanitize_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in s)[:80]


@router.get("/internal/document/{thread_id}", response_model=DocumentPrintPayload)
async def internal_document(
    thread_id: str,
    x_print_token: str | None = Header(default=None, alias="X-Print-Token"),
) -> DocumentPrintPayload:
    """Called by the Next.js print route to hydrate the page.

    Guarded by the same HMAC token the print URL was signed with, so the
    endpoint is never reachable from user traffic.
    """
    secret = os.environ.get("EXPORT_SIGNING_SECRET")
    if not secret or not x_print_token:
        raise HTTPException(status_code=401, detail="missing token")
    try:
        payload = verify_print_token(x_print_token, secret=secret)
    except PrintTokenExpired:
        raise HTTPException(status_code=401, detail="token expired")
    except PrintTokenInvalid:
        raise HTTPException(status_code=401, detail="invalid token")
    if payload.subject != "cme_document" or payload.resource_id != thread_id:
        raise HTTPException(status_code=403, detail="scope mismatch")

    data = await load_document_for_thread(thread_id)
    if not data:
        raise HTTPException(status_code=404, detail="document not found")
    return DocumentPrintPayload(**data)


@router.get("/document/{thread_id}")
async def sync_download_document(thread_id: str) -> Response:
    """User-facing sync download. Auth handled by Cloudflare Access layer."""
    data = await load_document_for_thread(thread_id)
    if not data:
        raise HTTPException(status_code=404, detail="document not found")
    url = build_print_url(
        subject="cme_document",
        resource_id=thread_id,
        path_prefix="/print/cme/document/",
    )
    try:
        pdf = await render_via_renderer(url)
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
        logger.warning("pdf renderer unreachable: %s", e)
        raise HTTPException(status_code=502, detail="pdf renderer unavailable")
    except httpx.HTTPStatusError as e:
        logger.warning("pdf renderer returned %s: %s", e.response.status_code, e.response.text[:200])
        raise HTTPException(status_code=502, detail="pdf render failed")
    safe_title = _sanitize_filename(data["title"])
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{safe_title}_{stamp}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "content-disposition": f'attachment; filename="{filename}"',
            "cache-control": "no-store",
        },
    )


def _serialize_job(job: DownloadJob) -> BundleJobResponse:
    selected = job.selected_document_ids
    if selected is not None:
        selected = [UUID(str(x)) for x in selected]
    return BundleJobResponse(
        id=job.id,
        project_id=job.project_id,
        scope=job.scope,
        status=job.status,
        selected_document_ids=selected,
        created_at=job.created_at,
        completed_at=job.completed_at,
        artifact_bytes=job.artifact_bytes,
        error=job.error,
    )


@router.post("/bundle", response_model=BundleJobResponse, status_code=202)
def create_bundle_job(
    body: BundleJobCreate,
    db: Session = Depends(get_db),
) -> BundleJobResponse:
    project = db.query(CMEProject).filter(CMEProject.id == body.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    if body.document_ids is not None:
        if not body.document_ids:
            raise HTTPException(
                status_code=400, detail="document_ids may not be empty list"
            )
        count = (
            db.query(CMEDocument)
            .filter(
                CMEDocument.id.in_(body.document_ids),
                CMEDocument.project_id == body.project_id,
                CMEDocument.is_current.is_(True),
            )
            .count()
        )
        if count != len(body.document_ids):
            raise HTTPException(
                status_code=400,
                detail="one or more document_ids do not belong to this project",
            )

    job = DownloadJob(
        thread_id=project.pipeline_thread_id or "",
        graph_id="bundle",
        scope="project_bundle",
        status="pending",
        project_id=project.id,
        selected_document_ids=(
            [str(x) for x in body.document_ids] if body.document_ids else None
        ),
        created_by=None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _serialize_job(job)


@router.get("/job/{job_id}", response_model=BundleJobResponse)
def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> BundleJobResponse:
    job = db.query(DownloadJob).filter(DownloadJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return _serialize_job(job)


@router.get("/artifact/{job_id}")
def stream_artifact(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> FileResponse:
    job = db.query(DownloadJob).filter(DownloadJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.status != "succeeded" or not job.artifact_path:
        raise HTTPException(status_code=409, detail="artifact not ready")
    return FileResponse(
        path=job.artifact_path,
        media_type="application/zip",
        filename=f"bundle-{job.id}.zip",
    )


@router.get("/jobs", response_model=list[BundleJobResponse])
def list_jobs(
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[BundleJobResponse]:
    rows = (
        db.query(DownloadJob)
        .order_by(DownloadJob.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_serialize_job(j) for j in rows]
