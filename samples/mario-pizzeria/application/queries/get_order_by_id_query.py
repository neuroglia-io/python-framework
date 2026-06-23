"""Get Order By ID Query and Handler for Mario's Pizzeria"""

from dataclasses import dataclass

from api.dtos import OrderDto, PizzaDto
from domain.repositories import ICustomerRepository, IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetOrderByIdQuery(Query[OperationResult[OrderDto]]):
    """Query to get an order by ID"""

    order_id: str


class GetOrderByIdQueryHandler(QueryHandler[GetOrderByIdQuery, OperationResult[OrderDto]]):
    """Handler for getting an order by ID"""

    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
        mapper: Mapper,
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.mapper = mapper

    async def handle_async(self, request: GetOrderByIdQuery) -> OperationResult[OrderDto]:
        try:
            order = await self.order_repository.get_async(request.order_id)
            if not order:
                return self.not_found("Order", request.order_id)

            # Get customer details
            if order.state.customer_id:
                customer = await self.customer_repository.get_async(order.state.customer_id)
            else:
                customer = None

            # Create OrderDto with customer information
            # OrderItems are now properly deserialized as dataclass instances (framework fix applied)
            pizza_dtos = []
            for item in order.state.order_items:
                # item is now an OrderItem instance, not a dict (thanks to framework enhancement)
                pizza_dtos.append(
                    PizzaDto(
                        id=item.line_item_id,
                        name=item.name,
                        size=item.size.value if hasattr(item.size, "value") else str(item.size),
                        toppings=list(item.toppings),
                        base_price=item.base_price,
                        total_price=item.total_price,  # Computed property now works!
                    )
                )

            order_dto = OrderDto(
                id=order.id(),
                customer_name=customer.state.name if customer else "Unknown",
                customer_phone=customer.state.phone if customer else "Unknown",
                customer_address=customer.state.address if customer else "Unknown",
                pizzas=pizza_dtos,
                status=(order.state.status.value if hasattr(order.state.status, "value") else str(order.state.status)),
                order_time=order.state.order_time or order.created_at,
                confirmed_time=getattr(order.state, "confirmed_time", None),
                cooking_started_time=getattr(order.state, "cooking_started_time", None),
                actual_ready_time=getattr(order.state, "actual_ready_time", None),
                estimated_ready_time=getattr(order.state, "estimated_ready_time", None),
                notes=getattr(order.state, "notes", None),
                total_amount=order.total_amount,  # Now works because items have .total_price
                pizza_count=order.pizza_count,  # Now works because items are proper instances
                chef_name=getattr(order.state, "chef_name", None),
                ready_by_name=getattr(order.state, "ready_by_name", None),
                delivery_name=getattr(order.state, "delivery_name", None),
            )
            return self.ok(order_dto)

        except Exception as e:
            return self.bad_request(f"Failed to get order: {str(e)}")
