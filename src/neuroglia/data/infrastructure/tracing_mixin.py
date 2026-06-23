"""
Repository tracing mixin for automatic OpenTelemetry instrumentation.

This module provides a mixin class that adds automatic distributed tracing to repository
operations. When mixed into any repository implementation, it automatically creates spans
for all CRUD operations with detailed attributes and metrics.

Examples:
    ```python
    from neuroglia.data.infrastructure.mongo import MotorRepository
    from neuroglia.data.infrastructure.tracing_mixin import TracedRepositoryMixin

    class UserRepository(TracedRepositoryMixin, MotorRepository[User, str]):
        pass  # Automatic tracing for all repository operations!

    # Usage - tracing happens automatically
    repository = UserRepository(mongo_client, serializer)
    user = await repository.get_async("user_123")  # Creates span "Repository.get"
    await repository.add_async(user)  # Creates span "Repository.add"
    ```

See Also:
    - OpenTelemetry Integration Guide: https://bvandewe.github.io/pyneuro/guides/opentelemetry-integration/
    - Repository Pattern: https://bvandewe.github.io/pyneuro/patterns/repository/
"""

import time
from typing import Optional

from neuroglia.data.abstractions import TEntity, TKey

# Try to import OpenTelemetry, gracefully degrade if not available
try:
    from opentelemetry import trace

    from neuroglia.observability.metrics import record_metric
    from neuroglia.observability.tracing import add_span_attributes, get_tracer

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class TracedRepositoryMixin:
    """
    Mixin to add automatic OpenTelemetry tracing to repository operations.

    This mixin wraps all standard repository operations (get, add, update, remove, contains)
    with automatic span creation, attribute enrichment, and metrics recording. It uses
    Python's MRO (Method Resolution Order) to intercept repository calls transparently.

    Features:
        - Automatic span creation for all CRUD operations
        - Semantic span naming: "Repository.get", "Repository.add", etc.
        - Rich span attributes: operation type, repository class, entity type, entity ID
        - Duration metrics with operation and repository labels
        - Error recording with span status management
        - Graceful degradation when OpenTelemetry is not available

    Span Attributes Created:
        - repository.operation: The operation name (get, add, update, remove, contains)
        - repository.type: The repository class name
        - entity.type: The entity class name
        - entity.id: The entity identifier (when applicable)

    Metrics Recorded:
        - neuroglia.repository.operation.duration (histogram):
            Duration of repository operations in milliseconds
            Labels: operation, repository, status

    Examples:
        ```python
        # Mix into any repository implementation
        class OrderRepository(TracedRepositoryMixin, MongoRepository[Order, str]):
            pass

        # All operations automatically traced
        order = Order(customer_id="cust_123")
        await repository.add_async(order)
        # Creates span: "Repository.add"
        # Attributes: {
        #   "repository.operation": "add",
        #   "repository.type": "OrderRepository",
        #   "entity.type": "Order",
        #   "entity.id": "order_456"
        # }
        # Metric: neuroglia.repository.operation.duration{operation="add", repository="OrderRepository"}

        retrieved = await repository.get_async("order_456")
        # Creates span: "Repository.get"
        # Attributes include entity.id for lookup operations
        ```

    Usage Notes:
        - Must be the FIRST base class in multiple inheritance for proper MRO
        - Works with any repository implementation (Mongo, Memory, Cache, etc.)
        - All spans include error recording and status on exceptions
        - No performance impact when OpenTelemetry is not installed

    See Also:
        - TracingPipelineBehavior: Automatic CQRS tracing
        - TracedEventHandler: Automatic event handler tracing
        - OpenTelemetry Integration Guide: https://bvandewe.github.io/pyneuro/guides/opentelemetry-integration/
    """

    async def contains_async(self, id: TKey) -> bool:
        """Check if entity exists with automatic tracing."""
        if not OTEL_AVAILABLE:
            return await super().contains_async(id)

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("Repository.contains") as span:
            try:
                start_time = time.time()

                # Add span attributes
                add_span_attributes(
                    {
                        "repository.operation": "contains",
                        "repository.type": type(self).__name__,
                        "span.operation.type": "repository",  # For dashboard queries
                        "entity.id": str(id),
                    }
                )

                # Execute operation
                result = await super().contains_async(id)

                # Record duration metric
                duration_ms = (time.time() - start_time) * 1000
                record_metric(
                    "histogram",
                    "neuroglia.repository.operation.duration",
                    duration_ms,
                    {
                        "operation": "contains",
                        "repository": type(self).__name__,
                        "status": "success",
                    },
                )

                # Add result to span
                span.set_attribute("repository.exists", result)

                return result

            except Exception as ex:
                # Record exception and set span status
                span.record_exception(ex)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(ex)))

                # Record error metric
                duration_ms = (time.time() - start_time) * 1000
                record_metric(
                    "histogram",
                    "neuroglia.repository.operation.duration",
                    duration_ms,
                    {
                        "operation": "contains",
                        "repository": type(self).__name__,
                        "status": "error",
                    },
                )

                raise

    async def get_async(self, id: TKey) -> Optional[TEntity]:
        """Get entity by ID with automatic tracing."""
        if not OTEL_AVAILABLE:
            return await super().get_async(id)

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("Repository.get") as span:
            try:
                start_time = time.time()

                # Add span attributes
                add_span_attributes(
                    {
                        "repository.operation": "update",
                        "repository.type": type(self).__name__,
                        "span.operation.type": "repository",  # For dashboard queries
                        "span.operation.type": "repository",  # For dashboard queries
                        "span.operation.type": "repository",  # For dashboard queries
                        "entity.id": str(id),
                    }
                )

                # Execute operation
                result = await super().get_async(id)

                # Record duration metric
                duration_ms = (time.time() - start_time) * 1000
                record_metric(
                    "histogram",
                    "neuroglia.repository.operation.duration",
                    duration_ms,
                    {
                        "operation": "get",
                        "repository": type(self).__name__,
                        "status": "success",
                    },
                )

                # Add result metadata to span
                if result is not None:
                    span.set_attribute("entity.type", type(result).__name__)
                    span.set_attribute("repository.found", True)
                else:
                    span.set_attribute("repository.found", False)

                return result

            except Exception as ex:
                # Record exception and set span status
                span.record_exception(ex)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(ex)))

                # Record error metric
                duration_ms = (time.time() - start_time) * 1000
                record_metric(
                    "histogram",
                    "neuroglia.repository.operation.duration",
                    duration_ms,
                    {
                        "operation": "get",
                        "repository": type(self).__name__,
                        "status": "error",
                    },
                )

                raise

    async def add_async(self, entity: TEntity) -> TEntity:
        """Add entity with automatic tracing."""
        if not OTEL_AVAILABLE:
            return await super().add_async(entity)

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("Repository.add") as span:
            try:
                start_time = time.time()

                # Add span attributes
                entity_id = str(entity.id) if hasattr(entity, "id") else None
                add_span_attributes(
                    {
                        "repository.operation": "add",
                        "repository.type": type(self).__name__,
                        "entity.type": type(entity).__name__,
                        "entity.id": entity_id,
                    }
                )

                # Execute operation
                result = await super().add_async(entity)

                # Record duration metric
                duration_ms = (time.time() - start_time) * 1000
                record_metric(
                    "histogram",
                    "neuroglia.repository.operation.duration",
                    duration_ms,
                    {
                        "operation": "add",
                        "repository": type(self).__name__,
                        "status": "success",
                    },
                )

                return result

            except Exception as ex:
                # Record exception and set span status
                span.record_exception(ex)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(ex)))

                # Record error metric
                duration_ms = (time.time() - start_time) * 1000
                record_metric(
                    "histogram",
                    "neuroglia.repository.operation.duration",
                    duration_ms,
                    {
                        "operation": "add",
                        "repository": type(self).__name__,
                        "status": "error",
                    },
                )

                raise

    async def update_async(self, entity: TEntity) -> TEntity:
        """Update entity with automatic tracing."""
        if not OTEL_AVAILABLE:
            return await super().update_async(entity)

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("Repository.update") as span:
            try:
                start_time = time.time()

                # Add span attributes
                entity_id = str(entity.id) if hasattr(entity, "id") else None
                add_span_attributes(
                    {
                        "repository.operation": "update",
                        "repository.type": type(self).__name__,
                        "entity.type": type(entity).__name__,
                        "entity.id": entity_id,
                    }
                )

                # Execute operation
                result = await super().update_async(entity)

                # Record duration metric
                duration_ms = (time.time() - start_time) * 1000
                record_metric(
                    "histogram",
                    "neuroglia.repository.operation.duration",
                    duration_ms,
                    {
                        "operation": "update",
                        "repository": type(self).__name__,
                        "status": "success",
                    },
                )

                return result

            except Exception as ex:
                # Record exception and set span status
                span.record_exception(ex)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(ex)))

                # Record error metric
                duration_ms = (time.time() - start_time) * 1000
                record_metric(
                    "histogram",
                    "neuroglia.repository.operation.duration",
                    duration_ms,
                    {
                        "operation": "update",
                        "repository": type(self).__name__,
                        "status": "error",
                    },
                )

                raise

    async def remove_async(self, id: TKey) -> None:
        """Remove entity with automatic tracing."""
        if not OTEL_AVAILABLE:
            return await super().remove_async(id)

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("Repository.remove") as span:
            try:
                start_time = time.time()

                # Add span attributes
                add_span_attributes(
                    {
                        "repository.operation": "remove",
                        "repository.type": type(self).__name__,
                        "span.operation.type": "repository",  # For dashboard queries
                        "entity.id": str(id),
                    }
                )

                # Execute operation
                result = await super().remove_async(id)

                # Record duration metric
                duration_ms = (time.time() - start_time) * 1000
                record_metric(
                    "histogram",
                    "neuroglia.repository.operation.duration",
                    duration_ms,
                    {
                        "operation": "remove",
                        "repository": type(self).__name__,
                        "status": "success",
                    },
                )

                return result

            except Exception as ex:
                # Record exception and set span status
                span.record_exception(ex)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(ex)))

                # Record error metric
                duration_ms = (time.time() - start_time) * 1000
                record_metric(
                    "histogram",
                    "neuroglia.repository.operation.duration",
                    duration_ms,
                    {
                        "operation": "remove",
                        "repository": type(self).__name__,
                        "status": "error",
                    },
                )

                raise
