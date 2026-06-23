"""Query for fetching delivery-relevant orders"""

from dataclasses import dataclass
from datetime import datetime
from typing import List

from api.dtos import OrderDto, PizzaDto
from domain.repositories import ICustomerRepository, IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetDeliveryOrdersQuery(Query[OperationResult[List[OrderDto]]]):
    """Query to fetch all orders relevant to delivery drivers (READY + DELIVERING)"""


class GetDeliveryOrdersHandler(QueryHandler[GetDeliveryOrdersQuery, OperationResult[List[OrderDto]]]):
    """Handler for fetching delivery-relevant orders"""

    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
        mapper: Mapper,
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.mapper = mapper

    async def handle_async(self, request: GetDeliveryOrdersQuery) -> OperationResult[list[OrderDto]]:
        """Handle getting delivery-relevant orders"""

        # Get active orders using native MongoDB filtering (excludes delivered and cancelled)
        active_orders = await self.order_repository.get_active_orders_async()

        # Filter for delivery-relevant orders only
        # Delivery drivers should see orders in these stages:
        # - READY: Cooked and waiting for driver pickup
        # - DELIVERING: Currently out for delivery with a driver
        #
        # Exclude from delivery view:
        # - PENDING: Still waiting for kitchen confirmation
        # - CONFIRMED: Kitchen hasn't started cooking yet
        # - COOKING: Still being prepared by kitchen
        # - DELIVERED: Completed
        # - CANCELLED: No longer needed

        delivery_orders = [order for order in active_orders if order.state.status.name in ["READY", "DELIVERING"]]

        # Sort by priority:
        # 1. DELIVERING orders first (sorted by out_for_delivery_time - oldest first)
        # 2. READY orders second (sorted by actual_ready_time - oldest first, FIFO)

        delivering_orders = [o for o in delivery_orders if o.state.status.name == "DELIVERING"]
        ready_orders = [o for o in delivery_orders if o.state.status.name == "READY"]

        # Sort each group
        delivering_orders.sort(key=lambda o: getattr(o.state, "out_for_delivery_time", None) or datetime.min)
        ready_orders.sort(key=lambda o: o.state.actual_ready_time or o.state.order_time or datetime.min)

        # Combine: delivering first, then ready
        sorted_orders = delivering_orders + ready_orders

        # Build DTOs with customer information
        order_dtos = []
        for order in sorted_orders:
            # Get customer details
            customer = None
            if order.state.customer_id:
                customer = await self.customer_repository.get_async(order.state.customer_id)

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

            order_dto = OrderDto(
                id=order.id(),
                pizzas=pizza_dtos,
                status=order.state.status.value,
                order_time=order.state.order_time or datetime.now(),
                confirmed_time=getattr(order.state, "confirmed_time", None),
                cooking_started_time=getattr(order.state, "cooking_started_time", None),
                actual_ready_time=getattr(order.state, "actual_ready_time", None),
                estimated_ready_time=getattr(order.state, "estimated_ready_time", None),
                notes=getattr(order.state, "notes", None),
                total_amount=order.total_amount,
                pizza_count=len(order.state.order_items),
                customer_name=customer.state.name if customer else "Unknown",
                customer_phone=customer.state.phone if customer else None,
                customer_address=customer.state.address if customer else None,
                payment_method=None,
                chef_name=getattr(order.state, "chef_name", None),
                ready_by_name=getattr(order.state, "ready_by_name", None),
                delivery_name=getattr(order.state, "delivery_name", None),
            )

            order_dtos.append(order_dto)

        return self.ok(order_dtos)
