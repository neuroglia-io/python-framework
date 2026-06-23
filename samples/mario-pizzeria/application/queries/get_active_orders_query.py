"""Get Active Orders Query and Handler for Mario's Pizzeria"""

from dataclasses import dataclass
from typing import List

from api.dtos import OrderDto, PizzaDto
from domain.repositories import ICustomerRepository, IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetActiveOrdersQuery(Query[OperationResult[List[OrderDto]]]):
    """Query to get all active orders (not delivered or cancelled)"""


class GetActiveOrdersQueryHandler(QueryHandler[GetActiveOrdersQuery, OperationResult[List[OrderDto]]]):
    """Handler for getting active orders"""

    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
        mapper: Mapper,
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.mapper = mapper

    async def handle_async(self, request: GetActiveOrdersQuery) -> OperationResult[list[OrderDto]]:
        try:
            # Get all active orders (not delivered or cancelled)
            orders = await self.order_repository.get_active_orders_async()

            order_dtos = []
            for order in orders:
                # Get customer details
                customer = await self.customer_repository.get_async(order.state.customer_id)

                # Create OrderDto with customer information - Map OrderItems (value objects) to PizzaDtos
                pizza_dtos = [
                    PizzaDto(
                        id=item.line_item_id,
                        name=item.name,
                        size=item.size.value,
                        toppings=list(item.toppings),
                        base_price=item.base_price,
                        total_price=item.total_price,
                    )
                    for item in order.state.order_items
                ]

                order_dto = OrderDto(
                    id=order.id(),
                    customer_name=customer.state.name if customer else "Unknown",
                    customer_phone=customer.state.phone if customer else "Unknown",
                    customer_address=customer.state.address if customer else "Unknown",
                    pizzas=pizza_dtos,
                    status=order.state.status.value,
                    order_time=order.state.order_time,
                    confirmed_time=getattr(order.state, "confirmed_time", None),
                    cooking_started_time=getattr(order.state, "cooking_started_time", None),
                    actual_ready_time=getattr(order.state, "actual_ready_time", None),
                    estimated_ready_time=getattr(order.state, "estimated_ready_time", None),
                    notes=getattr(order.state, "notes", None),
                    total_amount=order.total_amount,
                    pizza_count=order.pizza_count,
                    chef_name=getattr(order.state, "chef_name", None),
                    ready_by_name=getattr(order.state, "ready_by_name", None),
                    delivery_name=getattr(order.state, "delivery_name", None),
                )
                order_dtos.append(order_dto)

            return self.ok(order_dtos)

        except Exception as e:
            return self.bad_request(f"Failed to get active orders: {str(e)}")
