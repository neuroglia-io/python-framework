"""Query for fetching order status distribution for analytics"""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from domain.entities.enums import OrderStatus
from domain.repositories import IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler


@dataclass
class OrderStatusStatsDto:
    """Statistics for a specific order status"""

    status: str  # Order status name
    count: int  # Number of orders in this status
    percentage: float  # Percentage of total orders
    total_revenue: float  # Total revenue from orders in this status


@dataclass
class GetOrderStatusDistributionQuery(Query[OperationResult[List[OrderStatusStatsDto]]]):
    """Query to fetch order status distribution"""

    start_date: Optional[datetime] = None  # Start of date range (default: 30 days ago)
    end_date: Optional[datetime] = None  # End of date range (default: now)


class GetOrderStatusDistributionHandler(QueryHandler[GetOrderStatusDistributionQuery, OperationResult[List[OrderStatusStatsDto]]]):
    """Handler for fetching order status distribution"""

    def __init__(self, order_repository: IOrderRepository):
        self.order_repository = order_repository

    async def handle_async(self, request: GetOrderStatusDistributionQuery) -> OperationResult[list[OrderStatusStatsDto]]:
        """Handle getting order status distribution"""

        # Set default date range if not provided
        end_date = request.end_date or datetime.now(timezone.utc)
        start_date = request.start_date or (end_date - timedelta(days=30))

        # Ensure dates are timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        # Get orders in date range using optimized repository method
        filtered_orders = await self.order_repository.get_orders_for_status_distribution_async(start_date=start_date, end_date=end_date)

        total_orders = len(filtered_orders)

        if total_orders == 0:
            # Return empty list if no orders in range
            return self.ok([])

        # Count orders by status and calculate revenue
        status_counts = Counter()
        status_revenues = {}

        for order in filtered_orders:
            status = order.state.status.value
            status_counts[status] += 1

            if status not in status_revenues:
                status_revenues[status] = 0.0
            status_revenues[status] += float(order.total_amount)

        # Build status distribution stats
        distribution = []
        for status in OrderStatus:
            status_value = status.value
            count = status_counts.get(status_value, 0)
            percentage = (count / total_orders * 100) if total_orders > 0 else 0.0
            revenue = status_revenues.get(status_value, 0.0)

            # Only include statuses that have at least one order
            if count > 0:
                distribution.append(
                    OrderStatusStatsDto(
                        status=status_value,
                        count=count,
                        percentage=round(percentage, 1),
                        total_revenue=round(revenue, 2),
                    )
                )

        # Sort by count (most common status first)
        distribution.sort(key=lambda x: x.count, reverse=True)

        return self.ok(distribution)
