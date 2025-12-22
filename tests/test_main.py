"""Test basic application health."""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_health_check() -> None:
    """Test the health check endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/health")
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "wump-api"
    assert "version" in data


@pytest.mark.asyncio
async def test_docs_accessible() -> None:
    """Test that API documentation is accessible."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/docs")
        
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_openapi_schema() -> None:
    """Test that OpenAPI schema is accessible."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/openapi.json")
        
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "wump API"
    assert "paths" in schema
