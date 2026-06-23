"""Get Kitchen Status Query and Handler for Mario's Pizzeria"""

from dataclasses import dataclass

from api.dtos import KitchenStatusDto
from domain.repositories import IKitchenRepository

from neuroglia.core import OperationResult
from neuroglia.mapping import Mapper
from neuroglia.mediation import Query, QueryHandler


@dataclass
class GetKitchenStatusQuery(Query[OperationResult[KitchenStatusDto]]):
    """Query to get current kitchen status and capacity"""


class GetKitchenStatusQueryHandler(QueryHandler[GetKitchenStatusQuery, OperationResult[KitchenStatusDto]]):
    """Handler for getting kitchen status"""

    def __init__(self, kitchen_repository: IKitchenRepository, mapper: Mapper):
        self.kitchen_repository = kitchen_repository
        self.mapper = mapper

    async def handle_async(self, request: GetKitchenStatusQuery) -> OperationResult[KitchenStatusDto]:
        try:
            kitchen = await self.kitchen_repository.get_kitchen_state_async()

            # Create KitchenStatusDto manually for now
            kitchen_dto = KitchenStatusDto(
                pending_orders=[],  # TODO: Get actual pending orders
                cooking_orders=[],  # TODO: Get actual cooking orders
                ready_orders=[],  # TODO: Get actual ready orders
                total_pending=0,
                total_cooking=len(kitchen.active_orders),
                total_ready=0,
                average_wait_time_minutes=15.0,  # Default estimate
            )
            return self.ok(kitchen_dto)

        except Exception as e:
            return self.bad_request(f"Failed to get kitchen status: {str(e)}")
