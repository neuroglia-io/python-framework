"""
DTOs for customer notifications in Mario's Pizzeria API.

These DTOs provide the API contract for customer notification data transfer.
"""

from datetime import datetime
from typing import Optional

from neuroglia.utils import CamelModel


class CustomerNotificationDto(CamelModel):
    """DTO for customer notification data"""

    id: str
    customer_id: str
    notification_type: str
    title: str
    message: str
    order_id: Optional[str] = None
    status: str = "unread"
    created_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None

    def is_dismissible(self) -> bool:
        """Check if notification can be dismissed"""
        return self.status in ["unread", "read"]

    def is_order_related(self) -> bool:
        """Check if notification is related to an order"""
        return self.order_id is not None


class DismissNotificationDto(CamelModel):
    """DTO for dismissing a customer notification"""

    notification_id: str


class CustomerNotificationListDto(CamelModel):
    """DTO for customer notification list response"""

    notifications: list[CustomerNotificationDto]
    total_count: int
    unread_count: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False
