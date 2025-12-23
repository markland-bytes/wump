"""Structured logging configuration using structlog."""
import logging
import sys

import structlog
from structlog.types import EventDict, Processor

from app.core.config import settings


def add_app_context(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries."""
    event_dict["service"] = settings.otel_service_name
    event_dict["environment"] = settings.environment
    return event_dict


def configure_logging() -> None:
    """Configure structlog for structured JSON logging."""
    import os
    import sys
    
    # Determine log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Processors for structlog
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_app_context,
        structlog.processors.StackInfoRenderer(),
    ]

    # Check if we're running tests to avoid format_exc_info warning
    is_testing = (
        "pytest" in os.environ.get("_", "") or 
        os.environ.get("PYTEST_CURRENT_TEST") or
        "pytest" in sys.modules
    )
    
    # Add JSON renderer for production, console renderer for development
    if settings.log_format == "json" or settings.is_production or is_testing:
        # JSONRenderer handles exception formatting better than format_exc_info
        # Also skip format_exc_info during testing to avoid warnings
        processors.append(structlog.processors.JSONRenderer())
    else:
        # format_exc_info is only needed for console development output
        processors.append(structlog.processors.format_exc_info)
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    logger: structlog.BoundLogger = structlog.get_logger(name)
    return logger
