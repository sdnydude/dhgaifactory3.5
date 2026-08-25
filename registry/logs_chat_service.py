"""Logs-chat service (P5 T10) — deterministic LogQL retrieval + local-only
grounded answer generation over the Loki keep-all store.

Design rails (spec docs/log-program-architecture-2026-08-23.md §4.3 + rulings):
  - LOCAL ONLY: Ollama (LOGS_CHAT_MODEL, default granite4.1:8b). There is no
    cloud fallback and no anthropic import in this module tree — asserted by
    test_logs_chat.py.
  - Deterministic query building: the LLM never writes LogQL. Queries are
    built from the resolved container + question keywords.
  - Container grounding: names are resolved against live label_values; the
    finished answer is validated container-names-only (buffered, then
    streamed) — unknown container names degrade the answer.
  - Budget: 45 s total (30 s retrieve / 15 s generate). Reads never mutate;
    the only write is the immutable audit row (logs_chat_audit).
"""
import difflib
import json
import logging
import os
import re
import time
from typing import Optional

import httpx

from logs_chat_schemas import QuerySpec

logger = logging.getLogger(__name__)

LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://dhg-ollama:11434")
LOGS_CHAT_MODEL = os.getenv("LOGS_CHAT_MODEL", "granite4.1:8b")
BUDGET_TOTAL_S = 45.0
RETRIEVE_MAX_S = 30.0
GENERATE_MAX_S = 15.0
MAX_CONTEXT_CHARS = 32_000  # ~8k tokens at ~4 chars/token
MAX_ANSWER_TOKENS = 600
ERROR_HINTS = ("error", "fail", "crash", "panic", "fatal", "exception", "500", "broke")

SYSTEM_PROMPT = (
    "You are the DHG log analyst. Answer the question using ONLY the log lines "
    "provided. Name only containers that appear in the provided lines. Quote "
    "short decisive fragments rather than whole lines. If the lines do not "
    "answer the question, say so plainly — never invent log content, container "
    "names, or timestamps."
)

CONTAINER_TOKEN = re.compile(r"\b(?:dhg|portage|plane|cool)-[a-z0-9][a-z0-9_.-]*\b")


async def known_containers(client: httpx.AsyncClient) -> list[str]:
    r = await client.get(f"{LOKI_URL}/loki/api/v1/label/container/values")
    r.raise_for_status()
    return sorted(r.json().get("data") or [])


def resolve_container(question: str, explicit: Optional[str], known: list[str]) -> Optional[str]:
    """Deterministic fuzzy resolution of the container the question is about."""
    if explicit:
        if explicit in known:
            return explicit
        close = difflib.get_close_matches(explicit, known, n=1, cutoff=0.6)
        return close[0] if close else None
    words = re.findall(r"[a-z0-9][a-z0-9_.-]{2,}", question.lower())
    for w in sorted(words, key=len, reverse=True):
        if w in known:
            return w
        close = difflib.get_close_matches(w, known, n=1, cutoff=0.8)
        if close:
            return close[0]
    return None


def build_queries(container: Optional[str], minutes: int, question: str) -> list[QuerySpec]:
    """Deterministic LogQL — the model never writes queries."""
    q = question.lower()
    wants_errors = any(h in q for h in ERROR_HINTS)
    queries: list[QuerySpec] = []
    if container:
        sel = f'{{container="{container}"}}'
        if wants_errors:
            queries.append(QuerySpec(
                desc=f"{container} error-level lines ({minutes}m)",
                logql=sel + ' | level=~`(?i)error|fatal|panic|critical`',
            ))
        queries.append(QuerySpec(desc=f"{container} recent lines ({minutes}m)", logql=sel))
    else:
        queries.append(QuerySpec(
            desc=f"error-level lines, all containers ({minutes}m)",
            logql='{job="dhg-ai-factory"} | level=~`(?i)error|fatal|panic|critical`',
        ))
    return queries


async def fetch_context(
    client: httpx.AsyncClient, queries: list[QuerySpec], minutes: int, deadline: float,
) -> tuple[list[QuerySpec], list[str]]:
    """Run the queries against Loki; returns (queries+line counts, context lines)."""
    end = time.time()
    start = end - minutes * 60
    lines: list[str] = []
    budget_chars = MAX_CONTEXT_CHARS
    for spec in queries:
        if time.time() > deadline or budget_chars <= 0:
            spec.lines = 0
            continue
        r = await client.get(
            f"{LOKI_URL}/loki/api/v1/query_range",
            params={
                "query": spec.logql,
                "start": f"{start:.0f}000000000",
                "end": f"{end:.0f}000000000",
                "limit": 500,
                "direction": "backward",
            },
            timeout=min(25.0, max(1.0, deadline - time.time())),
        )
        r.raise_for_status()
        n = 0
        for stream in r.json()["data"]["result"]:
            cname = stream["stream"].get("container", "?")
            for _ts, text in stream["values"]:
                text = text.strip()[:400]
                entry = f"[{cname}] {text}"
                if budget_chars - len(entry) < 0:
                    break
                lines.append(entry)
                budget_chars -= len(entry)
                n += 1
        spec.lines = n
    return queries, lines


async def generate_answer(
    client: httpx.AsyncClient, question: str, context_lines: list[str], deadline: float,
) -> tuple[str, bool]:
    """Buffered generation (local Ollama only). Returns (text, completed)."""
    if not context_lines:
        return ("No log lines matched that question in the selected window.", True)
    payload = {
        "model": LOGS_CHAT_MODEL,
        "stream": True,
        "think": False,
        "options": {"num_predict": MAX_ANSWER_TOKENS},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Log lines:\n" + "\n".join(context_lines) + f"\n\nQuestion: {question}"},
        ],
    }
    text = ""
    try:
        async with client.stream(
            "POST", f"{OLLAMA_URL}/api/chat", json=payload,
            timeout=httpx.Timeout(max(1.0, deadline - time.time()), connect=5.0),
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                chunk = json.loads(line)
                text += chunk.get("message", {}).get("content", "")
                if chunk.get("done"):
                    return text, True
                if time.time() > deadline:
                    return text, False
    except httpx.TimeoutException:
        return text, False
    return text, bool(text)


def ground_answer(text: str, known: list[str], context_lines: list[str] | None = None) -> tuple[str, list[str]]:
    """Container-names-only grounding: every container-like token in the answer
    must exist in the live label set OR appear verbatim in the provided context
    lines (the model may faithfully quote log content that names other
    containers, including stopped ones and the job label). Returns
    (text, unknown_names) — unknown means invented, and degrades the answer."""
    mentioned = set(CONTAINER_TOKEN.findall(text))
    allowed = set(known)
    for line in context_lines or []:
        allowed.update(CONTAINER_TOKEN.findall(line))
    unknown = sorted(mentioned - allowed)
    return text, unknown
