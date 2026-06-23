"""API Controller for delivery operations"""

from api.dtos import OrderDto
from application.commands import AssignOrderToDeliveryCommand
from application.queries import GetOrdersByStatusQuery
from classy_fastapi import get, post
from pydantic import BaseModel

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase


class AssignOrderRequest(BaseModel):
    """Request model for assigning order to delivery"""

    delivery_person_id: str


class DeliveryController(ControllerBase):
    """Delivery management endpoints for the API"""

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mapper: Mapper,
        mediator: Mediator,
    ):
        super().__init__(service_provider, mapper, mediator)

    @get("/ready", responses=ControllerBase.error_responses)
    async def get_ready_orders(self):
        """Get all orders ready for delivery"""
        query = GetOrdersByStatusQuery(status="ready")
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @post("/{order_id}/assign", response_model=OrderDto, responses=ControllerBase.error_responses)
    async def assign_order(self, order_id: str, request: AssignOrderRequest):
        """Assign order to a delivery person"""
        command = AssignOrderToDeliveryCommand(order_id=order_id, delivery_person_id=request.delivery_person_id)
        result = await self.mediator.execute_async(command)
        return self.process(result)
