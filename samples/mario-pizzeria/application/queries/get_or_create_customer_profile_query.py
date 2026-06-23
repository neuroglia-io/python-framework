"""Query for getting or creating customer profile by user_id.

Handles three scenarios:
1. Profile exists by user_id (fast path) → Return immediately
2. Profile exists by email without user_id (pre-SSO) → Link and return
3. No profile exists → Create from token claims and return
"""

from dataclasses import dataclass
from typing import Optional

from api.dtos import CustomerProfileDto
from application.commands.create_customer_profile_command import (
    CreateCustomerProfileCommand,
)
from application.queries.get_customer_profile_query import GetCustomerProfileQuery
from domain.repositories import ICustomerRepository

from neuroglia.core import OperationResult
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator, Query, QueryHandler


@dataclass
class GetOrCreateCustomerProfileQuery(Query[OperationResult[CustomerProfileDto]]):
    """Query to get or create customer profile for authenticated user.

    If no profile exists by user_id, checks if one exists by email and links it.
    Otherwise creates a new profile from the provided user information.

    Args:
        user_id: Keycloak user ID (sub claim from JWT)
        email: User's email address from token claims
        name: User's full name from token claims
    """

    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None


class GetOrCreateCustomerProfileHandler(QueryHandler[GetOrCreateCustomerProfileQuery, OperationResult[CustomerProfileDto]]):
    """Handler for getting or creating customer profiles.

    Implements three-tier lookup strategy:
    1. Fast path: Check by user_id
    2. Migration path: Check by email and link existing profile
    3. Creation path: Create new profile from token claims
    """

    def __init__(
        self,
        customer_repository: ICustomerRepository,
        mediator: Mediator,
        mapper: Mapper,
    ):
        self.customer_repository = customer_repository
        self.mediator = mediator
        self.mapper = mapper

    async def handle_async(self, request: GetOrCreateCustomerProfileQuery) -> OperationResult[CustomerProfileDto]:
        """Handle the query by implementing the three-tier lookup strategy.

        Args:
            request: Query containing user_id, email, and name from token claims

        Returns:
            OperationResult[CustomerProfileDto]: Success with existing or newly created profile
        """

        # Scenario 1: Profile exists by user_id (fast path)
        existing_query = GetCustomerProfileQuery(user_id=request.user_id)
        existing_result = await self.mediator.execute_async(existing_query)

        if existing_result.is_success:
            return existing_result

        # Scenario 2: Check if profile exists by email (pre-SSO migration)
        if request.email:
            existing_customer = await self.customer_repository.get_by_email_async(request.email)

            if existing_customer:
                # Link existing profile to user_id
                if not existing_customer.state.user_id:
                    existing_customer.state.user_id = request.user_id
                    await self.customer_repository.update_async(existing_customer)

                # Return linked profile
                profile_dto = CustomerProfileDto(
                    id=existing_customer.id(),
                    user_id=request.user_id,
                    name=existing_customer.state.name or "Unknown",
                    email=existing_customer.state.email or request.email,
                    phone=existing_customer.state.phone or None,
                    address=existing_customer.state.address or None,
                    total_orders=0,
                )
                return self.ok(profile_dto)

        # Scenario 3: Create new profile
        name = request.name or "User"
        email = request.email or f"user-{request.user_id[:8]}@keycloak.local"

        # Parse name into first/last
        name_parts = name.split(" ", 1)
        first_name = name_parts[0] if name_parts else name
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        full_name = f"{first_name} {last_name}".strip()

        # Create profile via command
        command = CreateCustomerProfileCommand(
            user_id=request.user_id,
            name=full_name,
            email=email,
            phone=None,
            address=None,
        )

        create_result = await self.mediator.execute_async(command)

        if not create_result.is_success:
            return self.bad_request(f"Failed to create profile: {create_result.error_message}")

        return create_result
