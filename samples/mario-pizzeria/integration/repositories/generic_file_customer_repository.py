"""File-based implementation of customer repository using generic FileSystemRepository"""

from typing import Optional

from domain.entities import Customer
from domain.repositories import ICustomerRepository

from neuroglia.data.infrastructure.filesystem import FileSystemRepository


class FileCustomerRepository(FileSystemRepository[Customer, str], ICustomerRepository):
    """File-based implementation of customer repository using generic FileSystemRepository"""

    def __init__(self, data_directory: str = "data"):
        super().__init__(data_directory=data_directory, entity_type=Customer, key_type=str)

    async def get_by_phone_async(self, phone: str) -> Optional[Customer]:
        """Get customer by phone number"""
        all_customers = await self.get_all_async()
        customers = [customer for customer in all_customers if customer.state.phone == phone]
        return customers[0] if customers else None

    async def get_by_email_async(self, email: str) -> Optional[Customer]:
        """Get customer by email"""
        all_customers = await self.get_all_async()
        customers = [customer for customer in all_customers if customer.state.email == email]
        return customers[0] if customers else None

    async def get_frequent_customers_async(self, min_orders: int = 5) -> list[Customer]:
        """Get customers with at least the specified number of orders"""
        # For now, we'll return all customers as we don't have order count tracking
        # In a real implementation, this would query the order repository
        return await self.get_all_async()
