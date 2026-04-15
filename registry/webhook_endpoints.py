"""Machine-to-machine webhook endpoints called from LangGraph Cloud.

Reached via the public Cloudflare tunnel route `registry-webhook.digitalharmonyai.com`
(Cloudflare Access bypass), protected at the application layer by
`REGISTRY_WEBHOOK_SECRET` in the `X-Webhook-Secret` header.
"""
from __future__ import annotations

import hmac
import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import get_db
from models import CMEProject, DownloadJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cme/webhook", tags=["cme-webhook"])

_ACTIVE_STATUSES = ("pending", "running")


def _check_secret(x_webhook_secret: str | None) -> None:
    expected = os.environ.get("REGISTRY_WEBHOOK_SECRET")
    if not expected or not x_webhook_secret or not hmac.compare_digest(expected, x_webhook_secret):
        raise HTTPException(status_code=401, detail="invalid webhook secret")


class DriveSyncEnqueueBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    milestone: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Milestone that triggered the sync (informational, logged only)",
    )


class DriveSyncEnqueueResponse(BaseModel):
    job_id: str
    status: str


@router.post(
    "/drive-sync-enqueue",
    response_model=DriveSyncEnqueueResponse,
    status_code=202,
)
def enqueue_drive_sync(
    body: DriveSyncEnqueueBody,
    response: Response,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    db: Session = Depends(get_db),
) -> DriveSyncEnqueueResponse:
    _check_secret(x_webhook_secret)

    project = db.query(CMEProject).filter(CMEProject.id == body.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    existing = (
        db.query(DownloadJob)
        .filter(
            DownloadJob.project_id == body.project_id,
            DownloadJob.scope == "drive_sync",
            DownloadJob.status.in_(_ACTIVE_STATUSES),
        )
        .order_by(DownloadJob.created_at.desc())
        .first()
    )
    if existing is not None:
        logger.info(
            "drive_sync dedupe project=%s milestone=%s existing_job=%s",
            body.project_id, body.milestone, existing.id,
        )
        response.status_code = 200
        return DriveSyncEnqueueResponse(job_id=str(existing.id), status=existing.status)

    job = DownloadJob(
        thread_id=project.pipeline_thread_id or "",
        graph_id="drive_sync",
        scope="drive_sync",
        status="pending",
        project_id=project.id,
        created_by=f"webhook:{body.milestone}",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info(
        "drive_sync enqueued project=%s milestone=%s job=%s",
        body.project_id, body.milestone, job.id,
    )
    return DriveSyncEnqueueResponse(job_id=str(job.id), status="queued")
