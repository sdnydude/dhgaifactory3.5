"""Logs-chat API endpoint (P5 T10).

POST /api/logs/chat — SSE answer over container logs. Auth: dedicated
LOGS_CHAT_TOKEN bearer (hmac-compared; 401 without). This is deliberately
NOT under write_auth's WRITE_PREFIXES: one Authorization header cannot carry
both tokens, and the endpoint is read-only apart from its own immutable
audit row.
"""
import asyncio
import hmac
import logging
import os
import time

import httpx
from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
import logs_chat_service as svc
from logs_chat_schemas import LogsChatRequest
from metrics import registry_read_latency, registry_read_operations, registry_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/logs", tags=["logs-chat"])

HEARTBEAT_S = 5.0


from sse_utils import sse as _sse


def _token_ok(authorization: Optional[str]) -> bool:
    expected = os.getenv("LOGS_CHAT_TOKEN", "")
    if not expected or not authorization or not authorization.startswith("Bearer "):
        return False
    return hmac.compare_digest(authorization[len("Bearer "):], expected)


def _write_audit(db: Session, **fields) -> None:
    """Immutable audit row; failures never block the response (SecurityAuditLog precedent)."""
    try:
        from models import LogsChatAudit
        db.add(LogsChatAudit(**fields))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("logs_chat audit write failed")


async def _heartbeat_wrap(coro, phase: str, start: float, out: list):
    """Await `coro` (result appended to `out`), yielding a heartbeat SSE event
    every HEARTBEAT_S while it runs."""
    task = asyncio.ensure_future(coro)
    while not task.done():
        await asyncio.wait({task}, timeout=HEARTBEAT_S)
        if not task.done():
            yield _sse("heartbeat", {"phase": phase, "elapsed_ms": int((time.time() - start) * 1000)})
    out.append(task.result())


@router.post("/chat")
async def logs_chat(
    body: LogsChatRequest,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None),
):
    if not _token_ok(authorization):
        registry_errors.labels(error_type="logs_chat_unauthorized").inc()
        return JSONResponse(status_code=401, content={"detail": "logs-chat token required"})

    async def event_stream():
        start = time.time()
        deadline_total = start + svc.BUDGET_TOTAL_S
        status, container, queries, n_lines, answer_chars = "error", None, [], 0, 0
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                # ---- retrieve phase (budget 30s), heartbeats while waiting ----
                retrieve_deadline = min(start + svc.RETRIEVE_MAX_S, deadline_total)

                async def retrieve():
                    known = await svc.known_containers(client)
                    cont = svc.resolve_container(body.question, body.container, known)
                    qs = svc.build_queries(cont, body.minutes, body.question)
                    qs, lines = await svc.fetch_context(client, qs, body.minutes, retrieve_deadline)
                    return known, cont, qs, lines

                got: list = []
                async for hb in _heartbeat_wrap(retrieve(), "retrieve", start, got):
                    yield hb
                known, container, queries, lines = got[0]
                n_lines = len(lines)
                yield _sse("citations", {"container": container,
                                         "queries": [q.model_dump() for q in queries],
                                         "sample": lines[:30]})

                # ---- generate phase (budget 15s within total 45s), buffered ----
                gen_deadline = min(time.time() + svc.GENERATE_MAX_S, deadline_total)
                got_gen: list = []
                async for hb in _heartbeat_wrap(
                    svc.generate_answer(client, body.question, lines, gen_deadline), "generate", start, got_gen,
                ):
                    yield hb
                text, completed = got_gen[0]
                text, unknown = svc.ground_answer(text, known, lines)
                answer_chars = len(text)

                for i in range(0, len(text), 400):
                    yield _sse("delta", {"text": text[i:i + 400]})

                elapsed_ms = int((time.time() - start) * 1000)
                if not completed or unknown:
                    status = "degraded"
                    msg = ("answer truncated at the time budget" if not completed
                           else f"answer names unverified containers: {', '.join(unknown)}")
                    yield _sse("degraded", {"message": msg, "elapsed_ms": elapsed_ms})
                else:
                    status = "done"
                    yield _sse("done", {"model": svc.LOGS_CHAT_MODEL, "elapsed_ms": elapsed_ms,
                                        "context_lines": n_lines})
                registry_read_operations.labels(operation="logs_chat").inc()
                registry_read_latency.observe(elapsed_ms)
        except Exception:
            logger.exception("logs_chat failed")
            registry_errors.labels(error_type="logs_chat_failed").inc()
            yield _sse("error", {"message": "logs-chat is temporarily unavailable"})
        finally:
            _write_audit(
                db, question=body.question, resolved_container=container,
                logql_queries=[q.model_dump() for q in queries],
                context_lines=n_lines, answer_chars=answer_chars, status=status,
                model=svc.LOGS_CHAT_MODEL, elapsed_ms=int((time.time() - start) * 1000),
            )

    return StreamingResponse(event_stream(), media_type="text/event-stream")
