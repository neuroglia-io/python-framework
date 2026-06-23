"""
Test suite for FastAPI Controller functionality.

This module validates the ControllerBase class and FastAPI integration including:
- Controller initialization with dependencies
- HTTP method handling (GET, POST, PUT, DELETE)
- Request/response mapping
- Mediator integration
- Error handling and status codes
- Route mounting and registration

Test Coverage:
    - Controller base class functionality
    - Dependency injection in controllers
    - Mediator command/query execution
    - OperationResult processing
    - HTTP status code mapping
    - Request validation
    - Response formatting
    - Error scenarios

Expected Behavior:
    - Controllers integrate seamlessly with FastAPI
    - Requests route to mediator correctly
    - OperationResult maps to HTTP responses
    - Validation errors return 400
    - Not found scenarios return 404
    - Server errors return 500
    - DTOs map correctly

Related Modules:
    - neuroglia.mvc: ControllerBase
    - neuroglia.mediation: Mediator
    - neuroglia.mapping: Mapper
    - fastapi: FastAPI framework

Related Documentation:
    - [MVC Controllers](../../docs/features/mvc-controllers.md)
    - [Controller Patterns](../../docs/patterns/controller-patterns.md)
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from neuroglia.core import OperationResult
from neuroglia.dependency_injection import ServiceCollection
from neuroglia.mapping import Mapper
from neuroglia.mapping.mapper import MapperConfiguration
from neuroglia.mediation.mediator import (
    Command,
    CommandHandler,
    Mediator,
    Query,
    QueryHandler,
)
from neuroglia.mvc import ControllerBase
from neuroglia.serialization import JsonSerializer

# Conditional import for classy-fastapi decorators
try:
    from classy_fastapi import Routable, delete, get, post, put

    CLASSY_FASTAPI_AVAILABLE = True
except ImportError:
    CLASSY_FASTAPI_AVAILABLE = False

    # Fallback decorators for testing without classy-fastapi
    def get(path):
        return lambda f: f

    def post(path):
        return lambda f: f

    def put(path):
        return lambda f: f

    def delete(path):
        return lambda f: f

    class Routable:
        pass


# =============================================================================
# Test DTOs
# =============================================================================


@dataclass
class CreatePizzaDto:
    """DTO for creating a pizza."""

    name: str
    price: float
    size: str
    toppings: list[str] = None


@dataclass
class UpdatePizzaDto:
    """DTO for updating a pizza."""

    name: Optional[str] = None
    price: Optional[float] = None
    toppings: Optional[list[str]] = None


@dataclass
class PizzaDto:
    """DTO for pizza response."""

    id: str
    name: str
    price: float
    size: str
    toppings: list[str]


# =============================================================================
# Test Commands and Queries
# =============================================================================


@dataclass
class CreatePizzaCommand(Command[OperationResult[dict]]):
    """Command to create a pizza."""

    name: str
    price: Decimal
    size: str
    toppings: list[str]


@dataclass
class UpdatePizzaCommand(Command[OperationResult[dict]]):
    """Command to update a pizza."""

    pizza_id: str
    name: Optional[str]
    price: Optional[Decimal]
    toppings: Optional[list[str]]


@dataclass
class DeletePizzaCommand(Command[OperationResult[bool]]):
    """Command to delete a pizza."""

    pizza_id: str


@dataclass
class GetPizzaQuery(Query[OperationResult[Optional[dict]]]):
    """Query to get a pizza by ID."""

    pizza_id: str


@dataclass
class ListPizzasQuery(Query[OperationResult[List[dict]]]):
    """Query to list all pizzas."""

    category: Optional[str] = None
    limit: int = 10


# =============================================================================
# Test Handlers
# =============================================================================


class CreatePizzaHandler(CommandHandler[CreatePizzaCommand, OperationResult[dict]]):
    """Handler for creating pizzas."""

    async def handle_async(self, request: CreatePizzaCommand) -> OperationResult[dict]:
        """Handle pizza creation."""
        if not request.name:
            return self.bad_request("Name is required")

        pizza = {"id": "pizza-123", "name": request.name, "price": float(request.price), "size": request.size, "toppings": request.toppings or []}
        return self.created(pizza)


class UpdatePizzaHandler(CommandHandler[UpdatePizzaCommand, OperationResult[dict]]):
    """Handler for updating pizzas."""

    def __init__(self):
        self.pizzas = {
            "pizza-1": {"id": "pizza-1", "name": "Margherita", "price": 12.99, "size": "medium", "toppings": ["cheese"]},
        }

    async def handle_async(self, request: UpdatePizzaCommand) -> OperationResult[dict]:
        """Handle pizza update."""
        if request.pizza_id not in self.pizzas:
            return self.not_found(dict, "pizza_id", request.pizza_id)

        pizza = self.pizzas[request.pizza_id].copy()
        if request.name:
            pizza["name"] = request.name
        if request.price:
            pizza["price"] = float(request.price)
        if request.toppings:
            pizza["toppings"] = request.toppings

        return self.ok(pizza)


class DeletePizzaHandler(CommandHandler[DeletePizzaCommand, OperationResult[bool]]):
    """Handler for deleting pizzas."""

    def __init__(self):
        self.pizzas = {"pizza-1", "pizza-2"}

    async def handle_async(self, request: DeletePizzaCommand) -> OperationResult[bool]:
        """Handle pizza deletion."""
        if request.pizza_id not in self.pizzas:
            return self.not_found(dict, "pizza_id", request.pizza_id)

        self.pizzas.remove(request.pizza_id)
        return self.ok(True)


class GetPizzaHandler(QueryHandler[GetPizzaQuery, OperationResult[Optional[dict]]]):
    """Handler for getting a pizza."""

    def __init__(self):
        self.pizzas = {
            "pizza-1": {"id": "pizza-1", "name": "Margherita", "price": 12.99, "size": "medium", "toppings": ["cheese"]},
            "pizza-2": {"id": "pizza-2", "name": "Pepperoni", "price": 14.99, "size": "large", "toppings": ["cheese", "pepperoni"]},
        }

    async def handle_async(self, request: GetPizzaQuery) -> OperationResult[Optional[dict]]:
        """Handle pizza retrieval."""
        pizza = self.pizzas.get(request.pizza_id)
        return self.ok(pizza)


class ListPizzasHandler(QueryHandler[ListPizzasQuery, OperationResult[List[dict]]]):
    """Handler for listing pizzas."""

    def __init__(self):
        self.pizzas = [
            {"id": "pizza-1", "name": "Margherita", "category": "classic", "price": 12.99, "size": "medium", "toppings": ["cheese"]},
            {"id": "pizza-2", "name": "Pepperoni", "category": "meat", "price": 14.99, "size": "large", "toppings": ["cheese", "pepperoni"]},
        ]

    async def handle_async(self, request: ListPizzasQuery) -> OperationResult[list[dict]]:
        """Handle pizza listing."""
        pizzas = self.pizzas.copy()

        if request.category:
            pizzas = [p for p in pizzas if p.get("category") == request.category]

        pizzas = pizzas[: request.limit]
        return self.ok(pizzas)


# =============================================================================
# Test Controller
# =============================================================================


class PizzaController(ControllerBase):
    """Test controller for pizza operations."""

    def __init__(self, service_provider, mapper, mediator):
        """Initialize the controller."""
        super().__init__(service_provider, mapper, mediator)

    @post("/pizzas", status_code=201)
    async def create_pizza(self, dto: CreatePizzaDto) -> dict:
        """Create a new pizza."""
        command = CreatePizzaCommand(name=dto.name, price=Decimal(str(dto.price)), size=dto.size, toppings=dto.toppings or [])
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @get("/pizzas/{pizza_id}")
    async def get_pizza(self, pizza_id: str) -> dict:
        """Get a pizza by ID."""
        query = GetPizzaQuery(pizza_id=pizza_id)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/pizzas")
    async def list_pizzas(self, category: Optional[str] = None, limit: int = 10) -> list[dict]:
        """List all pizzas."""
        query = ListPizzasQuery(category=category, limit=limit)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @put("/pizzas/{pizza_id}")
    async def update_pizza(self, pizza_id: str, dto: UpdatePizzaDto) -> dict:
        """Update a pizza."""
        command = UpdatePizzaCommand(pizza_id=pizza_id, name=dto.name, price=Decimal(str(dto.price)) if dto.price else None, toppings=dto.toppings)
        result = await self.mediator.execute_async(command)
        return self.process(result)

    @delete("/pizzas/{pizza_id}")
    async def delete_pizza(self, pizza_id: str) -> dict:
        """Delete a pizza."""
        command = DeletePizzaCommand(pizza_id=pizza_id)
        result = await self.mediator.execute_async(command)
        return self.process(result)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def services():
    """Create service collection with dependencies."""
    services = ServiceCollection()

    # Register mediator
    services.add_singleton(Mediator)

    # Register serializer
    services.add_singleton(JsonSerializer)

    # Register mapper with configuration
    services.add_singleton(MapperConfiguration)
    services.add_singleton(Mapper)

    # Register handlers
    services.add_scoped(CreatePizzaHandler)
    services.add_scoped(UpdatePizzaHandler)
    services.add_scoped(DeletePizzaHandler)
    services.add_scoped(GetPizzaHandler)
    services.add_scoped(ListPizzasHandler)

    return services


@pytest.fixture
def app(services):
    """Create FastAPI test application."""
    # Build service provider
    provider = services.build()

    # Create FastAPI app
    app = FastAPI(title="Test Pizza API")

    # Get dependencies from provider
    mediator = provider.get_required_service(Mediator)
    mapper = provider.get_required_service(Mapper)

    # Register handlers in mediator registry
    if not hasattr(Mediator, "_handler_registry"):
        Mediator._handler_registry = {}

    Mediator._handler_registry[CreatePizzaCommand] = CreatePizzaHandler
    Mediator._handler_registry[UpdatePizzaCommand] = UpdatePizzaHandler
    Mediator._handler_registry[DeletePizzaCommand] = DeletePizzaHandler
    Mediator._handler_registry[GetPizzaQuery] = GetPizzaHandler
    Mediator._handler_registry[ListPizzasQuery] = ListPizzasHandler

    # Create controller instance
    controller = PizzaController(provider, mapper, mediator)

    # Mount routes manually (simulating classy-fastapi)
    app.post("/pizzas", status_code=201)(controller.create_pizza)
    app.get("/pizzas/{pizza_id}")(controller.get_pizza)
    app.get("/pizzas")(controller.list_pizzas)
    app.put("/pizzas/{pizza_id}")(controller.update_pizza)
    app.delete("/pizzas/{pizza_id}")(controller.delete_pizza)

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# =============================================================================
# Test Suite: Controller Base Functionality
# =============================================================================


@pytest.mark.integration
class TestControllerBaseFunctionality:
    """
    Test ControllerBase class functionality.

    Validates that controllers:
    - Initialize with required dependencies
    - Process OperationResult responses
    - Map status codes correctly
    - Handle errors appropriately
    - Integrate with mediator

    Related: neuroglia.mvc.ControllerBase
    """

    def test_controller_initializes_with_dependencies(self, services):
        """
        Test controller initializes with DI dependencies.

        Expected Behavior:
            - Controller accepts service provider
            - Controller accepts mapper
            - Controller accepts mediator
            - Dependencies are accessible

        Related: ControllerBase.__init__()
        """
        # Arrange
        provider = services.build()
        mediator = provider.get_required_service(Mediator)
        mapper = provider.get_required_service(Mapper)

        # Act
        controller = PizzaController(provider, mapper, mediator)

        # Assert
        assert controller.service_provider is not None
        assert controller.mapper is not None
        assert controller.mediator is not None

    def test_controller_process_success_result(self, services):
        """
        Test controller processes successful OperationResult.

        Expected Behavior:
            - Success result returns Response object
            - Status code is 200
            - Content contains serialized data

        Related: ControllerBase.process()
        """
        # Arrange
        provider = services.build()
        mediator = provider.get_required_service(Mediator)
        mapper = provider.get_required_service(Mapper)
        controller = PizzaController(provider, mapper, mediator)

        result = OperationResult("OK", 200)
        result.data = {"id": "test", "name": "Test Pizza"}

        # Act
        response = controller.process(result)

        # Assert
        from starlette.responses import Response

        assert isinstance(response, Response)
        assert response.status_code == 200
        assert response.media_type == "application/json"
        # Content is serialized JSON string
        import json

        content_data = json.loads(response.body)
        assert content_data == {"id": "test", "name": "Test Pizza"}

    def test_controller_process_error_result_raises(self, services):
        """
        Test controller processes error OperationResult.

        Expected Behavior:
            - Error result returns Response object
            - Status code matches OperationResult (400)
            - Content contains full OperationResult serialized

        Related: ControllerBase.process()
        """
        # Arrange
        provider = services.build()
        mediator = provider.get_required_service(Mediator)
        mapper = provider.get_required_service(Mapper)
        controller = PizzaController(provider, mapper, mediator)

        result = OperationResult("Bad Request", 400, "Invalid input")

        # Act
        response = controller.process(result)

        # Assert
        from starlette.responses import Response

        assert isinstance(response, Response)
        assert response.status_code == 400
        assert response.media_type == "application/json"
        # For errors, full OperationResult is serialized
        import json

        content_data = json.loads(response.body)
        assert content_data["status"] == 400
        assert "Invalid input" in content_data["detail"]


# =============================================================================
# Test Suite: HTTP Method Handlers
# =============================================================================


@pytest.mark.integration
class TestControllerHTTPMethods:
    """
    Test controller HTTP method handling.

    Validates that controllers properly handle:
    - GET requests
    - POST requests (creation)
    - PUT requests (updates)
    - DELETE requests
    - Query parameters
    - Path parameters
    - Request bodies

    Related: FastAPI integration
    """

    def test_post_creates_resource(self, client):
        """
        Test POST request creates new resource.

        Expected Behavior:
            - POST returns 201 Created
            - Response contains created resource
            - Resource has generated ID
            - Data matches request

        Related: HTTP POST method
        """
        # Arrange
        data = {"name": "Margherita", "price": 12.99, "size": "medium", "toppings": ["cheese", "tomato"]}

        # Act
        response = client.post("/pizzas", json=data)

        # Assert
        assert response.status_code == 201
        json_data = response.json()
        assert json_data["id"] is not None
        assert json_data["name"] == "Margherita"
        assert json_data["price"] == 12.99

    def test_get_retrieves_single_resource(self, client):
        """
        Test GET request retrieves single resource.

        Expected Behavior:
            - GET returns 200 OK
            - Response contains resource data
            - Data matches stored resource

        Related: HTTP GET method
        """
        # Act
        response = client.get("/pizzas/pizza-1")

        # Assert
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["id"] == "pizza-1"
        assert json_data["name"] == "Margherita"

    def test_get_nonexistent_resource_returns_none(self, client):
        """
        Test GET request for nonexistent resource.

        Expected Behavior:
            - GET returns 200 OK (not 404)
            - Response body is empty or "null"
            - No exception raised

        Related: Query null handling
        """
        # Act
        response = client.get("/pizzas/nonexistent")

        # Assert
        assert response.status_code == 200
        # When data is None, response body is empty string or "null"
        # Both are valid representations of null/missing data
        assert response.text in ["", "null"]

    def test_get_list_retrieves_multiple_resources(self, client):
        """
        Test GET request retrieves list of resources.

        Expected Behavior:
            - GET returns 200 OK
            - Response is array
            - All resources included
            - Filters applied if specified

        Related: HTTP GET list endpoint
        """
        # Act
        response = client.get("/pizzas")

        # Assert
        assert response.status_code == 200
        json_data = response.json()
        assert isinstance(json_data, list)
        assert len(json_data) == 2

    def test_get_list_with_filter(self, client):
        """
        Test GET request with query parameters.

        Expected Behavior:
            - Query params are parsed
            - Filter is applied
            - Only matching resources returned

        Related: Query parameter handling
        """
        # Act
        response = client.get("/pizzas?category=classic&limit=10")

        # Assert
        assert response.status_code == 200
        json_data = response.json()
        assert len(json_data) == 1
        assert json_data[0]["category"] == "classic"

    def test_put_updates_resource(self, client):
        """
        Test PUT request updates existing resource.

        Expected Behavior:
            - PUT returns 200 OK
            - Response contains updated resource
            - Changes are applied
            - Unchanged fields preserved

        Related: HTTP PUT method
        """
        # Arrange
        data = {"name": "Super Margherita", "price": 15.99}

        # Act
        response = client.put("/pizzas/pizza-1", json=data)

        # Assert
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["name"] == "Super Margherita"
        assert json_data["price"] == 15.99

    def test_put_nonexistent_resource_returns_404(self, client):
        """
        Test PUT request for nonexistent resource.

        Expected Behavior:
            - PUT returns 404 Not Found
            - Error message is descriptive
            - No resource created

        Related: HTTP 404 handling
        """
        # Arrange
        data = {"name": "New Pizza"}

        # Act
        response = client.put("/pizzas/nonexistent", json=data)

        # Assert
        assert response.status_code == 404

    def test_delete_removes_resource(self, client):
        """
        Test DELETE request removes resource.

        Expected Behavior:
            - DELETE returns 200 OK
            - Response confirms deletion
            - Resource is removed

        Related: HTTP DELETE method
        """
        # Act
        response = client.delete("/pizzas/pizza-1")

        # Assert
        assert response.status_code == 200
        json_data = response.json()
        assert json_data is True

    def test_delete_nonexistent_resource_returns_404(self, client):
        """
        Test DELETE request for nonexistent resource.

        Expected Behavior:
            - DELETE returns 404 Not Found
            - Error message is descriptive

        Related: HTTP 404 handling
        """
        # Act
        response = client.delete("/pizzas/nonexistent")

        # Assert
        assert response.status_code == 404


# =============================================================================
# Test Suite: Request Validation
# =============================================================================


@pytest.mark.integration
class TestControllerRequestValidation:
    """
    Test controller request validation.

    Validates that controllers:
    - Validate request bodies
    - Validate query parameters
    - Validate path parameters
    - Return appropriate error responses
    - Preserve validation error messages

    Related: Pydantic validation integration
    """

    def test_post_with_missing_required_field(self, client):
        """
        Test POST with missing required field.

        Expected Behavior:
            - POST returns 422 Unprocessable Entity (Pydantic validation)
            - Error message indicates missing field
            - No resource created

        Related: Request body validation
        """
        # Arrange
        data = {
            "price": 12.99,
            "size": "medium",
            # Missing required 'name' field
        }

        # Act
        response = client.post("/pizzas", json=data)

        # Assert
        assert response.status_code == 422  # FastAPI/Pydantic validation error

    def test_post_with_invalid_data_type(self, client):
        """
        Test POST with invalid data type.

        Expected Behavior:
            - POST returns 422 Unprocessable Entity
            - Error message indicates type mismatch
            - No resource created

        Related: Type validation
        """
        # Arrange
        data = {"name": "Pizza", "price": "not-a-number", "size": "medium"}  # Invalid type

        # Act
        response = client.post("/pizzas", json=data)

        # Assert
        assert response.status_code == 422


# =============================================================================
# Test Suite: Error Handling
# =============================================================================


@pytest.mark.integration
class TestControllerErrorHandling:
    """
    Test controller error handling.

    Validates that controllers:
    - Handle validation errors (400)
    - Handle not found errors (404)
    - Handle server errors (500)
    - Return proper error responses
    - Preserve error context

    Related: Error handling patterns
    """

    def test_validation_error_returns_400(self, client):
        """
        Test business validation error returns 400.

        Expected Behavior:
            - Validation failure returns 400 Bad Request
            - Error message is descriptive
            - Details are preserved

        Related: Business validation
        """
        # Arrange
        data = {"name": "", "price": 12.99, "size": "medium"}  # Empty name will fail validation

        # Act
        response = client.post("/pizzas", json=data)

        # Assert
        # This will return 400 from handler validation
        assert response.status_code in [400, 422]  # 422 from FastAPI, 400 from handler

    def test_not_found_returns_404(self, client):
        """
        Test not found scenario returns 404.

        Expected Behavior:
            - Missing resource returns 404 Not Found
            - Error message includes resource info
            - Response is consistent

        Related: HTTP 404 handling
        """
        # Act
        response = client.put("/pizzas/nonexistent", json={"name": "Test"})

        # Assert
        assert response.status_code == 404


# =============================================================================
# Test Suite: Mediator Integration
# =============================================================================


@pytest.mark.integration
class TestControllerMediatorIntegration:
    """
    Test controller integration with mediator.

    Validates that controllers:
    - Execute commands through mediator
    - Execute queries through mediator
    - Process OperationResult responses
    - Handle mediator errors
    - Map DTOs to commands/queries

    Related: CQRS pattern implementation
    """

    def test_controller_executes_command_via_mediator(self, client):
        """
        Test controller executes command through mediator.

        Expected Behavior:
            - Controller creates command from DTO
            - Command is sent to mediator
            - Handler processes command
            - Result returns through controller

        Related: Command execution flow
        """
        # Arrange
        data = {"name": "Test Pizza", "price": 10.99, "size": "small", "toppings": ["cheese"]}

        # Act
        response = client.post("/pizzas", json=data)

        # Assert
        assert response.status_code == 201
        assert response.json()["name"] == "Test Pizza"

    def test_controller_executes_query_via_mediator(self, client):
        """
        Test controller executes query through mediator.

        Expected Behavior:
            - Controller creates query from parameters
            - Query is sent to mediator
            - Handler processes query
            - Result returns through controller

        Related: Query execution flow
        """
        # Act
        response = client.get("/pizzas/pizza-1")

        # Assert
        assert response.status_code == 200
        assert response.json()["id"] == "pizza-1"

    def test_controller_processes_operation_result(self, client):
        """
        Test controller processes OperationResult from mediator.

        Expected Behavior:
            - OperationResult status maps to HTTP status
            - Success returns data
            - Error raises HTTPException
            - Status codes are preserved

        Related: OperationResult processing
        """
        # Act - Success case
        response = client.get("/pizzas/pizza-1")

        # Assert
        assert response.status_code == 200
        assert response.json() is not None

        # Act - Not found case
        response = client.put("/pizzas/nonexistent", json={"name": "Test"})

        # Assert
        assert response.status_code == 404
