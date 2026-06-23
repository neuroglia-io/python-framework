"""Order entity for Mario's Pizzeria domain"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from api.dtos import OrderDto
from domain.events import (
    CookingStartedEvent,
    OrderAssignedToDeliveryEvent,
    OrderCancelledEvent,
    OrderConfirmedEvent,
    OrderCreatedEvent,
    OrderDeliveredEvent,
    OrderOutForDeliveryEvent,
    OrderReadyEvent,
    PizzaAddedToOrderEvent,
    PizzaRemovedFromOrderEvent,
)
from multipledispatch import dispatch

from neuroglia.data.abstractions import AggregateRoot, AggregateState
from neuroglia.mapping.mapper import map_from, map_to

from .enums import OrderStatus
from .order_item import OrderItem


class OrderState(AggregateState[str]):
    """State for Order aggregate - contains all persisted data"""

    # Class-level type annotations (required for JsonSerializer deserialization)
    customer_id: Optional[str]
    order_items: list[OrderItem]  # Value objects
    status: OrderStatus
    order_time: Optional[datetime]
    confirmed_time: Optional[datetime]
    cooking_started_time: Optional[datetime]
    actual_ready_time: Optional[datetime]
    estimated_ready_time: Optional[datetime]
    delivery_person_id: Optional[str]  # Track who is delivering
    out_for_delivery_time: Optional[datetime]  # When order left for delivery
    notes: Optional[str]

    # User tracking fields - who performed each action
    chef_user_id: Optional[str]  # User who started cooking
    chef_name: Optional[str]  # Name of chef who started cooking
    ready_by_user_id: Optional[str]  # User who marked order as ready
    ready_by_name: Optional[str]  # Name of user who marked as ready
    delivery_user_id: Optional[str]  # User who delivered the order
    delivery_name: Optional[str]  # Name of delivery person

    def __init__(self):
        super().__init__()
        self.customer_id = None
        self.order_items = []  # Changed from list[Pizza] to list[OrderItem]
        self.status = OrderStatus.PENDING
        self.order_time = None
        self.confirmed_time = None
        self.cooking_started_time = None
        self.actual_ready_time = None
        self.estimated_ready_time = None
        self.delivery_person_id = None
        self.out_for_delivery_time = None
        self.delivered_time = None
        self.notes = None

        # Initialize user tracking fields
        self.chef_user_id = None
        self.chef_name = None
        self.ready_by_user_id = None
        self.ready_by_name = None
        self.delivery_user_id = None
        self.delivery_name = None

    @dispatch(OrderCreatedEvent)
    def on(self, event: OrderCreatedEvent) -> None:
        """Handle order creation event"""
        self.id = event.aggregate_id
        self.customer_id = event.customer_id
        self.order_time = event.order_time
        self.status = OrderStatus.PENDING

    @dispatch(PizzaAddedToOrderEvent)
    def on(self, event: PizzaAddedToOrderEvent) -> None:
        """Handle pizza added event - Note: actual Pizza object added via business logic"""
        # Pizza objects are managed by the aggregate's business logic
        # This event is for tracking/auditing purposes

    @dispatch(PizzaRemovedFromOrderEvent)
    def on(self, event: PizzaRemovedFromOrderEvent) -> None:
        """Handle pizza removed event - Note: actual Pizza object removed via business logic"""
        # Pizza objects are managed by the aggregate's business logic
        # This event is for tracking/auditing purposes

    @dispatch(OrderConfirmedEvent)
    def on(self, event: OrderConfirmedEvent) -> None:
        """Handle order confirmation event"""
        self.status = OrderStatus.CONFIRMED
        self.confirmed_time = event.confirmed_time

    @dispatch(CookingStartedEvent)
    def on(self, event: CookingStartedEvent) -> None:
        """Handle cooking started event"""
        self.status = OrderStatus.COOKING
        self.cooking_started_time = event.cooking_started_time
        self.chef_user_id = event.user_id
        self.chef_name = event.user_name

    @dispatch(OrderReadyEvent)
    def on(self, event: OrderReadyEvent) -> None:
        """Handle order ready event"""
        self.status = OrderStatus.READY
        self.actual_ready_time = event.ready_time
        self.ready_by_user_id = event.user_id
        self.ready_by_name = event.user_name

    @dispatch(OrderAssignedToDeliveryEvent)
    def on(self, event: OrderAssignedToDeliveryEvent) -> None:
        """Handle order assigned to delivery event"""
        self.delivery_person_id = event.delivery_person_id

    @dispatch(OrderOutForDeliveryEvent)
    def on(self, event: OrderOutForDeliveryEvent) -> None:
        """Handle order out for delivery event"""
        self.status = OrderStatus.DELIVERING
        self.out_for_delivery_time = event.out_for_delivery_time

    @dispatch(OrderDeliveredEvent)
    def on(self, event: OrderDeliveredEvent) -> None:
        """Handle order delivered event"""
        self.status = OrderStatus.DELIVERED
        self.delivered_time = event.delivered_time
        self.delivery_user_id = event.user_id
        self.delivery_name = event.user_name

    @dispatch(OrderCancelledEvent)
    def on(self, event: OrderCancelledEvent) -> None:
        """Handle order cancelled event"""
        self.status = OrderStatus.CANCELLED
        if event.reason:
            self.notes = f"Cancelled: {event.reason}"


@map_from(OrderDto)
@map_to(OrderDto)
class Order(AggregateRoot[OrderState, str]):
    """Order aggregate root with pizzas and status management"""

    def __init__(self, customer_id: str, estimated_ready_time: Optional[datetime] = None):
        super().__init__()

        # Register event and apply it to state
        self.state.on(self.register_event(OrderCreatedEvent(aggregate_id=str(uuid4()), customer_id=customer_id, order_time=datetime.now(timezone.utc))))

        # Set estimated ready time if provided
        if estimated_ready_time:
            self.state.estimated_ready_time = estimated_ready_time

    @property
    def total_amount(self) -> Decimal:
        """Calculate total order amount"""
        return sum((item.total_price for item in self.state.order_items), Decimal("0.00"))

    @property
    def pizza_count(self) -> int:
        """Get total number of pizzas in the order"""
        return len(self.state.order_items)

    def add_order_item(self, order_item: OrderItem) -> None:
        """Add an order item (pizza) to the order"""
        if self.state.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify confirmed orders")

        # Add order item to state
        self.state.order_items.append(order_item)

        # Register event
        self.state.on(self.register_event(PizzaAddedToOrderEvent(aggregate_id=self.id(), line_item_id=order_item.line_item_id, pizza_name=order_item.name, pizza_size=order_item.size.value, price=order_item.total_price)))

    def remove_pizza(self, line_item_id: str) -> None:
        """Remove a pizza from the order by line_item_id"""
        if self.state.status != OrderStatus.PENDING:
            raise ValueError("Cannot modify confirmed orders")

        # Check if pizza exists before removing
        pizza_existed = any(item.line_item_id == line_item_id for item in self.state.order_items)

        # Remove from state
        self.state.order_items = [item for item in self.state.order_items if item.line_item_id != line_item_id]

        # Register event only if pizza was actually removed
        if pizza_existed:
            self.state.on(self.register_event(PizzaRemovedFromOrderEvent(aggregate_id=self.id(), line_item_id=line_item_id)))

    def confirm_order(self) -> None:
        """Confirm the order and set status to confirmed"""
        if self.state.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be confirmed")

        if not self.state.order_items:
            raise ValueError("Cannot confirm empty order")

        # Register event and apply to state
        self.state.on(self.register_event(OrderConfirmedEvent(aggregate_id=self.id(), confirmed_time=datetime.now(timezone.utc), total_amount=self.total_amount, pizza_count=self.pizza_count)))

    def start_cooking(self, user_id: str, user_name: str) -> None:
        """Start cooking the order"""
        if self.state.status != OrderStatus.CONFIRMED:
            raise ValueError("Only confirmed orders can start cooking")

        cooking_time = datetime.now(timezone.utc)

        # Register event and apply to state
        self.state.on(self.register_event(CookingStartedEvent(aggregate_id=self.id(), cooking_started_time=cooking_time, user_id=user_id, user_name=user_name)))

    def mark_ready(self, user_id: str, user_name: str) -> None:
        """Mark order as ready for pickup/delivery"""
        if self.state.status != OrderStatus.COOKING:
            raise ValueError("Only cooking orders can be marked ready")

        ready_time = datetime.now(timezone.utc)

        # Register event and apply to state
        self.state.on(self.register_event(OrderReadyEvent(aggregate_id=self.id(), ready_time=ready_time, estimated_ready_time=getattr(self.state, "estimated_ready_time", None), user_id=user_id, user_name=user_name)))

    def assign_to_delivery(self, delivery_person_id: str) -> None:
        """Assign order to a delivery driver"""
        if self.state.status != OrderStatus.READY:
            raise ValueError("Only ready orders can be assigned to delivery")

        assignment_time = datetime.now(timezone.utc)

        # Register event and apply to state
        self.state.on(self.register_event(OrderAssignedToDeliveryEvent(aggregate_id=self.id(), delivery_person_id=delivery_person_id, assignment_time=assignment_time)))

    def mark_out_for_delivery(self) -> None:
        """Mark order as out for delivery"""
        if self.state.status != OrderStatus.READY:
            raise ValueError("Only ready orders can be marked out for delivery")

        if not self.state.delivery_person_id:
            raise ValueError("Order must be assigned to a delivery person first")

        out_for_delivery_time = datetime.now(timezone.utc)

        # Register event and apply to state
        self.state.on(self.register_event(OrderOutForDeliveryEvent(aggregate_id=self.id(), out_for_delivery_time=out_for_delivery_time)))

    def deliver_order(self, user_id: str, user_name: str) -> None:
        """Mark order as delivered"""
        if self.state.status != OrderStatus.DELIVERING:
            raise ValueError("Only orders out for delivery can be marked as delivered")

        delivered_time = datetime.now(timezone.utc)

        # Register event and apply to state
        self.state.on(self.register_event(OrderDeliveredEvent(aggregate_id=self.id(), delivered_time=delivered_time, user_id=user_id, user_name=user_name)))

    def cancel_order(self, reason: Optional[str] = None) -> None:
        """Cancel the order"""
        if self.state.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
            raise ValueError("Cannot cancel delivered or already cancelled orders")

        cancelled_time = datetime.now(timezone.utc)

        # Register event and apply to state
        self.state.on(self.register_event(OrderCancelledEvent(aggregate_id=self.id(), cancelled_time=cancelled_time, reason=reason)))

    def __str__(self) -> str:
        order_id = self.id()[:8] if self.id() else "Unknown"
        status_value = self.state.status.value if self.state.status else "Unknown"
        return f"Order {order_id} - {self.pizza_count} pizza(s) - ${self.total_amount:.2f} ({status_value})"
