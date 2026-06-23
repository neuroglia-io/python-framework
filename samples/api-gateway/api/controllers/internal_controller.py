import logging
from typing import Any

from classy_fastapi.decorators import post
from fastapi import Depends
from neuroglia.core import OperationResult
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase

from api.controllers.oauth2_scheme import validate_token
from application.commands.record_prompt_response_command import RecordPromptResponseCommand
from integration.models import RecordPromptResponseCommandDto

log = logging.getLogger(__name__)


class InternalController(ControllerBase):
    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        ControllerBase.__init__(self, service_provider, mapper, mediator)

    @post("/callback", response_model=Any, status_code=201, responses=ControllerBase.error_responses)
    async def submit_prompt_response(self, command_dto: RecordPromptResponseCommandDto, token: str = Depends(validate_token)) -> Any:
        """Handles callbacks from internal services.

        **Requires valid JWT Token.**
        """
        return self.process(await self.mediator.execute_async(self.mapper.map(command_dto, RecordPromptResponseCommand)))  # type: ignore
