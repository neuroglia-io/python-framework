"""Command for assigning order to delivery driver"""

from dataclasses import dataclass
from datetime import datetime

from api.dtos import OrderDto, PizzaDto
from domain.repositories import IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Command, CommandHandler


@dataclass
class AssignOrderToDeliveryCommand(Command[OperationResult[OrderDto]]):
    """Command to assign an order to a delivery driver and mark it as delivering"""

    order_id: str
    delivery_person_id: str


class AssignOrderToDeliveryHandler(CommandHandler[AssignOrderToDeliveryCommand, OperationResult[OrderDto]]):
    """Handler for assigning order to delivery"""

    def __init__(self, order_repository: IOrderRepository):
        self.order_repository = order_repository

    async def handle_async(self, request: AssignOrderToDeliveryCommand) -> OperationResult[OrderDto]:
        """Handle order assignment to delivery driver"""

        # Get the order
        order = await self.order_repository.get_async(request.order_id)
        if not order:
            return self.bad_request(f"Order {request.order_id} not found")

        # Assign to delivery driver
        try:
            order.assign_to_delivery(request.delivery_person_id)
            order.mark_out_for_delivery()

            # Save the updated order - events published automatically by repository
            await self.order_repository.update_async(order)

            # Return success with simple DTO
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
                status=(order.state.status.value if hasattr(order.state.status, "value") else str(order.state.status)),
                order_time=order.state.order_time or datetime.now(),
                confirmed_time=getattr(order.state, "confirmed_time", None),
                cooking_started_time=getattr(order.state, "cooking_started_time", None),
                actual_ready_time=getattr(order.state, "actual_ready_time", None),
                estimated_ready_time=getattr(order.state, "estimated_ready_time", None),
                notes=getattr(order.state, "notes", None),
                total_amount=order.total_amount,
                pizza_count=len(order.state.order_items),
                customer_name=None,  # We don't need customer details here
                customer_phone=None,
                customer_address=None,
                payment_method=None,
            )

            return self.ok(order_dto)

        except Exception as e:
            return self.bad_request(f"Failed to assign order to delivery: {str(e)}")
