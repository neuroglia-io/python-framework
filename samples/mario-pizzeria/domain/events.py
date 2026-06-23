"""
Domain events for Mario's Pizzeria business operations.

These events represent important business occurrences that have happened in the past
and may trigger side effects like notifications, logging, or updating read models.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from neuroglia.data.abstractions import DomainEvent
from neuroglia.eventing.cloud_events.decorators import cloudevent


@cloudevent("order.created.v1")
@dataclass
class OrderCreatedEvent(DomainEvent):
    """Event raised when a new order is created."""

    def __init__(self, aggregate_id: str, customer_id: str, order_time: datetime):
        super().__init__(aggregate_id)
        self.customer_id = customer_id
        self.order_time = order_time

    customer_id: str
    order_time: datetime


@cloudevent("order.pizza.added.v1")
@dataclass
class PizzaAddedToOrderEvent(DomainEvent):
    """Event raised when a pizza is added to an order."""

    def __init__(self, aggregate_id: str, line_item_id: str, pizza_name: str, pizza_size: str, price: Decimal):
        super().__init__(aggregate_id)
        self.line_item_id = line_item_id
        self.pizza_name = pizza_name
        self.pizza_size = pizza_size
        self.price = price

    line_item_id: str
    pizza_name: str
    pizza_size: str
    price: Decimal


@cloudevent("order.pizza.removed.v1")
@dataclass
class PizzaRemovedFromOrderEvent(DomainEvent):
    """Event raised when a pizza is removed from an order."""

    def __init__(self, aggregate_id: str, line_item_id: str):
        super().__init__(aggregate_id)
        self.line_item_id = line_item_id

    line_item_id: str


@cloudevent("order.confirmed.v1")
@dataclass
class OrderConfirmedEvent(DomainEvent):
    """Event raised when an order is confirmed."""

    def __init__(self, aggregate_id: str, confirmed_time: datetime, total_amount: Decimal, pizza_count: int):
        super().__init__(aggregate_id)
        self.confirmed_time = confirmed_time
        self.total_amount = total_amount
        self.pizza_count = pizza_count

    confirmed_time: datetime
    total_amount: Decimal
    pizza_count: int


@cloudevent("order.cooking.started.v1")
@dataclass
class CookingStartedEvent(DomainEvent):
    """Event raised when cooking starts for an order."""

    def __init__(
        self,
        aggregate_id: str,
        cooking_started_time: datetime,
        user_id: str,
        user_name: str,
    ):
        super().__init__(aggregate_id)
        self.cooking_started_time = cooking_started_time
        self.user_id = user_id
        self.user_name = user_name

    cooking_started_time: datetime
    user_id: str
    user_name: str


@cloudevent("order.ready.v1")
@dataclass
class OrderReadyEvent(DomainEvent):
    """Event raised when an order is ready for pickup/delivery."""

    def __init__(
        self,
        aggregate_id: str,
        ready_time: datetime,
        estimated_ready_time: Optional[datetime],
        user_id: str,
        user_name: str,
    ):
        super().__init__(aggregate_id)
        self.ready_time = ready_time
        self.estimated_ready_time = estimated_ready_time
        self.user_id = user_id
        self.user_name = user_name

    ready_time: datetime
    estimated_ready_time: Optional[datetime]
    user_id: str
    user_name: str


@cloudevent("order.delivery.driver.assigned.v1")
@dataclass
class OrderAssignedToDeliveryEvent(DomainEvent):
    """Event raised when an order is assigned to a delivery driver."""

    def __init__(self, aggregate_id: str, delivery_person_id: str, assignment_time: datetime):
        super().__init__(aggregate_id)
        self.delivery_person_id = delivery_person_id
        self.assignment_time = assignment_time

    delivery_person_id: str
    assignment_time: datetime


@cloudevent("order.delivery.started.v1")
@dataclass
class OrderOutForDeliveryEvent(DomainEvent):
    """Event raised when an order is out for delivery."""

    def __init__(self, aggregate_id: str, out_for_delivery_time: datetime):
        super().__init__(aggregate_id)
        self.out_for_delivery_time = out_for_delivery_time

    out_for_delivery_time: datetime


@cloudevent("order.delivered.v1")
@dataclass
class OrderDeliveredEvent(DomainEvent):
    """Event raised when an order is delivered."""

    def __init__(
        self,
        aggregate_id: str,
        delivered_time: datetime,
        user_id: str,
        user_name: str,
    ):
        super().__init__(aggregate_id)
        self.delivered_time = delivered_time
        self.user_id = user_id
        self.user_name = user_name

    delivered_time: datetime
    user_id: str
    user_name: str


@cloudevent("order.cancelled.v1")
@dataclass
class OrderCancelledEvent(DomainEvent):
    """Event raised when an order is cancelled."""

    def __init__(self, aggregate_id: str, cancelled_time: datetime, reason: Optional[str]):
        super().__init__(aggregate_id)
        self.cancelled_time = cancelled_time
        self.reason = reason

    cancelled_time: datetime
    reason: Optional[str]


@cloudevent("customer.registered.v1")
@dataclass
class CustomerRegisteredEvent(DomainEvent):
    """Event raised when a new customer is registered."""

    aggregate_id: str  # Must be defined here for dataclass __init__
    name: str
    email: str
    phone: str
    address: str
    user_id: Optional[str] = None  # Keycloak user ID for profile linkage

    def __post_init__(self):
        """Initialize parent class fields after dataclass initialization"""
        # Dataclasses don't automatically call parent __init__, so we need to set these manually
        if not hasattr(self, "created_at"):
            self.created_at = datetime.now()
        # aggregate_version is set by the parent
        if not hasattr(self, "aggregate_version"):
            self.aggregate_version = 0


@cloudevent("customer.contact.updated.v1")
@dataclass
class CustomerContactUpdatedEvent(DomainEvent):
    """Event raised when customer contact information is updated."""

    def __init__(self, aggregate_id: str, phone: str, address: str):
        super().__init__(aggregate_id)
        self.phone = phone
        self.address = address

    phone: str
    address: str


@cloudevent("customer.profile.created.v1")
@dataclass
class CustomerProfileCreatedEvent(DomainEvent):
    """
    Event raised when a customer profile is created (either explicitly or auto-created from Keycloak).

    This is distinct from CustomerRegisteredEvent - this specifically indicates
    profile creation which may trigger welcome emails, onboarding workflows, etc.
    """

    aggregate_id: str  # Customer ID
    user_id: str  # Keycloak user ID
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None

    def __post_init__(self):
        """Initialize parent class fields after dataclass initialization"""
        if not hasattr(self, "created_at"):
            self.created_at = datetime.now()
        if not hasattr(self, "aggregate_version"):
            self.aggregate_version = 0


@cloudevent("pizza.created.v1")
@dataclass
class PizzaCreatedEvent(DomainEvent):
    """Event raised when a new pizza is created."""

    def __init__(
        self,
        aggregate_id: str,
        name: str,
        size: str,
        base_price: Decimal,
        description: str,
        toppings: list[str],
    ):
        super().__init__(aggregate_id)
        self.name = name
        self.size = size
        self.base_price = base_price
        self.description = description
        self.toppings = toppings

    name: str
    size: str
    base_price: Decimal
    description: str
    toppings: list[str]


@cloudevent("pizza.toppings.updated.v1")
@dataclass
class ToppingsUpdatedEvent(DomainEvent):
    """Event raised when pizza toppings are updated."""

    def __init__(self, aggregate_id: str, toppings: list[str]):
        super().__init__(aggregate_id)
        self.toppings = toppings

    toppings: list[str]


@cloudevent("customer.notification.created.v1")
@dataclass
class CustomerNotificationCreatedEvent(DomainEvent):
    """Event raised when a customer notification is created."""

    def __init__(
        self,
        aggregate_id: str,
        customer_id: str,
        notification_type: str,
        title: str,
        message: str,
        order_id: Optional[str] = None,
    ):
        super().__init__(aggregate_id)
        self.customer_id = customer_id
        self.notification_type = notification_type
        self.title = title
        self.message = message
        self.order_id = order_id

    customer_id: str
    notification_type: str
    title: str
    message: str
    order_id: Optional[str]


@cloudevent("customer.notification.read.v1")
@dataclass
class CustomerNotificationReadEvent(DomainEvent):
    """Event raised when a customer notification is marked as read."""

    def __init__(self, aggregate_id: str, read_time: datetime):
        super().__init__(aggregate_id)
        self.read_time = read_time

    read_time: datetime


@cloudevent("customer.notification.dismissed.v1")
@dataclass
class CustomerNotificationDismissedEvent(DomainEvent):
    """Event raised when a customer notification is dismissed."""

    def __init__(self, aggregate_id: str, dismissed_time: datetime):
        super().__init__(aggregate_id)
        self.dismissed_time = dismissed_time

    dismissed_time: datetime


@cloudevent("customer.active.order.added.v1")
@dataclass
class CustomerActiveOrderAddedEvent(DomainEvent):
    """Event raised when an order is added to customer's active orders."""

    def __init__(self, aggregate_id: str, order_id: str):
        super().__init__(aggregate_id)
        self.order_id = order_id

    order_id: str


@cloudevent("customer.active.order.removed.v1")
@dataclass
class CustomerActiveOrderRemovedEvent(DomainEvent):
    """Event raised when an order is removed from customer's active orders."""

    def __init__(self, aggregate_id: str, order_id: str):
        super().__init__(aggregate_id)
        self.order_id = order_id

    order_id: str
