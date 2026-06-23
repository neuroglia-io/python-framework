"""
Mario's Pizzeria - Business Metrics Module

This module defines application-specific metrics for Mario's Pizzeria.
These metrics track business KPIs and operational metrics that are specific
to the pizza ordering and fulfillment domain.

Examples:
    ```python
    from observability.metrics import orders_created, order_value

    # Record business metrics in handlers
    orders_created.add(1, {"status": "pending", "payment": "credit_card"})
    order_value.record(float(order.total_amount), {"status": "pending"})
    ```

See Also:
    - OpenTelemetry Quick Reference: OTEL_QUICK_REFERENCE.md
    - Framework Observability: neuroglia.observability
"""

try:
    from neuroglia.observability.metrics import create_counter, create_histogram, create_up_down_counter

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


# Order Metrics
if OTEL_AVAILABLE:
    orders_created = create_counter(
        name="mario.orders.created",
        unit="orders",
        description="Total number of orders created",
    )

    orders_completed = create_counter(
        name="mario.orders.completed",
        unit="orders",
        description="Total number of orders completed",
    )

    orders_cancelled = create_counter(
        name="mario.orders.cancelled",
        unit="orders",
        description="Total number of orders cancelled",
    )

    orders_in_progress = create_up_down_counter(
        name="mario.orders.in_progress",
        unit="orders",
        description="Number of orders currently being prepared (up/down counter)",
    )

    order_value = create_histogram(
        name="mario.orders.value",
        unit="USD",
        description="Distribution of order values",
    )

    # Pizza Metrics
    pizzas_ordered = create_counter(
        name="mario.pizzas.ordered",
        unit="pizzas",
        description="Total number of pizzas ordered",
    )

    pizzas_by_size = create_counter(
        name="mario.pizzas.by_size",
        unit="pizzas",
        description="Total number of pizzas ordered by size",
    )

    # Kitchen Metrics
    kitchen_capacity_utilized = create_histogram(
        name="mario.kitchen.capacity_utilized",
        unit="percentage",
        description="Kitchen capacity utilization percentage",
    )

    cooking_duration = create_histogram(
        name="mario.kitchen.cooking_duration",
        unit="seconds",
        description="Time taken to cook pizzas",
    )

    # Customer Metrics
    customers_registered = create_counter(
        name="mario.customers.registered",
        unit="customers",
        description="Total number of customers registered",
    )

    customers_returning = create_counter(
        name="mario.customers.returning",
        unit="customers",
        description="Number of returning customers placing orders",
    )

else:
    # Graceful degradation - provide no-op metrics if OTEL not available
    class NoOpMetric:
        def add(self, value, attributes=None):
            pass

        def record(self, value, attributes=None):
            pass

    orders_created = NoOpMetric()
    orders_completed = NoOpMetric()
    orders_cancelled = NoOpMetric()
    orders_in_progress = NoOpMetric()
    order_value = NoOpMetric()
    pizzas_ordered = NoOpMetric()
    pizzas_by_size = NoOpMetric()
    kitchen_capacity_utilized = NoOpMetric()
    cooking_duration = NoOpMetric()
    customers_registered = NoOpMetric()
    customers_returning = NoOpMetric()


# Export all metrics
__all__ = [
    "orders_created",
    "orders_completed",
    "orders_cancelled",
    "orders_in_progress",
    "order_value",
    "pizzas_ordered",
    "pizzas_by_size",
    "kitchen_capacity_utilized",
    "cooking_duration",
    "customers_registered",
    "customers_returning",
]
