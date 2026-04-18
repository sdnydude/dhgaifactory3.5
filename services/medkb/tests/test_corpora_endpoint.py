import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient

from medkb.main import app
from medkb.db import get_session


@pytest.fixture
async def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
async def client(mock_session):
    async def override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_corpora_returns_empty(client, mock_session):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    resp = await client.get("/v1/corpora")
    assert resp.status_code == 200
    assert resp.json() == []
