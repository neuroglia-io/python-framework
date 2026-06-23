"""Complete Order Command and Handler for Mario's Pizzeria"""

from dataclasses import dataclass
from typing import Optional

from api.dtos import OrderDto, PizzaDto
from domain.repositories import (
    ICustomerRepository,
    IKitchenRepository,
    IOrderRepository,
)

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler

# OpenTelemetry imports for business metrics and span attributes
try:
    from datetime import datetime

    from observability.metrics import cooking_duration, orders_completed

    from neuroglia.observability.tracing import add_span_attributes

    OTEL_AVAILABLE = True
except ImportError:
    from datetime import datetime

    OTEL_AVAILABLE = False


@dataclass
class CompleteOrderCommand(Command[OperationResult[OrderDto]]):
    """Command to mark an order as ready"""

    order_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None


class CompleteOrderCommandHandler(CommandHandler[CompleteOrderCommand, OperationResult[OrderDto]]):
    """Handler for marking an order as ready"""

    def __init__(
        self,
        order_repository: IOrderRepository,
        kitchen_repository: IKitchenRepository,
        customer_repository: ICustomerRepository,
        mapper: Mapper,
    ):
        self.order_repository = order_repository
        self.kitchen_repository = kitchen_repository
        self.customer_repository = customer_repository
        self.mapper = mapper

    async def handle_async(self, request: CompleteOrderCommand) -> OperationResult[OrderDto]:
        try:
            # Add business context to span
            if OTEL_AVAILABLE:
                add_span_attributes(
                    {
                        "order.id": request.order_id,
                        "kitchen.user_id": request.user_id or "system",
                        "kitchen.user_name": request.user_name or "System",
                    }
                )

            # Get order
            order = await self.order_repository.get_async(request.order_id)
            if not order:
                return self.not_found("Order", request.order_id)

            # Get kitchen state
            kitchen = await self.kitchen_repository.get_kitchen_state_async()

            # Get user info from command or use defaults
            user_id = request.user_id or "system"
            user_name = request.user_name or "System"

            # Calculate cooking duration before marking ready (if we have started cooking)
            cooking_duration_seconds = 0.0
            if order.state.cooking_started_time:
                # Calculate duration from cooking start to now
                cooking_duration_seconds = (datetime.now() - order.state.cooking_started_time).total_seconds()

            # Mark order ready with user tracking
            order.mark_ready(user_id, user_name)
            kitchen.complete_order(order.id())

            # Save changes - events published automatically by repository
            await self.order_repository.update_async(order)
            await self.kitchen_repository.update_kitchen_state_async(kitchen)

            # Record business metrics
            if OTEL_AVAILABLE:
                # Record completion metrics
                orders_completed.add(
                    1,
                    {
                        "pizza_count": str(len(order.state.order_items)),
                    },
                )

                # Record cooking duration
                if cooking_duration_seconds > 0:
                    cooking_duration.record(
                        cooking_duration_seconds,
                        {
                            "pizza_count": str(len(order.state.order_items)),
                        },
                    )

                # Note: orders_in_progress tracking disabled - needs observable gauge pattern
                # Update kitchen capacity gauge
                # orders_in_progress.set(kitchen.current_capacity)

                # Add completion details to span
                add_span_attributes(
                    {
                        "order.status": order.state.status.value,
                        "order.pizza_count": len(order.state.order_items),
                        "order.cooking_duration_seconds": cooking_duration_seconds,
                        "kitchen.active_orders": kitchen.current_capacity,
                    }
                )

            # Get customer details for DTO
            customer = await self.customer_repository.get_async(order.state.customer_id)

            # Create OrderDto - Map OrderItems (value objects) to PizzaDtos
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
            return self.ok(order_dto)

        except ValueError as e:
            return self.bad_request(str(e))
        except Exception as e:
            return self.bad_request(f"Failed to complete order: {str(e)}")
