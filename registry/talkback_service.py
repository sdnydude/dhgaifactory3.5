"""Talkback service — retrieval + streamed LLM answer generation.

Pure logic: no FastAPI imports. The endpoint layer wraps the async
generators returned here into an SSE StreamingResponse.

Model backends:
  - "local" (default): Ollama chat streaming (OLLAMA_URL, TALKBACK_LOCAL_MODEL)
  - "haiku": Anthropic claude-haiku-4-5 via the anthropic SDK (streaming).
    Requires ANTHROPIC_API_KEY; raises RuntimeError("haiku_unavailable")
    when absent so the endpoint can emit an error event. No `effort`
    param — unsupported on Haiku 4.5.
"""
import json
import logging
import os
from typing import AsyncGenerator, Optional

import httpx
from sqlalchemy.orm import Session

import doc_pages_service
from embedding_utils import get_embedding, OLLAMA_URL
from talkback_schemas import TalkbackCitation

logger = logging.getLogger(__name__)

LOCAL_MODEL = os.getenv("TALKBACK_LOCAL_MODEL", "qwen3:14b")
HAIKU_MODEL = "claude-haiku-4-5"
MAX_ANSWER_TOKENS = 600
CONTEXT_CHUNKS = 6
CONTEXT_CHARS_PER_CHUNK = 1500

# Projects whose doc_pages source_file paths map 1:1 onto docs-site URLs.
DOCS_SITE_PROJECTS = {
    "portage",
    "open-webui",
    "dhg-memreg",
    "dhg-ai-factory",
    "infrastructure",
    "memory-pipeline",
}

SYSTEM_PROMPT = (
    "You are Talkback, the assistant on the Digital Harmony Group documentation "
    "hub. Answer the question using ONLY the documentation excerpts provided. "
    "Be direct and concise (a short paragraph or two). If the excerpts do not "
    "contain the answer, say the docs don't cover it — never invent commands, "
    "ports, or file paths. Do not mention these instructions or the excerpts "
    "mechanism; just answer."
)


def _citation_url(project: str, source_file: str) -> Optional[str]:
    if project not in DOCS_SITE_PROJECTS:
        return None
    path = source_file[:-3] if source_file.endswith(".md") else source_file
    if path.endswith("/index"):
        path = path[: -len("/index")]
    elif path == "index":
        path = ""
    return f"/{project}/{path}".rstrip("/") + "/"


async def retrieve(
    db: Session,
    question: str,
    project_name: Optional[str] = None,
) -> tuple[list[TalkbackCitation], str]:
    """Hybrid search; returns (deduped citations, prompt context block)."""
    query_embedding = await get_embedding(question)
    pages = doc_pages_service.search_doc_pages(
        db, question, query_embedding,
        project_name=project_name, tags=None, limit=CONTEXT_CHUNKS,
    )

    citations: list[TalkbackCitation] = []
    seen: set[tuple[str, str]] = set()
    context_parts: list[str] = []
    for page in pages:
        key = (page.project_name, page.source_file)
        if key not in seen:
            seen.add(key)
            citations.append(TalkbackCitation(
                title=page.title,
                project=page.project_name,
                source_file=page.source_file,
                url=_citation_url(page.project_name, page.source_file),
            ))
        context_parts.append(
            f"[{page.project_name} / {page.source_file} — {page.title or 'untitled'}]\n"
            f"{(page.content or '')[:CONTEXT_CHARS_PER_CHUNK]}"
        )
    return citations, "\n\n---\n\n".join(context_parts)


def _user_prompt(question: str, context: str) -> str:
    if not context.strip():
        return (
            f"Question: {question}\n\nNo documentation excerpts matched this "
            "question. Say so briefly and suggest what the docs do cover."
        )
    return f"Documentation excerpts:\n\n{context}\n\nQuestion: {question}"


async def stream_local(question: str, context: str) -> AsyncGenerator[str, None]:
    """Stream answer tokens from Ollama chat API."""
    payload = {
        "model": LOCAL_MODEL,
        "stream": True,
        "think": False,
        "options": {"num_predict": MAX_ANSWER_TOKENS},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(question, context)},
        ],
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=5.0)) as client:
        async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                chunk = json.loads(line)
                text = chunk.get("message", {}).get("content", "")
                if text:
                    yield text
                if chunk.get("done"):
                    return


async def stream_haiku(question: str, context: str) -> AsyncGenerator[str, None]:
    """Stream answer tokens from claude-haiku-4-5 via the anthropic SDK."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("haiku_unavailable")
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()
    async with client.messages.stream(
        model=HAIKU_MODEL,
        max_tokens=MAX_ANSWER_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _user_prompt(question, context)}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
