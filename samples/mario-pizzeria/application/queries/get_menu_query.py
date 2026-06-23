"""Get Menu Query and Handler for Mario's Pizzeria"""

from dataclasses import dataclass
from typing import List

from api.dtos import PizzaDto
from domain.repositories import IPizzaRepository

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetMenuQuery(Query[OperationResult[List[PizzaDto]]]):
    """Query to get the complete pizza menu"""


class GetMenuQueryHandler(QueryHandler[GetMenuQuery, OperationResult[List[PizzaDto]]]):
    """Handler for getting the pizza menu"""

    def __init__(self, pizza_repository: IPizzaRepository, mapper: Mapper):
        self.pizza_repository = pizza_repository
        self.mapper = mapper

    async def handle_async(self, request: GetMenuQuery) -> OperationResult[list[PizzaDto]]:
        try:
            pizzas = await self.pizza_repository.get_available_pizzas_async()
            # Pizza is an AggregateRoot, manually map from pizza.state
            pizza_dtos = [
                PizzaDto(
                    id=pizza.id(),
                    name=pizza.state.name,
                    size=pizza.state.size.value,
                    toppings=pizza.state.toppings,
                    base_price=pizza.state.base_price,
                    total_price=pizza.total_price,
                )
                for pizza in pizzas
            ]
            return self.ok(pizza_dtos)

        except Exception as e:
            return self.bad_request(f"Failed to get menu: {str(e)}")
