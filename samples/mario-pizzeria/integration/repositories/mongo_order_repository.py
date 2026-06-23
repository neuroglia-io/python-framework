"""
MongoDB repository for Order aggregates using Neuroglia's MotorRepository.

This extends the framework's MotorRepository to provide Order-specific queries
while inheriting all standard CRUD operations with automatic domain event publishing.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from domain.entities import Order
from domain.entities.enums import OrderStatus
from domain.repositories import IOrderRepository
from motor.motor_asyncio import AsyncIOMotorClient

from neuroglia.data.infrastructure.mongo import MotorRepository
from neuroglia.data.infrastructure.tracing_mixin import TracedRepositoryMixin
from neuroglia.serialization.json import JsonSerializer

if TYPE_CHECKING:
    from neuroglia.mediation.mediator import Mediator


class MongoOrderRepository(TracedRepositoryMixin, MotorRepository[Order, str], IOrderRepository):
    """
    Motor-based async MongoDB repository for Order aggregates with automatic tracing
    and domain event publishing.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations with
    automatic event publishing and adds Order-specific queries. TracedRepositoryMixin
    provides automatic OpenTelemetry instrumentation for all repository operations.
    """

    def __init__(
        self,
        client: AsyncIOMotorClient,
        database_name: str,
        collection_name: str,
        serializer: JsonSerializer,
        entity_type: type[Order],
        mediator: Optional["Mediator"] = None,
    ):
        """
        Initialize the Order repository.

        Args:
            client: Motor async MongoDB client
            database_name: Name of the database
            collection_name: Name of the collection
            serializer: JSON serializer for entity conversion
            entity_type: Type of entity stored in this repository
            mediator: Optional Mediator for automatic domain event publishing
        """
        super().__init__(
            client=client,
            database_name=database_name,
            collection_name="orders",
            serializer=serializer,
            mediator=mediator,
        )

    # Custom Order-specific queries
    # Note: Standard CRUD operations are inherited from MotorRepository

    async def get_by_customer_id_async(self, customer_id: str) -> list[Order]:
        """Get all orders for a customer"""
        return await self.find_async({"customer_id": customer_id})

    async def get_by_customer_phone_async(self, phone: str) -> list[Order]:
        """Get all orders for a customer by phone number"""
        return await self.find_async({"customer_phone": phone})

    async def get_by_status_async(self, status: OrderStatus) -> list[Order]:
        """Get all orders with specific status"""
        return await self.find_async({"status": status.name})

    async def get_orders_by_status_async(self, status: OrderStatus) -> list[Order]:
        """Get all orders with a specific status (interface method)"""
        return await self.get_by_status_async(status)

    async def get_orders_by_date_range_async(self, start_date: datetime, end_date: datetime) -> list[Order]:
        """
        Get orders within a date range.

        Queries orders created between start_date and end_date (inclusive).
        Uses the framework's created_at timestamp from AggregateState.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of orders created within the date range
        """
        query = {"created_at": {"$gte": start_date, "$lte": end_date}}
        return await self.find_async(query)

    async def get_active_orders_async(self) -> list[Order]:
        """Get all active orders (not delivered or cancelled)"""
        query = {"status": {"$nin": [OrderStatus.DELIVERED.name, OrderStatus.CANCELLED.name]}}
        return await self.find_async(query)

    async def get_pending_orders_async(self) -> list[Order]:
        """Get all pending orders"""
        return await self.get_by_status_async(OrderStatus.PENDING)

    async def get_cooking_orders_async(self) -> list[Order]:
        """Get all cooking orders"""
        return await self.get_by_status_async(OrderStatus.COOKING)

    async def get_ready_orders_async(self) -> list[Order]:
        """Get all ready orders"""
        return await self.get_by_status_async(OrderStatus.READY)

    async def get_orders_by_delivery_person_async(self, delivery_person_id: str) -> list[Order]:
        """
        Get all orders currently being delivered by a specific driver.

        Uses native MongoDB filtering for better performance.

        Args:
            delivery_person_id: The ID of the delivery person

        Returns:
            List of orders with status='delivering' and assigned to this driver
        """
        query = {
            "status": OrderStatus.DELIVERING.name,
            "delivery_person_id": delivery_person_id,
        }
        orders = await self.find_async(query)
        # Sort by out_for_delivery_time (oldest first)
        orders.sort(key=lambda o: getattr(o.state, "out_for_delivery_time", datetime.min))
        return orders

    # Optimized query methods for analytics (avoid get_all + in-memory filtering)

    async def get_orders_by_date_range_with_delivery_person_async(self, start_date: datetime, end_date: datetime, delivery_person_id: Optional[str] = None) -> list[Order]:
        """
        Get orders within a date range, optionally filtered by delivery person.
        Uses native MongoDB filtering for better performance.
        """
        query = {"created_at": {"$gte": start_date, "$lte": end_date}}

        if delivery_person_id:
            query["delivery_person_id"] = delivery_person_id

        return await self.find_async(query)

    async def get_orders_for_customer_stats_async(self, start_date: datetime, end_date: datetime) -> list[Order]:
        """
        Get orders within a date range for customer statistics.
        Uses native MongoDB date filtering.
        """
        query = {
            "created_at": {"$gte": start_date, "$lte": end_date},
            "customer_id": {"$exists": True, "$ne": None},  # Only orders with customer info
        }
        return await self.find_async(query)

    async def get_orders_for_kitchen_stats_async(self, start_date: datetime, end_date: datetime) -> list[Order]:
        """
        Get orders within a date range for kitchen performance stats.
        Filters to orders that have been cooked (exclude pending/cancelled).
        """
        query = {
            "created_at": {"$gte": start_date, "$lte": end_date},
            "status": {"$nin": [OrderStatus.PENDING.name, OrderStatus.CANCELLED.name]},
        }
        return await self.find_async(query)

    async def get_orders_for_timeseries_async(self, start_date: datetime, end_date: datetime, granularity: str = "hour") -> list[Order]:
        """
        Get orders within a date range for time series analysis.
        Uses native MongoDB filtering for date range.

        Uses order_time field (when order was placed) as this is the business-relevant timestamp.
        Falls back to created_at if order_time is not available (for backward compatibility).
        """
        query = {
            "$or": [
                {"order_time": {"$gte": start_date, "$lte": end_date}},
                {"created_at": {"$gte": start_date, "$lte": end_date}},
            ]
        }
        return await self.find_async(query)

    async def get_orders_for_status_distribution_async(self, start_date: datetime, end_date: datetime) -> list[Order]:
        """
        Get orders within a date range for status distribution.
        Uses native MongoDB filtering.

        Uses order_time field (when order was placed) as this is the business-relevant timestamp.
        Falls back to created_at if order_time is not available (for backward compatibility).
        """
        query = {
            "$or": [
                {"order_time": {"$gte": start_date, "$lte": end_date}},
                {"created_at": {"$gte": start_date, "$lte": end_date}},
            ]
        }
        return await self.find_async(query)

    async def get_orders_for_pizza_analytics_async(self, start_date: datetime, end_date: datetime) -> list[Order]:
        """
        Get orders within a date range for pizza sales analytics.
        Uses native MongoDB filtering.
        """
        query = {
            "created_at": {"$gte": start_date, "$lte": end_date},
            "status": {"$ne": OrderStatus.CANCELLED.name},  # Exclude cancelled orders
        }
        return await self.find_async(query)
