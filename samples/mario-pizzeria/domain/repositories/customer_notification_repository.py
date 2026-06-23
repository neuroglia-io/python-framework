"""Customer notification repository interface for Mario's Pizzeria domain"""

from abc import ABC, abstractmethod
from typing import Optional

from domain.entities.customer_notification import CustomerNotification


class ICustomerNotificationRepository(ABC):
    """Interface for customer notification repository operations"""

    @abstractmethod
    async def get_by_id_async(self, notification_id: str) -> Optional[CustomerNotification]:
        """Get notification by ID"""

    @abstractmethod
    async def get_by_customer_id_async(self, customer_id: str, page: int = 1, page_size: int = 20) -> list[CustomerNotification]:
        """Get notifications for a specific customer"""

    @abstractmethod
    async def save_async(self, notification: CustomerNotification) -> None:
        """Save a customer notification"""

    @abstractmethod
    async def delete_async(self, notification_id: str) -> None:
        """Delete a notification"""

    @abstractmethod
    async def count_unread_by_customer_async(self, customer_id: str) -> int:
        """Count unread notifications for a customer"""
