"""OpenTelemetry configuration and utilities."""
import os
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import settings


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
    })

    # Configure tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Add OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_otlp_endpoint,
        insecure=True,  # For development - should be configurable in production
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
