"""Command for updating customer profile"""

from dataclasses import dataclass
from typing import Optional

from api.dtos.profile_dtos import CustomerProfileDto
from domain.repositories import ICustomerRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Command, CommandHandler


@dataclass
class UpdateCustomerProfileCommand(Command[OperationResult[CustomerProfileDto]]):
    """Command to update customer profile"""

    customer_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class UpdateCustomerProfileHandler(CommandHandler[UpdateCustomerProfileCommand, OperationResult[CustomerProfileDto]]):
    """Handler for updating customer profiles"""

    def __init__(self, customer_repository: ICustomerRepository):
        self.customer_repository = customer_repository

    async def handle_async(self, request: UpdateCustomerProfileCommand) -> OperationResult[CustomerProfileDto]:
        """Handle profile update"""

        # Retrieve customer
        customer = await self.customer_repository.get_async(request.customer_id)
        if not customer:
            return self.not_found(f"Customer {request.customer_id} not found")

        # Update contact information if provided
        phone_update = request.phone if request.phone is not None else customer.state.phone
        address_update = request.address if request.address is not None else customer.state.address

        if request.phone is not None or request.address is not None:
            customer.update_contact_info(phone=phone_update, address=address_update)

        # Update name/email if provided (direct state update as no specific domain method exists)
        if request.name:
            customer.state.name = request.name
        if request.email:
            # Check if email is already taken by another customer
            existing = await self.customer_repository.get_by_email_async(request.email)
            if existing and existing.id() != customer.id():
                return self.bad_request("Email already in use by another customer")
            customer.state.email = request.email

        # Save - events published automatically by repository
        await self.customer_repository.update_async(customer)

        # Get order count for user (TODO: Query order repository for statistics)

        # Map to DTO
        user_id = customer.state.user_id or ""
        profile_dto = CustomerProfileDto(
            id=customer.id(),
            user_id=user_id,
            name=customer.state.name or "",
            email=customer.state.email or "",
            phone=customer.state.phone,
            address=customer.state.address,
            total_orders=0,  # TODO: Get from order stats
        )

        return self.ok(profile_dto)
