# import httpx
import logging
from typing import Any

from classy_fastapi.decorators import get, post
from fastapi import Depends
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase

from api.controllers.oauth2_scheme import validate_token
from application.commands import SetHostInfoCommand, SetHostLockCommand, SetHostUnlockCommand
from application.queries import ReadHostInfoQuery, IsHostLockedQuery
from application.settings import DesktopControllerSettings
from integration.models import SetHostInfoCommandDto

log = logging.getLogger(__name__)


class HostController(ControllerBase):
    app_settings: DesktopControllerSettings

    def __init__(self, app_settings: DesktopControllerSettings, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        self.app_settings = app_settings
        ControllerBase.__init__(self, service_provider, mapper, mediator)

    @get("/info", response_model=Any, status_code=200, responses=ControllerBase.error_responses)
    async def get_host_info(self):
        log.debug(f"get_host_info")
        return self.process(await self.mediator.execute_async(ReadHostInfoQuery()))

    @post("/info", response_model=Any, status_code=201, responses=ControllerBase.error_responses)
    async def set_host_info(self, command_dto: SetHostInfoCommandDto, token: str = Depends(validate_token)) -> Any:
        """Sets data of the hostinfo.json file and resets the state to PENDING."""
        log.debug(f"set_host_info: command_dto:{command_dto}, token={token}")
        return self.process(await self.mediator.execute_async(self.mapper.map(command_dto, SetHostInfoCommand)))

    @post("/lock", response_model=Any, status_code=201, responses=ControllerBase.error_responses)
    async def set_host_lock(self, token: str = Depends(validate_token)) -> Any:
        """Lock VDI desktop."""
        log.debug(f"set_host_lock: token={token}")
        return self.process(await self.mediator.execute_async(SetHostLockCommand()))

    @post("/unlock", response_model=Any, status_code=201, responses=ControllerBase.error_responses)
    async def set_host_unlock(self, token: str = Depends(validate_token)) -> Any:
        """Unlock VDI desktop."""
        log.debug(f"set_host_unlock: token={token}")
        return self.process(await self.mediator.execute_async(SetHostUnlockCommand()))

    @get("/is_locked", response_model=Any, status_code=200, responses=ControllerBase.error_responses)
    async def is_host_locked(self, token: str = Depends(validate_token)):
        query = IsHostLockedQuery()
        log.debug(f"get_host_is_locked: query:{query}, token={token}")
        return self.process(await self.mediator.execute_async(query))
