"""
Event handlers package for Mario's Pizzeria.

This package contains domain event handlers organized by aggregate/entity:
- order_event_handlers: Order lifecycle and pizza management events
- customer_event_handlers: Customer registration, profile, and contact update events
- pizza_event_handlers: Pizza creation and topping modification events
"""

# Customer event handlers
from .customer_event_handlers import (
    CustomerContactUpdatedEventHandler,
    CustomerProfileCreatedEventHandler,
    CustomerRegisteredEventHandler,
)

# Order event handlers
from .order_event_handlers import (
    CookingStartedEventHandler,
    OrderCancelledEventHandler,
    OrderConfirmedEventHandler,
    OrderDeliveredEventHandler,
    OrderReadyEventHandler,
    PizzaAddedToOrderEventHandler,
    PizzaRemovedFromOrderEventHandler,
)

# Pizza event handlers
from .pizza_event_handlers import PizzaCreatedEventHandler, ToppingsUpdatedEventHandler

__all__ = [
    # Order handlers
    "OrderConfirmedEventHandler",
    "CookingStartedEventHandler",
    "OrderReadyEventHandler",
    "OrderDeliveredEventHandler",
    "OrderCancelledEventHandler",
    "PizzaAddedToOrderEventHandler",
    "PizzaRemovedFromOrderEventHandler",
    # Customer handlers
    "CustomerRegisteredEventHandler",
    "CustomerProfileCreatedEventHandler",
    "CustomerContactUpdatedEventHandler",
    # Pizza handlers
    "PizzaCreatedEventHandler",
    "ToppingsUpdatedEventHandler",
]
