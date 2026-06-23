"""Query for fetching delivery driver performance analytics"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from domain.repositories import IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler


@dataclass
class DriverPerformanceDto:
    """Performance statistics for a delivery driver"""

    driver_id: str  # Delivery person ID
    driver_name: str  # Driver name (if available, else ID)
    total_deliveries: int  # Number of completed deliveries
    total_revenue: float  # Total revenue from delivered orders
    average_order_value: float  # Average value per delivery
    completion_rate: float  # Percentage of assigned orders that were delivered
    total_assigned: int  # Total orders assigned (including not delivered)


@dataclass
class GetOrdersByDriverQuery(Query[OperationResult[List[DriverPerformanceDto]]]):
    """Query to fetch delivery driver performance metrics"""

    start_date: Optional[datetime] = None  # Start of date range (default: 30 days ago)
    end_date: Optional[datetime] = None  # End of date range (default: now)
    limit: int = 10  # Maximum number of drivers to return


class GetOrdersByDriverHandler(QueryHandler[GetOrdersByDriverQuery, OperationResult[List[DriverPerformanceDto]]]):
    """Handler for fetching delivery driver performance"""

    def __init__(self, order_repository: IOrderRepository):
        self.order_repository = order_repository

    async def handle_async(self, request: GetOrdersByDriverQuery) -> OperationResult[list[DriverPerformanceDto]]:
        """Handle getting delivery driver performance"""

        # Set default date range if not provided
        end_date = request.end_date or datetime.now(timezone.utc)
        start_date = request.start_date or (end_date - timedelta(days=30))

        # Ensure dates are timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        # Get orders in date range using optimized repository method
        # This already filters by date range
        filtered_orders = await self.order_repository.get_orders_by_date_range_with_delivery_person_async(start_date=start_date, end_date=end_date)

        # Further filter to only orders with delivery person assigned
        # Use getattr for defensive programming (old orders may not have delivery_person_id)
        filtered_orders = [order for order in filtered_orders if getattr(order.state, "delivery_person_id", None) is not None]

        if not filtered_orders:
            return self.ok([])

        # Group orders by driver
        driver_stats = {}

        for order in filtered_orders:
            driver_id = getattr(order.state, "delivery_person_id", None)
            if not driver_id:
                continue

            if driver_id not in driver_stats:
                driver_stats[driver_id] = {
                    "assigned": 0,
                    "delivered": 0,
                    "revenue": Decimal("0.00"),
                }

            driver_stats[driver_id]["assigned"] += 1

            # Count only delivered orders for revenue and completion
            if order.state.status.name == "DELIVERED":
                driver_stats[driver_id]["delivered"] += 1
                driver_stats[driver_id]["revenue"] += order.total_amount

        # Build driver performance DTOs
        performance = []
        for driver_id, stats in driver_stats.items():
            total_assigned = stats["assigned"]
            total_delivered = stats["delivered"]
            total_revenue = float(stats["revenue"])
            avg_order_value = total_revenue / total_delivered if total_delivered > 0 else 0.0
            completion_rate = (total_delivered / total_assigned * 100) if total_assigned > 0 else 0.0

            performance.append(
                DriverPerformanceDto(
                    driver_id=driver_id,
                    driver_name=self._get_driver_name(driver_id),
                    total_deliveries=total_delivered,
                    total_revenue=round(total_revenue, 2),
                    average_order_value=round(avg_order_value, 2),
                    completion_rate=round(completion_rate, 1),
                    total_assigned=total_assigned,
                )
            )

        # Sort by total deliveries (most active drivers first)
        performance.sort(key=lambda x: x.total_deliveries, reverse=True)

        # Apply limit
        return self.ok(performance[: request.limit])

    def _get_driver_name(self, driver_id: str) -> str:
        """Get driver name from ID (placeholder for now)"""
        # TODO: Look up driver name from user repository
        # For now, return a friendly version of the ID
        return f"Driver {driver_id[-8:]}" if len(driver_id) > 8 else f"Driver {driver_id}"
