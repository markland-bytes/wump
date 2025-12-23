"""Test basic application health."""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
import time

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
async def test_health_check_response_structure() -> None:
    """Test that health check response has correct structure."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/health")
        
    assert response.status_code == 200
    data = response.json()
    
    # Check required top-level fields
    assert "status" in data
    assert "service" in data
    assert "version" in data
    assert "timestamp" in data
    assert "checks" in data
    
    # Check required checks fields
    assert "database" in data["checks"]
    assert "cache" in data["checks"]
    
    # Check database check structure
    db_check = data["checks"]["database"]
    assert "status" in db_check
    assert "response_time_ms" in db_check
    assert "timestamp" in db_check
    
    # Check cache check structure
    cache_check = data["checks"]["cache"]
    assert "status" in cache_check
    assert "response_time_ms" in cache_check
    assert "timestamp" in cache_check


@pytest.mark.asyncio
async def test_health_check_response_values() -> None:
    """Test that health check response contains expected values."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/health")
        
    data = response.json()
    
    assert data["service"] == "wump-api"
    assert data["version"] == "0.1.0"
    assert data["status"] in ["healthy", "degraded"]
    
    # Check that statuses are valid
    for service in ["database", "cache"]:
        assert data["checks"][service]["status"] in ["healthy", "unhealthy"]
        assert isinstance(data["checks"][service]["response_time_ms"], (int, float))
        assert data["checks"][service]["response_time_ms"] >= 0


@pytest.mark.asyncio
async def test_health_check_timestamps_iso8601() -> None:
    """Test that timestamps are in ISO 8601 format."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/health")
        
    data = response.json()
    
    # Check timestamp format (should end with Z for UTC)
    assert data["timestamp"].endswith("Z")
    assert data["checks"]["database"]["timestamp"].endswith("Z")
    assert data["checks"]["cache"]["timestamp"].endswith("Z")


@pytest.mark.asyncio
async def test_health_check_response_time_tracking() -> None:
    """Test that response times are tracked for each service."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/health")
        
    data = response.json()
    
    # Response times should be present and non-negative
    db_time = data["checks"]["database"]["response_time_ms"]
    cache_time = data["checks"]["cache"]["response_time_ms"]
    
    assert db_time >= 0
    assert cache_time >= 0
    assert isinstance(db_time, (int, float))
    assert isinstance(cache_time, (int, float))


@pytest.mark.asyncio
async def test_health_check_all_healthy() -> None:
    """Test health check when all services are healthy."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/health")
        
    assert response.status_code == 200
    data = response.json()
    
    # Should return healthy only if both services are healthy
    if (data["checks"]["database"]["status"] == "healthy" and 
        data["checks"]["cache"]["status"] == "healthy"):
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_database_unhealthy_returns_degraded() -> None:
    """Test health check returns degraded when database is unhealthy."""
    with patch('app.core.database.check_database_connection', new_callable=AsyncMock) as mock_db:
        mock_db.return_value = False
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["checks"]["database"]["status"] == "unhealthy"
        assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_check_cache_unhealthy_returns_degraded() -> None:
    """Test health check returns degraded when cache is unhealthy."""
    with patch('app.core.cache.check_cache_connection', new_callable=AsyncMock) as mock_cache:
        mock_cache.return_value = False
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["checks"]["cache"]["status"] == "unhealthy"
        assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_check_both_unhealthy_returns_degraded() -> None:
    """Test health check returns degraded when both services are unhealthy."""
    with patch('app.core.database.check_database_connection', new_callable=AsyncMock) as mock_db, \
         patch('app.core.cache.check_cache_connection', new_callable=AsyncMock) as mock_cache:
        
        mock_db.return_value = False
        mock_cache.return_value = False
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["checks"]["database"]["status"] == "unhealthy"
        assert data["checks"]["cache"]["status"] == "unhealthy"
        assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_check_always_returns_200() -> None:
    """Test that health check endpoint always returns 200 status code."""
    # Even when services are unhealthy, we return 200 (the response body indicates degraded status)
    with patch('app.core.database.check_database_connection', new_callable=AsyncMock) as mock_db, \
         patch('app.core.cache.check_cache_connection', new_callable=AsyncMock) as mock_cache:
        
        mock_db.return_value = False
        mock_cache.return_value = False
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/health")
        
        # The endpoint always returns 200, status field indicates degradation
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_check_response_is_json() -> None:
    """Test that health check response is valid JSON."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/health")
        
    assert response.status_code == 200
    
    # Should not raise an exception
    data = response.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_health_check_response_time_reasonable() -> None:
    """Test that health check completes in reasonable time."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        start = time.time()
        response = await client.get("/health")
        elapsed = time.time() - start
        
    assert response.status_code == 200
    # Health check should complete in under 5 seconds
    assert elapsed < 5.0


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
