import uuid

from typing import Dict, Any
from classy_fastapi import Routable
from fastapi import Response
from fastapi.routing import APIRoute
from neuroglia.core.operation_result import OperationResult
from neuroglia.core.problem_details import ProblemDetails
from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.serialization.json import JsonSerializer


def generate_unique_id_function(route: APIRoute) -> str | APIRoute:
    if route.tags and route.name:
        tag = str(route.tags[0])
        return f"{tag.lower()}_{route.name}"
    elif route.methods and route.name:
        method = str(route.methods.pop()).lower()
        name = route.name.lower()
        return f"{name}_{method}"
    else:
        method = str(route.methods.pop()).lower()
        name = route.name.lower()
        return f"{name}"


class ControllerBase(Routable):
    """Represents the base class of all API controllers"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        """Initializes a new ControllerBase"""
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.json_serializer = self.service_provider.get_required_service(JsonSerializer)
        self.name = self.__class__.__name__.replace("Controller", "").strip()
        super().__init__(
            prefix=f"/{self.name.lower()}",
            tags=[self.name],
            generate_unique_id_function=generate_unique_id_function,
        )

    service_provider: ServiceProviderBase
    """ Gets the current ServiceProviderBase """

    mapper: Mapper
    """ Gets the service used to map objects """

    mediator: Mediator
    """ Gets the service used to mediate calls """

    json_serializer: JsonSerializer

    name: str
    """ Gets/sets the name of the controller, which is used to configure the controller's router. Defaults to the lowercased name of the implementing controller class, excluding the term 'Controller' """

    def process(self, result: OperationResult):
        """Processes the specified operation result"""
        content = result.data if result.status >= 200 and result.status < 300 else result
        media_type = "application/json"
        if content is not None:
            content = self.json_serializer.serialize_to_text(content)
            media_type = "application/json"
        return Response(status_code=result.status, content=content, media_type=media_type)

    error_responses: Dict[int | str, Dict[str, Any]] | None = {
        400: {"model": ProblemDetails, "description": "Bad Request"},
        404: {"model": ProblemDetails, "description": "Not Found"},
        500: {"model": ProblemDetails, "description": "Internal Server Error"},
    }
