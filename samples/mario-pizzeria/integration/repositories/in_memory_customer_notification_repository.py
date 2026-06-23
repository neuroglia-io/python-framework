"""In-memory customer notification repository implementation for Mario's Pizzeria"""

from datetime import datetime
from typing import Optional

from domain.entities.customer_notification import CustomerNotification
from domain.repositories.customer_notification_repository import (
    ICustomerNotificationRepository,
)


class InMemoryCustomerNotificationRepository(ICustomerNotificationRepository):
    """In-memory implementation of customer notification repository for testing"""

    def __init__(self):
        self._notifications: dict[str, CustomerNotification] = {}

    async def get_by_id_async(self, notification_id: str) -> Optional[CustomerNotification]:
        """Get notification by ID"""
        return self._notifications.get(notification_id)

    async def get_by_customer_id_async(self, customer_id: str, page: int = 1, page_size: int = 20) -> list[CustomerNotification]:
        """Get notifications for a specific customer"""
        customer_notifications = [notification for notification in self._notifications.values() if notification.state.customer_id == customer_id]

        # Sort by created_at descending (most recent first)
        customer_notifications.sort(key=lambda n: n.state.created_at or datetime.min, reverse=True)

        # Apply pagination
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        return customer_notifications[start_index:end_index]

    async def save_async(self, notification: CustomerNotification) -> None:
        """Save a customer notification"""
        self._notifications[notification.id()] = notification

    async def delete_async(self, notification_id: str) -> None:
        """Delete a notification"""
        if notification_id in self._notifications:
            del self._notifications[notification_id]

    async def count_unread_by_customer_async(self, customer_id: str) -> int:
        """Count unread notifications for a customer"""
        count = 0
        for notification in self._notifications.values():
            if notification.state.customer_id == customer_id and notification.state.status.name == "UNREAD":
                count += 1
        return count
