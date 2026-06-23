from typing import List

from api.dtos import PizzaDto
from application.commands import AddPizzaCommand, RemovePizzaCommand, UpdatePizzaCommand
from application.queries import GetMenuQuery
from classy_fastapi import delete, get, post, put

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase


class MenuController(ControllerBase):
    """Mario's pizza menu management endpoints"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/", response_model=List[PizzaDto], responses=ControllerBase.error_responses)
    async def get_menu(self):
        """Get the complete pizza menu"""
        return self.process(await self.mediator.execute_async(GetMenuQuery()))

    @get("/pizzas", response_model=List[PizzaDto], responses=ControllerBase.error_responses)
    async def get_pizzas(self):
        """Get available pizzas (alias for menu)"""
        return await self.get_menu()

    @post("/add", response_model=PizzaDto, status_code=201, responses=ControllerBase.error_responses)
    async def add_pizza(self, command: AddPizzaCommand):
        """Add a new pizza to the menu"""
        return self.process(await self.mediator.execute_async(command))

    @put("/update", response_model=PizzaDto, responses=ControllerBase.error_responses)
    async def update_pizza(self, command: UpdatePizzaCommand):
        """Update an existing pizza on the menu"""
        return self.process(await self.mediator.execute_async(command))

    @delete("/remove", status_code=204, responses=ControllerBase.error_responses)
    async def remove_pizza(self, command: RemovePizzaCommand):
        """Remove a pizza from the menu"""
        result = await self.mediator.execute_async(command)
        return self.process(result)
