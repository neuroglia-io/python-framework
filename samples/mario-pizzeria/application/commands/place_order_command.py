"""Place Order Command and Handler for Mario's Pizzeria"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from api.dtos import CreateOrderDto, CreatePizzaDto, OrderDto, PizzaDto
from domain.entities import Customer, Order, PizzaSize
from domain.entities.order_item import OrderItem
from domain.repositories import ICustomerRepository, IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mapping.mapper import map_from
from neuroglia.mediation import Command, CommandHandler

# OpenTelemetry imports for business metrics and span attributes
try:
    from observability.metrics import (
        customers_returning,
        order_value,
        orders_created,
        pizzas_by_size,
        pizzas_ordered,
    )

    from neuroglia.observability.tracing import add_span_attributes

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


@dataclass
@map_from(CreateOrderDto)
class PlaceOrderCommand(Command[OperationResult[OrderDto]]):
    """Command to place a new pizza order"""

    customer_name: str
    customer_phone: str
    customer_address: Optional[str] = None
    customer_email: Optional[str] = None
    pizzas: list[CreatePizzaDto] = field(default_factory=list)
    payment_method: str = "cash"
    notes: Optional[str] = None
    customer_id: Optional[str] = None  # Optional - will be created/retrieved in handler


class PlaceOrderCommandHandler(CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]):
    """Handler for placing new pizza orders"""

    def __init__(
        self,
        order_repository: IOrderRepository,
        customer_repository: ICustomerRepository,
        mapper: Mapper,
    ):
        self.order_repository = order_repository
        self.customer_repository = customer_repository
        self.mapper = mapper

    async def handle_async(self, request: PlaceOrderCommand) -> OperationResult[OrderDto]:
        try:
            # Add business context to span (automatic tracing via TracingPipelineBehavior)
            if OTEL_AVAILABLE:
                add_span_attributes(
                    {
                        "order.customer_name": request.customer_name,
                        "order.customer_phone": request.customer_phone,
                        "order.pizza_count": len(request.pizzas),
                        "order.payment_method": request.payment_method,
                    }
                )

            # Get or create customer profile
            customer = await self._create_or_get_customer(request)

            if not customer:
                return self.bad_request("Failed to create or retrieve customer profile")

            # Create order with customer_id
            order = Order(customer_id=customer.id())
            if request.notes:
                order.state.notes = request.notes

            # Add pizzas to order as OrderItems (value objects)
            for pizza_item in request.pizzas:
                # Convert size string to enum
                size = PizzaSize(pizza_item.size.lower())

                # Determine base price based on pizza name
                base_price = Decimal("12.99")  # Default base price
                if pizza_item.name.lower() == "margherita":
                    base_price = Decimal("12.99")
                elif pizza_item.name.lower() == "pepperoni":
                    base_price = Decimal("14.99")
                elif pizza_item.name.lower() == "supreme":
                    base_price = Decimal("17.99")

                # Create OrderItem (value object snapshot of pizza data)
                # Note: line_item_id is generated here as a unique identifier for this order item
                order_item = OrderItem(
                    line_item_id=str(uuid4()),  # Generate unique ID for this line item
                    name=pizza_item.name,
                    size=size,
                    base_price=base_price,
                    toppings=pizza_item.toppings,
                )

                order.add_order_item(order_item)

                # Record pizza metrics
                if OTEL_AVAILABLE:
                    pizzas_ordered.add(1, {"pizza_name": pizza_item.name})
                    pizzas_by_size.add(1, {"size": size.value})

            # Validate order has items
            if not order.state.order_items:
                return self.bad_request("Order must contain at least one pizza")

            # Confirm order (raises domain event)
            order.confirm_order()

            # Save order - events published automatically by repository
            await self.order_repository.add_async(order)

            # Record business metrics
            if OTEL_AVAILABLE:
                orders_created.add(
                    1,
                    {
                        "status": order.state.status.value,
                        "payment_method": request.payment_method,
                    },
                )
                order_value.record(
                    float(order.total_amount),
                    {
                        "payment_method": request.payment_method,
                    },
                )
                # Add order details to span
                add_span_attributes(
                    {
                        "order.id": order.id(),
                        "order.total_amount": float(order.total_amount),
                        "order.item_count": len(order.state.order_items),
                        "order.status": order.state.status.value,
                    }
                )

            # Create OrderDto with customer information
            # Map OrderItems (value objects) to PizzaDtos
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
                customer_name=customer.state.name,
                customer_phone=customer.state.phone,
                customer_address=customer.state.address,
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
                payment_method=request.payment_method,
            )
            return self.created(order_dto)

        except ValueError as e:
            return self.bad_request(str(e))
        except Exception as e:
            return self.bad_request(f"Failed to place order: {str(e)}")

    async def _create_or_get_customer(self, request: PlaceOrderCommand) -> Customer:
        """Create or get customer record"""
        # Try to find existing customer by phone
        existing_customer = await self.customer_repository.get_by_phone_async(request.customer_phone)

        if existing_customer:
            # Record returning customer metric
            if OTEL_AVAILABLE:
                customers_returning.add(
                    1,
                    {
                        "customer_type": "phone_match",
                    },
                )

            # Update address if provided and customer doesn't have one
            if request.customer_address and not existing_customer.state.address:
                existing_customer.update_contact_info(address=request.customer_address)
                # Save updated customer - events published automatically by repository
                await self.customer_repository.update_async(existing_customer)
            return existing_customer
        else:
            # Create new customer
            customer = Customer(
                name=request.customer_name,
                email=request.customer_email or f"{request.customer_phone}@placeholder.com",
                phone=request.customer_phone,
                address=request.customer_address,
            )
            await self.customer_repository.add_async(customer)
            return customer
