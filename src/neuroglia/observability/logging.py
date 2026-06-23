"""
OpenTelemetry Logging Module

Provides structured logging with trace context correlation and integration
with OpenTelemetry logging exporters.
"""

import json
import logging
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.trace import format_span_id, format_trace_id


class TraceContextFilter(logging.Filter):
    """
    Logging filter that adds trace context (trace_id, span_id) to log records.
    This enables correlation between logs and traces.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            record.trace_id = format_trace_id(ctx.trace_id)
            record.span_id = format_span_id(ctx.span_id)
            record.trace_flags = f"{ctx.trace_flags:02x}"
        else:
            record.trace_id = "0" * 32
            record.span_id = "0" * 16
            record.trace_flags = "00"
        return True


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter that outputs structured logs with trace context.
    """

    def __init__(self, service_name: str = "unknown"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "service.name": self.service_name,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add trace context if available
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
            log_data["span_id"] = record.span_id
            log_data["trace_flags"] = record.trace_flags

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


def configure_logging(
    level: int = logging.INFO,
    service_name: str = "unknown-service",
    enable_structured_logging: bool = True,
    enable_trace_context: bool = True,
) -> logging.Logger:
    """
    Configure logging with trace context and optional structured output.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Name of the service for log attribution
        enable_structured_logging: Enable JSON structured logging
        enable_trace_context: Enable trace context injection

    Returns:
        logging.Logger: Configured root logger

    Example:
        >>> configure_logging(
        ...     level=logging.INFO,
        ...     service_name="mario-pizzeria",
        ...     enable_structured_logging=True
        ... )
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(level)

    # Configure formatter
    if enable_structured_logging:
        formatter = StructuredFormatter(service_name=service_name)
    else:
        # Simple text format with trace context
        if enable_trace_context:
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - [trace_id=%(trace_id)s span_id=%(span_id)s] - %(message)s")
        else:
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    handler.setFormatter(formatter)

    # Add trace context filter
    if enable_trace_context:
        handler.addFilter(TraceContextFilter())

    root_logger.addHandler(handler)

    logging.info(f"✅ Logging configured for service '{service_name}' at level {logging.getLevelName(level)}")

    return root_logger


def get_logger_with_trace_context(name: str) -> logging.Logger:
    """
    Get a logger configured with trace context.

    Args:
        name: Name of the logger (typically __name__)

    Returns:
        logging.Logger: Logger with trace context support

    Example:
        >>> log = get_logger_with_trace_context(__name__)
        >>> log.info("Processing order", extra={"order_id": "123"})
    """
    logger = logging.getLogger(name)

    # Ensure at least one handler has trace context filter
    has_trace_filter = False
    for handler in logger.handlers:
        for filter in handler.filters:
            if isinstance(filter, TraceContextFilter):
                has_trace_filter = True
                break

    if not has_trace_filter:
        for handler in logger.handlers:
            handler.addFilter(TraceContextFilter())

    return logger


def log_with_trace(
    logger: logging.Logger,
    level: int,
    message: str,
    attributes: Optional[dict[str, Any]] = None,
):
    """
    Log a message with trace context and additional attributes.

    Args:
        logger: Logger to use
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Log message
        attributes: Additional attributes to include in the log

    Example:
        >>> log = logging.getLogger(__name__)
        >>> log_with_trace(
        ...     log,
        ...     logging.INFO,
        ...     "Order processed successfully",
        ...     {"order_id": "123", "customer_id": "456"}
        ... )
    """
    extra = attributes or {}

    # Add current span context
    span = trace.get_current_span()
    if span and span.is_recording():
        ctx = span.get_span_context()
        extra["trace_id"] = format_trace_id(ctx.trace_id)
        extra["span_id"] = format_span_id(ctx.span_id)

    logger.log(level, message, extra={"extra": extra})


class LoggingContext:
    """
    Context manager for adding contextual information to logs within a scope.
    """

    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None

    def __enter__(self):
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        self.old_factory = old_factory
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


# Example usage context manager
def with_logging_context(**context):
    """
    Context manager for adding contextual information to all logs within the scope.

    Args:
        **context: Key-value pairs to add to log records

    Example:
        >>> with with_logging_context(order_id="123", customer_id="456"):
        ...     log.info("Processing order")  # Will include order_id and customer_id
        ...     log.info("Order validated")   # Will include order_id and customer_id
    """
    logger = logging.getLogger()
    return LoggingContext(logger, **context)
