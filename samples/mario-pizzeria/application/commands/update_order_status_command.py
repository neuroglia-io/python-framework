"""Command for updating order status in the kitchen"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from api.dtos import OrderDto, PizzaDto
from domain.repositories import IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Command, CommandHandler

# OpenTelemetry imports for business metrics
try:
    from observability.metrics import orders_cancelled

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

    # Provide no-op metric if OTEL not available
    class NoOpMetric:
        def add(self, value, attributes=None):
            pass

    orders_cancelled = NoOpMetric()


@dataclass
class UpdateOrderStatusCommand(Command[OperationResult[OrderDto]]):
    """Command to update order status (kitchen operations)"""

    order_id: str
    new_status: str  # "confirmed", "cooking", "ready", "delivered", "cancelled"
    notes: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None


class UpdateOrderStatusHandler(CommandHandler[UpdateOrderStatusCommand, OperationResult[OrderDto]]):
    """Handler for updating order status"""

    def __init__(self, order_repository: IOrderRepository):
        self.order_repository = order_repository

    async def handle_async(self, request: UpdateOrderStatusCommand) -> OperationResult[OrderDto]:
        """Handle order status update"""

        # Get the order
        order = await self.order_repository.get_async(request.order_id)
        if not order:
            return self.bad_request(f"Order {request.order_id} not found")

        # Validate status transition
        valid_statuses = ["confirmed", "cooking", "ready", "delivering", "delivered", "cancelled"]
        if request.new_status not in valid_statuses:
            return self.bad_request(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

        # Get user info from command or use defaults
        user_id = request.user_id or "system"
        user_name = request.user_name or "System"

        # Update order status based on new status
        try:
            if request.new_status == "confirmed":
                order.confirm_order()
            elif request.new_status == "cooking":
                order.start_cooking(user_id, user_name)
            elif request.new_status == "ready":
                order.mark_ready(user_id, user_name)
            elif request.new_status == "delivering":
                # Note: This should normally be done via AssignOrderToDeliveryCommand
                # but we support it here for direct status updates
                if not getattr(order.state, "delivery_person_id", None):
                    return self.bad_request("Order must be assigned to a delivery person first")
                order.mark_out_for_delivery()
            elif request.new_status == "delivered":
                order.deliver_order(user_id, user_name)
            elif request.new_status == "cancelled":
                order.cancel_order()

                # Record business metrics for cancellation
                if OTEL_AVAILABLE:
                    orders_cancelled.add(
                        1,
                        {
                            "pizza_count": str(len(order.state.order_items)),
                            "reason": "manual" if request.notes else "unknown",
                        },
                    )

            # Save the updated order - events published automatically by repository
            await self.order_repository.update_async(order)

            # Return success (we'll construct a simple response)
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
                chef_name=getattr(order.state, "chef_name", None),
                ready_by_name=getattr(order.state, "ready_by_name", None),
                delivery_name=getattr(order.state, "delivery_name", None),
            )

            return self.ok(order_dto)

        except Exception as e:
            return self.bad_request(f"Failed to update order status: {str(e)}")
