"""FastAPI application factory and main entry point."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.core.config import settings
from src.app.core.logging import configure_logging, get_logger

# Configure logging on module import
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup/shutdown events."""
    # Startup
    logger.info("Starting wump API", version="0.1.0", environment=settings.environment)
    
    # TODO: Initialize database connection pool
    # TODO: Initialize Valkey/Redis connection
    # TODO: Initialize OpenTelemetry (if enabled)
    
    yield
    
    # Shutdown
    logger.info("Shutting down wump API")
    # TODO: Close database connections
    # TODO: Close Valkey/Redis connections


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
    async def health_check() -> dict[str, str]:
        """Basic health check endpoint."""
        return {
            "status": "healthy",
            "service": "wump-api",
            "version": "0.1.0",
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
