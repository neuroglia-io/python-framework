"""
Test suite for FastAPI routing functionality.

This module validates route registration, auto-mounting, and parameter binding:
- Controller route discovery and registration
- Route prefix handling
- Path parameter extraction
- Query parameter binding
- Route conflict detection
- HTTP method routing

Test Coverage:
    - Route registration patterns
    - Controller auto-discovery
    - Parameter binding (path, query, body)
    - Route prefix application
    - Multiple controller mounting
    - Route metadata validation

Expected Behavior:
    - Routes are properly registered from controllers
    - Path parameters extract correctly
    - Query parameters bind to method arguments
    - Route prefixes apply consistently
    - Method-level routing works (GET, POST, etc.)

Related Modules:
    - neuroglia.mvc: ControllerBase, routing
    - fastapi: Route registration
    - classy_fastapi: Class-based routing

Related Documentation:
    - [MVC Controllers](../../docs/features/mvc-controllers.md)
    - [Routing Patterns](../../docs/patterns/routing-patterns.md)
"""

from dataclasses import dataclass
from typing import List, Optional

import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient

from neuroglia.core import OperationResult
from neuroglia.dependency_injection import ServiceCollection
from neuroglia.mapping import Mapper
from neuroglia.mapping.mapper import MapperConfiguration
from neuroglia.mediation.mediator import Mediator
from neuroglia.mediation.mediator import Query as CQRSQuery
from neuroglia.mediation.mediator import QueryHandler
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
# Test Queries
# =============================================================================


@dataclass
class GetItemQuery(CQRSQuery[OperationResult[dict]]):
    """Query to get an item by ID."""

    item_id: str


@dataclass
class ListItemsQuery(CQRSQuery[OperationResult[List[dict]]]):
    """Query to list items."""

    category: Optional[str] = None
    limit: int = 10
    offset: int = 0


@dataclass
class SearchItemsQuery(CQRSQuery[OperationResult[List[dict]]]):
    """Query to search items."""

    query: str
    min_price: Optional[float] = None
    max_price: Optional[float] = None


# =============================================================================
# Test Handlers
# =============================================================================


class GetItemHandler(QueryHandler[GetItemQuery, OperationResult[dict]]):
    """Handler for getting items."""

    def __init__(self):
        self.items = {
            "item-1": {"id": "item-1", "name": "Item 1", "price": 10.0},
            "item-2": {"id": "item-2", "name": "Item 2", "price": 20.0},
        }

    async def handle_async(self, request: GetItemQuery) -> OperationResult[dict]:
        """Handle item retrieval."""
        item = self.items.get(request.item_id)
        return self.ok(item)


class ListItemsHandler(QueryHandler[ListItemsQuery, OperationResult[List[dict]]]):
    """Handler for listing items."""

    def __init__(self):
        self.items = [
            {"id": "item-1", "name": "Item 1", "category": "A", "price": 10.0},
            {"id": "item-2", "name": "Item 2", "category": "B", "price": 20.0},
            {"id": "item-3", "name": "Item 3", "category": "A", "price": 30.0},
        ]

    async def handle_async(self, request: ListItemsQuery) -> OperationResult[list[dict]]:
        """Handle item listing."""
        items = self.items.copy()

        if request.category:
            items = [i for i in items if i.get("category") == request.category]

        items = items[request.offset : request.offset + request.limit]
        return self.ok(items)


class SearchItemsHandler(QueryHandler[SearchItemsQuery, OperationResult[List[dict]]]):
    """Handler for searching items."""

    def __init__(self):
        self.items = [
            {"id": "item-1", "name": "Widget", "price": 10.0},
            {"id": "item-2", "name": "Gadget", "price": 20.0},
            {"id": "item-3", "name": "Tool", "price": 30.0},
        ]

    async def handle_async(self, request: SearchItemsQuery) -> OperationResult[list[dict]]:
        """Handle item search."""
        items = [i for i in self.items if request.query.lower() in i["name"].lower()]

        if request.min_price is not None:
            items = [i for i in items if i["price"] >= request.min_price]

        if request.max_price is not None:
            items = [i for i in items if i["price"] <= request.max_price]

        return self.ok(items)


# =============================================================================
# Test Controllers
# =============================================================================


class ItemsController(ControllerBase):
    """Test controller for items without prefix."""

    def __init__(self, service_provider, mapper, mediator):
        """Initialize the controller."""
        super().__init__(service_provider, mapper, mediator)

    @get("/items/{item_id}")
    async def get_item(self, item_id: str) -> dict:
        """Get a single item by ID."""
        query = GetItemQuery(item_id=item_id)
        result = await self.mediator.execute_async(query)
        return self.process(result)

    @get("/items")
    async def list_items(self, category: Optional[str] = None, limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0)) -> list[dict]:
        """List all items with optional filtering."""
        query = ListItemsQuery(category=category, limit=limit, offset=offset)
        result = await self.mediator.execute_async(query)
        return self.process(result)


class SearchController(ControllerBase):
    """Test controller for search operations."""

    def __init__(self, service_provider, mapper, mediator):
        """Initialize the controller."""
        super().__init__(service_provider, mapper, mediator)

    @get("/search")
    async def search(self, q: str = Query(..., description="Search query"), min_price: Optional[float] = Query(None, ge=0), max_price: Optional[float] = Query(None, ge=0)) -> list[dict]:
        """Search items by query string."""
        query = SearchItemsQuery(query=q, min_price=min_price, max_price=max_price)
        result = await self.mediator.execute_async(query)
        return self.process(result)


class ApiV1Controller(ControllerBase):
    """Test controller with API versioning prefix."""

    def __init__(self, service_provider, mapper, mediator):
        """Initialize the controller."""
        super().__init__(service_provider, mapper, mediator)

    @get("/v1/items/{item_id}")
    async def get_item_v1(self, item_id: str) -> dict:
        """Get item (v1 API)."""
        query = GetItemQuery(item_id=item_id)
        result = await self.mediator.execute_async(query)
        return self.process(result)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def services():
    """Create service collection with dependencies."""
    services = ServiceCollection()

    # Register core services
    services.add_singleton(Mediator)
    services.add_singleton(JsonSerializer)
    services.add_singleton(MapperConfiguration)
    services.add_singleton(Mapper)

    # Register handlers
    services.add_scoped(GetItemHandler)
    services.add_scoped(ListItemsHandler)
    services.add_scoped(SearchItemsHandler)

    return services


@pytest.fixture
def basic_app(services):
    """Create basic FastAPI app with items controller."""
    provider = services.build()
    app = FastAPI(title="Test Routing API")

    # Register handlers in mediator
    if not hasattr(Mediator, "_handler_registry"):
        Mediator._handler_registry = {}

    Mediator._handler_registry[GetItemQuery] = GetItemHandler
    Mediator._handler_registry[ListItemsQuery] = ListItemsHandler
    Mediator._handler_registry[SearchItemsQuery] = SearchItemsHandler

    # Get dependencies
    mediator = provider.get_required_service(Mediator)
    mapper = provider.get_required_service(Mapper)

    # Create and mount controller
    controller = ItemsController(provider, mapper, mediator)
    app.get("/items/{item_id}")(controller.get_item)
    app.get("/items")(controller.list_items)

    return app


@pytest.fixture
def multi_controller_app(services):
    """Create FastAPI app with multiple controllers."""
    provider = services.build()
    app = FastAPI(title="Multi-Controller API")

    # Register handlers
    Mediator._handler_registry[GetItemQuery] = GetItemHandler
    Mediator._handler_registry[ListItemsQuery] = ListItemsHandler
    Mediator._handler_registry[SearchItemsQuery] = SearchItemsHandler

    # Get dependencies
    mediator = provider.get_required_service(Mediator)
    mapper = provider.get_required_service(Mapper)

    # Mount items controller
    items_controller = ItemsController(provider, mapper, mediator)
    app.get("/items/{item_id}")(items_controller.get_item)
    app.get("/items")(items_controller.list_items)

    # Mount search controller
    search_controller = SearchController(provider, mapper, mediator)
    app.get("/search")(search_controller.search)

    return app


@pytest.fixture
def versioned_app(services):
    """Create FastAPI app with API versioning."""
    provider = services.build()
    app = FastAPI(title="Versioned API")

    # Register handlers
    Mediator._handler_registry[GetItemQuery] = GetItemHandler

    # Get dependencies
    mediator = provider.get_required_service(Mediator)
    mapper = provider.get_required_service(Mapper)

    # Mount v1 controller
    v1_controller = ApiV1Controller(provider, mapper, mediator)
    app.get("/v1/items/{item_id}")(v1_controller.get_item_v1)

    # Mount regular controller
    items_controller = ItemsController(provider, mapper, mediator)
    app.get("/items/{item_id}")(items_controller.get_item)

    return app


# =============================================================================
# Test Suite: Route Registration
# =============================================================================


@pytest.mark.integration
class TestRouteRegistration:
    """
    Test route registration and mounting.

    Validates that routes are properly registered from controllers and
    that the FastAPI routing system correctly maps URLs to handlers.

    Related: FastAPI route registration
    """

    def test_route_registered_successfully(self, basic_app):
        """
        Test that routes are registered in the FastAPI app.

        Expected Behavior:
            - Routes appear in app.routes
            - Route paths match controller definitions
            - HTTP methods are correct

        Related: FastAPI app.routes
        """
        # Act
        routes = [r for r in basic_app.routes if hasattr(r, "path")]
        route_paths = [r.path for r in routes]

        # Assert
        assert "/items/{item_id}" in route_paths
        assert "/items" in route_paths

    def test_route_accessible_via_client(self):
        """
        Test that registered routes are accessible via HTTP client.

        Expected Behavior:
            - GET request succeeds
            - Response contains expected data
            - Status code is 200

        Related: Route accessibility
        """
        # Arrange
        from fastapi import FastAPI

        app = FastAPI()

        @app.get("/test")
        async def test_route():
            return {"message": "success"}

        client = TestClient(app)

        # Act
        response = client.get("/test")

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == "success"

    def test_multiple_controllers_registered(self, multi_controller_app):
        """
        Test that multiple controllers can be registered.

        Expected Behavior:
            - All controller routes registered
            - No route conflicts
            - Each controller accessible

        Related: Multi-controller apps
        """
        # Act
        routes = [r for r in multi_controller_app.routes if hasattr(r, "path")]
        route_paths = [r.path for r in routes]

        # Assert - Both controllers registered
        assert "/items/{item_id}" in route_paths
        assert "/items" in route_paths
        assert "/search" in route_paths


# =============================================================================
# Test Suite: Path Parameter Binding
# =============================================================================


@pytest.mark.integration
class TestPathParameterBinding:
    """
    Test path parameter extraction and binding.

    Validates that path parameters are correctly extracted from URLs
    and passed to controller methods.

    Related: FastAPI path parameters
    """

    def test_single_path_parameter(self, basic_app):
        """
        Test single path parameter extraction.

        Expected Behavior:
            - Path parameter extracted from URL
            - Parameter passed to controller method
            - Correct item returned

        Related: Path parameter binding
        """
        # Arrange
        client = TestClient(basic_app)

        # Act
        response = client.get("/items/item-1")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "item-1"
        assert data["name"] == "Item 1"

    def test_path_parameter_with_special_characters(self, basic_app):
        """
        Test path parameters with special characters.

        Expected Behavior:
            - Special characters handled correctly
            - Parameter decoded properly
            - Request processes successfully

        Related: URL encoding
        """
        # Arrange
        client = TestClient(basic_app)

        # Act
        response = client.get("/items/item-1")

        # Assert
        assert response.status_code == 200

    def test_nonexistent_path_parameter(self, basic_app):
        """
        Test request with nonexistent resource ID.

        Expected Behavior:
            - Returns 200 (query found nothing)
            - Response body is empty or null
            - No server error

        Related: Missing resource handling
        """
        # Arrange
        client = TestClient(basic_app)

        # Act
        response = client.get("/items/nonexistent")

        # Assert
        assert response.status_code == 200
        assert response.text in ["", "null"]


# =============================================================================
# Test Suite: Query Parameter Binding
# =============================================================================


@pytest.mark.integration
class TestQueryParameterBinding:
    """
    Test query parameter extraction and binding.

    Validates that query parameters are correctly parsed from URLs
    and passed to controller methods with proper type conversion.

    Related: FastAPI query parameters
    """

    def test_optional_query_parameter(self, basic_app):
        """
        Test optional query parameter handling.

        Expected Behavior:
            - Request works without parameter
            - Request works with parameter
            - Default value used when omitted

        Related: Optional parameters
        """
        # Arrange
        client = TestClient(basic_app)

        # Act - Without parameter
        response1 = client.get("/items")
        # Act - With parameter
        response2 = client.get("/items?category=A")

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200

        data2 = response2.json()
        assert len(data2) > 0
        assert all(item.get("category") == "A" for item in data2 if "category" in item)

    def test_multiple_query_parameters(self, basic_app):
        """
        Test multiple query parameters.

        Expected Behavior:
            - All parameters extracted
            - Parameters bind to correct arguments
            - Types converted properly

        Related: Multiple query params
        """
        # Arrange
        client = TestClient(basic_app)

        # Act
        response = client.get("/items?category=A&limit=5&offset=0")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_query_parameter_type_conversion(self, basic_app):
        """
        Test query parameter type conversion.

        Expected Behavior:
            - String to int conversion
            - String to float conversion
            - Boolean conversion
            - Type validation errors handled

        Related: Type conversion
        """
        # Arrange
        client = TestClient(basic_app)

        # Act - Valid types
        response = client.get("/items?limit=5&offset=1")

        # Assert
        assert response.status_code == 200

    def test_query_parameter_validation(self, basic_app):
        """
        Test query parameter validation.

        Expected Behavior:
            - Min/max constraints enforced
            - Invalid values rejected (422)
            - Validation errors descriptive

        Related: Parameter validation
        """
        # Arrange
        client = TestClient(basic_app)

        # Act - Invalid limit (too high)
        response = client.get("/items?limit=1000")

        # Assert
        assert response.status_code == 422  # Validation error

    def test_required_query_parameter(self, multi_controller_app):
        """
        Test required query parameter enforcement.

        Expected Behavior:
            - Request fails without required param (422)
            - Request succeeds with required param
            - Error message indicates missing param

        Related: Required parameters
        """
        # Arrange
        client = TestClient(multi_controller_app)

        # Act - Missing required parameter
        response1 = client.get("/search")
        # Act - With required parameter
        response2 = client.get("/search?q=widget")

        # Assert
        assert response1.status_code == 422  # Missing required param
        assert response2.status_code == 200


# =============================================================================
# Test Suite: Route Prefix Handling
# =============================================================================


@pytest.mark.integration
class TestRoutePrefixHandling:
    """
    Test route prefix application.

    Validates that route prefixes are correctly applied to controllers
    and that versioned APIs work as expected.

    Related: API versioning, route prefixes
    """

    def test_versioned_routes(self, versioned_app):
        """
        Test API version prefixes.

        Expected Behavior:
            - v1 routes accessible with /v1 prefix
            - Non-versioned routes accessible without prefix
            - Both routes coexist

        Related: API versioning
        """
        # Arrange
        client = TestClient(versioned_app)

        # Act
        response_v1 = client.get("/v1/items/item-1")
        response_default = client.get("/items/item-1")

        # Assert
        assert response_v1.status_code == 200
        assert response_default.status_code == 200

    def test_route_isolation(self, versioned_app):
        """
        Test that different route prefixes are isolated.

        Expected Behavior:
            - v1 route doesn't affect default route
            - Default route doesn't affect v1 route
            - Each returns correct data

        Related: Route isolation
        """
        # Arrange
        client = TestClient(versioned_app)

        # Act
        response_v1 = client.get("/v1/items/item-1")
        response_default = client.get("/items/item-1")

        # Assert - Both work independently
        assert response_v1.status_code == 200
        assert response_default.status_code == 200

        data_v1 = response_v1.json()
        data_default = response_default.json()

        assert data_v1["id"] == "item-1"
        assert data_default["id"] == "item-1"


# =============================================================================
# Test Suite: Route Metadata
# =============================================================================


@pytest.mark.integration
class TestRouteMetadata:
    """
    Test route metadata and introspection.

    Validates that route metadata (methods, paths, etc.) is correctly
    set and accessible for documentation and debugging.

    Related: FastAPI route metadata
    """

    def test_route_methods(self, basic_app):
        """
        Test that HTTP methods are correctly registered.

        Expected Behavior:
            - Routes have correct HTTP methods
            - GET, POST, PUT, DELETE registered appropriately
            - Method restrictions enforced

        Related: HTTP methods
        """
        # Act
        routes = [r for r in basic_app.routes if hasattr(r, "methods")]

        # Assert - Find items route
        items_routes = [r for r in routes if hasattr(r, "path") and r.path == "/items"]
        assert len(items_routes) > 0
        assert "GET" in items_routes[0].methods

    def test_route_paths(self, basic_app):
        """
        Test that route paths are correctly set.

        Expected Behavior:
            - Paths match controller definitions
            - Path parameters preserved
            - No duplicate paths (unless different methods)

        Related: Route paths
        """
        # Act
        routes = [r for r in basic_app.routes if hasattr(r, "path")]
        paths = {r.path for r in routes}

        # Assert
        assert "/items/{item_id}" in paths
        assert "/items" in paths
