"""Worker loop: claims pending download_jobs and dispatches by scope.

Single-replica deployment — plain FOR UPDATE. If we ever run multiple
renderer replicas, swap in SKIP LOCKED.

Scope dispatch:
  project_bundle -> bundler.assemble_bundle
  drive_sync     -> drive_sync.sync_project_to_drive
The 'document' scope is served inline by the registry API and is never
enqueued, so it is excluded from the claim filter.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import text

from bundler import assemble_bundle
from drive_sync import sync_project_to_drive

logger = logging.getLogger(__name__)

_CLAIM_SQL = text(
    """
    SELECT id, scope, project_id, thread_id, graph_id,
           selected_document_ids, created_by
      FROM download_jobs
     WHERE status = 'pending'
       AND scope IN ('project_bundle', 'drive_sync')
     ORDER BY created_at
     LIMIT 1
     FOR UPDATE
    """
)


def claim_next_job_sync(db) -> Any | None:
    result = db.execute(_CLAIM_SQL)
    row = result.fetchone()
    if row is None:
        return None
    db.execute(
        text(
            "UPDATE download_jobs SET status='running', started_at=now() "
            "WHERE id=:id"
        ),
        {"id": row.id},
    )
    db.commit()
    return row


def mark_completed_sync(db, job_id: Any) -> None:
    db.execute(
        text(
            "UPDATE download_jobs SET status='succeeded', completed_at=now() "
            "WHERE id=:id"
        ),
        {"id": job_id},
    )
    db.commit()


def mark_failed_sync(db, job_id: Any, error: str) -> None:
    db.execute(
        text(
            "UPDATE download_jobs "
            "SET status='failed', completed_at=now(), error=:error "
            "WHERE id=:id"
        ),
        {"id": job_id, "error": error[:2000]},
    )
    db.commit()


async def _claim() -> Any | None:
    def _inner():
        from db import session_scope

        with session_scope() as db:
            return claim_next_job_sync(db)

    return await asyncio.to_thread(_inner)


async def run_worker(stop_event: asyncio.Event) -> None:
    logger.info("worker loop started")
    while not stop_event.is_set():
        job = await _claim()
        if job is None:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                pass
            continue

        logger.info(
            "claimed job",
            extra={"job_id": str(job.id), "scope": job.scope},
        )
        try:
            if job.scope == "project_bundle":
                await assemble_bundle(job)
            elif job.scope == "drive_sync":
                await sync_project_to_drive(job)
            else:
                raise RuntimeError(f"unsupported scope {job.scope}")

            job_id = job.id

            def _ok(jid=job_id):
                from db import session_scope

                with session_scope() as db:
                    mark_completed_sync(db, jid)

            await asyncio.to_thread(_ok)
        except Exception as exc:
            logger.exception("job failed", extra={"job_id": str(job.id)})

            job_id = job.id
            err = str(exc)

            def _fail(jid=job_id, e=err):
                from db import session_scope

                with session_scope() as db:
                    mark_failed_sync(db, jid, e)

            await asyncio.to_thread(_fail)
