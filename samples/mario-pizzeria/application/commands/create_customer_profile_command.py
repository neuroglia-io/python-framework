"""Command for creating customer profile"""

from dataclasses import dataclass
from typing import Optional

from api.dtos.profile_dtos import CustomerProfileDto
from domain.entities import Customer
from domain.events import CustomerProfileCreatedEvent
from domain.repositories import ICustomerRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Command, CommandHandler, Mediator

# OpenTelemetry imports for business metrics
try:
    from observability.metrics import customers_registered

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

    # Provide no-op metric if OTEL not available
    class NoOpMetric:
        def add(self, value, attributes=None):
            pass

    customers_registered = NoOpMetric()


@dataclass
class CreateCustomerProfileCommand(Command[OperationResult[CustomerProfileDto]]):
    """Command to create a new customer profile"""

    user_id: str  # Keycloak user ID
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None


class CreateCustomerProfileHandler(CommandHandler[CreateCustomerProfileCommand, OperationResult[CustomerProfileDto]]):
    """Handler for creating customer profiles"""

    def __init__(
        self,
        customer_repository: ICustomerRepository,
        mediator: Mediator,
    ):
        self.customer_repository = customer_repository
        self.mediator = mediator

    async def handle_async(self, request: CreateCustomerProfileCommand) -> OperationResult[CustomerProfileDto]:
        """Handle profile creation"""

        # Check if customer already exists by email
        existing = await self.customer_repository.get_by_email_async(request.email)
        if existing:
            return self.bad_request("A customer with this email already exists")

        # Create new customer with user_id
        customer = Customer(
            name=request.name,
            email=request.email,
            phone=request.phone,
            address=request.address,
            user_id=request.user_id,
        )

        # Save - events published automatically by repository
        await self.customer_repository.add_async(customer)

        # Record business metrics
        if OTEL_AVAILABLE:
            customers_registered.add(
                1,
                {
                    "registration_method": "direct",  # vs SSO, API, etc.
                },
            )

        # Publish CustomerProfileCreatedEvent for profile-specific side effects
        # (welcome emails, onboarding workflows, etc.)
        profile_created_event = CustomerProfileCreatedEvent(
            aggregate_id=customer.id(),
            user_id=request.user_id,
            name=request.name,
            email=request.email,
            phone=request.phone,
            address=request.address,
        )
        await self.mediator.publish_async(profile_created_event)

        # Map to DTO (convert empty strings to None for validation)
        profile_dto = CustomerProfileDto(
            id=customer.id(),
            user_id=request.user_id,
            name=customer.state.name or request.name,
            email=customer.state.email or request.email,
            phone=customer.state.phone if customer.state.phone else None,
            address=customer.state.address if customer.state.address else None,
            total_orders=0,
        )

        return self.created(profile_dto)
