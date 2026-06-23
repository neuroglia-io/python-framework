"""Query for retrieving active kitchen orders"""

from dataclasses import dataclass
from datetime import datetime
from typing import List

from api.dtos import OrderDto, PizzaDto
from domain.repositories import ICustomerRepository, IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetActiveKitchenOrdersQuery(Query[OperationResult[List[OrderDto]]]):
    """Query to get all active orders for kitchen display"""

    include_completed: bool = False


class GetActiveKitchenOrdersHandler(QueryHandler[GetActiveKitchenOrdersQuery, OperationResult[List[OrderDto]]]):
    """Handler for kitchen orders query"""

    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
        mapper: Mapper,
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.mapper = mapper

    async def handle_async(self, request: GetActiveKitchenOrdersQuery) -> OperationResult[list[OrderDto]]:
        """Handle kitchen orders retrieval"""

        # Get active orders using native MongoDB filtering (excludes delivered and cancelled)
        active_orders = await self.order_repository.get_active_orders_async()

        # Filter for kitchen-relevant orders only
        # Kitchen should only see orders in these stages:
        # - PENDING: New orders waiting to be confirmed
        # - CONFIRMED: Confirmed and ready to start cooking
        # - COOKING: Currently being prepared
        #
        # Exclude from kitchen view:
        # - READY: Already cooked, waiting for delivery pickup (driver's responsibility)
        # - DELIVERING: Out for delivery (driver's responsibility)
        # - DELIVERED: Completed
        # - CANCELLED: No longer needed

        kitchen_orders = [order for order in active_orders if order.state.status.name in ["PENDING", "CONFIRMED", "COOKING"]]

        # Sort by order time (oldest first for kitchen priority)
        kitchen_orders.sort(key=lambda o: o.state.order_time or datetime.min, reverse=False)

        # Build DTOs with customer information
        order_dtos = []
        for order in kitchen_orders:
            # Get customer information
            customer = None
            if order.state.customer_id:
                customer = await self.customer_repository.get_async(order.state.customer_id)

            # Map pizzas
            pizza_dtos = [
                PizzaDto(
                    name=item.name,
                    size=item.size.value if hasattr(item.size, "value") else str(item.size),
                    toppings=list(item.toppings),
                    base_price=item.base_price,
                    total_price=item.total_price,
                )
                for item in order.state.order_items
            ]

            # Construct OrderDto
            order_dto = OrderDto(
                id=order.id(),
                customer_name=customer.state.name if customer else "Walk-in",
                customer_phone=customer.state.phone if customer else None,
                customer_address=customer.state.address if customer else None,
                pizzas=pizza_dtos,
                status=(order.state.status.value if hasattr(order.state.status, "value") else str(order.state.status)),
                order_time=order.state.order_time or datetime.now(),
                confirmed_time=getattr(order.state, "confirmed_time", None),
                cooking_started_time=getattr(order.state, "cooking_started_time", None),
                actual_ready_time=getattr(order.state, "actual_ready_time", None),
                estimated_ready_time=getattr(order.state, "estimated_ready_time", None),
                notes=getattr(order.state, "notes", None),
                total_amount=order.total_amount,
                pizza_count=len(order.state.order_items),
                payment_method=None,
                chef_name=getattr(order.state, "chef_name", None),
                ready_by_name=getattr(order.state, "ready_by_name", None),
                delivery_name=getattr(order.state, "delivery_name", None),
            )
            order_dtos.append(order_dto)

        return self.ok(order_dtos)
