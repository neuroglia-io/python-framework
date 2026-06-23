"""
Test for Pizza event handlers to verify CloudEvent publishing.
"""

import asyncio
from decimal import Decimal

import pytest
from application.events.pizza_event_handlers import PizzaCreatedEventHandler
from domain.entities.enums import PizzaSize
from domain.events import PizzaCreatedEvent

from neuroglia.eventing.cloud_events.cloud_event import CloudEvent
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublishingOptions,
)
from neuroglia.mediation import Mediator


@pytest.mark.asyncio
async def test_pizza_created_event_handler_publishes_cloud_event():
    """Test that PizzaCreatedEventHandler publishes a CloudEvent"""

    # Arrange
    mediator = Mediator()
    cloud_event_bus = CloudEventBus()
    cloud_event_options = CloudEventPublishingOptions(source="https://mario-pizzeria.io", type_prefix="io.mario-pizzeria")

    handler = PizzaCreatedEventHandler(mediator, cloud_event_bus, cloud_event_options)

    # Track published cloud events
    published_events = []

    def on_cloud_event(event: CloudEvent):
        published_events.append(event)

    cloud_event_bus.output_stream.subscribe(on_cloud_event)

    # Act
    event = PizzaCreatedEvent(
        aggregate_id="pizza-123",
        name="Margherita",
        size=PizzaSize.LARGE.value,
        base_price=Decimal("12.99"),
        description="Classic pizza with tomato and mozzarella",
        toppings=["basil", "extra cheese"],
    )

    await handler.handle_async(event)

    # Assert
    assert len(published_events) == 1
    cloud_event = published_events[0]
    assert cloud_event.type == "io.mario-pizzeria.PizzaCreatedEvent"
    assert cloud_event.source == "https://mario-pizzeria.io"
    assert cloud_event.subject == "pizza-123"
    assert cloud_event.data["name"] == "Margherita"
    assert cloud_event.data["size"] == "large"
    assert str(cloud_event.data["base_price"]) == "12.99"
    assert cloud_event.data["toppings"] == ["basil", "extra cheese"]
    print("✅ Pizza CloudEvent published successfully!")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_pizza_created_event_handler_publishes_cloud_event())
