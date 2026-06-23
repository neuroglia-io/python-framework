"""Query for fetching orders ready for delivery"""

from dataclasses import dataclass
from datetime import datetime

from api.dtos import OrderDto, PizzaDto
from domain.repositories import ICustomerRepository, IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetReadyOrdersQuery(Query[OperationResult[list[OrderDto]]]):
    """Query to fetch all orders ready for delivery pickup"""


class GetReadyOrdersHandler(QueryHandler[GetReadyOrdersQuery, OperationResult[list[OrderDto]]]):
    """Handler for fetching ready orders"""

    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
        mapper: Mapper,
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.mapper = mapper

    async def handle_async(self, request: GetReadyOrdersQuery) -> OperationResult[list[OrderDto]]:
        """Handle getting ready orders"""

        # Get ready orders using native MongoDB filtering
        ready_orders = await self.order_repository.get_ready_orders_async()

        # Sort by ready time (oldest first - FIFO)
        ready_orders.sort(key=lambda o: o.state.actual_ready_time or o.state.order_time or datetime.min)

        # Build DTOs with customer information
        order_dtos = []
        for order in ready_orders:
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
