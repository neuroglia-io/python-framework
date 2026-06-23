"""
Structlog integration for Neuroglia framework.

Provides structured logging with automatic OpenTelemetry trace correlation,
JSON output for production, and console output for development.

This module is optional - it requires the `structlog` package to be installed.
If structlog is not available, a fallback to standard logging is provided.

Usage:
    from neuroglia.observability.structlog_integration import configure_structlog, get_structlog_logger

    # In application startup
    configure_structlog(
        service_name="my-service",
        log_level="INFO",
        json_format=True,  # JSON for production
        add_trace_context=True,
    )

    # In application code
    log = get_structlog_logger(__name__)
    log.info("order_created", order_id="123", customer_id="456", total=99.99)

Output Example (JSON):
    {
        "timestamp": "2025-01-19T10:30:00.000Z",
        "level": "info",
        "logger": "application.handlers",
        "event": "order_created",
        "order_id": "123",
        "customer_id": "456",
        "total": 99.99,
        "trace_id": "0af7651916cd43dd8448eb211c80319c",
        "span_id": "b7ad6b7169203331"
    }
"""

import logging
from typing import Any, Optional

from opentelemetry import trace

# Feature detection for structlog
try:
    import structlog
    from structlog.types import Processor

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    structlog = None  # type: ignore[assignment]
    Processor = Any  # type: ignore[assignment, misc]


log = logging.getLogger(__name__)


def add_otel_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add OpenTelemetry trace context to log records.

    This is a structlog processor that automatically adds trace_id and span_id
    from the current OpenTelemetry span context.

    Args:
        logger: The wrapped logger object.
        method_name: The name of the method called on the logger.
        event_dict: The event dictionary being logged.

    Returns:
        The event dictionary with trace context added.
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def configure_structlog(
    service_name: str,
    log_level: str = "INFO",
    json_format: bool = True,
    add_trace_context: bool = True,
    additional_processors: Optional[list[Processor]] = None,
    suppress_noisy_loggers: bool = True,
) -> None:
    """Configure structlog with OpenTelemetry trace correlation.

    Sets up structlog for structured logging with automatic trace context
    injection and choice of JSON or console output format.

    Args:
        service_name: Name of the service for log attribution.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: Use JSON output (True) or console output (False).
                     JSON is recommended for production, console for development.
        add_trace_context: Add OpenTelemetry trace/span IDs to logs.
        additional_processors: Additional structlog processors to add to the chain.
        suppress_noisy_loggers: Reduce log level of noisy third-party loggers.

    Raises:
        ImportError: If structlog is not installed.

    Example:
        >>> configure_structlog(
        ...     service_name="my-service",
        ...     log_level="INFO",
        ...     json_format=True,
        ...     add_trace_context=True,
        ... )
    """
    if not STRUCTLOG_AVAILABLE:
        raise ImportError("structlog is required for structured logging. " "Install with: pip install structlog")

    # Base processors for all configurations
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add service name processor
    def add_service_name(
        logger: logging.Logger,
        method_name: str,
        event_dict: dict[str, Any],
    ) -> dict[str, Any]:
        event_dict["service.name"] = service_name
        return event_dict

    processors.append(add_service_name)

    # Add OpenTelemetry context processor
    if add_trace_context:
        processors.append(add_otel_context)

    # Add custom processors
    if additional_processors:
        processors.extend(additional_processors)

    # Add output formatter (must be last)
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging to work with structlog
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
    )

    # Reduce noise from third-party libraries
    if suppress_noisy_loggers:
        noisy_loggers = [
            "uvicorn",
            "uvicorn.access",
            "uvicorn.error",
            "fastapi",
            "httpx",
            "httpcore",
            "pymongo",
            "motor",
            "asyncio",
            "opentelemetry",
            "opentelemetry.sdk",
        ]
        for logger_name in noisy_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    log.info(f"✅ Structlog configured for service '{service_name}' at level {log_level}")


def get_structlog_logger(name: str) -> Any:
    """Get a structlog logger instance.

    Returns a structlog bound logger if structlog is available,
    otherwise falls back to standard library logging.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Structlog bound logger instance, or standard logging.Logger as fallback.

    Example:
        >>> log = get_structlog_logger(__name__)
        >>> log.info("user_login", user_id="123", ip_address="192.168.1.1")
    """
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)


def bind_contextvars(**context: Any) -> None:
    """Bind context variables that will be included in all subsequent log entries.

    This is useful for adding request-scoped context like user_id or request_id
    that should appear in all logs within that context.

    Args:
        **context: Key-value pairs to bind to the logging context.

    Example:
        >>> bind_contextvars(user_id="123", request_id="abc-xyz")
        >>> log.info("processing")  # Will include user_id and request_id
    """
    if STRUCTLOG_AVAILABLE:
        structlog.contextvars.bind_contextvars(**context)
    else:
        log.debug(f"Structlog not available, context not bound: {context}")


def clear_contextvars() -> None:
    """Clear all bound context variables.

    Should be called at the end of a request or context scope to prevent
    context from leaking to other requests.
    """
    if STRUCTLOG_AVAILABLE:
        structlog.contextvars.clear_contextvars()
