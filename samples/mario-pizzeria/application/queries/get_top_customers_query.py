"""Query for fetching top customers by order activity"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from domain.repositories import ICustomerRepository, IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Query, QueryHandler


@dataclass
class TopCustomerDto:
    """Statistics for a top customer"""

    customer_id: str
    customer_name: str
    customer_email: Optional[str]
    total_orders: int
    total_spent: float
    last_order_date: Optional[datetime]
    favorite_pizza: Optional[str]  # Most ordered pizza
    is_vip: bool  # High-value customer flag


@dataclass
class GetTopCustomersQuery(Query[OperationResult[List[TopCustomerDto]]]):
    """Query to fetch top customers by activity"""

    period_days: int = 30  # Look back period
    limit: int = 10  # Top N customers
    min_orders: int = 2  # Minimum orders to qualify


class GetTopCustomersHandler(QueryHandler[GetTopCustomersQuery, OperationResult[List[TopCustomerDto]]]):
    """Handler for fetching top customers"""

    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository

    async def handle_async(self, request: GetTopCustomersQuery) -> OperationResult[list[TopCustomerDto]]:
        """Handle getting top customers"""

        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=request.period_days)

        # Get orders in period using optimized repository method
        period_orders = await self.order_repository.get_orders_for_customer_stats_async(start_date=start_date, end_date=end_date)

        # Group by customer
        customer_stats = {}

        for order in period_orders:
            customer_id = order.state.customer_id
            if not customer_id:
                continue

            if customer_id not in customer_stats:
                customer_stats[customer_id] = {
                    "order_count": 0,
                    "total_spent": 0.0,
                    "last_order": None,
                    "pizza_counts": {},
                }

            stats = customer_stats[customer_id]
            stats["order_count"] += 1
            stats["total_spent"] += float(order.total_amount)

            # Track last order
            if not stats["last_order"] or order.state.order_time > stats["last_order"]:
                stats["last_order"] = order.state.order_time

            # Count pizzas
            for item in order.state.order_items:
                pizza_name = item.name
                if pizza_name not in stats["pizza_counts"]:
                    stats["pizza_counts"][pizza_name] = 0
                stats["pizza_counts"][pizza_name] += 1

        # Filter customers with minimum orders
        qualified_customers = {cid: stats for cid, stats in customer_stats.items() if stats["order_count"] >= request.min_orders}

        # Get customer details
        top_customers = []

        for customer_id, stats in qualified_customers.items():
            # Get customer name from any order (they all have the same customer info)
            sample_order = next((o for o in period_orders if o.state.customer_id == customer_id), None)

            customer_name = "Unknown"
            customer_email = None

            if sample_order:
                # Orders store customer snapshot data
                customer_name = getattr(sample_order.state, "customer_name", "Unknown")
                customer_email = getattr(sample_order.state, "customer_email", None)

            # Find favorite pizza
            favorite_pizza = None
            if stats["pizza_counts"]:
                favorite_pizza = max(stats["pizza_counts"], key=stats["pizza_counts"].get)

            # VIP threshold: >$100 spent or >5 orders
            is_vip = stats["total_spent"] > 100.0 or stats["order_count"] > 5

            top_customers.append(
                TopCustomerDto(
                    customer_id=customer_id,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    total_orders=stats["order_count"],
                    total_spent=stats["total_spent"],
                    last_order_date=stats["last_order"],
                    favorite_pizza=favorite_pizza,
                    is_vip=is_vip,
                )
            )

        # Sort by total spent (descending)
        top_customers.sort(key=lambda x: x.total_spent, reverse=True)

        # Limit results
        return self.ok(top_customers[: request.limit])
