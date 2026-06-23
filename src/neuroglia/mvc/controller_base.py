from typing import TYPE_CHECKING, Any, Dict

from classy_fastapi import Routable
from fastapi import Response
from fastapi.routing import APIRoute

from neuroglia.core.operation_result import OperationResult
from neuroglia.core.problem_details import ProblemDetails
from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator

if TYPE_CHECKING:
    from neuroglia.serialization.json import JsonSerializer


def generate_unique_id_function(route: APIRoute) -> str | APIRoute:
    """
    Generates unique operation IDs for OpenAPI documentation from FastAPI routes.

    This function creates consistent, predictable operation IDs for API endpoints
    based on controller tags, route names, and HTTP methods, improving OpenAPI
    documentation quality and client SDK generation.

    Args:
        route (APIRoute): The FastAPI route to generate an ID for

    Returns:
        str | APIRoute: Unique operation ID string or the route itself

    Examples:
        ```python
        # Route: GET /users/{id} with tag "Users" and name "get_user"
        # Generated ID: "users_get_user"

        # Route: POST /orders with tag "Orders" and name "create_order"
        # Generated ID: "orders_create_order"

        # Route: PUT /products/{id} with name "update_product"
        # Generated ID: "update_product_put"
        ```

    Note:
        This function is automatically applied to all ControllerBase routes
        to ensure consistent OpenAPI operation ID generation.
    """
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
    """
    Represents the abstraction for all API controllers in the MVC pattern implementation.

    This abstraction provides a foundation for building type-safe, auto-discoverable REST API
    controllers with integrated dependency injection, CQRS mediation, object mapping, and
    consistent error handling following FastAPI conventions.

    Key Features:
        - Automatic route prefix generation from controller name
        - Integrated dependency injection container access
        - Built-in CQRS mediator for command/query processing
        - Automatic object mapping between DTOs and domain entities
        - Consistent OperationResult processing and HTTP response handling
        - OpenAPI documentation generation with error response schemas

    Attributes:
        service_provider (ServiceProviderBase): Dependency injection container
        mapper (Mapper): Object-to-object mapping service
        mediator (Mediator): CQRS command/query dispatcher
        json_serializer (JsonSerializer): JSON serialization service
        name (str): Controller name used for routing (auto-generated from class name)
        error_responses (Dict): Standard HTTP error response schemas for OpenAPI

    Examples:
        ```python
        from classy_fastapi.decorators import get, post, put, delete

        class UsersController(ControllerBase):
            # Automatic route prefix: /users
            # Automatic tags: ["Users"]

            @get("/{user_id}", response_model=UserDto)
            async def get_user(self, user_id: str) -> UserDto:
                query = GetUserByIdQuery(user_id=user_id)
                result = await self.mediator.execute_async(query)
                return self.process(result)

            @post("/", response_model=UserDto, status_code=201)
            async def create_user(self, create_user_dto: CreateUserDto) -> UserDto:
                command = self.mapper.map(create_user_dto, CreateUserCommand)
                result = await self.mediator.execute_async(command)
                return self.process(result)

            @put("/{user_id}", response_model=UserDto)
            async def update_user(self, user_id: str, update_user_dto: UpdateUserDto) -> UserDto:
                command = UpdateUserCommand(user_id=user_id, **update_user_dto.dict())
                result = await self.mediator.execute_async(command)
                return self.process(result)

            @delete("/{user_id}", status_code=204)
            async def delete_user(self, user_id: str) -> None:
                command = DeleteUserCommand(user_id=user_id)
                result = await self.mediator.execute_async(command)
                return self.process(result)

        # Custom controller with different prefix
        class AdminUsersController(ControllerBase):
            def __init__(self, service_provider, mapper, mediator):
                super().__init__(service_provider, mapper, mediator)
                # Override default prefix
                self.prefix = "/admin/users"
        ```

    Architecture:
        ```
        HTTP Request -> FastAPI -> Controller -> Mediator -> Handler -> Repository
                    ^                      ^           ^          ^
                    |                      |           |          |
                Auto Routes          DTO Mapping  CQRS Logic  Data Access
        ```

    See Also:
        - MVC Controllers: https://bvandewe.github.io/pyneuro/features/mvc-controllers/
        - CQRS Integration: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Object Mapping: https://bvandewe.github.io/pyneuro/features/object-mapping/
        - Getting Started: https://bvandewe.github.io/pyneuro/getting-started/
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        """
        Initializes a new controller instance with dependency injection and routing configuration.

        Args:
            service_provider (ServiceProviderBase): The dependency injection container
            mapper (Mapper): Object mapping service for DTO/entity transformations
            mediator (Mediator): CQRS mediator for command/query dispatch

        Note:
            Controllers are automatically discovered and registered by the framework.
            The constructor parameters are injected automatically when using
            the standard application builder configuration.
        """
        # Late import to avoid circular dependency
        from neuroglia.serialization.json import JsonSerializer

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

    json_serializer: "JsonSerializer"

    name: str
    """ Gets/sets the name of the controller, which is used to configure the controller's router. Defaults to the lowercased name of the implementing controller class, excluding the term 'Controller' """

    def process(self, result: OperationResult):
        """
        Processes an OperationResult into a proper HTTP response with status codes and serialization.

        This method handles the conversion from CQRS operation results to HTTP responses,
        including proper status code mapping, content serialization, and media type setting.

        Args:
            result (OperationResult): The operation result from a command or query handler

        Returns:
            Response: FastAPI Response object with appropriate status code and content

        Examples:
            ```python
            @get("/{id}")
            async def get_item(self, id: str):
                query = GetItemByIdQuery(id=id)
                result = await self.mediator.execute_async(query)
                return self.process(result)  # Converts to HTTP response

            # For success (200): Returns result.data as JSON
            # For errors (4xx/5xx): Returns full OperationResult as JSON
            ```
        """
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
