"""Request ID middleware for distributed tracing."""
import time
import uuid
from contextvars import ContextVar

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

# Context variable for storing request ID
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and track unique request IDs for distributed tracing.
    
    This middleware:
    - Generates a unique UUID4 for each incoming request
    - Adds the request ID to response headers as 'X-Request-ID'
    - Stores the request ID in contextvars for use throughout the request lifecycle
    - Logs request start and completion with timing information
    - Integrates with structlog's contextvars for automatic inclusion in all logs
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process incoming request with request ID generation and logging."""
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Store in contextvar for use throughout request
        request_id_var.set(request_id)
        
        # Bind to structlog context for automatic inclusion in all logs
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        # Record start time
        start_time = time.time()
        
        # Log request start
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params) if request.query_params else None,
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Calculate duration
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            # Log request completion
            logger.info(
                "Request completed",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            
            return response
            
        except Exception as exc:
            # Calculate duration for error case
            duration_ms = round((time.time() - start_time) * 1000, 2)
            
            # Log request error
            logger.error(
                "Request failed",
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=duration_ms,
                exc_info=True,
            )
            
            # Re-raise the exception
            raise
        
        finally:
            # Clear contextvars for this request
            structlog.contextvars.clear_contextvars()


def get_request_id() -> str:
    """Get the current request ID from context.
    
    Returns:
        The current request ID, or empty string if no request is active.
    """
    return request_id_var.get("")