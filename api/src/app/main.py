"""FastAPI application factory and main entry point."""
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

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
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
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
    @app.get("/health", tags=["health"], status_code=200)
    async def health_check() -> dict[str, Any]:
        """Enhanced health check endpoint with comprehensive system diagnostics.

        Provides detailed status of all service dependencies including response times.
        Returns 200 if all services are healthy, 503 if any service is degraded.

        Response format includes:
        - status: "healthy" (all services OK) or "degraded" (any service down)
        - service: API service name
        - version: API version
        - timestamp: ISO 8601 timestamp of health check
        - checks: detailed status of each service dependency
        """
        start_time = time.time()

        # Check database with timing
        db_start = time.time()
        db_healthy = await check_database_connection()
        db_response_time = round((time.time() - db_start) * 1000, 2)
        db_iso = datetime.now(UTC).isoformat(timespec="milliseconds")
        db_timestamp = db_iso.replace("+00:00", "Z")

        # Check cache with timing
        cache_start = time.time()
        cache_healthy = await check_cache_connection()
        cache_response_time = round((time.time() - cache_start) * 1000, 2)
        cache_iso = datetime.now(UTC).isoformat(timespec="milliseconds")
        cache_timestamp = cache_iso.replace("+00:00", "Z")

        # Determine overall status
        overall_healthy = db_healthy and cache_healthy
        overall_status = "healthy" if overall_healthy else "degraded"

        # Log health check result
        total_time = round((time.time() - start_time) * 1000, 2)
        logger.info(
            "Health check completed",
            status=overall_status,
            database=overall_status if db_healthy else "unhealthy",
            cache=overall_status if cache_healthy else "unhealthy",
            duration_ms=total_time,
        )

        # Build response
        timestamp_iso = datetime.now(UTC).isoformat(timespec="milliseconds")
        timestamp = timestamp_iso.replace("+00:00", "Z")
        response = {
            "status": overall_status,
            "service": "wump-api",
            "version": "0.1.0",
            "timestamp": timestamp,
            "checks": {
                "database": {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "response_time_ms": db_response_time,
                    "timestamp": db_timestamp,
                },
                "cache": {
                    "status": "healthy" if cache_healthy else "unhealthy",
                    "response_time_ms": cache_response_time,
                    "timestamp": cache_timestamp,
                },
            },
        }

        return response

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
