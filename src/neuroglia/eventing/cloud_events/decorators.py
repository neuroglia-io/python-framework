"""
Decorators for CloudEvent handler registration and type-based routing.

This module provides decorators for marking event handlers with their associated
CloudEvent types, enabling automatic handler discovery and type-safe event routing
in event-driven architectures.

Features:
    - Type-based handler registration
    - Automatic handler discovery
    - CloudEvent type metadata attachment
    - Integration with event bus systems

Examples:
    ```python
    from neuroglia.eventing.cloud_events import cloudevent
    from neuroglia.eventing import CloudEvent

    @cloudevent("order.created.v1")
    class OrderCreatedHandler:
        async def handle(self, event: CloudEvent):
            # Handle order created event
            pass

    @cloudevent("payment.processed.v1")
    class PaymentHandler:
        async def handle(self, event: CloudEvent):
            # Handle payment processed event
            pass
    ```

See Also:
    - Event Handling: https://bvandewe.github.io/pyneuro/patterns/
    - CloudEvents: https://cloudevents.io/
"""


def cloudevent(cloud_event_type: str):
    """
    Decorator for marking event handlers with their associated CloudEvent type.

    This decorator enables automatic registration and routing of event handlers
    based on CloudEvent types, supporting event-driven architecture patterns
    with type safety and automatic handler discovery.

    Args:
        cloud_event_type (str): The CloudEvent type that this handler processes

    Returns:
        Callable: Decorated class with CloudEvent type metadata

    Examples:
        ```python
        @cloudevent("order.created.v1")
        class OrderCreatedHandler:
            async def handle(self, event: CloudEvent):
                order_data = event.data
                await self.process_new_order(order_data["orderId"])

        @cloudevent("payment.processed.v1")
        class PaymentProcessedHandler:
            async def handle(self, event: CloudEvent):
                payment_info = event.data
                await self.update_order_status(payment_info["orderId"])

        # Handler discovery and registration
        event_bus = provider.get_service(EventBus)
        event_bus.register_handlers_from_module("app.handlers")

        # Automatic routing
        order_event = CloudEvent(
            id="evt-123",
            source="/orders",
            type="order.created.v1",  # Routes to OrderCreatedHandler
            data={"orderId": "123"}
        )
        await event_bus.publish(order_event)
        ```

    See Also:
        - Event Handling Guide: https://bvandewe.github.io/pyneuro/patterns/
        - CloudEvents: https://bvandewe.github.io/pyneuro/features/
    """

    def decorator(cls):
        cls.__cloudevent__type__ = cloud_event_type
        return cls

    return decorator
