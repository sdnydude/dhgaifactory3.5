"""Talkback API endpoint.

Route:
  POST /api/talkback   hybrid doc retrieval + streamed LLM answer (SSE)

Response is text/event-stream:
  event: citations  → the retrieved sources (emitted first, powers the UI)
  event: delta      → answer text chunks (repeated)
  event: error      → terminal failure (replaces done)
  event: done       → {"model", "elapsed_ms"}
"""
import json
import logging
import time

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
import talkback_service as svc
from talkback_schemas import TalkbackRequest

logger = logging.getLogger(__name__)

from metrics import (
    registry_read_latency,
    registry_read_operations,
    registry_errors,
)

router = APIRouter(prefix="/api/talkback", tags=["talkback"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("")
async def talkback(body: TalkbackRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    """Stream a documentation answer grounded in hybrid doc_pages retrieval."""

    async def event_stream():
        start = time.time()
        try:
            citations, context = await svc.retrieve(db, body.question, body.project_name)
            yield _sse("citations", {
                "citations": [c.model_dump() for c in citations],
            })

            generator = svc.stream_haiku if body.model == "haiku" else svc.stream_local
            try:
                async for text in generator(body.question, context):
                    yield _sse("delta", {"text": text})
            except RuntimeError as e:
                if str(e) == "haiku_unavailable":
                    yield _sse("error", {
                        "message": "Haiku is not configured on this server. Try the local model.",
                    })
                    registry_errors.labels(error_type="talkback_haiku_unavailable").inc()
                    return
                raise

            registry_read_operations.labels(operation="talkback").inc()
            registry_read_latency.observe((time.time() - start) * 1000)
            yield _sse("done", {
                "model": body.model,
                "elapsed_ms": int((time.time() - start) * 1000),
            })
        except Exception as e:
            logger.error("talkback failed (model=%s): %s", body.model, e)
            registry_errors.labels(error_type="talkback_failed").inc()
            yield _sse("error", {"message": "Talkback is temporarily unavailable."})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
