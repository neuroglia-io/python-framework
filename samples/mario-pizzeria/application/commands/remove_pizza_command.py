"""Remove Pizza from Menu Command for Mario's Pizzeria"""

from dataclasses import dataclass

from domain.repositories import IPizzaRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Command, CommandHandler


@dataclass
class RemovePizzaCommand(Command[OperationResult[bool]]):
    """Command to remove a pizza from the menu"""

    pizza_id: str


class RemovePizzaCommandHandler(CommandHandler[RemovePizzaCommand, OperationResult[bool]]):
    """Handler for removing a pizza from the menu"""

    def __init__(self, pizza_repository: IPizzaRepository):
        self.pizza_repository = pizza_repository

    async def handle_async(self, request: RemovePizzaCommand) -> OperationResult[bool]:
        try:
            # Get existing pizza
            pizza = await self.pizza_repository.get_async(request.pizza_id)
            if not pizza:
                return self.bad_request(f"Pizza with ID '{request.pizza_id}' not found")

            # Remove the pizza - events published automatically by repository
            await self.pizza_repository.remove_async(request.pizza_id)

            return self.ok(True)

        except Exception as e:
            return self.bad_request(f"Failed to remove pizza: {str(e)}")
