"""
OpenTelemetry Tracing Module

Provides utilities for distributed tracing including decorators for automatic
span creation, context management, and span attribute handling.
"""
import functools
import logging
from collections.abc import Callable
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.trace import Span, StatusCode, Tracer
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

log = logging.getLogger(__name__)

# Global tracer cache
_tracers: dict[str, Tracer] = {}


def get_tracer(name: str, version: Optional[str] = None) -> Tracer:
    """
    Get or create a tracer for the given name.

    Args:
        name: Name of the tracer (typically __name__ of the module)
        version: Optional version of the instrumented code

    Returns:
        Tracer: OpenTelemetry tracer instance

    Example:
        >>> tracer = get_tracer(__name__)
        >>> with tracer.start_as_current_span("operation"):
        ...     # Your code here
        ...     pass
    """
    key = f"{name}:{version}" if version else name
    if key not in _tracers:
        _tracers[key] = trace.get_tracer(name, version)
    return _tracers[key]


def get_current_span() -> Span:
    """
    Get the currently active span.

    Returns:
        Span: The current span or a non-recording span if none is active
    """
    return trace.get_current_span()


def add_span_attributes(attributes: dict[str, Any], span: Optional[Span] = None):
    """
    Add attributes to a span.

    Args:
        attributes: Dictionary of attributes to add
        span: Span to add attributes to (defaults to current span)

    Example:
        >>> add_span_attributes({
        ...     "user.id": "user_123",
        ...     "order.id": "order_456"
        ... })
    """
    target_span = span or get_current_span()
    if target_span.is_recording():
        for key, value in attributes.items():
            target_span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[dict[str, Any]] = None, span: Optional[Span] = None):
    """
    Add an event to a span with optional attributes.

    Args:
        name: Name of the event
        attributes: Optional attributes for the event
        span: Span to add event to (defaults to current span)

    Example:
        >>> add_span_event("order_validated", {
        ...     "order.id": "order_123",
        ...     "validation.result": "success"
        ... })
    """
    target_span = span or get_current_span()
    if target_span.is_recording():
        target_span.add_event(name, attributes=attributes or {})


def record_exception(exception: Exception, attributes: Optional[dict[str, Any]] = None, span: Optional[Span] = None):
    """
    Record an exception in a span.

    Args:
        exception: The exception to record
        attributes: Optional additional attributes
        span: Span to record exception in (defaults to current span)

    Example:
        >>> try:
        ...     risky_operation()
        ... except ValueError as ex:
        ...     record_exception(ex, {"context": "processing_order"})
        ...     raise
    """
    target_span = span or get_current_span()
    if target_span.is_recording():
        target_span.record_exception(exception, attributes=attributes)
        target_span.set_status(StatusCode.ERROR, str(exception))


def trace_async(
    span_name: Optional[str] = None,
    tracer_name: Optional[str] = None,
    attributes: Optional[dict[str, Any]] = None,
    record_exception_on_error: bool = True,
):
    """
    Decorator for automatically tracing async functions.

    Args:
        span_name: Name of the span (defaults to function name)
        tracer_name: Name of the tracer (defaults to function module)
        attributes: Static attributes to add to the span
        record_exception_on_error: Whether to record exceptions automatically

    Example:
        >>> @trace_async(attributes={"operation.type": "database"})
        ... async def get_user(user_id: str):
        ...     return await db.get_user(user_id)
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            _tracer_name = tracer_name or func.__module__
            _span_name = span_name or func.__name__

            tracer = get_tracer(_tracer_name)

            with tracer.start_as_current_span(_span_name) as span:
                # Add static attributes
                if attributes:
                    add_span_attributes(attributes, span)

                # Add function information
                add_span_attributes(
                    {
                        "code.function": func.__name__,
                        "code.namespace": func.__module__,
                    },
                    span,
                )

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(StatusCode.OK)
                    return result
                except Exception as ex:
                    if record_exception_on_error:
                        record_exception(ex, span=span)
                    raise

        return wrapper

    return decorator


def trace_sync(
    span_name: Optional[str] = None,
    tracer_name: Optional[str] = None,
    attributes: Optional[dict[str, Any]] = None,
    record_exception_on_error: bool = True,
):
    """
    Decorator for automatically tracing synchronous functions.

    Args:
        span_name: Name of the span (defaults to function name)
        tracer_name: Name of the tracer (defaults to function module)
        attributes: Static attributes to add to the span
        record_exception_on_error: Whether to record exceptions automatically

    Example:
        >>> @trace_sync(attributes={"operation.type": "calculation"})
        ... def calculate_total(items):
        ...     return sum(item.price for item in items)
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _tracer_name = tracer_name or func.__module__
            _span_name = span_name or func.__name__

            tracer = get_tracer(_tracer_name)

            with tracer.start_as_current_span(_span_name) as span:
                # Add static attributes
                if attributes:
                    add_span_attributes(attributes, span)

                # Add function information
                add_span_attributes(
                    {
                        "code.function": func.__name__,
                        "code.namespace": func.__module__,
                    },
                    span,
                )

                try:
                    result = func(*args, **kwargs)
                    span.set_status(StatusCode.OK)
                    return result
                except Exception as ex:
                    if record_exception_on_error:
                        record_exception(ex, span=span)
                    raise

        return wrapper

    return decorator


def extract_trace_context(headers: dict[str, str]) -> Any:
    """
    Extract trace context from HTTP headers.

    Args:
        headers: HTTP headers dictionary

    Returns:
        Extracted context
    """
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(carrier=headers)


def inject_trace_context(headers: dict[str, str]) -> dict[str, str]:
    """
    Inject trace context into HTTP headers.

    Args:
        headers: HTTP headers dictionary to inject into

    Returns:
        Headers with injected trace context
    """
    propagator = TraceContextTextMapPropagator()
    propagator.inject(carrier=headers)
    return headers
