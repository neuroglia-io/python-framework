import logging
from typing import Any

from classy_fastapi.decorators import get, post
from fastapi import Depends
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.mvc.controller_base import ControllerBase

from api.controllers.oauth2_scheme import validate_token
from application.commands import TestHostScriptCommand
from application.queries import ReadTestFileFromHostQuery
from integration.models import TestHostScriptCommandDto

log = logging.getLogger(__name__)


class CustomController(ControllerBase):
    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        ControllerBase.__init__(self, service_provider, mapper, mediator)

    @post(
        "/test/shell_script_on_host.sh",
        response_model=Any,
        status_code=201,
        responses=ControllerBase.error_responses,
    )
    async def run_test_write_file_on_host(self, command_dto: TestHostScriptCommandDto, decoded_token: str = Depends(validate_token)) -> Any:
        """Runs ~/test_shell_script_on_host.sh -i {req.user_input} on the Docker Host and returns the output"""
        log.debug(f"Valid Token! {decoded_token}")
        return self.process(await self.mediator.execute_async(self.mapper.map(command_dto, TestHostScriptCommand)))

    @get(
        "/test/tmp/test.txt/read",
        response_model=Any,
        status_code=201,
        responses=ControllerBase.error_responses,
    )
    async def read_test_file_from_host(self) -> Any:
        """Reads a file from the Docker host."""
        return self.process(await self.mediator.execute_async(ReadTestFileFromHostQuery()))
