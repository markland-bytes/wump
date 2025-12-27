"""Shared pytest fixtures for test suite."""

import asyncio
import os
from collections.abc import AsyncGenerator
from typing import Any

# Set test environment variables BEFORE any app imports
# This ensures tracing and other features are disabled during app initialization
os.environ["ENVIRONMENT"] = "testing"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["OTEL_ENABLED"] = "false"  # Disable OpenTelemetry to prevent background threads
os.environ["VALKEY_URL"] = ""  # Prevent cache client creation at module load - tests use FakeRedis

import pytest
import pytest_asyncio
import redis.asyncio as redis
from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.main import app
from app.models.base import Base


# Additional test environment setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment() -> None:
    """Setup additional test environment variables.

    Note: Critical environment variables (ENVIRONMENT, LOG_LEVEL, OTEL_ENABLED)
    are set at module level to ensure they're applied before app initialization.

    VALKEY_URL is intentionally NOT set here - tests default to FakeRedis (in-memory).
    Set VALKEY_URL environment variable to use real Redis/Valkey for testing.
    """
    pass


# @pytest.fixture(scope="session")
# def event_loop():
#     """Create an event loop for the test session."""
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Get settings configured for testing.

    Returns:
        Settings: Test environment settings
    """
    return Settings(
        environment="testing",
        log_level="WARNING",
    )


# ===== Database Fixtures =====


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create test database engine for the session.

    Creates tables before tests and drops them after.
    Uses SQLite in-memory database by default for test isolation.

    Yields:
        AsyncEngine: Test database engine
    """
    # Use SQLite in-memory for tests by default
    # Can be overridden with DATABASE_URL environment variable (e.g., for PostgreSQL integration tests)
    database_url = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///:memory:"
    )

    # Configure engine based on database type
    if database_url.startswith("sqlite"):
        # SQLite doesn't use connection pooling the same way
        engine = create_async_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False},  # Required for SQLite with async
        )
    else:
        # PostgreSQL or other databases
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=5,  # Smaller pool for tests
            max_overflow=5,
            pool_pre_ping=True,
        )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create a clean test database session with transaction rollback.

    Each test gets a fresh session that rolls back after the test,
    ensuring test isolation.

    Args:
        test_engine: Test database engine

    Yields:
        AsyncSession: Clean database session for testing
    """
    # Create session factory
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Create session and start transaction
    async with async_session_maker() as session:
        transaction = await session.begin()
        try:
            yield session
        finally:
            # Always rollback to ensure test isolation
            await transaction.rollback()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_session: AsyncSession) -> AsyncSession:
    """Alias for test_session to match common naming convention.

    Args:
        test_session: Test session fixture

    Returns:
        AsyncSession: Database session for testing
    """
    return test_session


@pytest_asyncio.fixture(scope="session")
async def verify_test_database() -> bool:
    """Verify test database connection is available.

    Returns:
        bool: True if database is accessible

    Raises:
        RuntimeError: If database connection fails
    """
    database_url = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///:memory:"
    )

    # Configure engine based on database type
    if database_url.startswith("sqlite"):
        engine = create_async_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False},
        )
    else:
        engine = create_async_engine(database_url, echo=False)

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        raise RuntimeError(f"Test database connection failed: {e}") from e
    finally:
        await engine.dispose()


# ===== Cache Fixtures =====


@pytest_asyncio.fixture(scope="session")
async def test_cache() -> AsyncGenerator[Redis, None]:
    """Create test cache client.

    Uses FakeRedis (in-memory) by default for test isolation.
    Can be overridden with VALKEY_URL environment variable for real Redis/Valkey testing.

    Yields:
        Redis: Test cache client (FakeRedis or real Redis)
    """
    cache_url = os.getenv("VALKEY_URL", None)

    # Use FakeRedis by default (in-memory, no service needed)
    if cache_url is None:
        client: Redis = FakeAsyncRedis(
            decode_responses=True,
        )
    else:
        # Use real Redis/Valkey if URL is provided
        client = redis.from_url(  # type: ignore[no-untyped-call]
            cache_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=5,
            socket_connect_timeout=5,
        )

    # Verify connection
    try:
        await client.ping()
    except Exception as e:
        await client.close()
        raise RuntimeError(f"Test cache connection failed: {e}") from e

    yield client

    # Cleanup
    await client.close()


@pytest_asyncio.fixture(scope="function")
async def cache(test_cache: Redis) -> AsyncGenerator[Redis, None]:
    """Provide clean cache for each test with automatic cleanup.

    Flushes the test cache database before and after each test.

    Args:
        test_cache: Session-scoped cache client

    Yields:
        Redis: Clean cache client for testing
    """
    # Clear cache before test
    await test_cache.flushdb()

    yield test_cache

    # Clear cache after test
    await test_cache.flushdb()


# ===== API Client Fixtures =====


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing.

    Yields:
        AsyncClient: HTTP client for testing FastAPI endpoints

    Example:
        async def test_endpoint(async_client: AsyncClient):
            response = await async_client.get("/health")
            assert response.status_code == 200
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def api_client(async_client: AsyncClient) -> AsyncClient:
    """Alias for async_client to match common naming convention.

    Args:
        async_client: Async client fixture

    Returns:
        AsyncClient: HTTP client for testing
    """
    return async_client


# ===== Utility Fixtures =====


@pytest.fixture
def anyio_backend() -> str:
    """Specify asyncio as the backend for anyio tests.

    Returns:
        str: Backend name
    """
    return "asyncio"
