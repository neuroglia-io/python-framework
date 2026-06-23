"""
OpenTelemetry SDK configuration and initialization.

This module handles low-level OpenTelemetry SDK setup including:
- Resource configuration with service metadata
- Instrumentation providers setup (tracing, metrics, logging)
- OTLP exporters configuration
- Batch processing and performance tuning
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)

# Optional OpenTelemetry imports with graceful degradation
try:
    # Core OpenTelemetry
    from opentelemetry import baggage, trace
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,
    )

    # OTLP Exporters
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    # Prometheus metrics (optional)
    try:
        from opentelemetry.exporter.prometheus import PrometheusMetricReader
    except ImportError:
        PrometheusMetricReader = None

    # Auto-instrumentation
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import (
        BatchLogRecordProcessor,
        ConsoleLogExporter,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import (
        ConsoleMetricExporter,
        PeriodicExportingMetricReader,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    OTEL_AVAILABLE = True
    log.debug("✓ OpenTelemetry dependencies loaded successfully")

except ImportError as e:
    OTEL_AVAILABLE = False
    log.warning(f"⚠️ OpenTelemetry dependencies not available: {e}")

    # Provide stub classes for graceful degradation
    class MockResource:
        @classmethod
        def create(cls, attributes=None):
            return cls()

    class MockProvider:
        pass

    Resource = MockResource
    TracerProvider = MockProvider
    MeterProvider = MockProvider
    LoggerProvider = MockProvider


@dataclass
class OpenTelemetryConfig:
    """
    OpenTelemetry SDK configuration with comprehensive settings.

    This configuration controls all aspects of OpenTelemetry initialization
    including resource attributes, exporters, instrumentation, and performance tuning.
    """

    # Service identification
    service_name: str
    service_version: str = "unknown"
    deployment_environment: str = "development"

    # OTLP export configuration
    otlp_endpoint: str = "http://localhost:4317"
    enable_console_export: bool = False

    # Resource attributes (merged with standard attributes)
    additional_resource_attributes: dict[str, str] = field(default_factory=dict)

    # Instrumentation controls
    enable_fastapi_instrumentation: bool = True
    enable_httpx_instrumentation: bool = True
    enable_logging_instrumentation: bool = True
    enable_system_metrics: bool = False

    # Performance and batch processing
    batch_span_processor_max_queue_size: int = 2048
    batch_span_processor_schedule_delay_millis: int = 5000
    batch_span_processor_max_export_batch_size: int = 512

    # Metrics configuration
    metric_export_interval_millis: int = 60000  # 1 minute
    metric_export_timeout_millis: int = 30000  # 30 seconds

    def get_resource_attributes(self) -> dict[str, str]:
        """
        Get complete resource attributes including service metadata.

        Returns:
            Dictionary of resource attributes for OpenTelemetry Resource
        """
        # Standard service attributes
        attributes = {
            "service.name": self.service_name,
            "service.version": self.service_version,
            "deployment.environment": self.deployment_environment,
        }

        # Add additional custom attributes
        attributes.update(self.additional_resource_attributes)

        # Add environment-based attributes
        if hostname := os.getenv("HOSTNAME"):
            attributes["host.name"] = hostname
        if k8s_pod := os.getenv("K8S_POD_NAME"):
            attributes["k8s.pod.name"] = k8s_pod
        if k8s_namespace := os.getenv("K8S_NAMESPACE"):
            attributes["k8s.namespace.name"] = k8s_namespace

        return attributes


def configure_opentelemetry(
    service_name: str,
    service_version: str = "unknown",
    otlp_endpoint: str = "http://localhost:4317",
    enable_console_export: bool = False,
    deployment_environment: str = "development",
    additional_resource_attributes: Optional[dict[str, str]] = None,
    # Instrumentation controls
    enable_fastapi_instrumentation: bool = True,
    enable_httpx_instrumentation: bool = True,
    enable_logging_instrumentation: bool = True,
    enable_system_metrics: bool = False,
    # Performance tuning
    batch_span_processor_max_queue_size: int = 2048,
    batch_span_processor_schedule_delay_millis: int = 5000,
    batch_span_processor_max_export_batch_size: int = 512,
    # Metrics
    metric_export_interval_millis: int = 60000,
    metric_export_timeout_millis: int = 30000,
) -> None:
    """
    Configure OpenTelemetry SDK with comprehensive observability setup.

    This function initializes the complete OpenTelemetry stack including:
    - Resource configuration with service metadata
    - Tracing with OTLP and optional console export
    - Metrics with Prometheus and OTLP export
    - Logging instrumentation with trace correlation
    - Auto-instrumentation for FastAPI, HTTPX, and system metrics

    Args:
        service_name: Name of the service for telemetry identification
        service_version: Version of the service (e.g., "1.2.3")
        otlp_endpoint: OpenTelemetry Collector endpoint (e.g., "http://otel-collector:4317")
        enable_console_export: Enable console exporters for development/debugging
        deployment_environment: Environment name (development, staging, production)
        additional_resource_attributes: Custom resource attributes to include
        enable_fastapi_instrumentation: Enable automatic FastAPI tracing
        enable_httpx_instrumentation: Enable automatic HTTPX client tracing
        enable_logging_instrumentation: Enable logging with trace correlation
        enable_system_metrics: Enable system metrics collection (CPU, memory, etc.)
        batch_span_processor_max_queue_size: Maximum spans in batch processor queue
        batch_span_processor_schedule_delay_millis: Batch export delay in milliseconds
        batch_span_processor_max_export_batch_size: Maximum spans per export batch
        metric_export_interval_millis: Metrics export interval in milliseconds
        metric_export_timeout_millis: Metrics export timeout in milliseconds

    Raises:
        RuntimeError: If OpenTelemetry dependencies are not available
    """
    if not OTEL_AVAILABLE:
        raise RuntimeError("OpenTelemetry dependencies not available. " "Install with: pip install opentelemetry-distro opentelemetry-exporter-otlp")

    global _config

    # Create configuration object
    config = OpenTelemetryConfig(
        service_name=service_name,
        service_version=service_version,
        deployment_environment=deployment_environment,
        otlp_endpoint=otlp_endpoint,
        enable_console_export=enable_console_export,
        additional_resource_attributes=additional_resource_attributes or {},
        enable_fastapi_instrumentation=enable_fastapi_instrumentation,
        enable_httpx_instrumentation=enable_httpx_instrumentation,
        enable_logging_instrumentation=enable_logging_instrumentation,
        enable_system_metrics=enable_system_metrics,
        batch_span_processor_max_queue_size=batch_span_processor_max_queue_size,
        batch_span_processor_schedule_delay_millis=batch_span_processor_schedule_delay_millis,
        batch_span_processor_max_export_batch_size=batch_span_processor_max_export_batch_size,
        metric_export_interval_millis=metric_export_interval_millis,
        metric_export_timeout_millis=metric_export_timeout_millis,
    )

    # Configure resource with service attributes
    resource = Resource.create(config.get_resource_attributes())
    log.info(f"🏷️ OpenTelemetry resource configured: {config.service_name} v{config.service_version}")

    # Configure tracing
    _configure_tracing(config, resource)

    # Configure metrics
    _configure_metrics(config, resource)

    # Configure logging
    _configure_logging(config, resource)

    # Configure auto-instrumentation
    _configure_instrumentation(config)

    # Save configuration globally
    _config = config

    log.info(f"🔭 OpenTelemetry SDK initialized for '{config.service_name}' " f"[OTLP: {config.otlp_endpoint}, Console: {config.enable_console_export}]")


def _configure_tracing(config: OpenTelemetryConfig, resource: Resource) -> None:
    """Configure OpenTelemetry tracing with OTLP and optional console export"""
    global _tracer_provider

    try:
        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)
        _tracer_provider = tracer_provider

        # Configure OTLP span exporter
        otlp_span_exporter = OTLPSpanExporter(endpoint=config.otlp_endpoint)
        span_processor = BatchSpanProcessor(
            otlp_span_exporter,
            max_queue_size=config.batch_span_processor_max_queue_size,
            schedule_delay_millis=config.batch_span_processor_schedule_delay_millis,
            max_export_batch_size=config.batch_span_processor_max_export_batch_size,
        )
        tracer_provider.add_span_processor(span_processor)

        # Add console exporter for debugging
        if config.enable_console_export:
            console_span_processor = BatchSpanProcessor(ConsoleSpanExporter())
            tracer_provider.add_span_processor(console_span_processor)
            log.debug("🖥️ Console span exporter enabled")

        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)
        log.info(f"🔍 Tracing configured: OTLP={config.otlp_endpoint}")

    except Exception as e:
        log.error(f"❌ Tracing configuration failed: {e}")


def _configure_metrics(config: OpenTelemetryConfig, resource: Resource) -> None:
    """Configure OpenTelemetry metrics with Prometheus and OTLP export"""
    global _meter_provider

    try:
        # Create metric readers
        readers = []

        # Prometheus reader for /metrics endpoint (optional)
        if PrometheusMetricReader is not None:
            try:
                prometheus_reader = PrometheusMetricReader()
                readers.append(prometheus_reader)
                log.debug("📊 Prometheus metrics reader configured")
            except Exception as e:
                log.warning(f"⚠️ Prometheus reader setup failed: {e}")
        else:
            log.info("ℹ️ Prometheus exporter not available - using OTLP metrics only")

        # OTLP metric reader
        try:
            otlp_metric_exporter = OTLPMetricExporter(endpoint=config.otlp_endpoint)
            otlp_reader = PeriodicExportingMetricReader(
                exporter=otlp_metric_exporter,
                export_interval_millis=config.metric_export_interval_millis,
                export_timeout_millis=config.metric_export_timeout_millis,
            )
            readers.append(otlp_reader)
            log.debug(f"📈 OTLP metrics reader configured: {config.otlp_endpoint}")
        except Exception as e:
            log.warning(f"⚠️ OTLP metrics reader setup failed: {e}")

        # Console reader for debugging
        if config.enable_console_export:
            try:
                console_reader = PeriodicExportingMetricReader(
                    exporter=ConsoleMetricExporter(),
                    export_interval_millis=config.metric_export_interval_millis,
                )
                readers.append(console_reader)
                log.debug("🖥️ Console metrics reader enabled")
            except Exception as e:
                log.warning(f"⚠️ Console metrics reader setup failed: {e}")

        # Create meter provider with all readers
        if readers:
            from opentelemetry import metrics

            meter_provider = MeterProvider(resource=resource, metric_readers=readers)
            _meter_provider = meter_provider
            metrics.set_meter_provider(meter_provider)
            log.info(f"📊 Metrics configured with {len(readers)} readers")
        else:
            log.warning("⚠️ No metric readers configured - metrics disabled")

    except Exception as e:
        log.error(f"❌ Metrics configuration failed: {e}")


def _configure_logging(config: OpenTelemetryConfig, resource: Resource) -> None:
    """Configure OpenTelemetry logging with trace correlation"""
    try:
        # Create logger provider
        logger_provider = LoggerProvider(resource=resource)

        # Configure OTLP log exporter
        otlp_log_exporter = OTLPLogExporter(endpoint=config.otlp_endpoint)
        log_processor = BatchLogRecordProcessor(otlp_log_exporter)
        logger_provider.add_log_record_processor(log_processor)

        # Add console exporter for debugging
        if config.enable_console_export:
            console_log_processor = BatchLogRecordProcessor(ConsoleLogExporter())
            logger_provider.add_log_record_processor(console_log_processor)
            log.debug("🖥️ Console log exporter enabled")

        # Set global logger provider
        from opentelemetry import _logs

        _logs.set_logger_provider(logger_provider)

        # Configure logging handler for automatic trace correlation
        handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
        logging.getLogger().addHandler(handler)

        log.info(f"📝 Logging configured with trace correlation: OTLP={config.otlp_endpoint}")

    except Exception as e:
        log.error(f"❌ Logging configuration failed: {e}")


def _configure_instrumentation(config: OpenTelemetryConfig) -> None:
    """Configure auto-instrumentation for supported libraries"""
    instrumentation_count = 0

    # FastAPI instrumentation
    if config.enable_fastapi_instrumentation:
        try:
            FastAPIInstrumentor().instrument()
            instrumentation_count += 1
            log.debug("🚀 FastAPI instrumentation enabled")
        except Exception as e:
            log.warning(f"⚠️ FastAPI instrumentation failed: {e}")

    # HTTPX client instrumentation
    if config.enable_httpx_instrumentation:
        try:
            HTTPXClientInstrumentor().instrument()
            instrumentation_count += 1
            log.debug("🌐 HTTPX client instrumentation enabled")
        except Exception as e:
            log.warning(f"⚠️ HTTPX instrumentation failed: {e}")

    # Logging instrumentation for trace correlation
    if config.enable_logging_instrumentation:
        try:
            LoggingInstrumentor().instrument()
            instrumentation_count += 1
            log.debug("📝 Logging instrumentation enabled")
        except Exception as e:
            log.warning(f"⚠️ Logging instrumentation failed: {e}")

    # System metrics instrumentation
    if config.enable_system_metrics:
        try:
            SystemMetricsInstrumentor().instrument()
            instrumentation_count += 1
            log.debug("💻 System metrics instrumentation enabled")
        except Exception as e:
            log.warning(f"⚠️ System metrics instrumentation failed: {e}")

    log.info(f"🔧 Auto-instrumentation configured: {instrumentation_count} instrumentors enabled")


def is_opentelemetry_available() -> bool:
    """
    Check if OpenTelemetry dependencies are available.

    Returns:
        True if all required OpenTelemetry packages are installed
    """
    return OTEL_AVAILABLE


def get_current_trace_id() -> Optional[str]:
    """
    Get the current trace ID if tracing is active.

    Returns:
        Trace ID as hex string, or None if no active trace
    """
    if not OTEL_AVAILABLE:
        return None

    try:
        span = trace.get_current_span()
        if span and span.is_recording():
            trace_id = span.get_span_context().trace_id
            return format(trace_id, "032x")
    except Exception:
        pass

    return None


def get_current_span_id() -> Optional[str]:
    """
    Get the current span ID if tracing is active.

    Returns:
        Span ID as hex string, or None if no active span
    """
    if not OTEL_AVAILABLE:
        return None

    try:
        span = trace.get_current_span()
        if span and span.is_recording():
            span_id = span.get_span_context().span_id
            return format(span_id, "016x")
    except Exception:
        pass

    return None


def add_baggage(key: str, value: str) -> None:
    """
    Add baggage to the current context.

    Args:
        key: Baggage key
        value: Baggage value
    """
    if not OTEL_AVAILABLE:
        return

    try:
        baggage.set_baggage(key, value)
    except Exception as e:
        log.warning(f"⚠️ Failed to add baggage {key}={value}: {e}")


def get_baggage(key: str) -> Optional[str]:
    """
    Get baggage from the current context.

    Args:
        key: Baggage key

    Returns:
        Baggage value or None if not found
    """
    if not OTEL_AVAILABLE:
        return None

    try:
        return baggage.get_baggage(key)
    except Exception:
        return None


# Global provider references for shutdown
_tracer_provider = None
_meter_provider = None
_config = None


def shutdown_opentelemetry() -> None:
    """
    Gracefully shutdown OpenTelemetry SDK, flushing remaining telemetry.
    Should be called during application shutdown.
    """
    global _tracer_provider, _meter_provider

    if _tracer_provider:
        try:
            _tracer_provider.shutdown()
            log.info("✅ TracerProvider shutdown complete")
        except Exception as ex:
            log.error(f"❌ Error shutting down TracerProvider: {ex}")

    if _meter_provider:
        try:
            _meter_provider.shutdown()
            log.info("✅ MeterProvider shutdown complete")
        except Exception as ex:
            log.error(f"❌ Error shutting down MeterProvider: {ex}")


def get_otel_config() -> Optional[OpenTelemetryConfig]:
    """Get the current OpenTelemetry configuration"""
    return _config


def is_otel_configured() -> bool:
    """Check if OpenTelemetry has been configured"""
    return _tracer_provider is not None and _meter_provider is not None


def instrument_fastapi_app(app, app_name: Optional[str] = None) -> None:
    """
    Instrument a FastAPI application with OpenTelemetry.

    This enables automatic HTTP request/response instrumentation including:
    - Request duration metrics
    - HTTP status code tracking
    - Endpoint-level metrics
    - Distributed tracing spans

    Args:
        app: FastAPI application instance
        app_name: Optional name for the instrumented app (for multi-app scenarios)
    """
    if not OTEL_AVAILABLE:
        log.warning("⚠️ FastAPI instrumentation not available - OpenTelemetry not installed")
        return

    try:
        # Check if app is already instrumented to avoid double instrumentation
        if hasattr(app, "_is_otel_instrumented"):
            log.info(f"📊 FastAPI app '{app_name or 'unknown'}' already instrumented")
            return

        # Apply FastAPI instrumentation
        FastAPIInstrumentor.instrument_app(app)

        # Mark app as instrumented
        app._is_otel_instrumented = True

        log.info(f"📊 FastAPI app '{app_name or 'default'}' instrumented for HTTP metrics")

    except Exception as ex:
        log.error(f"❌ Failed to instrument FastAPI app '{app_name}': {ex}")
