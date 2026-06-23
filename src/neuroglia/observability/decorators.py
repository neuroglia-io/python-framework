"""
Decorators for automatic metrics recording.

Provides convenience decorators for tracking operation counts and latencies
without manual instrumentation in every handler.

Usage:
    from neuroglia.observability.decorators import track_operation, track_latency

    @track_operation("skills_manager.skills.created")
    async def handle_async(self, command):
        # Your logic here
        ...

    @track_latency("api.request")
    async def endpoint(self, request):
        # Your logic here
        ...
"""
import asyncio
import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from neuroglia.observability.metrics import create_counter, create_histogram

P = ParamSpec("P")
T = TypeVar("T")


def track_operation(
    metric_name: str,
    success_status: str = "success",
    error_status: str = "error",
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to track operation count and status.

    Creates a counter metric that increments on each call, with a status
    label indicating success or error.

    Args:
        metric_name: Base name for the metric (e.g., "skills_manager.skills.created").
        success_status: Status label for successful operations (default: "success").
        error_status: Status label for failed operations (default: "error").

    Returns:
        Decorated function with automatic operation tracking.

    Example:
        >>> @track_operation("skills_manager.skills.created")
        ... async def create_skill(self, command):
        ...     # On success: counter increments with status="success"
        ...     # On exception: counter increments with status="error"
        ...     return result
    """
    # Create counter lazily on first call
    counter = create_counter(
        name=metric_name,
        description=f"Total {metric_name.split('.')[-1]} operations",
        unit="1",
    )

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                try:
                    result = await func(*args, **kwargs)
                    counter.add(1, {"status": success_status})
                    return result
                except Exception:
                    counter.add(1, {"status": error_status})
                    raise

            return async_wrapper  # type: ignore[return-value]
        else:

            @wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                try:
                    result = func(*args, **kwargs)
                    counter.add(1, {"status": success_status})
                    return result
                except Exception:
                    counter.add(1, {"status": error_status})
                    raise

            return sync_wrapper  # type: ignore[return-value]

    return decorator


def track_latency(
    metric_name: str,
    unit: str = "ms",
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to track operation latency.

    Creates a histogram metric that records the duration of each call.

    Args:
        metric_name: Base name for the metric (e.g., "api.request").
        unit: Unit of measurement (default: "ms").

    Returns:
        Decorated function with automatic latency tracking.

    Example:
        >>> @track_latency("api.request")
        ... async def handle_request(self, request):
        ...     # Duration is recorded as histogram after completion
        ...     return response
    """
    # Create histogram lazily on first call
    histogram = create_histogram(
        name=f"{metric_name}.latency",
        description=f"{metric_name} latency",
        unit=unit,
    )

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                start = time.perf_counter()
                try:
                    return await func(*args, **kwargs)
                finally:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    histogram.record(elapsed_ms)

            return async_wrapper  # type: ignore[return-value]
        else:

            @wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                start = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    histogram.record(elapsed_ms)

            return sync_wrapper  # type: ignore[return-value]

    return decorator


def track_operation_and_latency(
    metric_name: str,
    success_status: str = "success",
    error_status: str = "error",
    latency_unit: str = "ms",
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Combined decorator to track both operation count and latency.

    Combines the functionality of @track_operation and @track_latency
    into a single decorator for convenience.

    Args:
        metric_name: Base name for both metrics.
        success_status: Status label for successful operations.
        error_status: Status label for failed operations.
        latency_unit: Unit for latency measurement (default: "ms").

    Returns:
        Decorated function with both operation and latency tracking.

    Example:
        >>> @track_operation_and_latency("skills_manager.skills.created")
        ... async def create_skill(self, command):
        ...     # Records both count and latency metrics
        ...     return result
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # Apply both decorators
        decorated = track_latency(metric_name, latency_unit)(func)
        decorated = track_operation(metric_name, success_status, error_status)(decorated)
        return decorated  # type: ignore[return-value]

    return decorator
