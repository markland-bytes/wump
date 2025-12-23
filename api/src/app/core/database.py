"""Database connection management with async SQLAlchemy."""

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class DBErrorMessage:
    """Standardized database error messages."""
    CREATE_ENGINE_NO_URL = "Database URL is not configured"
    CREATE_ENGINE_MIN_DB_POOL_SIZE = "DATABASE_POOL_SIZE must be at least 1"
    CREATE_ENGINE_NEGATIVE_MAX_OVERFLOW = "DATABASE_MAX_OVERFLOW must be non-negative"
    CREATE_ENGINE_FAILED = "Failed to create database engine"
    
    GET_DB_SESSION_FAILED = "Failed to create database session"
    CLOSE_DATABASE_FAILED = "Failed to close database connections"


def create_engine() -> AsyncEngine:
    """Create AsyncEngine with connection pooling configuration.
    
    Returns:
        AsyncEngine: Configured async SQLAlchemy engine
        
    Connection Pool Configuration:
        - pool_size: Number of connections to keep in the pool (default: 20)
        - max_overflow: Maximum overflow connections (default: 10)
        - pool_timeout: Timeout for acquiring a connection (default: 30s)
        - echo: Log all SQL statements (False in production)
        
    Raises:
        ValueError: If database URL is invalid or settings are misconfigured
    """
    try:
        if not settings.database_url:
            raise ValueError(DBErrorMessage.CREATE_ENGINE_NO_URL)
            
        if settings.database_pool_size < 1:
            raise ValueError(DBErrorMessage.CREATE_ENGINE_MIN_DB_POOL_SIZE)
            
        if settings.database_max_overflow < 0:
            raise ValueError(DBErrorMessage.CREATE_ENGINE_NEGATIVE_MAX_OVERFLOW)
        
        logger.info(
            "Creating async database engine",
            url=settings.database_url.split("@")[1] if "@" in settings.database_url else "***",
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
        )
        
        engine = create_async_engine(
            settings.database_url,
            echo=False,  # Set to True for SQL logging
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,  # Test connections before using them
            pool_recycle=3600,  # Recycle connections after 1 hour
        )
        
        return engine
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to create database engine, due to configuration error: {e}")
        raise ValueError(DBErrorMessage.CREATE_ENGINE_FAILED) from e


# Create engine instance
engine: AsyncEngine = create_engine()

# Create async session factory
async_session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.
    
    Yields:
        AsyncSession: Database session for route handlers
        
    Raises:
        RuntimeError: If database session cannot be created
        
    Example:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    session = async_session_maker()
    try:
        async with session:
            yield session
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error occurred: {e}")
        raise RuntimeError(DBErrorMessage.GET_DB_SESSION_FAILED) from e


async def check_database_connection() -> bool:
    """Check if database connection is available.
    
    Used for health checks and diagnostics.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.debug("Database connection check passed")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed with error: {e}")
        return False


async def close_database() -> None:
    """Close all database connections.
    
    Should be called during application shutdown.
    
    Raises:
        RuntimeError: If graceful shutdown fails (connection closure is attempted once)
    """
    try:
        logger.info("Closing database connections")
        await engine.dispose()
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
        raise RuntimeError(DBErrorMessage.CLOSE_DATABASE_FAILED) from e
