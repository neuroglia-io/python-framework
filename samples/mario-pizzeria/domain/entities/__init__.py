"""Domain entities for Mario's Pizzeria"""

# Export all entities for clean import access
from .customer import Customer, CustomerState
from .customer_notification import (
    CustomerNotification,
    CustomerNotificationState,
    NotificationStatus,
    NotificationType,
)
from .enums import OrderStatus, PizzaSize
from .kitchen import Kitchen
from .order import Order, OrderState
from .order_item import OrderItem
from .pizza import Pizza, PizzaState

__all__ = [
    # Enums
    "PizzaSize",
    "OrderStatus",
    "NotificationType",
    "NotificationStatus",
    # Entities & States
    "Pizza",
    "PizzaState",
    "Customer",
    "CustomerState",
    "CustomerNotification",
    "CustomerNotificationState",
    "Order",
    "OrderState",
    "OrderItem",  # Value object
    "Kitchen",
]
