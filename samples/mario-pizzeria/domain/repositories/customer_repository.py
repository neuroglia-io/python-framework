"""Repository interface for managing customers"""

from abc import ABC, abstractmethod
from typing import Optional

from domain.entities import Customer

from neuroglia.data.infrastructure.abstractions import Repository


class ICustomerRepository(Repository[Customer, str], ABC):
    """Repository interface for managing customers"""

    @abstractmethod
    async def get_all_async(self) -> list[Customer]:
        """Get all customers (Note: Use with caution on large datasets, prefer filtered queries)"""

    @abstractmethod
    async def get_by_user_id_async(self, user_id: str) -> Optional[Customer]:
        """Get a customer by Keycloak user ID"""

    @abstractmethod
    async def get_by_phone_async(self, phone: str) -> Optional[Customer]:
        """Get a customer by phone number"""

    @abstractmethod
    async def get_by_email_async(self, email: str) -> Optional[Customer]:
        """Get a customer by email address"""

    @abstractmethod
    async def get_frequent_customers_async(self, min_orders: int = 5) -> list[Customer]:
        """Get customers with at least the specified number of orders"""
