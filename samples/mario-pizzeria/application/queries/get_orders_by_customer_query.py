"""Query for retrieving customer order history"""

from dataclasses import dataclass
from datetime import datetime

from api.dtos import OrderDto, PizzaDto
from domain.repositories import ICustomerRepository, IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetOrdersByCustomerQuery(Query[OperationResult[list[OrderDto]]]):
    """Query to get all orders for a specific customer"""

    customer_id: str
    limit: int = 50


class GetOrdersByCustomerHandler(QueryHandler[GetOrdersByCustomerQuery, OperationResult[list[OrderDto]]]):
    """Handler for customer order history queries"""

    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
        mapper: Mapper,
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.mapper = mapper

    async def handle_async(self, request: GetOrdersByCustomerQuery) -> OperationResult[list[OrderDto]]:
        """Handle order history retrieval"""

        # Get customer information first
        customer = await self.customer_repository.get_async(request.customer_id)
        if not customer:
            return self.bad_request(f"Customer {request.customer_id} not found")

        # Get orders for customer using optimized filtered query
        customer_orders = await self.order_repository.get_by_customer_id_async(request.customer_id)

        # Sort by order time (most recent first)
        customer_orders.sort(key=lambda o: o.state.order_time or datetime.min, reverse=True)

        # Limit results
        customer_orders = customer_orders[: request.limit]

        # Map to DTOs - manually construct due to entity.id() being a method
        order_dtos = []
        for order in customer_orders:
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

            # Construct OrderDto with id from entity.id()
            # Use getattr() for safety in case fields are missing from old data
            order_dto = OrderDto(
                id=order.id(),  # Get ID from entity method
                customer_name=customer.state.name if customer else None,
                customer_phone=customer.state.phone if customer else None,
                customer_address=customer.state.address if customer else None,
                pizzas=pizza_dtos,
                status=(order.state.status.value if hasattr(order.state.status, "value") else str(order.state.status)),
                order_time=order.state.order_time or datetime.now(),  # Handle None
                confirmed_time=getattr(order.state, "confirmed_time", None),
                cooking_started_time=getattr(order.state, "cooking_started_time", None),
                actual_ready_time=getattr(order.state, "actual_ready_time", None),
                estimated_ready_time=getattr(order.state, "estimated_ready_time", None),
                notes=getattr(order.state, "notes", None),
                total_amount=order.total_amount,  # Property, not method
                pizza_count=len(order.state.order_items),
                payment_method=None,  # Add if available in order state
                chef_name=getattr(order.state, "chef_name", None),
                ready_by_name=getattr(order.state, "ready_by_name", None),
                delivery_name=getattr(order.state, "delivery_name", None),
            )
            order_dtos.append(order_dto)

        return self.ok(order_dtos)
