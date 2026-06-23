import logging
from typing import Any

from classy_fastapi.decorators import get, post
from fastapi import Depends
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase

from api.controllers.oauth2_scheme import validate_token
from application.commands import SetUserInfoCommand
from application.queries import ReadUserInfoQuery
from integration.models import SetUserInfoCommandDto

log = logging.getLogger(__name__)


class UserController(ControllerBase):
    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        ControllerBase.__init__(self, service_provider, mapper, mediator)

    @post(
        "/info",
        response_model=Any,
        status_code=201,
        responses=ControllerBase.error_responses,
    )
    async def set_user_info(self, command_dto: SetUserInfoCommandDto, token: str = Depends(validate_token)) -> Any:
        """Sets data of the userinfo.json file."""
        return self.process(await self.mediator.execute_async(self.mapper.map(command_dto, SetUserInfoCommand)))

    @get(
        "/info",
        response_model=Any,
        status_code=201,
        responses=ControllerBase.error_responses,
    )
    async def get_user_info(self) -> Any:
        """Gets data of the userinfo.json file."""
        return self.process(await self.mediator.execute_async(ReadUserInfoQuery()))
