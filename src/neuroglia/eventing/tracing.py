"""
OpenTelemetry Tracing for Event Handlers

Provides automatic distributed tracing for domain event handlers with duration metrics.
"""

import logging
import time
from typing import TypeVar

from neuroglia.data.abstractions import DomainEvent
from neuroglia.mediation import DomainEventHandler

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

TEvent = TypeVar("TEvent", bound=DomainEvent)


class TracedEventHandler(DomainEventHandler[TEvent]):
    """
    Wrapper for event handlers that automatically creates distributed tracing spans.

    Features:
    - Automatic span creation for event processing
    - Duration metrics (neuroglia.event.processing.duration)
    - Event type and handler tracking
    - Automatic error recording

    Usage:
        # Wrap existing event handlers
        class MyEventHandler(EventHandler[OrderCreatedEvent]):
            async def handle_async(self, event):
                # Process event
                pass

        # The framework can automatically wrap handlers with tracing
        traced_handler = TracedEventHandler(MyEventHandler())
    """

    def __init__(self, inner_handler: DomainEventHandler[TEvent]):
        """
        Initialize the traced event handler wrapper.

        Args:
            inner_handler: The actual event handler to wrap
        """
        self._inner_handler = inner_handler
        if not OTEL_AVAILABLE:
            log.warning("⚠️ TracedEventHandler: OpenTelemetry not available. " "Event tracing will be disabled.")

    async def handle_async(self, notification: TEvent):
        """
        Handle the event with automatic tracing.

        Args:
            notification: The domain event to handle
        """
        # If OTEL is not available, just pass through
        if not OTEL_AVAILABLE:
            return await self._inner_handler.handle_async(notification)

        # Get event and handler information
        event_type = type(notification).__name__
        handler_type = type(self._inner_handler).__name__

        # Create span name
        span_name = f"Event.{event_type}"

        # Get tracer
        tracer = get_tracer(__name__)

        # Start span and record timing
        with tracer.start_as_current_span(span_name) as span:
            start_time = time.time()

            # Add attributes to span
            attributes = {
                "event.type": event_type,
                "event.handler": handler_type,
                "code.function": handler_type,
                "code.namespace": type(self._inner_handler).__module__,
            }

            # Add event-specific attributes if available
            if hasattr(notification, "id"):
                attributes["event.id"] = str(notification.id)
            if hasattr(notification, "aggregate_id"):
                attributes["aggregate.id"] = str(notification.aggregate_id)
            if hasattr(notification, "aggregate_type"):
                attributes["aggregate.type"] = notification.aggregate_type
            if hasattr(notification, "occurred_at"):
                attributes["event.occurred_at"] = str(notification.occurred_at)

            add_span_attributes(attributes)

            try:
                # Execute the handler
                await self._inner_handler.handle_async(notification)

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Record metric
                metric_attributes = {"event.type": event_type, "handler.type": handler_type, "status": "success"}
                record_metric("histogram", "neuroglia.event.processing.duration", duration_ms, metric_attributes, unit="ms", description="Event handler processing duration")

                # Set span status
                span.set_status(StatusCode.OK)

                # Log completion
                log.debug(f"✅ Event '{event_type}' processed by '{handler_type}' in {duration_ms:.2f}ms")

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
                    "event.type": event_type,
                    "handler.type": handler_type,
                    "status": "error",
                    "error.type": type(ex).__name__,
                }
                record_metric("histogram", "neuroglia.event.processing.duration", duration_ms, metric_attributes, unit="ms", description="Event handler processing duration")

                # Log error
                log.error(f"❌ Event '{event_type}' processing failed in '{handler_type}' after {duration_ms:.2f}ms: {ex}")

                # Re-raise the exception
                raise


def wrap_event_handler_with_tracing(handler: DomainEventHandler[TEvent]) -> DomainEventHandler[TEvent]:
    """
    Convenience function to wrap an event handler with tracing.

    Args:
        handler: The event handler to wrap

    Returns:
        DomainEventHandler: The wrapped event handler with tracing

    Example:
        >>> handler = MyEventHandler()
        >>> traced_handler = wrap_event_handler_with_tracing(handler)
    """
    if OTEL_AVAILABLE:
        return TracedEventHandler(handler)
    return handler
