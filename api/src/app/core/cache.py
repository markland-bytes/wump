"""Valkey/Redis connection management with async client."""

from typing import Any

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.connection import ConnectionPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheErrorMessage:
    """Standardized cache error messages."""

    CREATE_CLIENT_NO_URL = "Valkey URL is not configured"
    CREATE_CLIENT_POOL_MIN_SIZE = "VALKEY_POOL_SIZE must be at least 1"
    CREATE_CLIENT_FAILED = "Failed to create Valkey client"
    GET_CACHE_FAILED = "Failed to get cache connection"
    CLOSE_CACHE_FAILED = "Failed to close cache connections"


def create_client() -> Redis[bytes]:
    """Create async Redis client with connection pooling.

    Returns:
        Redis[bytes]: Configured async Redis client

    Connection Pool Configuration:
        - max_connections: Maximum connections in the pool (default: 20)
        - decode_responses: Whether to decode responses (False for bytes)
        - socket_connect_timeout: Timeout for socket connection (default: 5s)
        - socket_keepalive: Enable TCP keepalive (True)
        - health_check_interval: Health check interval (30s)

    Raises:
        ValueError: If Valkey URL is invalid or settings are misconfigured
    """
    try:
        if not settings.valkey_url:
            raise ValueError(CacheErrorMessage.CREATE_CLIENT_NO_URL)

        logger.info(
            "Creating async Valkey client",
            url=settings.valkey_url.split("@")[1] if "@" in settings.valkey_url else "***",
            max_connections=20,
        )

        # Create connection pool with configuration
        client = redis.from_url(
            settings.valkey_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )

        return client
    except ValueError:
        raise
    except Exception as e:
        logger.error(
            f"Failed to create Valkey client due to configuration error: {e}"
        )
        raise ValueError(CacheErrorMessage.CREATE_CLIENT_FAILED) from e


# Create client instance
cache_client: Redis[Any] = create_client()


async def get_cache() -> Redis[Any]:
    """FastAPI dependency for cache access.

    Returns:
        Redis[Any]: Cache client for route handlers

    Raises:
        RuntimeError: If cache client cannot be accessed

    Example:
        @app.get("/data")
        async def get_data(cache: Redis = Depends(get_cache)):
            cached = await cache.get("data_key")
            if cached:
                return json.loads(cached)
            # Fetch and cache data
    """
    try:
        # Test connection is alive
        await cache_client.ping()
        return cache_client
    except Exception as e:
        logger.error(f"Cache connection error occurred: {e}")
        raise RuntimeError(CacheErrorMessage.GET_CACHE_FAILED) from e


async def check_cache_connection() -> bool:
    """Check if cache connection is available.

    Used for health checks and diagnostics.

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        await cache_client.ping()
        logger.debug("Cache connection check passed")
        return True
    except Exception as e:
        logger.error(f"Cache connection check failed with error: {e}")
        return False


async def close_cache() -> None:
    """Close all cache connections.

    Should be called during application shutdown.

    Raises:
        RuntimeError: If graceful shutdown fails
    """
    try:
        logger.info("Closing cache connections")
        await cache_client.close()
        # Wait for connection pool to be cleaned up
        await cache_client.connection_pool.disconnect()
    except Exception as e:
        logger.error(f"Error closing cache connections: {e}")
        raise RuntimeError(CacheErrorMessage.CLOSE_CACHE_FAILED) from e
