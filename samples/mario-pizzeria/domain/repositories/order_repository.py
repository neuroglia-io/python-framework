"""Repository interface for managing pizza orders"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from domain.entities import Order, OrderStatus

from neuroglia.data.infrastructure.abstractions import Repository


class IOrderRepository(Repository[Order, str], ABC):
    """Repository interface for managing pizza orders"""

    @abstractmethod
    async def get_all_async(self) -> list[Order]:
        """Get all orders (Note: Use with caution on large datasets, prefer filtered queries)"""

    @abstractmethod
    async def get_by_customer_id_async(self, customer_id: str) -> list[Order]:
        """Get all orders for a specific customer"""

    @abstractmethod
    async def get_by_customer_phone_async(self, phone: str) -> list[Order]:
        """Get all orders for a customer by phone number"""

    @abstractmethod
    async def get_orders_by_status_async(self, status: OrderStatus) -> list[Order]:
        """Get all orders with a specific status"""

    @abstractmethod
    async def get_orders_by_date_range_async(self, start_date: datetime, end_date: datetime) -> list[Order]:
        """Get orders within a date range"""

    @abstractmethod
    async def get_active_orders_async(self) -> list[Order]:
        """Get all active orders (not delivered or cancelled)"""

    @abstractmethod
    async def get_ready_orders_async(self) -> list[Order]:
        """Get all orders with status='ready' (ready for delivery pickup)"""

    @abstractmethod
    async def get_orders_by_delivery_person_async(self, delivery_person_id: str) -> list[Order]:
        """Get all orders currently being delivered by a specific driver"""

    # Optimized query methods for analytics (avoid get_all + in-memory filtering)

    @abstractmethod
    async def get_orders_by_date_range_with_delivery_person_async(self, start_date: datetime, end_date: datetime, delivery_person_id: Optional[str] = None) -> list[Order]:
        """
        Get orders within a date range, optionally filtered by delivery person.
        Optimized for staff performance queries.
        """

    @abstractmethod
    async def get_orders_for_customer_stats_async(self, start_date: datetime, end_date: datetime) -> list[Order]:
        """
        Get orders within a date range with only fields needed for customer statistics.
        Optimized for customer analytics queries.
        """

    @abstractmethod
    async def get_orders_for_kitchen_stats_async(self, start_date: datetime, end_date: datetime) -> list[Order]:
        """
        Get orders within a date range with fields needed for kitchen performance.
        Filters to orders that have been cooked (exclude pending/cancelled).
        """

    @abstractmethod
    async def get_orders_for_timeseries_async(self, start_date: datetime, end_date: datetime, granularity: str = "hour") -> list[Order]:
        """
        Get orders within a date range for time series analysis.
        Returns minimal fields needed for grouping by time periods.
        """

    @abstractmethod
    async def get_orders_for_status_distribution_async(self, start_date: datetime, end_date: datetime) -> list[Order]:
        """
        Get orders within a date range for status distribution analysis.
        Returns only status and count information.
        """

    @abstractmethod
    async def get_orders_for_pizza_analytics_async(self, start_date: datetime, end_date: datetime) -> list[Order]:
        """
        Get orders within a date range for pizza sales analytics.
        Includes order items for pizza popularity analysis.
        """
