"""
CQRS Metrics Pipeline Behavior for Neuroglia Framework

This module provides automatic metrics collection for CQRS commands and queries
executed through the mediator pipeline. It tracks execution counts, duration,
success/failure rates, and other performance metrics.

Usage:
    ```python
    from neuroglia.mediation.metrics_middleware import add_cqrs_metrics

    # During service configuration
    services = ServiceCollection()
    services.add_cqrs_metrics()  # Automatically registers MetricsPipelineBehavior
    ```

Metrics Collected:
    - cqrs.executions.total: Counter of command/query executions
    - cqrs.execution.duration: Histogram of execution times
    - cqrs.executions.success: Counter of successful executions
    - cqrs.executions.failures: Counter of failed executions
"""

import logging
import time
from typing import Generic, TypeVar

from neuroglia.mediation import Command, PipelineBehavior, Query

log = logging.getLogger(__name__)

# Type variables for generic pipeline behavior
TRequest = TypeVar("TRequest")
TResult = TypeVar("TResult")

# Try to import OpenTelemetry metrics
try:
    from opentelemetry.metrics import get_meter

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class MetricsPipelineBehavior(PipelineBehavior[TRequest, TResult], Generic[TRequest, TResult]):
    """
    Pipeline behavior that automatically collects CQRS execution metrics.

    Features:
    - Execution count tracking (commands vs queries)
    - Duration measurement with percentiles
    - Success/failure rate monitoring
    - Request type breakdown for detailed analysis
    - Automatic error categorization

    Metrics:
    - cqrs.executions.total: Total executions by type and status
    - cqrs.execution.duration: Execution time distribution
    - cqrs.executions.success: Successful executions counter
    - cqrs.executions.failures: Failed executions counter

    Usage:
        # Register in service collection
        services.add_pipeline_behavior(MetricsPipelineBehavior)

        # All commands and queries will automatically be metered
    """

    # Class-level meters (shared across all instances to avoid re-creating metrics)
    _meters_initialized = False
    _executions_total = None
    _executions_success = None
    _executions_failures = None
    _execution_duration = None

    def __init__(self):
        """Initialize the metrics pipeline behavior"""
        if not OTEL_AVAILABLE:
            return

        # Initialize class-level meters only once
        if not MetricsPipelineBehavior._meters_initialized:
            meter = get_meter(__name__)

            # Execution counters
            MetricsPipelineBehavior._executions_total = meter.create_counter(name="cqrs.executions.total", unit="executions", description="Total number of CQRS command/query executions")

            MetricsPipelineBehavior._executions_success = meter.create_counter(name="cqrs.executions.success", unit="executions", description="Number of successful CQRS executions")

            MetricsPipelineBehavior._executions_failures = meter.create_counter(name="cqrs.executions.failures", unit="executions", description="Number of failed CQRS executions")

            # Execution duration histogram
            MetricsPipelineBehavior._execution_duration = meter.create_histogram(name="cqrs.execution.duration", unit="ms", description="Duration of CQRS command/query execution")

            MetricsPipelineBehavior._meters_initialized = True
            log.debug("📊 MetricsPipelineBehavior meters initialized")

        # Set instance properties to reference class-level meters
        self.executions_total = MetricsPipelineBehavior._executions_total
        self.executions_success = MetricsPipelineBehavior._executions_success
        self.executions_failures = MetricsPipelineBehavior._executions_failures
        self.execution_duration = MetricsPipelineBehavior._execution_duration

    async def handle_async(self, request: TRequest, next_handler) -> TResult:
        """
        Handle the request with automatic metrics collection.

        Args:
            request: The command or query request
            next_handler: The next handler in the pipeline

        Returns:
            TResult: The result from the handler
        """
        # If OTEL is not available, just pass through
        if not OTEL_AVAILABLE:
            return await next_handler()

        # Determine request type and operation category
        request_type = type(request).__name__
        is_command = isinstance(request, Command)
        is_query = isinstance(request, Query)

        if is_command:
            operation_category = "command"
        elif is_query:
            operation_category = "query"
        else:
            operation_category = "request"

        # Common metric labels
        base_labels = {
            "operation": operation_category,
            "type": request_type,
        }

        # Record execution start
        start_time = time.time()

        # Increment total executions counter
        self.executions_total.add(1, base_labels)

        try:
            # Execute the handler
            result = await next_handler()

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Determine if execution was successful
            is_success = True
            error_type = None

            if hasattr(result, "is_success"):
                is_success = result.is_success
                if not is_success and hasattr(result, "error_message"):
                    # Categorize error type
                    error_msg = result.error_message.lower()
                    if "not found" in error_msg:
                        error_type = "not_found"
                    elif "validation" in error_msg or "invalid" in error_msg:
                        error_type = "validation"
                    elif "permission" in error_msg or "unauthorized" in error_msg:
                        error_type = "authorization"
                    else:
                        error_type = "business_rule"

            # Record success/failure metrics
            status_labels = {**base_labels, "status": "success" if is_success else "failure"}

            if is_success:
                self.executions_success.add(1, base_labels)
            else:
                failure_labels = {**base_labels, "error_type": error_type or "unknown"}
                self.executions_failures.add(1, failure_labels)

            # Record execution duration
            self.execution_duration.record(duration_ms, status_labels)

            # Log metrics (debug level)
            log.debug(f"📊 CQRS Metrics - {operation_category}.{request_type}: " f"{'✅' if is_success else '❌'} {duration_ms:.2f}ms")

            return result

        except Exception as e:
            # Calculate duration for failed execution
            duration_ms = (time.time() - start_time) * 1000

            # Categorize exception type
            exception_type = type(e).__name__.lower()
            if "notfound" in exception_type:
                error_category = "not_found"
            elif "validation" in exception_type or "value" in exception_type:
                error_category = "validation"
            elif "permission" in exception_type or "unauthorized" in exception_type:
                error_category = "authorization"
            else:
                error_category = "exception"

            # Record failure metrics
            failure_labels = {**base_labels, "error_type": error_category, "status": "failure"}
            self.executions_failures.add(1, failure_labels)
            self.execution_duration.record(duration_ms, failure_labels)

            # Log error metrics
            log.debug(f"📊 CQRS Metrics - {operation_category}.{request_type}: " f"❌ Exception {type(e).__name__} after {duration_ms:.2f}ms")

            # Re-raise the exception
            raise


def add_cqrs_metrics(services) -> None:
    """
    Register CQRS metrics collection pipeline behavior.

    This is a convenience method that registers the MetricsPipelineBehavior
    to automatically collect metrics for all CQRS operations.

    Args:
        services: ServiceCollection instance

    Example:
        ```python
        services = ServiceCollection()
        add_cqrs_metrics(services)
        ```
    """
    if not OTEL_AVAILABLE:
        log.warning("⚠️ OpenTelemetry not available. CQRS metrics will be disabled.")
        return

    # Import here to avoid circular imports
    from neuroglia.dependency_injection import ServiceCollection
    from neuroglia.mediation.pipeline_behavior import PipelineBehavior

    if not isinstance(services, ServiceCollection):
        log.error("❌ services parameter must be a ServiceCollection instance")
        return

    log.info("📊 Registering MetricsPipelineBehavior for automatic CQRS metrics...")

    # Register as PipelineBehavior interface only (for mediator to discover)
    # Don't register the concrete type to avoid duplicate behavior instances
    services.add_scoped(PipelineBehavior, implementation_factory=lambda sp: MetricsPipelineBehavior())

    log.info("✅ CQRS metrics pipeline behavior registered successfully")


# Export the main classes and functions
__all__ = ["MetricsPipelineBehavior", "add_cqrs_metrics"]
