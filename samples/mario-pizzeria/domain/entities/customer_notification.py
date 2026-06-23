"""
Customer notification entity for Mario's Pizzeria domain.

This module contains both the CustomerNotificationState (data) and CustomerNotification (behavior)
classes following the state separation pattern with multipledispatch event handlers.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

# Import domain events (will be defined in events.py)
from domain.events import (
    CustomerNotificationCreatedEvent,
    CustomerNotificationDismissedEvent,
    CustomerNotificationReadEvent,
)
from multipledispatch import dispatch

from neuroglia.data.abstractions import AggregateRoot, AggregateState


class NotificationType(Enum):
    """Types of customer notifications"""

    ORDER_COOKING_STARTED = "order_cooking_started"
    ORDER_READY = "order_ready"
    ORDER_DELIVERED = "order_delivered"
    ORDER_CANCELLED = "order_cancelled"
    GENERAL = "general"


class NotificationStatus(Enum):
    """Status of customer notifications"""

    UNREAD = "unread"
    READ = "read"
    DISMISSED = "dismissed"


@dataclass
class CustomerNotificationState(AggregateState[str]):
    """
    State object for CustomerNotification aggregate.

    Contains all notification data that needs to be persisted.
    State mutations are handled through @dispatch event handlers.
    """

    customer_id: str = ""
    notification_type: NotificationType = NotificationType.GENERAL
    title: str = ""
    message: str = ""
    order_id: Optional[str] = None
    status: NotificationStatus = NotificationStatus.UNREAD
    created_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None

    def __post_init__(self):
        """Set default creation time if not provided"""
        if self.created_at is None:
            self.created_at = datetime.now()

    @dispatch(CustomerNotificationCreatedEvent)
    def on(self, event: CustomerNotificationCreatedEvent) -> None:
        """Handle CustomerNotificationCreatedEvent to initialize notification state"""
        self.id = event.aggregate_id
        self.customer_id = event.customer_id
        self.notification_type = NotificationType(event.notification_type)
        self.title = event.title
        self.message = event.message
        self.order_id = event.order_id
        self.status = NotificationStatus.UNREAD
        self.created_at = event.created_at

    @dispatch(CustomerNotificationReadEvent)
    def on(self, event: CustomerNotificationReadEvent) -> None:
        """Handle CustomerNotificationReadEvent to mark notification as read"""
        self.status = NotificationStatus.READ
        self.read_at = event.read_time

    @dispatch(CustomerNotificationDismissedEvent)
    def on(self, event: CustomerNotificationDismissedEvent) -> None:
        """Handle CustomerNotificationDismissedEvent to dismiss notification"""
        self.status = NotificationStatus.DISMISSED
        self.dismissed_at = event.dismissed_time


class CustomerNotification(AggregateRoot[CustomerNotificationState, str]):
    """
    Customer notification aggregate root with notification management behavior.

    Uses Neuroglia's AggregateRoot with state separation pattern:
    - All data in CustomerNotificationState (persisted)
    - All behavior in CustomerNotification aggregate (not persisted)
    - Domain events registered and applied to state via multipledispatch

    Pattern: self.state.on(self.register_event(Event(...)))
    """

    def __init__(
        self,
        customer_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        order_id: Optional[str] = None,
    ):
        super().__init__()

        # Register event and apply it to state using multipledispatch
        event = CustomerNotificationCreatedEvent(
            aggregate_id=str(uuid4()),
            customer_id=customer_id,
            notification_type=notification_type.value,
            title=title,
            message=message,
            order_id=order_id,
        )

        self.state.on(self.register_event(event))

    def mark_as_read(self) -> None:
        """Mark notification as read"""
        if self.state.status == NotificationStatus.UNREAD:
            read_event = CustomerNotificationReadEvent(
                aggregate_id=self.id(),
                read_time=datetime.now(),
            )
            self.state.on(self.register_event(read_event))

    def dismiss(self) -> None:
        """Dismiss notification"""
        dismiss_event = CustomerNotificationDismissedEvent(
            aggregate_id=self.id(),
            dismissed_time=datetime.now(),
        )
        self.state.on(self.register_event(dismiss_event))

    def is_dismissible(self) -> bool:
        """Check if notification can be dismissed"""
        return self.state.status in [NotificationStatus.UNREAD, NotificationStatus.READ]

    def is_order_related(self) -> bool:
        """Check if notification is related to an order"""
        return self.state.order_id is not None

    def __str__(self) -> str:
        status_str = self.state.status.value
        return f"{self.state.title} [{status_str}]"
