import pytest
from httpx import ASGITransport, AsyncClient

from medkb.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_healthz_returns_200(client):
    resp = await client.get("/v1/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_metrics_returns_prometheus_format(client):
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "medkb_query_requests" in resp.text
