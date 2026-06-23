"""Update Pizza Command for Mario's Pizzeria"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from api.dtos import PizzaDto
from domain.entities import PizzaSize
from domain.repositories import IPizzaRepository

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler


@dataclass
class UpdatePizzaCommand(Command[OperationResult[PizzaDto]]):
    """Command to update an existing pizza on the menu"""

    pizza_id: str
    name: Optional[str] = None
    base_price: Optional[Decimal] = None
    size: Optional[str] = None  # Will be converted to PizzaSize enum
    description: Optional[str] = None
    toppings: Optional[list[str]] = None


class UpdatePizzaCommandHandler(CommandHandler[UpdatePizzaCommand, OperationResult[PizzaDto]]):
    """Handler for updating an existing pizza"""

    def __init__(self, pizza_repository: IPizzaRepository, mapper: Mapper):
        self.pizza_repository = pizza_repository
        self.mapper = mapper

    async def handle_async(self, request: UpdatePizzaCommand) -> OperationResult[PizzaDto]:
        try:
            # Get existing pizza
            pizza = await self.pizza_repository.get_async(request.pizza_id)
            if not pizza:
                return self.bad_request(f"Pizza with ID '{request.pizza_id}' not found")

            # Update name if provided
            if request.name is not None:
                # Check if new name conflicts with another pizza
                existing = await self.pizza_repository.get_by_name_async(request.name)
                if existing and existing.id() != request.pizza_id:
                    return self.bad_request(f"Pizza with name '{request.name}' already exists")
                pizza.state.name = request.name

            # Update base price if provided
            if request.base_price is not None:
                if request.base_price <= 0:
                    return self.bad_request("Base price must be greater than 0")
                pizza.state.base_price = request.base_price

            # Update size if provided
            if request.size is not None:
                try:
                    size_enum = PizzaSize[request.size.upper()]
                    pizza.state.size = size_enum
                except KeyError:
                    return self.bad_request(f"Invalid pizza size: {request.size}. Must be one of: {', '.join([s.name for s in PizzaSize])}")

            # Update description if provided
            if request.description is not None:
                pizza.state.description = request.description

            # Update toppings if provided
            if request.toppings is not None:
                # Clear existing toppings and add new ones
                pizza.state.toppings = request.toppings

            # Save updated pizza - events published automatically by repository
            await self.pizza_repository.update_async(pizza)

            # Map to DTO (with null-safety checks)
            pizza_dto = PizzaDto(
                id=pizza.id(),
                name=pizza.state.name or "",
                size=pizza.state.size.value if pizza.state.size else "",
                toppings=pizza.state.toppings,
                base_price=pizza.state.base_price or Decimal("0"),
                total_price=pizza.total_price,
            )

            return self.ok(pizza_dto)

        except Exception as e:
            return self.bad_request(f"Failed to update pizza: {str(e)}")
