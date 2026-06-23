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
from application.commands import ValidateExternalDependenciesCommand
from integration.models import (
    ExternalDependenciesHealthCheckResultDto,
    SelfHealthCheckResultDto,
)

log = logging.getLogger(__name__)


class AppController(ControllerBase):
    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        ControllerBase.__init__(self, service_provider, mapper, mediator)

    @post("/self/health", response_model=SelfHealthCheckResultDto, status_code=201, responses=ControllerBase.error_responses)
    async def ping(self) -> Any:
        """Validates whether the App is online."""
        res = OperationResult(title="HealthCheck", status=201, detail="The AI Gateway is online.")
        data = {"online": True, "detail": "The AI Gateway is online."}
        res.data = SelfHealthCheckResultDto(**data)
        return self.process(res)

    @post("/dependencies/health", response_model=ExternalDependenciesHealthCheckResultDto, status_code=201, responses=ControllerBase.error_responses)
    async def validate_external_dependencies(self, token: str = Depends(validate_token)) -> Any:
        """Validates whether the App's external dependencies (Keycloak, EventsGateway, ...) are online.

        **Requires valid JWT Token.**
        """
        return self.process(await self.mediator.execute_async(ValidateExternalDependenciesCommand()))
