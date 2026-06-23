"""Query for fetching orders timeseries data for analytics"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Literal, Optional

from domain.repositories import IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler

# Type alias for period grouping
PeriodType = Literal["day", "week", "month"]


@dataclass
class TimeseriesDataPoint:
    """Single data point in timeseries"""

    period: str  # Date string (YYYY-MM-DD for day, YYYY-Wxx for week, YYYY-MM for month)
    total_orders: int
    total_revenue: float
    average_order_value: float
    orders_delivered: int
    orders_cancelled: int = 0


@dataclass
class GetOrdersTimeseriesQuery(Query[OperationResult[List[TimeseriesDataPoint]]]):
    """Query to fetch orders timeseries data"""

    start_date: Optional[datetime] = None  # Start of date range (default: 30 days ago)
    end_date: Optional[datetime] = None  # End of date range (default: now)
    period: PeriodType = "day"  # Grouping period: day, week, or month


class GetOrdersTimeseriesHandler(QueryHandler[GetOrdersTimeseriesQuery, OperationResult[List[TimeseriesDataPoint]]]):
    """Handler for fetching orders timeseries data"""

    def __init__(self, order_repository: IOrderRepository):
        self.order_repository = order_repository

    async def handle_async(self, request: GetOrdersTimeseriesQuery) -> OperationResult[list[TimeseriesDataPoint]]:
        """Handle getting orders timeseries data"""

        # Set default date range if not provided
        end_date = request.end_date or datetime.now(timezone.utc)
        start_date = request.start_date or (end_date - timedelta(days=30))

        # Ensure dates are timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        # Get orders in date range using optimized repository method
        filtered_orders = await self.order_repository.get_orders_for_timeseries_async(start_date=start_date, end_date=end_date, granularity=request.period)

        # Group orders by period
        period_data = {}

        for order in filtered_orders:
            if not order.state.order_time:
                continue

            # Determine period key based on grouping
            period_key = self._get_period_key(order.state.order_time, request.period)

            # Initialize period data if not exists
            if period_key not in period_data:
                period_data[period_key] = {
                    "orders": [],
                    "revenue": Decimal("0.00"),
                    "delivered": 0,
                    "cancelled": 0,
                }

            # Add order to period
            period_data[period_key]["orders"].append(order)
            period_data[period_key]["revenue"] += order.total_amount

            # Count by status
            if order.state.status.name == "DELIVERED":
                period_data[period_key]["delivered"] += 1
            elif order.state.status.name == "CANCELLED":
                period_data[period_key]["cancelled"] += 1

        # Build timeseries data points
        timeseries = []
        for period_key in sorted(period_data.keys()):
            data = period_data[period_key]
            total_orders = len(data["orders"])
            total_revenue = float(data["revenue"])
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0

            timeseries.append(
                TimeseriesDataPoint(
                    period=period_key,
                    total_orders=total_orders,
                    total_revenue=round(total_revenue, 2),
                    average_order_value=round(avg_order_value, 2),
                    orders_delivered=data["delivered"],
                    orders_cancelled=data["cancelled"],
                )
            )

        return self.ok(timeseries)

    def _get_period_key(self, dt: datetime, period: PeriodType) -> str:
        """Get period key for grouping"""
        if period == "day":
            return dt.strftime("%Y-%m-%d")
        elif period == "week":
            # ISO week format: YYYY-Wxx
            return dt.strftime("%Y-W%V")
        elif period == "month":
            return dt.strftime("%Y-%m")
        else:
            return dt.strftime("%Y-%m-%d")
