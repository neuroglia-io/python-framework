"""Query for fetching management dashboard overview statistics"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from domain.repositories import IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler


@dataclass
class OverviewStatisticsDto:
    """DTO for dashboard overview statistics"""

    # Today's metrics
    total_orders_today: int
    revenue_today: float
    average_order_value_today: float
    active_orders: int

    # Kitchen metrics
    orders_pending: int
    orders_confirmed: int
    orders_cooking: int
    orders_ready: int

    # Delivery metrics
    orders_delivering: int
    orders_delivered_today: int

    # Comparisons (vs yesterday)
    orders_change_percent: float
    revenue_change_percent: float

    # Average times
    average_prep_time_minutes: Optional[float] = None
    average_delivery_time_minutes: Optional[float] = None


@dataclass
class GetOverviewStatisticsQuery(Query[OperationResult[OverviewStatisticsDto]]):
    """Query to fetch dashboard overview statistics"""


class GetOverviewStatisticsHandler(QueryHandler[GetOverviewStatisticsQuery, OperationResult[OverviewStatisticsDto]]):
    """Handler for fetching overview statistics"""

    def __init__(self, order_repository: IOrderRepository):
        self.order_repository = order_repository

    async def handle_async(self, request: GetOverviewStatisticsQuery) -> OperationResult[OverviewStatisticsDto]:
        """Handle getting overview statistics"""

        # Define time ranges (use timezone-aware datetime to match order timestamps)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        yesterday_end = today_start

        # Get today's orders using optimized repository method
        today_orders = await self.order_repository.get_orders_by_date_range_async(start_date=today_start, end_date=now)

        # Get yesterday's orders using optimized repository method
        yesterday_orders = await self.order_repository.get_orders_by_date_range_async(start_date=yesterday_start, end_date=yesterday_end)

        # Calculate today's metrics
        total_orders_today = len(today_orders)
        revenue_today = sum(o.total_amount for o in today_orders)
        average_order_value_today = revenue_today / total_orders_today if total_orders_today > 0 else 0.0

        # Calculate yesterday's metrics for comparison
        yesterday_orders_count = len(yesterday_orders)
        yesterday_revenue = sum(o.total_amount for o in yesterday_orders)

        # Calculate percentage changes
        orders_change_percent = ((total_orders_today - yesterday_orders_count) / yesterday_orders_count * 100) if yesterday_orders_count > 0 else 0.0

        revenue_change_percent = ((revenue_today - yesterday_revenue) / yesterday_revenue * 100) if yesterday_revenue > 0 else 0.0

        # Count orders by status (use lowercase status values to match OrderStatus enum)
        orders_by_status = {
            "pending": 0,
            "confirmed": 0,
            "cooking": 0,
            "ready": 0,
            "delivering": 0,
            "delivered": 0,
        }

        # Get active orders for status distribution
        active_orders_list = await self.order_repository.get_active_orders_async()

        for order in active_orders_list:
            # Use .value to get the string value from OrderStatus enum
            status = order.state.status.value.lower() if hasattr(order.state.status, "value") else str(order.state.status).lower()
            if status in orders_by_status:
                orders_by_status[status] += 1

        # Active orders = pending + confirmed + cooking + ready + delivering
        active_orders = orders_by_status["pending"] + orders_by_status["confirmed"] + orders_by_status["cooking"] + orders_by_status["ready"] + orders_by_status["delivering"]

        # Count today's delivered orders (case-insensitive comparison)
        orders_delivered_today = len([o for o in today_orders if o.state.status.value.lower() == "delivered"])

        # Calculate average prep time (from confirmed to ready)
        prep_times = []
        for order in today_orders:
            if hasattr(order.state, "confirmed_time") and hasattr(order.state, "actual_ready_time") and order.state.confirmed_time and order.state.actual_ready_time:
                prep_time = (order.state.actual_ready_time - order.state.confirmed_time).total_seconds() / 60
                prep_times.append(prep_time)

        average_prep_time = sum(prep_times) / len(prep_times) if prep_times else None

        # Calculate average delivery time (from ready to delivered)
        delivery_times = []
        for order in today_orders:
            if hasattr(order.state, "actual_ready_time") and hasattr(order.state, "delivered_time") and order.state.actual_ready_time and getattr(order.state, "delivered_time", None):
                delivery_time = (order.state.delivered_time - order.state.actual_ready_time).total_seconds() / 60
                delivery_times.append(delivery_time)

        average_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else None

        # Build DTO
        statistics = OverviewStatisticsDto(
            total_orders_today=total_orders_today,
            revenue_today=round(revenue_today, 2),
            average_order_value_today=round(average_order_value_today, 2),
            active_orders=active_orders,
            orders_pending=orders_by_status["pending"],
            orders_confirmed=orders_by_status["confirmed"],
            orders_cooking=orders_by_status["cooking"],
            orders_ready=orders_by_status["ready"],
            orders_delivering=orders_by_status["delivering"],
            orders_delivered_today=orders_delivered_today,
            orders_change_percent=round(orders_change_percent, 1),
            revenue_change_percent=round(revenue_change_percent, 1),
            average_prep_time_minutes=round(average_prep_time, 1) if average_prep_time else None,
            average_delivery_time_minutes=(round(average_delivery_time, 1) if average_delivery_time else None),
        )

        return self.ok(statistics)
