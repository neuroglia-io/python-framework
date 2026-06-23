"""
Pizza event handlers for Mario's Pizzeria.

These handlers process pizza-related domain events to implement side effects like
notifications, menu updates, and analytics.
"""

import logging

from application.events.base_domain_event_handler import BaseDomainEventHandler
from domain.events import PizzaCreatedEvent, ToppingsUpdatedEvent

from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublishingOptions,
)
from neuroglia.mediation import DomainEventHandler, Mediator

# Set up logger
logger = logging.getLogger(__name__)


class PizzaCreatedEventHandler(BaseDomainEventHandler[PizzaCreatedEvent], DomainEventHandler[PizzaCreatedEvent]):
    """Handles pizza creation events - publishes cloud events for pizza catalog updates"""

    def __init__(
        self,
        mediator: Mediator,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
    ):
        super().__init__(mediator, cloud_event_bus, cloud_event_publishing_options)

    async def handle_async(self, event: PizzaCreatedEvent) -> None:
        """Process pizza created event"""
        logger.info(f"🍕 New pizza created: {event.name} ({event.size}) - ${event.base_price} " f"with toppings: {', '.join(event.toppings) if event.toppings else 'none'}")

        # In a real application, you might:
        # - Update menu display systems
        # - Notify admin dashboard
        # - Update inventory management system
        # - Trigger analytics/reporting
        # - Update cache/CDN for menu

        # CloudEvent published automatically by DomainEventCloudEventBehavior
        return None


class ToppingsUpdatedEventHandler(BaseDomainEventHandler[ToppingsUpdatedEvent], DomainEventHandler[ToppingsUpdatedEvent]):
    """Handles topping updates - publishes cloud events for pizza modifications"""

    def __init__(
        self,
        mediator: Mediator,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
    ):
        super().__init__(mediator, cloud_event_bus, cloud_event_publishing_options)

    async def handle_async(self, event: ToppingsUpdatedEvent) -> None:
        """Process toppings updated event"""
        logger.info(f"🧀 Toppings updated for pizza {event.aggregate_id}: {', '.join(event.toppings) if event.toppings else 'none'}")

        # In a real application, you might:
        # - Update pizza customization displays
        # - Recalculate pricing
        # - Update inventory for toppings
        # - Notify kitchen prep systems

        # CloudEvent published automatically by DomainEventCloudEventBehavior
        return None
