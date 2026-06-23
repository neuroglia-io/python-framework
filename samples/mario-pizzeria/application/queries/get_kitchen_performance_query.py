"""Query for fetching kitchen performance analytics"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from domain.repositories import IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler


@dataclass
class KitchenPerformanceDto:
    """Performance statistics for the kitchen"""

    total_orders_cooked: int  # Orders that reached "ready" status
    average_cooking_time_minutes: float  # Avg time from cooking_started to ready
    orders_on_time: int  # Orders ready by estimated time
    orders_late: int  # Orders ready after estimated time
    on_time_percentage: float  # Percentage of orders ready on time
    peak_hour: Optional[str] = None  # Hour with most orders (HH:00 format)
    peak_hour_orders: int = 0  # Number of orders in peak hour
    total_pizzas_made: int = 0  # Total number of pizzas across all orders


@dataclass
class GetKitchenPerformanceQuery(Query[OperationResult[KitchenPerformanceDto]]):
    """Query to fetch kitchen performance metrics"""

    start_date: Optional[datetime] = None  # Start of date range (default: 30 days ago)
    end_date: Optional[datetime] = None  # End of date range (default: now)


class GetKitchenPerformanceHandler(QueryHandler[GetKitchenPerformanceQuery, OperationResult[KitchenPerformanceDto]]):
    """Handler for fetching kitchen performance metrics"""

    def __init__(self, order_repository: IOrderRepository):
        self.order_repository = order_repository

    async def handle_async(self, request: GetKitchenPerformanceQuery) -> OperationResult[KitchenPerformanceDto]:
        """Handle getting kitchen performance metrics"""

        # Set default date range if not provided
        end_date = request.end_date or datetime.now(timezone.utc)
        start_date = request.start_date or (end_date - timedelta(days=30))

        # Ensure dates are timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        # Get orders in date range using optimized repository method
        filtered_orders = await self.order_repository.get_orders_by_date_range_async(start_date=start_date, end_date=end_date)

        if not filtered_orders:
            # Return empty metrics if no orders
            return self.ok(
                KitchenPerformanceDto(
                    total_orders_cooked=0,
                    average_cooking_time_minutes=0.0,
                    orders_on_time=0,
                    orders_late=0,
                    on_time_percentage=0.0,
                    peak_hour=None,
                    peak_hour_orders=0,
                    total_pizzas_made=0,
                )
            )

        # Analyze orders that reached "ready" status
        # Use getattr for defensive programming (old orders may not have these fields)
        cooked_orders = [order for order in filtered_orders if getattr(order.state, "actual_ready_time", None) is not None and getattr(order.state, "cooking_started_time", None) is not None]

        total_orders_cooked = len(cooked_orders)
        total_pizzas_made = sum(len(order.state.order_items) for order in filtered_orders)

        # Calculate average cooking time
        cooking_times = []
        on_time_count = 0
        late_count = 0

        for order in cooked_orders:
            # Calculate actual cooking duration
            cooking_started = getattr(order.state, "cooking_started_time", None)
            actual_ready = getattr(order.state, "actual_ready_time", None)

            if cooking_started and actual_ready:
                duration = (actual_ready - cooking_started).total_seconds() / 60.0  # Convert to minutes
                cooking_times.append(duration)

                # Check if order was ready on time
                estimated_ready = getattr(order.state, "estimated_ready_time", None)
                if estimated_ready:
                    if actual_ready <= estimated_ready:
                        on_time_count += 1
                    else:
                        late_count += 1

        avg_cooking_time = sum(cooking_times) / len(cooking_times) if cooking_times else 0.0
        on_time_percentage = (on_time_count / (on_time_count + late_count) * 100) if (on_time_count + late_count) > 0 else 0.0

        # Find peak hour
        hour_counts = {}
        for order in filtered_orders:
            if order.state.order_time:
                hour = order.state.order_time.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1

        peak_hour = None
        peak_hour_orders = 0
        if hour_counts:
            peak_hour_num = max(hour_counts.items(), key=lambda x: x[1])[0]
            peak_hour = f"{peak_hour_num:02d}:00"
            peak_hour_orders = hour_counts[peak_hour_num]

        return self.ok(
            KitchenPerformanceDto(
                total_orders_cooked=total_orders_cooked,
                average_cooking_time_minutes=round(avg_cooking_time, 1),
                orders_on_time=on_time_count,
                orders_late=late_count,
                on_time_percentage=round(on_time_percentage, 1),
                peak_hour=peak_hour,
                peak_hour_orders=peak_hour_orders,
                total_pizzas_made=total_pizzas_made,
            )
        )
