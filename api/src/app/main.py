"""FastAPI application factory and main entry point."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.cache import check_cache_connection, close_cache
from app.core.config import settings
from app.core.database import check_database_connection, close_database
from app.core.logging import configure_logging, get_logger

# Configure logging on module import
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup/shutdown events."""
    # Startup
    logger.info("Starting wump API", version="0.1.0", environment=settings.environment)
    
    yield
    
    # Shutdown
    logger.info("Shutting down wump API")
    await close_database()
    await close_cache()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="wump API",
        description="Who's Using My Package? - Dependency sponsorship discovery API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check() -> dict[str, str | bool]:
        """Health check endpoint with database and cache connectivity status.
        
        Returns 200 if service is healthy, 503 if database or cache is unavailable.
        """
        db_healthy = await check_database_connection()
        cache_healthy = await check_cache_connection()
        
        status_code = "healthy" if (db_healthy and cache_healthy) else "degraded"
        
        if not db_healthy:
            logger.warning("Health check: database connection failed")
        if not cache_healthy:
            logger.warning("Health check: cache connection failed")
        
        return {
            "status": status_code,
            "service": "wump-api",
            "version": "0.1.0",
            "database": "healthy" if db_healthy else "unhealthy",
            "cache": "healthy" if cache_healthy else "unhealthy",
        }

    # TODO: Include API routers
    # app.include_router(packages.router, prefix="/api/v1")
    # app.include_router(organizations.router, prefix="/api/v1")

    logger.info("FastAPI application created", cors_origins=settings.cors_origins_list)
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=not settings.is_production,
        log_config=None,  # Use our structlog config
    )
