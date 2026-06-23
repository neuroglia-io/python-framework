from typing import List

from neuroglia.mvc import ControllerBase
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from classy_fastapi import get

from api.dtos import KitchenStatusDto, OrderDto
from application.queries import GetKitchenStatusQuery, GetOrdersByStatusQuery


class KitchenController(ControllerBase):
    """Mario's kitchen management endpoints"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    @get("/status", response_model=KitchenStatusDto, responses=ControllerBase.error_responses)
    async def get_kitchen_status(self):
        """Get current kitchen status and capacity"""
        query = GetKitchenStatusQuery()
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/queue", response_model=List[OrderDto], responses=ControllerBase.error_responses)
    async def get_cooking_queue(self):
        """Get orders currently being cooked"""
        query = GetOrdersByStatusQuery(status="cooking")
        result = await self.mediator.execute_async(query)
        return self.process(result)
