"""Query for fetching staff performance analytics (today's leaderboard)"""

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import List

from domain.repositories import IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler


@dataclass
class StaffMemberDto:
    """Performance statistics for a staff member (chef or driver)"""

    staff_id: str
    staff_name: str
    role: str  # "chef" or "driver"
    tasks_completed: int  # Orders cooked or delivered
    tasks_in_progress: int  # Currently active tasks
    average_time_minutes: float  # Avg time to complete tasks
    total_revenue: float  # Revenue generated from their tasks
    performance_score: float  # Calculated score (0-100)


@dataclass
class GetStaffPerformanceQuery(Query[OperationResult[List[StaffMemberDto]]]):
    """Query to fetch today's staff performance for leaderboard"""

    date: datetime | None = None  # Specific date (default: today)
    limit: int = 10  # Top N performers


class GetStaffPerformanceHandler(QueryHandler[GetStaffPerformanceQuery, OperationResult[List[StaffMemberDto]]]):
    """Handler for fetching staff performance"""

    def __init__(self, order_repository: IOrderRepository):
        self.order_repository = order_repository

    async def handle_async(self, request: GetStaffPerformanceQuery) -> OperationResult[list[StaffMemberDto]]:
        """Handle getting staff performance for today"""

        # Get today's date range
        target_date = request.date or datetime.now(timezone.utc)
        start_of_day = datetime.combine(target_date.date(), time.min, tzinfo=timezone.utc)
        end_of_day = datetime.combine(target_date.date(), time.max, tzinfo=timezone.utc)

        # Get orders for the date range
        today_orders = await self.order_repository.get_orders_by_date_range_async(start_date=start_of_day, end_date=end_of_day)

        staff_performance = []

        # Track CHEF performance using new user tracking fields
        chef_stats = {}

        for order in today_orders:
            # Get chef who actually cooked the order (from new tracking fields)
            chef_user_id = getattr(order.state, "chef_user_id", None)
            chef_name = getattr(order.state, "chef_name", None)

            if chef_user_id:
                if chef_user_id not in chef_stats:
                    chef_stats[chef_user_id] = {
                        "name": chef_name or f"Chef {chef_user_id[:8]}",
                        "cooked": 0,
                        "in_progress": 0,
                        "total_time": 0.0,
                        "revenue": 0.0,
                        "count_with_time": 0,
                    }

                # Check if order was completed
                if order.state.status.value.lower() in ["ready", "delivering", "delivered"]:
                    chef_stats[chef_user_id]["cooked"] += 1
                    chef_stats[chef_user_id]["revenue"] += float(order.total_amount)

                    # Calculate cooking time if timestamps available
                    cooking_started = getattr(order.state, "cooking_started_time", None)
                    actual_ready = getattr(order.state, "actual_ready_time", None)

                    if cooking_started and actual_ready:
                        cooking_time = (actual_ready - cooking_started).total_seconds() / 60
                        chef_stats[chef_user_id]["total_time"] += cooking_time
                        chef_stats[chef_user_id]["count_with_time"] += 1

                elif order.state.status.value.lower() == "cooking":
                    chef_stats[chef_user_id]["in_progress"] += 1

        # Track DRIVER performance using new user tracking fields
        driver_stats = {}

        for order in today_orders:
            # Get driver who actually delivered the order (from new tracking fields)
            delivery_user_id = getattr(order.state, "delivery_user_id", None)
            delivery_name = getattr(order.state, "delivery_name", None)

            if delivery_user_id:
                if delivery_user_id not in driver_stats:
                    driver_stats[delivery_user_id] = {
                        "name": delivery_name or f"Driver {delivery_user_id[:8]}",
                        "delivered": 0,
                        "in_progress": 0,
                        "total_time": 0.0,
                        "revenue": 0.0,
                        "count_with_time": 0,
                    }

                # Check if delivered
                if order.state.status.value.lower() == "delivered":
                    driver_stats[delivery_user_id]["delivered"] += 1
                    driver_stats[delivery_user_id]["revenue"] += float(order.total_amount)

                    # Calculate delivery time if timestamps available
                    out_for_delivery = getattr(order.state, "out_for_delivery_time", None)
                    delivered_time = getattr(order.state, "delivered_time", None)

                    if out_for_delivery and delivered_time:
                        delivery_time = (delivered_time - out_for_delivery).total_seconds() / 60
                        driver_stats[delivery_user_id]["total_time"] += delivery_time
                        driver_stats[delivery_user_id]["count_with_time"] += 1

                elif order.state.status.value.lower() == "delivering":
                    driver_stats[delivery_user_id]["in_progress"] += 1

        # Convert chef stats to DTOs
        for chef_id, stats in chef_stats.items():
            avg_time = stats["total_time"] / stats["count_with_time"] if stats["count_with_time"] > 0 else 0.0

            # Calculate performance score (higher orders, lower time, higher revenue = better)
            performance_score = min(100.0, (stats["cooked"] * 10) + (stats["revenue"] / 10))

            staff_performance.append(
                StaffMemberDto(
                    staff_id=chef_id,
                    staff_name=stats["name"],
                    role="chef",
                    tasks_completed=stats["cooked"],
                    tasks_in_progress=stats["in_progress"],
                    average_time_minutes=avg_time,
                    total_revenue=stats["revenue"],
                    performance_score=performance_score,
                )
            )

        # Convert driver stats to DTOs
        for driver_id, stats in driver_stats.items():
            avg_time = stats["total_time"] / stats["count_with_time"] if stats["count_with_time"] > 0 else 0.0

            # Calculate performance score
            performance_score = min(100.0, (stats["delivered"] * 10) + (stats["revenue"] / 10))

            staff_performance.append(
                StaffMemberDto(
                    staff_id=driver_id,
                    staff_name=stats["name"],
                    role="driver",
                    tasks_completed=stats["delivered"],
                    tasks_in_progress=stats["in_progress"],
                    average_time_minutes=avg_time,
                    total_revenue=stats["revenue"],
                    performance_score=performance_score,
                )
            )

        # Sort by performance score
        staff_performance.sort(key=lambda x: x.performance_score, reverse=True)

        # Limit results
        return self.ok(staff_performance[: request.limit])
