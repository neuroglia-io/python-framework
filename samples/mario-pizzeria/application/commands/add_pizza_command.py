"""Add Pizza to Menu Command for Mario's Pizzeria"""

import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from api.dtos import PizzaDto
from domain.entities import Pizza, PizzaSize
from domain.repositories import IPizzaRepository

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mediation import Command, CommandHandler


@dataclass
class AddPizzaCommand(Command[OperationResult[PizzaDto]]):
    """Command to add a new pizza to the menu"""

    name: str
    base_price: Decimal
    size: str  # Will be converted to PizzaSize enum
    description: Optional[str] = None
    toppings: list[str] = None


class AddPizzaCommandHandler(CommandHandler[AddPizzaCommand, OperationResult[PizzaDto]]):
    """Handler for adding a new pizza to the menu"""

    def __init__(self, pizza_repository: IPizzaRepository, mapper: Mapper):
        self.pizza_repository = pizza_repository
        self.mapper = mapper

    async def handle_async(self, command: AddPizzaCommand) -> OperationResult[PizzaDto]:
        try:
            # Validate pizza name doesn't already exist
            existing_pizza = await self.pizza_repository.get_by_name_async(command.name)
            if existing_pizza:
                return self.bad_request(f"Pizza with name '{command.name}' already exists")

            # Validate base price
            if command.base_price <= 0:
                return self.bad_request("Base price must be greater than 0")

            # Convert size string to enum
            try:
                size_enum = PizzaSize[command.size.upper()]
            except KeyError:
                return self.bad_request(f"Invalid pizza size: {command.size}. Must be one of: {', '.join([s.name for s in PizzaSize])}")

            # Create new pizza entity
            pizza = Pizza(
                name=command.name,
                base_price=command.base_price,
                size=size_enum,
                description=command.description or "",
            )

            # Add toppings if provided
            if command.toppings:
                for topping in command.toppings:
                    pizza.add_topping(topping)

            # Save to repository - events published automatically
            await self.pizza_repository.add_async(pizza)

            # Map to DTO (with null-safety checks)
            pizza_dto = PizzaDto(
                id=pizza.id(),
                name=pizza.state.name or "",
                size=pizza.state.size.value if pizza.state.size else "",
                toppings=pizza.state.toppings,
                base_price=pizza.state.base_price or Decimal("0"),
                total_price=pizza.total_price,
            )

            # Artificial delay for testing/demo purposes
            await asyncio.sleep(3)

            return self.created(pizza_dto)

        except Exception as e:
            return self.bad_request(f"Failed to add pizza: {str(e)}")
