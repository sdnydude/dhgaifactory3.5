import os
import sys

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import app


@pytest.mark.asyncio
async def test_list_projects_returns_real_rows() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.get("/api/cme/export/projects?limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert "projects" in body
    assert isinstance(body["projects"], list)
    assert body["limit"] == 5
    if body["projects"]:
        item = body["projects"][0]
        for k in ("id", "name", "status", "document_count"):
            assert k in item


@pytest.mark.asyncio
async def test_list_projects_search_filter() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.get(
            "/api/cme/export/projects?search=zzz_not_a_real_project"
        )
    assert resp.status_code == 200
    assert resp.json()["projects"] == []


@pytest.mark.asyncio
async def test_project_documents_returns_current_versions() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        list_resp = await c.get("/api/cme/export/projects?limit=1")
        projects = list_resp.json()["projects"]
        if not projects:
            pytest.skip("no projects in DB to exercise the endpoint")
        pid = projects[0]["id"]

        docs_resp = await c.get(
            f"/api/cme/export/projects/{pid}/documents"
        )
    assert docs_resp.status_code == 200
    body = docs_resp.json()
    assert body["project_id"] == pid
    assert isinstance(body["documents"], list)
    for d in body["documents"]:
        assert d["is_current"] is True
