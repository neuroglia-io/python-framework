"""
CQRS Metrics Extensions for Neuroglia Framework

This module provides extension methods to register CQRS metrics collection
capabilities with the dependency injection container.
"""

import logging

from neuroglia.dependency_injection import ServiceCollection

log = logging.getLogger(__name__)

# Import the metrics middleware to avoid circular imports
try:
    from neuroglia.mediation.metrics_middleware import (
        OTEL_AVAILABLE,
        MetricsPipelineBehavior,
    )

    MIDDLEWARE_AVAILABLE = True
except ImportError:
    MIDDLEWARE_AVAILABLE = False
    OTEL_AVAILABLE = False


def add_cqrs_metrics(services: ServiceCollection) -> ServiceCollection:
    """
    Add CQRS metrics collection to the service collection.

    This method registers the MetricsPipelineBehavior which automatically
    collects execution metrics for all commands and queries processed
    through the mediator pipeline.

    Metrics collected:
    - cqrs.executions.total: Total executions by type and status
    - cqrs.execution.duration: Execution time histogram
    - cqrs.executions.success: Successful executions counter
    - cqrs.executions.failures: Failed executions counter

    Args:
        services: The service collection to configure

    Returns:
        ServiceCollection: The configured service collection for method chaining

    Recommended Usage:
        ```python
        from neuroglia.hosting.web import WebApplicationBuilder
        from neuroglia.mediation import Mediator

        builder = WebApplicationBuilder()

        # Configure mediator with handlers (required first)
        Mediator.configure(builder, ["application.commands", "application.queries"])

        # Add CQRS metrics collection
        builder.services.add_cqrs_metrics()

        app = builder.build()
        app.run()
        ```

    Legacy Usage:
        ```python
        from neuroglia.dependency_injection import ServiceCollection

        services = ServiceCollection()
        services.add_mediator()      # Required - must be called first
        services.add_cqrs_metrics()  # Add CQRS metrics collection
        ```

    Requirements:
        - Mediator must be registered first (via Mediator.configure() or services.add_mediator())
        - OpenTelemetry packages must be installed
    """
    if not MIDDLEWARE_AVAILABLE:
        log.warning("⚠️ MetricsPipelineBehavior not available. " "CQRS metrics will be disabled. Check imports and dependencies.")
        return services

    if not OTEL_AVAILABLE:
        log.warning("⚠️ OpenTelemetry not available. " "CQRS metrics will be disabled. Install opentelemetry-api and opentelemetry-sdk.")
        return services

    log.info("📊 Adding CQRS metrics collection to service collection...")

    # Register the metrics pipeline behavior as a scoped service
    # This will automatically collect metrics for all CQRS operations
    from neuroglia.mediation import PipelineBehavior

    services.add_scoped(PipelineBehavior, MetricsPipelineBehavior)

    log.info("✅ CQRS metrics collection registered successfully")
    return services


# Register the extension method on ServiceCollection
setattr(ServiceCollection, "add_cqrs_metrics", add_cqrs_metrics)
