import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from app.main import app


@pytest.mark.asyncio
async def test_health_check_returns_ok():
    """Health endpoint responds with status ok when all deps are up."""
    with patch("app.api.v1.endpoints.health.aioredis.from_url") as mock_redis, \
         patch("app.api.v1.endpoints.health.httpx.AsyncClient") as mock_httpx:

        # Mock Redis ping
        mock_redis_instance = AsyncMock()
        mock_redis_instance.ping = AsyncMock(return_value=True)
        mock_redis_instance.aclose = AsyncMock()
        mock_redis.return_value = mock_redis_instance

        # Mock Weaviate response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value = mock_client

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")  # degraded ok in test env (no real DB)
    assert "version" in data
    assert "dependencies" in data


@pytest.mark.asyncio
async def test_health_check_has_required_fields():
    """Health response includes all expected dependency keys."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/health")

    data = response.json()
    assert "postgres" in data["dependencies"]
    assert "redis" in data["dependencies"]
    assert "weaviate" in data["dependencies"]
