"""
OpenTelemetry Observability Module for Neuroglia Framework

This module provides comprehensive OpenTelemetry integration for distributed tracing,
metrics collection, and structured logging with trace correlation.

Key Features:
- Automatic instrumentation for FastAPI, HTTPX, and logging
- TracerProvider and MeterProvider initialization with OTLP exporters
- Context propagation across service boundaries
- Resource detection (service name, version, host information)
- Configurable exporters (OTLP, Console, Jaeger compatibility)
- Decorators for easy manual instrumentation

Multi-App FastAPI Instrumentation:
    For applications with mounted sub-apps, only instrument the main app:

    # ✅ Correct - only instrument main app
    app = FastAPI()
    api_app = FastAPI()
    app.mount("/api", api_app)
    instrument_fastapi_app(app, "my-service")  # Captures all endpoints

    # ❌ Wrong - causes duplicate metrics warnings
    instrument_fastapi_app(app, "main")
    instrument_fastapi_app(api_app, "api")    # Don't do this!

Usage:
    from neuroglia.observability import configure_opentelemetry, get_tracer, trace_async

    # Initialize at application startup
    configure_opentelemetry(
        service_name="my-service",
        service_version="1.0.0",
        otlp_endpoint="http://otel-collector:4317"
    )

    # Get tracer for manual instrumentation
    tracer = get_tracer(__name__)

    # Use decorator for automatic tracing
    @trace_async()
    async def my_function():
        pass
"""

# Metrics Decorators (CR-3)
from neuroglia.observability.decorators import (
    track_latency,
    track_operation,
    track_operation_and_latency,
)
from neuroglia.observability.framework import Observability

# Health Check Providers (CR-2)
from neuroglia.observability.health_checks import (
    HealthCheckProvider,
    HealthCheckResult,
    HttpServiceHealthCheck,
    MongoDBHealthCheck,
    Neo4jHealthCheck,
    QdrantHealthCheck,
    RedisHealthCheck,
)
from neuroglia.observability.logging import (
    configure_logging,
    get_logger_with_trace_context,
    log_with_trace,
)
from neuroglia.observability.metrics import (
    add_metrics_endpoint,
    create_counter,
    create_histogram,
    create_observable_gauge,
    create_up_down_counter,
    get_meter,
    record_metric,
)
from neuroglia.observability.otel_sdk import (
    OpenTelemetryConfig,
    configure_opentelemetry,
    instrument_fastapi_app,
    shutdown_opentelemetry,
)
from neuroglia.observability.settings import (
    ApplicationSettingsWithObservability,
    ObservabilityConfig,
    ObservabilitySettingsMixin,
)
from neuroglia.observability.tracing import (
    add_span_attributes,
    add_span_event,
    get_current_span,
    get_tracer,
    record_exception,
    trace_async,
    trace_sync,
)

# Structlog Integration (CR-1) - Optional
try:
    from neuroglia.observability.structlog_integration import (
        bind_contextvars,
        clear_contextvars,
        configure_structlog,
        get_structlog_logger,
    )

    _STRUCTLOG_AVAILABLE = True
except ImportError:
    _STRUCTLOG_AVAILABLE = False

__all__ = [
    # New Framework-Style Configuration
    "Observability",
    "ObservabilityConfig",
    "ObservabilitySettingsMixin",
    "ApplicationSettingsWithObservability",
    # Legacy Configuration (still supported)
    "OpenTelemetryConfig",
    "configure_opentelemetry",
    "shutdown_opentelemetry",
    # Tracing
    "get_tracer",
    "get_current_span",
    "trace_async",
    "trace_sync",
    "add_span_attributes",
    "add_span_event",
    "record_exception",
    # Metrics
    "get_meter",
    "create_counter",
    "create_histogram",
    "create_up_down_counter",
    "create_observable_gauge",
    "record_metric",
    # Logging
    "configure_logging",
    "get_logger_with_trace_context",
    "log_with_trace",
    # Prometheus and HTTP Instrumentation
    "instrument_fastapi_app",
    "add_metrics_endpoint",
    # Health Check Providers (CR-2)
    "HealthCheckProvider",
    "HealthCheckResult",
    "MongoDBHealthCheck",
    "RedisHealthCheck",
    "Neo4jHealthCheck",
    "QdrantHealthCheck",
    "HttpServiceHealthCheck",
    # Metrics Decorators (CR-3)
    "track_operation",
    "track_latency",
    "track_operation_and_latency",
]

# Add structlog exports if available (CR-1)
if _STRUCTLOG_AVAILABLE:
    __all__.extend(
        [
            "configure_structlog",
            "get_structlog_logger",
            "bind_contextvars",
            "clear_contextvars",
        ]
    )
