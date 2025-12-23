"""Request ID middleware for distributed tracing."""
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

import structlog
from fastapi import Request, Response
from opentelemetry.trace.status import Status, StatusCode
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.core.tracing import create_span, get_tracer

# Context variable for storing request ID
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to generate and track unique request IDs for distributed tracing.

    This middleware:
    - Generates a unique UUID4 for each incoming request
    - Adds the request ID to response headers as 'X-Request-ID'
    - Stores the request ID in contextvars for use throughout the request lifecycle
    - Logs request start and completion with timing information
    - Integrates with structlog's contextvars for automatic inclusion in all logs
    - Creates OpenTelemetry spans for distributed tracing (when enabled)
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process incoming request with request ID generation and logging."""
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Store in contextvar for use throughout request
        request_id_var.set(request_id)

        # Bind to structlog context for automatic inclusion in all logs
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Create OpenTelemetry span if tracing is enabled
        with create_span(
            tracer,
            f"{request.method} {request.url.path}",
            **{
                "http.method": request.method,
                "http.url": str(request.url),
                "http.route": request.url.path,
                "request.id": request_id,
                "user_agent.original": request.headers.get("user-agent", ""),
            }
        ) as span:
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

                # Update span with response information
                span.set_attribute("http.status_code", response.status_code)
                content_length = response.headers.get("content-length", "0")
                span.set_attribute("http.response.size", len(content_length))
                span.set_attribute("request.duration_ms", duration_ms)

                # Set span status based on HTTP status code
                if response.status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR, f"HTTP {response.status_code}"))
                else:
                    span.set_status(Status(StatusCode.OK))

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

                # Update span with error information
                span.record_exception(exc)
                span.set_attribute("request.duration_ms", duration_ms)
                span.set_status(Status(StatusCode.ERROR, str(exc)))

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
