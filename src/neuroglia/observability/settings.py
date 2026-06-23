"""
Observability settings and configuration mixins for ApplicationSettings.

This module provides mixins that can be added to any ApplicationSettings class
to enable comprehensive observability with the three pillars: metrics, tracing, and logging.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilitySettingsMixin(BaseModel):
    """
    Mixin for observability configuration in ApplicationSettings.

    Provides the three pillars of observability with smart defaults:
    - Metrics: OpenTelemetry metrics with Prometheus export
    - Tracing: Distributed tracing with OTLP export
    - Logging: Structured logging with trace correlation

    Can be mixed into any ApplicationSettings class to add observability support.

    Example:
        class MyAppSettings(ApplicationSettings, ObservabilitySettingsMixin):
            service_name: str = "my-service"
            observability_health_checks: List[str] = ["database", "redis"]
    """

    # Service Identity (should be overridden in ApplicationSettings)
    service_name: str = "neuroglia-service"
    service_version: str = "1.0.0"
    deployment_environment: str = "development"

    # Master Observability Control
    observability_enabled: bool = True
    """Enable/disable all observability features"""

    # Three Pillars Control
    observability_metrics_enabled: bool = True
    """Enable OpenTelemetry metrics collection and Prometheus export"""

    observability_tracing_enabled: bool = True
    """Enable distributed tracing with OpenTelemetry"""

    observability_logging_enabled: bool = True
    """Enable structured logging with trace correlation"""

    # Standard Endpoints Configuration
    observability_health_endpoint: bool = True
    """Enable /health endpoint with dependency checks"""

    observability_metrics_endpoint: bool = True
    """Enable /metrics endpoint for Prometheus scraping"""

    observability_ready_endpoint: bool = True
    """Enable /ready endpoint for Kubernetes readiness probes"""

    # Endpoint Paths (customizable)
    observability_health_path: str = "/health"
    """Path for health check endpoint"""

    observability_metrics_path: str = "/metrics"
    """Path for Prometheus metrics endpoint"""

    observability_ready_path: str = "/ready"
    """Path for readiness check endpoint"""

    # Health Check Dependencies
    observability_health_checks: list[str] = Field(default_factory=list)
    """List of dependency names to check in health endpoint (e.g., ['mongodb', 'redis', 'keycloak'])"""

    # OpenTelemetry Configuration
    otel_enabled: bool = True
    """Enable OpenTelemetry SDK initialization"""

    otel_endpoint: str = "http://localhost:4317"
    """OTLP collector endpoint for traces and metrics export"""

    otel_protocol: str = "grpc"
    """OTLP protocol (grpc or http/protobuf)"""

    otel_timeout: int = 10
    """OTLP export timeout in seconds"""

    otel_console_export: bool = False
    """Enable console exporters for debugging (logs traces/metrics to stdout)"""

    # Batch Processing Configuration
    otel_batch_max_queue_size: int = 2048
    """Maximum queue size for batch span processor"""

    otel_batch_schedule_delay_ms: int = 5000
    """Schedule delay for batch span processor in milliseconds"""

    otel_batch_max_export_size: int = 512
    """Maximum export batch size for span processor"""

    # Metrics Configuration
    otel_metrics_interval_ms: int = 60000
    """Metrics export interval in milliseconds (default: 1 minute)"""

    otel_metrics_timeout_ms: int = 30000
    """Metrics export timeout in milliseconds (default: 30 seconds)"""

    # Instrumentation Control
    otel_instrument_fastapi: bool = True
    """Enable automatic FastAPI HTTP instrumentation"""

    otel_instrument_httpx: bool = True
    """Enable automatic HTTPX client instrumentation"""

    otel_instrument_logging: bool = True
    """Enable automatic logging instrumentation"""

    otel_instrument_system_metrics: bool = True
    """Enable system metrics collection (CPU, memory, etc.)"""

    # Additional Resource Attributes
    otel_resource_attributes: dict = Field(default_factory=dict)
    """Additional OpenTelemetry resource attributes as key-value pairs"""

    # Service Info Gauge (CR-4)
    otel_service_info_gauge: bool = True
    """Emit a service_info gauge metric with service metadata for discovery"""

    # Pydantic v2 configuration
    # No env_prefix to allow transparent environment variable reading
    model_config = ConfigDict()


class ObservabilityConfig:
    """
    Runtime configuration for observability features.

    This class is created from ObservabilitySettingsMixin during application startup
    and registered in the dependency injection container.
    """

    def __init__(self, settings_mixin: ObservabilitySettingsMixin, **overrides):
        """
        Create observability configuration from settings mixin with optional overrides.

        Args:
            settings_mixin: Settings object with ObservabilitySettingsMixin
            **overrides: Optional configuration overrides
        """
        # Service identity
        self.service_name = overrides.get("service_name", settings_mixin.service_name)
        self.service_version = overrides.get("service_version", settings_mixin.service_version)
        self.deployment_environment = overrides.get("deployment_environment", settings_mixin.deployment_environment)

        # Master control
        self.observability_enabled = overrides.get("observability_enabled", settings_mixin.observability_enabled)

        # Three pillars
        self.metrics_enabled = overrides.get("metrics_enabled", settings_mixin.observability_metrics_enabled)
        self.tracing_enabled = overrides.get("tracing_enabled", settings_mixin.observability_tracing_enabled)
        self.logging_enabled = overrides.get("logging_enabled", settings_mixin.observability_logging_enabled)

        # Standard endpoints
        self.health_endpoint = overrides.get("health_endpoint", settings_mixin.observability_health_endpoint)
        self.metrics_endpoint = overrides.get("metrics_endpoint", settings_mixin.observability_metrics_endpoint)
        self.ready_endpoint = overrides.get("ready_endpoint", settings_mixin.observability_ready_endpoint)

        # Endpoint paths
        self.health_path = overrides.get("health_path", settings_mixin.observability_health_path)
        self.metrics_path = overrides.get("metrics_path", settings_mixin.observability_metrics_path)
        self.ready_path = overrides.get("ready_path", settings_mixin.observability_ready_path)

        # Health checks
        self.health_checks = overrides.get("health_checks", settings_mixin.observability_health_checks or [])

        # OpenTelemetry
        self.otel_enabled = overrides.get("otel_enabled", settings_mixin.otel_enabled)
        self.otel_endpoint = overrides.get("otel_endpoint", settings_mixin.otel_endpoint)
        self.otel_protocol = overrides.get("otel_protocol", settings_mixin.otel_protocol)
        self.otel_timeout = overrides.get("otel_timeout", settings_mixin.otel_timeout)
        self.otel_console_export = overrides.get("otel_console_export", settings_mixin.otel_console_export)

        # Batch processing
        self.batch_max_queue_size = overrides.get("batch_max_queue_size", settings_mixin.otel_batch_max_queue_size)
        self.batch_schedule_delay_ms = overrides.get("batch_schedule_delay_ms", settings_mixin.otel_batch_schedule_delay_ms)
        self.batch_max_export_size = overrides.get("batch_max_export_size", settings_mixin.otel_batch_max_export_size)

        # Metrics
        self.metrics_interval_ms = overrides.get("metrics_interval_ms", settings_mixin.otel_metrics_interval_ms)
        self.metrics_timeout_ms = overrides.get("metrics_timeout_ms", settings_mixin.otel_metrics_timeout_ms)

        # Instrumentation
        self.instrument_fastapi = overrides.get("instrument_fastapi", settings_mixin.otel_instrument_fastapi)
        self.instrument_httpx = overrides.get("instrument_httpx", settings_mixin.otel_instrument_httpx)
        self.instrument_logging = overrides.get("instrument_logging", settings_mixin.otel_instrument_logging)
        self.instrument_system_metrics = overrides.get("instrument_system_metrics", settings_mixin.otel_instrument_system_metrics)

        # Resource attributes
        self.resource_attributes = overrides.get("resource_attributes", settings_mixin.otel_resource_attributes or {})

        # Service info gauge (CR-4)
        self.service_info_gauge = overrides.get("service_info_gauge", getattr(settings_mixin, "otel_service_info_gauge", True))

    def is_any_pillar_enabled(self) -> bool:
        """Check if any observability pillar is enabled"""
        return self.observability_enabled and (self.metrics_enabled or self.tracing_enabled or self.logging_enabled)

    def is_any_endpoint_enabled(self) -> bool:
        """Check if any standard endpoint is enabled"""
        return self.health_endpoint or self.metrics_endpoint or self.ready_endpoint


class ApplicationSettingsWithObservability(BaseSettings, ObservabilitySettingsMixin):
    """
    Convenience class that combines base ApplicationSettings fields with observability support.

    This provides an easy way for applications to get observability without manually mixing in classes.
    Applications should inherit from this and add their own application-specific settings.

    Example:
        from neuroglia.observability.settings import ApplicationSettingsWithObservability

        class MyAppSettings(ApplicationSettingsWithObservability):
            service_name: str = "my-service"
            debug: bool = True
            database_url: str = "postgresql://..."
            observability_health_checks: List[str] = ["database", "redis"]
    """

    # Base ApplicationSettings fields (copied to avoid circular imports)
    consumer_group: Optional[str] = None
    """Consumer group name for event processing. Optional - only needed for event-driven apps."""

    connection_strings: dict = Field(default_factory=dict)
    """Database and service connection strings. Can be empty for in-memory testing."""

    cloud_event_sink: Optional[str] = None
    """Cloud event sink URL. Optional - only needed when publishing events."""

    cloud_event_source: Optional[str] = None
    """Cloud event source identifier. Optional - only needed when publishing events."""

    cloud_event_type_prefix: str = ""
    """Prefix for cloud event types. Defaults to empty string."""

    cloud_event_retry_attempts: int = 5
    """Number of retry attempts for cloud event publishing."""

    cloud_event_retry_delay: float = 1.0
    """Delay between cloud event retry attempts in seconds."""

    # Override model_config to remove env_prefix for transparent environment variable reading
    model_config = SettingsConfigDict()
