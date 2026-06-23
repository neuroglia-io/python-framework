"""
Observability framework integration for the Neuroglia framework.

This module provides the main Observability class that follows the framework's
.configure(builder) pattern and integrates with ApplicationSettings to provide
comprehensive observability with minimal configuration.
"""

import datetime
import logging
from typing import TYPE_CHECKING, Optional

from fastapi import FastAPI, Response

if TYPE_CHECKING:
    from neuroglia.hosting.web import WebApplicationBuilder
    from neuroglia.observability.health_checks import HealthCheckProvider

from neuroglia.observability.settings import (
    ObservabilityConfig,
    ObservabilitySettingsMixin,
)

log = logging.getLogger(__name__)


class Observability:
    """
    Observability service configurator following Neuroglia framework patterns.

    Provides comprehensive observability setup with the three pillars:
    - Metrics: OpenTelemetry metrics with Prometheus export
    - Tracing: Distributed tracing with OTLP export
    - Logging: Structured logging with trace correlation

    Usage:
        builder = WebApplicationBuilder(app_settings)
        Observability.configure(builder)  # Uses settings from app_settings

        # Optional overrides
        Observability.configure(builder,
            tracing_enabled=False,
            health_checks=['mongodb']
        )
    """

    @classmethod
    def configure(
        cls,
        builder: "WebApplicationBuilder",
        auto_enable_cqrs_metrics: bool = True,
        health_check_providers: Optional[list["HealthCheckProvider"]] = None,
        **overrides,
    ) -> None:
        """
        Configure comprehensive observability for the application.

        Args:
            builder: The enhanced web application builder (must contain app_settings)
            auto_enable_cqrs_metrics: Auto-enable CQRS metrics if Mediator is detected (default: True)
            health_check_providers: List of HealthCheckProvider instances for dependency monitoring
            **overrides: Optional configuration overrides (tracing_enabled=False, etc.)
        """
        app_settings = builder.app_settings

        # Check if app_settings has observability configuration
        if not cls._has_observability_settings(app_settings):
            raise ValueError("Observability configuration not found in app_settings. " "Please inherit from ApplicationSettingsWithObservability or mix in ObservabilitySettingsMixin. " f"Current settings type: {type(app_settings)}")

        # Create observability configuration from app_settings
        config = ObservabilityConfig(app_settings, **overrides)

        # Store health check providers on config for use by endpoints
        config.health_check_providers = health_check_providers or []

        # Register configuration in DI container for access throughout application
        builder.services.add_singleton(ObservabilityConfig, lambda: config)

        # Configure OpenTelemetry if any pillar is enabled
        if config.is_any_pillar_enabled() and config.otel_enabled:
            cls._configure_opentelemetry(builder, config)

        # Configure tracing pipeline behavior if tracing is enabled
        if config.tracing_enabled:
            try:
                from neuroglia.mediation.tracing_middleware import (
                    TracingPipelineBehavior,
                )

                TracingPipelineBehavior.configure(builder)
                log.info("🔍 Tracing pipeline behavior configured")
            except ImportError:
                log.warning("⚠️ TracingPipelineBehavior not available - tracing middleware skipped")

        # Auto-enable CQRS metrics if metrics enabled and Mediator is configured
        if config.metrics_enabled and auto_enable_cqrs_metrics:
            if cls._has_mediator_configured(builder):
                try:
                    from neuroglia.mediation.metrics_middleware import add_cqrs_metrics

                    add_cqrs_metrics(builder.services)
                    log.info("📊 CQRS metrics auto-enabled (mediator detected)")
                except ImportError:
                    log.warning("⚠️ CQRS metrics middleware not available - metrics skipped")

        # Register standard endpoints for automatic addition during app build
        if config.is_any_endpoint_enabled():
            cls._register_standard_endpoints(builder, config)

        log.info(f"🔭 Observability configured for '{config.service_name}' " f"[Metrics: {'✓' if config.metrics_enabled else '✗'}, " f"Tracing: {'✓' if config.tracing_enabled else '✗'}, " f"Logging: {'✓' if config.logging_enabled else '✗'}]")

    @classmethod
    def _has_observability_settings(cls, settings) -> bool:
        """Check if settings object has observability configuration"""
        return isinstance(settings, ObservabilitySettingsMixin) or hasattr(settings, "observability_enabled")

    @classmethod
    def _has_mediator_configured(cls, builder: "WebApplicationBuilder") -> bool:
        """
        Check if Mediator has been configured in the service provider.

        Returns:
            True if Mediator is registered, False otherwise
        """
        try:
            from neuroglia.mediation import Mediator

            # Build a temporary service provider to check registration
            provider = builder.services.build()
            mediator = provider.get_service(Mediator)
            return mediator is not None
        except Exception as ex:
            log.debug(f"Could not detect Mediator: {ex}")
            return False

    @classmethod
    def _configure_opentelemetry(cls, builder: "WebApplicationBuilder", config: ObservabilityConfig) -> None:
        """Configure OpenTelemetry SDK based on enabled pillars"""
        try:
            from neuroglia.observability.otel_sdk import configure_opentelemetry

            # Build OpenTelemetry configuration from observability config
            otel_config = {
                "service_name": config.service_name,
                "service_version": config.service_version,
                "otlp_endpoint": config.otel_endpoint,
                "enable_console_export": config.otel_console_export,
                "deployment_environment": config.deployment_environment,
                "additional_resource_attributes": config.resource_attributes,
                # Pillar controls
                "enable_fastapi_instrumentation": config.tracing_enabled and config.instrument_fastapi,
                "enable_httpx_instrumentation": config.tracing_enabled and config.instrument_httpx,
                "enable_logging_instrumentation": config.logging_enabled and config.instrument_logging,
                "enable_system_metrics": config.metrics_enabled and config.instrument_system_metrics,
                # Batch processing
                "batch_span_processor_max_queue_size": config.batch_max_queue_size,
                "batch_span_processor_schedule_delay_millis": config.batch_schedule_delay_ms,
                "batch_span_processor_max_export_batch_size": config.batch_max_export_size,
                # Metrics
                "metric_export_interval_millis": config.metrics_interval_ms,
                "metric_export_timeout_millis": config.metrics_timeout_ms,
            }

            # Configure OpenTelemetry with our settings
            configure_opentelemetry(**otel_config)

            log.info(f"🔭 OpenTelemetry configured: endpoint={config.otel_endpoint}")

            # Create service info gauge (CR-4)
            if getattr(config, "service_info_gauge", True):
                cls._create_service_info_gauge(config)

        except ImportError as e:
            log.error(f"❌ OpenTelemetry configuration failed - missing dependencies: {e}")
        except Exception as e:
            log.error(f"❌ OpenTelemetry configuration error: {e}")

    @classmethod
    def _create_service_info_gauge(cls, config: ObservabilityConfig) -> None:
        """Create service info gauge metric for service discovery (CR-4)"""
        try:
            from opentelemetry.metrics import Observation

            from neuroglia.observability.metrics import create_observable_gauge

            def _service_info_callback(options):
                return [
                    Observation(
                        1,
                        {
                            "service.name": config.service_name,
                            "service.version": config.service_version,
                            "deployment.environment": config.deployment_environment,
                        },
                    )
                ]

            create_observable_gauge(
                name="service.info",
                callback=_service_info_callback,
                unit="1",
                description="Service metadata gauge for discovery",
            )
            log.info("🏷️ Service info gauge created")

        except Exception as e:
            log.warning(f"⚠️ Could not create service info gauge: {e}")

    @classmethod
    def _register_standard_endpoints(cls, builder: "WebApplicationBuilder", config: ObservabilityConfig) -> None:
        """Register standard endpoints for automatic addition to main app during build"""

        # Store configuration for later use during app building
        builder._observability_config = config

        log.info(f"📊 Standard endpoints registered: " f"health={config.health_path if config.health_endpoint else 'disabled'}, " f"metrics={config.metrics_path if config.metrics_endpoint else 'disabled'}, " f"ready={config.ready_path if config.ready_endpoint else 'disabled'}")


class StandardEndpoints:
    """Standard observability endpoints implementation"""

    @staticmethod
    def add_health_endpoint(app: FastAPI, config: ObservabilityConfig) -> None:
        """Add health check endpoint with dependency monitoring"""

        @app.get(config.health_path, include_in_schema=False, tags=["observability"])
        async def health_check():
            """
            Health check endpoint with dependency status.

            Returns overall service health and status of configured dependencies.
            """
            health_status = {"status": "healthy", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "service": {"name": config.service_name, "version": config.service_version, "environment": config.deployment_environment}}

            # Add dependency checks if configured
            providers = getattr(config, "health_check_providers", [])
            if config.health_checks or providers:
                dependencies = {}
                overall_healthy = True

                # Check all registered health check providers
                for provider in providers:
                    try:
                        result = await provider.check()
                        dep_status = {
                            "status": result.status,
                        }
                        if result.message:
                            dep_status["message"] = result.message
                        if result.latency_ms is not None:
                            dep_status["latency_ms"] = round(result.latency_ms, 2)
                        dependencies[provider.name] = dep_status

                        if result.status != "healthy":
                            overall_healthy = False
                    except Exception as e:
                        log.warning(f"Health check failed for {provider.name}: {e}")
                        dependencies[provider.name] = {"status": "unhealthy", "message": str(e)}
                        overall_healthy = False

                # Handle string-based health checks without providers (legacy)
                for dependency in config.health_checks:
                    if dependency not in dependencies:
                        dependencies[dependency] = {"status": "healthy", "message": "No provider configured"}

                health_status["dependencies"] = dependencies
                if not overall_healthy:
                    health_status["status"] = "degraded"

            return health_status

    @staticmethod
    def add_ready_endpoint(app: FastAPI, config: ObservabilityConfig) -> None:
        """Add readiness probe endpoint for Kubernetes"""

        @app.get(config.ready_path, include_in_schema=False, tags=["observability"])
        async def readiness_check():
            """
            Readiness probe endpoint for Kubernetes.

            Indicates whether the service is ready to accept traffic.
            """
            ready_status = {"ready": True, "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(), "service": config.service_name}

            # Add basic readiness checks
            checks = {"application": "ready"}

            # Use health check providers for readiness
            providers = getattr(config, "health_check_providers", [])
            for provider in providers:
                try:
                    result = await provider.check()
                    checks[provider.name] = "ready" if result.status == "healthy" else "not_ready"
                except Exception as e:
                    log.warning(f"Readiness check failed for {provider.name}: {e}")
                    checks[provider.name] = "not_ready"

            ready_status["checks"] = checks
            return ready_status

    @staticmethod
    def add_metrics_endpoint(app: FastAPI, config: ObservabilityConfig) -> None:
        """Add Prometheus metrics endpoint"""

        try:
            from neuroglia.observability.metrics import add_metrics_endpoint

            # Use existing metrics endpoint implementation
            add_metrics_endpoint(app, config.metrics_path)

        except ImportError:
            log.warning("⚠️ Prometheus metrics endpoint not available - missing dependencies")

            # Fallback minimal metrics endpoint
            @app.get(config.metrics_path, include_in_schema=False)
            async def metrics_fallback():
                """Fallback metrics endpoint when Prometheus is not available"""
                return Response(content="# Prometheus metrics not available\n# Install prometheus-client for full metrics support\n", media_type="text/plain")

    # Note: _check_dependency_health has been replaced by HealthCheckProvider implementations
    # in neuroglia/observability/health_checks.py (CR-2)
