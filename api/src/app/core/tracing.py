"""OpenTelemetry configuration and utilities."""
import functools
import os
from typing import Any, Callable, TypeVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.status import Status, StatusCode

from app.core.config import settings

# Type variables for generic decorators
F = TypeVar("F", bound=Callable[..., Any])


def is_tracing_enabled() -> bool:
    """Check if tracing should be enabled.

    Tracing is disabled during tests and when explicitly disabled in config.
    """
    # Disable during tests
    if "pytest" in os.environ.get("_", "") or os.environ.get("PYTEST_CURRENT_TEST"):
        return False

    # Check configuration
    return settings.otel_enabled


def configure_tracing() -> None:
    """Configure OpenTelemetry tracing if enabled."""
    if not is_tracing_enabled():
        return

    # Create resource with service information
    resource = Resource.create({
        "service.name": settings.otel_service_name,
        "service.version": "0.1.0",
        "deployment.environment": settings.environment,
        "service.namespace": "wump",
        "service.instance.id": f"{settings.otel_service_name}-1",
    })

    # Configure tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Add OTLP exporter for Jaeger
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_otlp_endpoint,
        insecure=True,  # For development - should be configurable in production
        headers={}
    )
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Set the tracer provider
    trace.set_tracer_provider(tracer_provider)


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance for the given module name."""
    return trace.get_tracer(name)


def instrument_fastapi_app(app: Any) -> None:
    """Instrument FastAPI app with OpenTelemetry if tracing is enabled."""
    if not is_tracing_enabled():
        return

    FastAPIInstrumentor.instrument_app(app)


def create_span(tracer: trace.Tracer, name: str, **attributes: Any) -> Any:
    """Create a span if tracing is enabled, otherwise return a no-op context manager."""
    if not is_tracing_enabled():
        return _NoOpSpan()

    span = tracer.start_span(name)
    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, str(value))
    return span


# Tracing Decorators

def trace_async(
    span_name: str | None = None,
    tracer_name: str | None = None,
    **span_attributes: Any
) -> Callable[[F], F]:
    """Decorator to trace async functions with OpenTelemetry spans.
    
    Args:
        span_name: Custom span name. If None, uses module.function_name
        tracer_name: Custom tracer name. If None, uses function's module
        **span_attributes: Additional span attributes to set
    
    Example:
        @trace_async("cache.check_connection", cache_type="redis")
        async def check_cache_connection() -> bool:
            return await cache_client.ping()
    """
    def decorator(func: F) -> F:
        if not is_tracing_enabled():
            return func
            
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer(tracer_name or func.__module__)
            name = span_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_span(name) as span:
                # Set provided attributes
                for key, value in span_attributes.items():
                    if value is not None:
                        span.set_attribute(key, str(value))
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    raise
        
        return async_wrapper  # type: ignore
    return decorator


def trace_sync(
    span_name: str | None = None,
    tracer_name: str | None = None,
    **span_attributes: Any
) -> Callable[[F], F]:
    """Decorator to trace synchronous functions with OpenTelemetry spans.
    
    Args:
        span_name: Custom span name. If None, uses module.function_name
        tracer_name: Custom tracer name. If None, uses function's module
        **span_attributes: Additional span attributes to set
    
    Example:
        @trace_sync("config.load_settings", component="database")
        def load_database_config() -> dict:
            return {"host": "localhost", "port": 5432}
    """
    def decorator(func: F) -> F:
        if not is_tracing_enabled():
            return func
            
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer(tracer_name or func.__module__)
            name = span_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_span(name) as span:
                # Set provided attributes
                for key, value in span_attributes.items():
                    if value is not None:
                        span.set_attribute(key, str(value))
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    raise
        
        return sync_wrapper  # type: ignore
    return decorator


def trace_database(operation: str | None = None) -> Callable[[F], F]:
    """Specialized decorator for database operations.
    
    Args:
        operation: Database operation type. If None, uses function name
    
    Example:
        @trace_database()
        async def check_database_connection() -> bool:
            # Database health check logic
            return True
    """
    def decorator(func: F) -> F:
        op_name = operation or func.__name__
        return trace_async(
            span_name=op_name,
            **{
                "db.operation": op_name,
                "db.system": "postgresql",
                "component": "database"
            }
        )(func)
    return decorator


def trace_cache(operation: str | None = None) -> Callable[[F], F]:
    """Specialized decorator for cache operations.
    
    Args:
        operation: Cache operation type. If None, uses function name
    
    Example:
        @trace_cache()
        async def check_cache_connection() -> bool:
            # Cache health check logic
            return True
    """
    def decorator(func: F) -> F:
        op_name = operation or func.__name__
        return trace_async(
            span_name=op_name,
            **{
                "cache.operation": op_name,
                "cache.system": "redis",
                "component": "cache"
            }
        )(func)
    return decorator


class _NoOpSpan:
    """No-op span for when tracing is disabled."""

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass
