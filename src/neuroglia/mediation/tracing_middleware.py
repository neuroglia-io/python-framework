"""
OpenTelemetry Tracing Middleware for CQRS Pattern

Provides automatic distributed tracing for commands and queries with duration metrics
and automatic error handling.
"""

import logging
import time
from typing import Generic, TypeVar

from neuroglia.hosting import ApplicationBuilderBase
from neuroglia.mediation import Command, Query
from neuroglia.mediation.mediator import PipelineBehavior, Request

# Import OTEL tracing utilities (only if OTEL is configured)
try:
    from opentelemetry.trace import StatusCode

    from neuroglia.observability.metrics import record_metric
    from neuroglia.observability.tracing import (
        add_span_attributes,
        get_tracer,
        record_exception,
    )

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

log = logging.getLogger(__name__)

TRequest = TypeVar("TRequest", bound=Request)
TResult = TypeVar("TResult")


class TracingPipelineBehavior(PipelineBehavior[TRequest, TResult], Generic[TRequest, TResult]):
    """
    Pipeline behavior that automatically creates distributed tracing spans for commands and queries.

    Features:
    - Automatic span creation with semantic naming (Command.PlaceOrder, Query.GetUser)
    - Duration metrics (neuroglia.command.duration, neuroglia.query.duration)
    - Automatic error recording and span status management
    - Request type and result attributes
    - Success/failure tracking

    Usage:
        # Register in service collection
        services.add_pipeline_behavior(TracingPipelineBehavior)

        # All commands and queries will automatically be traced
    """

    def __init__(self):
        """Initialize the tracing pipeline behavior"""
        if not OTEL_AVAILABLE:
            log.warning("⚠️ TracingPipelineBehavior: OpenTelemetry not available. " "Tracing will be disabled. Install opentelemetry-api to enable tracing.")

    async def handle_async(self, request: TRequest, next_handler) -> TResult:
        """
        Handle the request with automatic tracing.

        Args:
            request: The command or query request
            next_handler: The next handler in the pipeline

        Returns:
            TResult: The result from the handler
        """
        # If OTEL is not available, just pass through
        if not OTEL_AVAILABLE:
            return await next_handler()

        # Determine request type
        request_type = type(request).__name__
        is_command = isinstance(request, Command)
        is_query = isinstance(request, Query)

        # Determine operation category
        if is_command:
            operation_category = "Command"
            metric_name = "neuroglia.command.duration"
        elif is_query:
            operation_category = "Query"
            metric_name = "neuroglia.query.duration"
        else:
            operation_category = "Request"
            metric_name = "neuroglia.request.duration"

        # Create span name
        span_name = f"{operation_category}.{request_type}"

        # Get tracer
        tracer = get_tracer(__name__)

        # Start span and record timing
        with tracer.start_as_current_span(span_name) as span:
            start_time = time.time()

            # Add attributes to span
            attributes = {
                "cqrs.operation": operation_category.lower(),
                "cqrs.type": request_type,
                "span.operation.type": operation_category.lower(),  # For dashboard queries
                "code.function": request_type,
                "code.namespace": type(request).__module__,
            }

            # Add request-specific attributes if available
            if hasattr(request, "id"):
                attributes["request.id"] = str(request.id)
            if hasattr(request, "aggregate_id"):
                attributes["aggregate.id"] = str(request.aggregate_id)

            add_span_attributes(attributes)

            try:
                # Execute the handler
                result = await next_handler()

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Add result attributes
                result_attributes = {"status": "success"}
                if hasattr(result, "is_success"):
                    result_attributes["result.is_success"] = result.is_success
                    if not result.is_success and hasattr(result, "error_message"):
                        result_attributes["result.error"] = result.error_message

                add_span_attributes(result_attributes)

                # Record metric
                metric_attributes = {"type": request_type, "operation": operation_category.lower(), "status": "success" if not hasattr(result, "is_success") or result.is_success else "failure"}
                record_metric("histogram", metric_name, duration_ms, metric_attributes, unit="ms", description=f"{operation_category} execution duration")

                # Set span status
                span.set_status(StatusCode.OK)

                # Log completion
                log.debug(f"✅ {operation_category} '{request_type}' completed in {duration_ms:.2f}ms")

                return result

            except Exception as ex:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Record exception in span
                record_exception(ex)

                # Add error attributes
                add_span_attributes(
                    {
                        "status": "error",
                        "error.type": type(ex).__name__,
                        "error.message": str(ex),
                    }
                )

                # Record error metric
                metric_attributes = {
                    "type": request_type,
                    "operation": operation_category.lower(),
                    "status": "error",
                    "error.type": type(ex).__name__,
                }
                record_metric("histogram", metric_name, duration_ms, metric_attributes, unit="ms", description=f"{operation_category} execution duration")

                # Log error
                log.error(f"❌ {operation_category} '{request_type}' failed after {duration_ms:.2f}ms: {ex}")

                # Re-raise the exception
                raise

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> ApplicationBuilderBase:
        """
        Registers TracingPipelineBehavior as a pipeline behavior for automatic CQRS tracing.

        Args:
            builder: The application builder with services collection

        Returns:
            The builder for method chaining
        """
        log.info("🔭 Registering TracingPipelineBehavior for automatic CQRS tracing...")

        # Register as concrete type first (required for DI resolution)
        builder.services.add_scoped(TracingPipelineBehavior)

        # Also register as PipelineBehavior interface (for mediator to discover)
        builder.services.add_scoped(PipelineBehavior, implementation_factory=lambda sp: sp.get_required_service(TracingPipelineBehavior))

        log.info("✅ TracingPipelineBehavior registered")
        return builder
