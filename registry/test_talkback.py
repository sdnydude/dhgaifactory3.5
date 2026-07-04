"""
Talkback Service + Endpoint Tests
=================================
Unit tests for talkback_service.py (citation URL mapping, retrieval) and the
POST /api/talkback SSE endpoint (event ordering, validation, model routing).

Run with: pytest registry/test_talkback.py -v
"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ── Helpers ─────────────────────────────────────────────────────────────


def _make_page(**overrides):
    """Mock row matching the DocPage ORM fields talkback consumes."""
    row = MagicMock()
    row.project_name = overrides.get("project_name", "portage")
    row.source_file = overrides.get("source_file", "api/admin.md")
    row.title = overrides.get("title", "Admin API")
    row.content = overrides.get("content", "Admin endpoints for Portage.")
    return row


def _parse_sse(body: str):
    """Parse an SSE body into a list of (event, data_dict) tuples."""
    events = []
    current_event = None
    for line in body.splitlines():
        if line.startswith("event: "):
            current_event = line[len("event: "):]
        elif line.startswith("data: "):
            events.append((current_event, json.loads(line[len("data: "):])))
    return events


# ── _citation_url ───────────────────────────────────────────────────────


def test_citation_url_maps_docs_site_paths():
    import talkback_service as svc

    assert svc._citation_url("portage", "api/admin.md") == "/portage/api/admin/"


def test_citation_url_maps_index_to_directory_root():
    import talkback_service as svc

    assert svc._citation_url("portage", "ship-log/index.md") == "/portage/ship-log/"


def test_citation_url_none_for_non_docs_site_project():
    import talkback_service as svc

    assert svc._citation_url("claude-code-tresor", "README.md") is None


# ── retrieve ────────────────────────────────────────────────────────────


def test_retrieve_dedupes_citations_and_builds_context():
    import talkback_service as svc

    pages = [
        _make_page(source_file="api/admin.md", content="chunk one"),
        _make_page(source_file="api/admin.md", content="chunk two"),
        _make_page(source_file="features.md", title="Features", content="chunk three"),
    ]
    with patch.object(svc, "get_embedding", new=AsyncMock(return_value=[0.1] * 768)), \
         patch.object(svc.doc_pages_service, "search_doc_pages", return_value=pages):
        citations, context = asyncio.run(svc.retrieve(MagicMock(), "how do admin endpoints work?"))

    assert len(citations) == 2  # deduped by (project, source_file)
    assert citations[0].url == "/portage/api/admin/"
    assert "chunk one" in context and "chunk two" in context and "chunk three" in context


def test_retrieve_empty_results_gives_empty_context():
    import talkback_service as svc

    with patch.object(svc, "get_embedding", new=AsyncMock(return_value=None)), \
         patch.object(svc.doc_pages_service, "search_doc_pages", return_value=[]):
        citations, context = asyncio.run(svc.retrieve(MagicMock(), "unknown topic?"))

    assert citations == []
    assert context == ""


# ── endpoint (SSE) ──────────────────────────────────────────────────────


async def _fake_stream(question, context):
    yield "Hello "
    yield "world."


def test_talkback_endpoint_streams_citations_then_deltas_then_done(client):
    import talkback_service as svc

    fake_citation = svc.TalkbackCitation(
        title="Admin API", project="portage",
        source_file="api/admin.md", url="/portage/api/admin/",
    )
    with patch.object(svc, "retrieve", new=AsyncMock(return_value=([fake_citation], "ctx"))), \
         patch.object(svc, "stream_local", new=_fake_stream):
        resp = client.post("/api/talkback", json={"question": "how do admin endpoints work?"})

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse(resp.text)
    kinds = [e[0] for e in events]
    assert kinds[0] == "citations"
    assert "delta" in kinds
    assert kinds[-1] == "done"
    assert events[0][1]["citations"][0]["url"] == "/portage/api/admin/"
    deltas = "".join(d["text"] for k, d in events if k == "delta")
    assert deltas == "Hello world."


def test_talkback_endpoint_rejects_short_question(client):
    resp = client.post("/api/talkback", json={"question": "hi"})
    assert resp.status_code == 422


def test_talkback_endpoint_haiku_without_key_yields_error_event(client, monkeypatch):
    import talkback_service as svc

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fake_citation = svc.TalkbackCitation(
        title="Admin API", project="portage",
        source_file="api/admin.md", url="/portage/api/admin/",
    )
    with patch.object(svc, "retrieve", new=AsyncMock(return_value=([fake_citation], "ctx"))):
        resp = client.post(
            "/api/talkback",
            json={"question": "how do admin endpoints work?", "model": "haiku"},
        )

    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    kinds = [e[0] for e in events]
    assert kinds[0] == "citations"
    assert "error" in kinds
