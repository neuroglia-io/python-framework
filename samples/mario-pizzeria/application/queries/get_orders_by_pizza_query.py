"""Query for fetching pizza popularity analytics"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from domain.repositories import IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler


@dataclass
class PizzaAnalytics:
    """Analytics data for a single pizza"""

    pizza_name: str
    total_orders: int
    total_revenue: float
    average_price: float
    percentage_of_total: float


@dataclass
class GetOrdersByPizzaQuery(Query[OperationResult[List[PizzaAnalytics]]]):
    """Query to fetch pizza popularity analytics"""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 10  # Top N pizzas


class GetOrdersByPizzaHandler(QueryHandler[GetOrdersByPizzaQuery, OperationResult[List[PizzaAnalytics]]]):
    """Handler for fetching pizza popularity analytics"""

    def __init__(self, order_repository: IOrderRepository):
        self.order_repository = order_repository

    async def handle_async(self, request: GetOrdersByPizzaQuery) -> OperationResult[list[PizzaAnalytics]]:
        """Handle getting pizza analytics"""

        # Set default date range
        end_date = request.end_date or datetime.now(timezone.utc)
        start_date = request.start_date or (end_date - timedelta(days=30))

        # Ensure timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        # Get orders in date range using optimized repository method
        filtered_orders = await self.order_repository.get_orders_for_pizza_analytics_async(start_date=start_date, end_date=end_date)

        # Aggregate by pizza
        pizza_data = {}
        total_revenue = Decimal("0.00")

        for order in filtered_orders:
            for item in order.state.order_items:
                pizza_name = item.name  # OrderItem has 'name' property

                if pizza_name not in pizza_data:
                    pizza_data[pizza_name] = {
                        "count": 0,
                        "revenue": Decimal("0.00"),
                        "prices": [],
                    }

                # Each order item is 1 pizza (no quantity field)
                pizza_data[pizza_name]["count"] += 1
                item_revenue = item.total_price  # OrderItem has total_price property
                pizza_data[pizza_name]["revenue"] += item_revenue
                pizza_data[pizza_name]["prices"].append(float(item.total_price))
                total_revenue += item_revenue

        # Build analytics list
        analytics = []
        total_revenue_float = float(total_revenue)

        for pizza_name, data in pizza_data.items():
            revenue = float(data["revenue"])
            count = data["count"]
            avg_price = sum(data["prices"]) / len(data["prices"]) if data["prices"] else 0.0
            percentage = (revenue / total_revenue_float * 100) if total_revenue_float > 0 else 0.0

            analytics.append(
                PizzaAnalytics(
                    pizza_name=pizza_name,
                    total_orders=count,
                    total_revenue=round(revenue, 2),
                    average_price=round(avg_price, 2),
                    percentage_of_total=round(percentage, 1),
                )
            )

        # Sort by revenue (descending) and limit
        analytics.sort(key=lambda x: x.total_revenue, reverse=True)
        analytics = analytics[: request.limit]

        return self.ok(analytics)
