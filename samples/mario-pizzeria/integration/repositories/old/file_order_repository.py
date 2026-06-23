"""File-based implementation of order repository using generic FileSystemRepository"""

from datetime import datetime

from domain.entities import Order, OrderStatus
from domain.repositories import IOrderRepository

from neuroglia.data.infrastructure.filesystem import FileSystemRepository


class FileOrderRepository(FileSystemRepository[Order, str], IOrderRepository):
    """File-based implementation of order repository using generic FileSystemRepository"""

    def __init__(self, data_directory: str = "data"):
        super().__init__(data_directory=data_directory, entity_type=Order, key_type=str)

    async def get_by_customer_phone_async(self, phone: str) -> list[Order]:
        """Get all orders for a customer by phone number"""
        # Note: This would require a relationship lookup in a real implementation
        # For now, we'll return empty list as Order entity doesn't directly store phone
        return []

    async def get_orders_by_status_async(self, status: OrderStatus) -> list[Order]:
        """Get all orders with a specific status"""
        all_orders = await self.get_all_async()
        return [order for order in all_orders if order.status == status]

    async def get_orders_by_date_range_async(self, start_date: datetime, end_date: datetime) -> list[Order]:
        """Get orders within a date range"""
        all_orders = await self.get_all_async()
        return [order for order in all_orders if start_date <= order.created_at <= end_date]

    async def get_active_orders_async(self) -> list[Order]:
        """Get all active orders (not delivered or cancelled)"""
        all_orders = await self.get_all_async()
        active_statuses = {OrderStatus.CONFIRMED, OrderStatus.COOKING}
        return [order for order in all_orders if order.status in active_statuses]
