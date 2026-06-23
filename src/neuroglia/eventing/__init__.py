"""
Event-driven architecture components for building reactive and scalable systems.

This module provides comprehensive event handling capabilities including CloudEvents
specification support, domain events, event routing, and handler discovery for
implementing robust event-driven architectures and microservice communication.

Key Components:
    - CloudEvent: Standardized event format for inter-service communication
    - DomainEvent: Base class for business domain events
    - Event decorators: Handler registration and routing support
    - Infrastructure: Event publishing and subscription mechanisms

Features:
    - CloudEvents v1.0 specification compliance
    - Automatic event handler discovery and registration
    - Type-safe event routing and processing
    - Domain event integration with aggregates
    - Event sourcing and CQRS pattern support
    - Extensible attribute system for custom metadata

Examples:
    ```python
    from neuroglia.eventing import CloudEvent, DomainEvent
    from neuroglia.eventing.cloud_events import cloudevent

    # CloudEvent creation
    event = CloudEvent(
        id="order-created-123",
        source="/orders/service",
        type="order.created.v1",
        subject="order/123",
        data={"orderId": "123", "total": 99.99}
    )

    # Domain event
    class OrderCreatedDomainEvent(DomainEvent):
        def __init__(self, order_id: str, customer_id: str):
            super().__init__()
            self.order_id = order_id
            self.customer_id = customer_id

    # Event handler
    @cloudevent("order.created.v1")
    class OrderCreatedHandler:
        async def handle(self, event: CloudEvent):
            # Process order creation
            pass

    # Service registration
    services.add_eventing()
    event_bus = provider.get_service(EventBus)

    # Event publishing
    await event_bus.publish(event)
    ```

See Also:
    - Event-Driven Architecture: https://bvandewe.github.io/pyneuro/patterns/
    - CloudEvents Guide: https://bvandewe.github.io/pyneuro/features/
    - Domain Events: https://bvandewe.github.io/pyneuro/patterns/
"""

# Re-export DomainEvent from data module for convenient access in eventing context
from ..data.abstractions import DomainEvent
from .cloud_events import CloudEvent

__all__ = [
    "CloudEvent",
    "DomainEvent",
]
