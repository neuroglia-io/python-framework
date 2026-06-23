"""
OpenTelemetry Metrics Module

Provides utilities for creating and recording metrics including counters,
histograms, gauges, and business-specific measurements.
"""
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Optional

from opentelemetry import metrics
from opentelemetry.metrics import (
    Counter,
    Histogram,
    Meter,
    ObservableGauge,
    UpDownCounter,
)

if TYPE_CHECKING:
    from opentelemetry.exporter.prometheus import PrometheusMetricReader

log = logging.getLogger(__name__)

# Global meter cache
_meters: dict[str, Meter] = {}

# Global instrument cache
_instruments: dict[str, Any] = {}


def get_meter(name: str, version: Optional[str] = None) -> Meter:
    """
    Get or create a meter for the given name.

    Args:
        name: Name of the meter (typically service or module name)
        version: Optional version of the instrumented code

    Returns:
        Meter: OpenTelemetry meter instance

    Example:
        >>> meter = get_meter("mario-pizzeria")
        >>> counter = meter.create_counter("orders.created")
    """
    key = f"{name}:{version}" if version else name
    if key not in _meters:
        _meters[key] = metrics.get_meter(name, version or "")
    return _meters[key]


def create_counter(
    name: str,
    unit: str = "1",
    description: str = "",
    meter_name: Optional[str] = None,
) -> Counter:
    """
    Create or retrieve a counter instrument.

    Counters are monotonically increasing values (only go up).
    Use for: request counts, items created, events processed.

    Args:
        name: Name of the counter
        unit: Unit of measurement (e.g., "1", "requests", "bytes")
        description: Description of what this counter measures
        meter_name: Name of the meter (defaults to "default")

    Returns:
        Counter: OpenTelemetry counter instrument

    Example:
        >>> orders_counter = create_counter(
        ...     "mario.orders.created",
        ...     unit="orders",
        ...     description="Total orders created"
        ... )
        >>> orders_counter.add(1, {"status": "pending"})
    """
    key = f"counter:{name}"
    if key not in _instruments:
        meter = get_meter(meter_name or "default")
        _instruments[key] = meter.create_counter(name, unit=unit, description=description)
    return _instruments[key]


def create_histogram(
    name: str,
    unit: str = "1",
    description: str = "",
    meter_name: Optional[str] = None,
) -> Histogram:
    """
    Create or retrieve a histogram instrument.

    Histograms record distributions of values.
    Use for: request durations, response sizes, operation times.

    Args:
        name: Name of the histogram
        unit: Unit of measurement (e.g., "ms", "bytes", "1")
        description: Description of what this histogram measures
        meter_name: Name of the meter (defaults to "default")

    Returns:
        Histogram: OpenTelemetry histogram instrument

    Example:
        >>> duration_histogram = create_histogram(
        ...     "mario.command.duration",
        ...     unit="ms",
        ...     description="Command execution duration"
        ... )
        >>> duration_histogram.record(123.45, {"command.type": "PlaceOrder"})
    """
    key = f"histogram:{name}"
    if key not in _instruments:
        meter = get_meter(meter_name or "default")
        _instruments[key] = meter.create_histogram(name, unit=unit, description=description)
    return _instruments[key]


def create_up_down_counter(
    name: str,
    unit: str = "1",
    description: str = "",
    meter_name: Optional[str] = None,
) -> UpDownCounter:
    """
    Create or retrieve an up-down counter instrument.

    Up-down counters can increase and decrease.
    Use for: active connections, queue size, concurrent requests.

    Args:
        name: Name of the counter
        unit: Unit of measurement
        description: Description of what this counter measures
        meter_name: Name of the meter (defaults to "default")

    Returns:
        UpDownCounter: OpenTelemetry up-down counter instrument

    Example:
        >>> active_orders = create_up_down_counter(
        ...     "mario.orders.active",
        ...     unit="orders",
        ...     description="Number of active orders"
        ... )
        >>> active_orders.add(1)  # Order started
        >>> active_orders.add(-1)  # Order completed
    """
    key = f"updowncounter:{name}"
    if key not in _instruments:
        meter = get_meter(meter_name or "default")
        _instruments[key] = meter.create_up_down_counter(name, unit=unit, description=description)
    return _instruments[key]


def create_observable_gauge(
    name: str,
    callback: Callable,
    unit: str = "1",
    description: str = "",
    meter_name: Optional[str] = None,
) -> ObservableGauge:
    """
    Create or retrieve an observable gauge instrument.

    Observable gauges are sampled periodically by calling a callback.
    Use for: current memory usage, temperature, queue depth.

    Args:
        name: Name of the gauge
        callback: Function that returns the current value
        unit: Unit of measurement
        description: Description of what this gauge measures
        meter_name: Name of the meter (defaults to "default")

    Returns:
        ObservableGauge: OpenTelemetry observable gauge instrument

    Example:
        >>> def get_queue_size():
        ...     return len(order_queue)
        ...
        >>> queue_gauge = create_observable_gauge(
        ...     "mario.queue.size",
        ...     callback=get_queue_size,
        ...     unit="items",
        ...     description="Current order queue size"
        ... )
    """
    key = f"gauge:{name}"
    if key not in _instruments:
        meter = get_meter(meter_name or "default")
        _instruments[key] = meter.create_observable_gauge(name, callbacks=[callback], unit=unit, description=description)
    return _instruments[key]


def record_metric(
    instrument_type: str,
    name: str,
    value: float,
    attributes: Optional[dict[str, Any]] = None,
    unit: str = "1",
    description: str = "",
):
    """
    Convenience function to record a metric value.

    Args:
        instrument_type: Type of instrument ("counter", "histogram", "updowncounter")
        name: Name of the metric
        value: Value to record
        attributes: Optional attributes/labels
        unit: Unit of measurement
        description: Description of the metric

    Example:
        >>> record_metric(
        ...     "counter",
        ...     "mario.pizzas.ordered",
        ...     quantity,
        ...     attributes={"pizza.type": "margherita"}
        ... )
    """
    attrs = attributes or {}

    if instrument_type == "counter":
        instrument = create_counter(name, unit=unit, description=description)
        instrument.add(value, attrs)
    elif instrument_type == "histogram":
        instrument = create_histogram(name, unit=unit, description=description)
        instrument.record(value, attrs)
    elif instrument_type == "updowncounter":
        instrument = create_up_down_counter(name, unit=unit, description=description)
        instrument.add(value, attrs)
    else:
        log.warning(f"Unknown instrument type: {instrument_type}")


# Prometheus Metrics Endpoint Support
try:
    from fastapi import Response
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from prometheus_client import CONTENT_TYPE_LATEST
    from prometheus_client import REGISTRY as default_registry
    from prometheus_client import generate_latest

    _prometheus_available = True

except ImportError:
    log.warning("⚠️ Prometheus metrics endpoint dependencies not available")
    _prometheus_available = False
    # Set to None - will be handled in functions
    Response = None
    PrometheusMetricReader = None
    CONTENT_TYPE_LATEST = None
    generate_latest = None
    default_registry = None

_prometheus_reader = None


def create_prometheus_metrics_reader():
    """
    Create a Prometheus metrics reader for OpenTelemetry.

    Returns:
        PrometheusMetricReader configured for metrics export, or None if not available
    """
    if not _prometheus_available:
        log.warning("⚠️ PrometheusMetricReader not available")
        return None

    global _prometheus_reader

    if _prometheus_reader is not None:
        return _prometheus_reader

    try:
        # Create PrometheusMetricReader (uses default registry internally)
        _prometheus_reader = PrometheusMetricReader()

        log.info("📊 Prometheus metrics reader created")
        return _prometheus_reader

    except Exception as ex:
        log.error(f"❌ Failed to create Prometheus metrics reader: {ex}")
        return None


def add_metrics_endpoint(app, path: str = "/metrics"):
    """
    Add a Prometheus metrics endpoint to a FastAPI application.

    This endpoint serves OpenTelemetry metrics in Prometheus format.
    Note: Requires that OpenTelemetry MeterProvider is configured with PrometheusMetricReader.

    Args:
        app: FastAPI application to add endpoint to
        path: HTTP path for metrics endpoint (default: /metrics)
    """
    if not _prometheus_available:
        log.error("❌ Cannot add metrics endpoint - Prometheus dependencies not installed")
        return

    @app.get(path, include_in_schema=False)
    async def metrics():
        """Prometheus metrics endpoint"""
        try:
            # Generate Prometheus format metrics from the default registry
            metrics_data = generate_latest(default_registry)
            return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

        except Exception as ex:
            log.error(f"❌ Error generating metrics: {ex}")
            return Response(content=f"# Error generating metrics: {ex}\n", media_type=CONTENT_TYPE_LATEST)

    log.info(f"📊 Prometheus metrics endpoint added at {path}")


def get_prometheus_reader():
    """Get the current Prometheus metrics reader"""
    return _prometheus_reader if _prometheus_available else None
