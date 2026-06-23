"""Domain enums for Mario's Pizzeria"""

from enum import Enum


class PizzaSize(Enum):
    """Pizza size options"""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class OrderStatus(Enum):
    """Order lifecycle statuses"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    COOKING = "cooking"
    READY = "ready"
    DELIVERING = "delivering"  # New: Order is out for delivery
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
