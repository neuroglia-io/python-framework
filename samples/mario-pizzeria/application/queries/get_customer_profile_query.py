"""Query for retrieving customer profile"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from api.dtos.notification_dtos import CustomerNotificationDto
from api.dtos.order_dtos import OrderDto, PizzaDto
from api.dtos.profile_dtos import CustomerProfileDto
from domain.entities import Customer
from domain.repositories import ICustomerRepository, IOrderRepository

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetCustomerProfileQuery(Query[OperationResult[CustomerProfileDto]]):
    """
    Query to get customer profile.

    Supports lookup by either customer_id or user_id (Keycloak).
    Exactly one must be provided.
    """

    customer_id: Optional[str] = None
    user_id: Optional[str] = None


class GetCustomerProfileHandler(QueryHandler[GetCustomerProfileQuery, OperationResult[CustomerProfileDto]]):
    """Handler for customer profile queries"""

    def __init__(
        self,
        customer_repository: ICustomerRepository,
        order_repository: IOrderRepository,
        mapper: Mapper,
    ):
        self.customer_repository = customer_repository
        self.order_repository = order_repository
        self.mapper = mapper

    async def handle_async(self, request: GetCustomerProfileQuery) -> OperationResult[CustomerProfileDto]:
        """Handle profile retrieval by customer_id or user_id"""

        # Validate input - exactly one identifier must be provided
        if not request.customer_id and not request.user_id:
            return self.bad_request("Either customer_id or user_id must be provided")

        if request.customer_id and request.user_id:
            return self.bad_request("Cannot specify both customer_id and user_id")

        # Find customer by appropriate identifier
        customer: Optional[Customer] = None

        if request.customer_id:
            customer = await self.customer_repository.get_async(request.customer_id)
            if not customer:
                return self.not_found(Customer, request.customer_id)
        else:
            # user_id lookup
            customer = await self.customer_repository.get_by_user_id_async(request.user_id)
            if not customer:
                return self.bad_request(f"No customer profile found for user_id={request.user_id}")

        # Get order statistics - use customer-specific query instead of loading all orders
        customer_orders = await self.order_repository.get_by_customer_id_async(customer.id())

        # Calculate favorite pizza
        favorite_pizza = None
        if customer_orders:
            pizza_counts: dict[str, int] = {}
            for order in customer_orders:
                for item in order.state.order_items:
                    # Each OrderItem represents one pizza, so increment by 1
                    pizza_counts[item.name] = pizza_counts.get(item.name, 0) + 1
            if pizza_counts:
                favorite_pizza = max(pizza_counts, key=lambda name: pizza_counts[name])

        # Get active orders (orders that are not delivered or cancelled)
        active_orders = [order for order in customer_orders if hasattr(order.state, "status") and order.state.status not in ["delivered", "cancelled"]]

        # Map active orders to DTOs
        active_order_dtos = []
        for order in active_orders:
            # Map pizzas in the order
            pizza_dtos = []
            for item in order.state.order_items:
                pizza_dto = PizzaDto(
                    name=item.name,
                    size=item.size.value if hasattr(item.size, "value") else str(item.size),
                    total_price=item.total_price,  # Use calculated total price
                    toppings=list(item.toppings) if item.toppings else [],
                )
                pizza_dtos.append(pizza_dto)

            order_dto = OrderDto(
                id=order.id(),
                customer_name=customer.state.name or "",
                customer_phone=customer.state.phone or "",
                customer_address=customer.state.address or "",
                customer_email=customer.state.email or "",
                pizzas=pizza_dtos,
                total_amount=order.total_amount,  # Use calculated total amount
                pizza_count=len(pizza_dtos),  # Count of pizzas in order
                status=order.state.status.value if hasattr(order.state.status, "value") else str(order.state.status),
                order_time=order.state.order_time,
                payment_method="unknown",  # OrderState doesn't store payment method
                notes=getattr(order.state, "notes", None) or "",
            )
            active_order_dtos.append(order_dto)

        # Get customer notifications (placeholder for now - will need notification repository)
        notification_dtos = []
        unread_notification_count = 0

        # TODO: Implement actual notification retrieval when notification repository is available
        # For now, add sample notifications if customer has active orders
        if active_order_dtos:
            sample_notification = CustomerNotificationDto(
                id="sample-notification-1",
                customer_id=customer.id(),
                notification_type="order_cooking_started",
                title="👨‍🍳 Cooking Started",
                message="Your order is now being prepared!",
                order_id=active_order_dtos[0].id,
                status="unread",
                created_at=datetime.now(timezone.utc),
                read_at=None,
                dismissed_at=None,
            )
            notification_dtos.append(sample_notification)
            unread_notification_count = 1

        # Map to DTO (convert empty strings to None for validation)
        user_id = customer.state.user_id or ""
        profile_dto = CustomerProfileDto(
            id=customer.id(),
            user_id=user_id,
            name=customer.state.name or "",
            email=customer.state.email or "",
            phone=customer.state.phone if customer.state.phone else None,
            address=customer.state.address if customer.state.address else None,
            total_orders=len(customer_orders),
            favorite_pizza=favorite_pizza,
            active_orders=active_order_dtos,
            notifications=notification_dtos,
            unread_notification_count=unread_notification_count,
        )

        return self.ok(profile_dto)
