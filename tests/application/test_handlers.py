"""
Test suite for Command and Query Handler base classes.

This module validates the base handler functionality including:
- CommandHandler base class operations
- QueryHandler base class operations
- OperationResult helper methods (ok, created, bad_request, etc.)
- Handler state management
- Error handling patterns
- Response formatting

Test Coverage:
    - Handler initialization
    - OperationResult creation methods
    - Status code validation
    - Error message formatting
    - Data payload handling
    - Multiple handler instances
    - Handler lifecycle

Expected Behavior:
    - Handlers provide consistent OperationResult responses
    - Helper methods create correct status codes
    - Error messages are properly formatted
    - Data payloads are type-safe
    - Handlers are stateless (unless explicitly stateful)
    - Multiple handlers can coexist

Related Modules:
    - neuroglia.mediation.mediator: CommandHandler, QueryHandler base classes
    - neuroglia.core: OperationResult, ProblemDetails
    - neuroglia.dependency_injection: Service provider integration

Related Documentation:
    - [CQRS Handlers](../../docs/features/simple-cqrs.md)
    - [OperationResult Pattern](../../docs/patterns/operation-result.md)
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import pytest

from neuroglia.core import OperationResult
from neuroglia.mediation.mediator import Command, CommandHandler, Query, QueryHandler

# =============================================================================
# Test Commands for Handler Testing
# =============================================================================


@dataclass
class CreatePizzaTestCommand(Command[OperationResult[dict]]):
    """Command to create a pizza."""

    name: str
    price: Decimal
    size: str


@dataclass
class UpdatePizzaTestCommand(Command[OperationResult[dict]]):
    """Command to update a pizza."""

    pizza_id: str
    name: Optional[str] = None
    price: Optional[Decimal] = None


@dataclass
class DeletePizzaTestCommand(Command[OperationResult[bool]]):
    """Command to delete a pizza."""

    pizza_id: str


@dataclass
class InvalidTestCommand(Command[OperationResult[dict]]):
    """Command with invalid data for testing validation."""

    name: str
    price: Decimal


# =============================================================================
# Test Queries for Handler Testing
# =============================================================================


@dataclass
class GetPizzaTestQuery(Query[OperationResult[Optional[dict]]]):
    """Query to retrieve a pizza by ID."""

    pizza_id: str


@dataclass
class ListPizzasTestQuery(Query[OperationResult[list[dict]]]):
    """Query to list all pizzas."""

    category: Optional[str] = None
    limit: int = 10


@dataclass
class SearchPizzasTestQuery(Query[OperationResult[list[dict]]]):
    """Query to search pizzas by criteria."""

    search_term: str
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None


# =============================================================================
# Test Handler Implementations
# =============================================================================


class CreatePizzaTestHandler(CommandHandler[CreatePizzaTestCommand, OperationResult[dict]]):
    """Test handler for creating pizzas."""

    def __init__(self):
        self.commands_handled = []

    async def handle_async(self, request: CreatePizzaTestCommand) -> OperationResult[dict]:
        """Handle pizza creation."""
        self.commands_handled.append(request)

        # Simulate validation
        if not request.name:
            return self.bad_request("Pizza name is required")

        if request.price <= 0:
            return self.bad_request("Pizza price must be positive")

        # Simulate successful creation
        pizza = {"id": "pizza-123", "name": request.name, "price": float(request.price), "size": request.size}

        return self.created(pizza)


class UpdatePizzaTestHandler(CommandHandler[UpdatePizzaTestCommand, OperationResult[dict]]):
    """Test handler for updating pizzas."""

    def __init__(self):
        self.commands_handled = []
        self.pizzas = {
            "pizza-1": {"id": "pizza-1", "name": "Margherita", "price": 12.99},
            "pizza-2": {"id": "pizza-2", "name": "Pepperoni", "price": 14.99},
        }

    async def handle_async(self, request: UpdatePizzaTestCommand) -> OperationResult[dict]:
        """Handle pizza update."""
        self.commands_handled.append(request)

        # Check if pizza exists
        if request.pizza_id not in self.pizzas:
            return self.not_found(dict, "pizza_id", request.pizza_id)

        # Update pizza
        pizza = self.pizzas[request.pizza_id].copy()
        if request.name:
            pizza["name"] = request.name
        if request.price:
            pizza["price"] = float(request.price)

        self.pizzas[request.pizza_id] = pizza

        return self.ok(pizza)


class DeletePizzaTestHandler(CommandHandler[DeletePizzaTestCommand, OperationResult[bool]]):
    """Test handler for deleting pizzas."""

    def __init__(self):
        self.commands_handled = []
        self.pizzas = {"pizza-1", "pizza-2", "pizza-3"}

    async def handle_async(self, request: DeletePizzaTestCommand) -> OperationResult[bool]:
        """Handle pizza deletion."""
        self.commands_handled.append(request)

        if request.pizza_id not in self.pizzas:
            return self.not_found(dict, "pizza_id", request.pizza_id)

        self.pizzas.remove(request.pizza_id)
        return self.ok(True)


class GetPizzaTestHandler(QueryHandler[GetPizzaTestQuery, OperationResult[Optional[dict]]]):
    """Test handler for retrieving a pizza."""

    def __init__(self):
        self.queries_handled = []
        self.pizzas = {
            "pizza-1": {"id": "pizza-1", "name": "Margherita", "price": 12.99},
            "pizza-2": {"id": "pizza-2", "name": "Pepperoni", "price": 14.99},
        }

    async def handle_async(self, request: GetPizzaTestQuery) -> OperationResult[Optional[dict]]:
        """Handle pizza retrieval."""
        self.queries_handled.append(request)

        pizza = self.pizzas.get(request.pizza_id)
        return self.ok(pizza)


class ListPizzasTestHandler(QueryHandler[ListPizzasTestQuery, OperationResult[list[dict]]]):
    """Test handler for listing pizzas."""

    def __init__(self):
        self.queries_handled = []
        self.pizzas = [
            {"id": "pizza-1", "name": "Margherita", "category": "classic", "price": 12.99},
            {"id": "pizza-2", "name": "Pepperoni", "category": "meat", "price": 14.99},
            {"id": "pizza-3", "name": "Vegetarian", "category": "veggie", "price": 13.99},
            {"id": "pizza-4", "name": "Quattro Formaggi", "category": "classic", "price": 15.99},
        ]

    async def handle_async(self, request: ListPizzasTestQuery) -> OperationResult[list[dict]]:
        """Handle pizza listing."""
        self.queries_handled.append(request)

        pizzas = self.pizzas.copy()

        # Filter by category if specified
        if request.category:
            pizzas = [p for p in pizzas if p.get("category") == request.category]

        # Apply limit
        pizzas = pizzas[: request.limit]

        return self.ok(pizzas)


class SearchPizzasTestHandler(QueryHandler[SearchPizzasTestQuery, OperationResult[list[dict]]]):
    """Test handler for searching pizzas."""

    def __init__(self):
        self.queries_handled = []
        self.pizzas = [
            {"id": "pizza-1", "name": "Margherita", "price": 12.99},
            {"id": "pizza-2", "name": "Pepperoni", "price": 14.99},
            {"id": "pizza-3", "name": "Vegetarian", "price": 13.99},
        ]

    async def handle_async(self, request: SearchPizzasTestQuery) -> OperationResult[list[dict]]:
        """Handle pizza search."""
        self.queries_handled.append(request)

        results = []

        for pizza in self.pizzas:
            # Match search term
            if request.search_term.lower() not in pizza["name"].lower():
                continue

            # Filter by price range
            if request.min_price and pizza["price"] < float(request.min_price):
                continue
            if request.max_price and pizza["price"] > float(request.max_price):
                continue

            results.append(pizza)

        return self.ok(results)


# =============================================================================
# Test Suite: Command Handler Operations
# =============================================================================


@pytest.mark.unit
class TestCommandHandlerOperations:
    """
    Test CommandHandler base class functionality.

    Validates that command handlers:
    - Create proper OperationResult responses
    - Use correct status codes
    - Format error messages properly
    - Handle data payloads correctly
    - Maintain handler state appropriately

    Related: neuroglia.mediation.mediator.CommandHandler
    """

    @pytest.mark.asyncio
    async def test_handler_created_response(self):
        """
        Test handler returns 201 Created response.

        Expected Behavior:
            - Handler uses self.created() helper
            - Status code is 201
            - Result is_success is True
            - Data payload is intact

        Related: CommandHandler.created()
        """
        # Arrange
        handler = CreatePizzaTestHandler()
        command = CreatePizzaTestCommand(name="Margherita", price=Decimal("12.99"), size="medium")

        # Act
        result = await handler.handle_async(command)

        # Assert
        assert result is not None
        assert result.is_success
        assert result.status == 201  # Created
        assert result.data is not None
        assert result.data["name"] == "Margherita"
        assert result.data["price"] == 12.99

    @pytest.mark.asyncio
    async def test_handler_ok_response(self):
        """
        Test handler returns 200 OK response.

        Expected Behavior:
            - Handler uses self.ok() helper
            - Status code is 200
            - Result is_success is True
            - Data payload is correct

        Related: CommandHandler.ok()
        """
        # Arrange
        handler = UpdatePizzaTestHandler()
        command = UpdatePizzaTestCommand(pizza_id="pizza-1", name="Super Margherita")

        # Act
        result = await handler.handle_async(command)

        # Assert
        assert result is not None
        assert result.is_success
        assert result.status == 200  # OK
        assert result.data is not None
        assert result.data["name"] == "Super Margherita"

    @pytest.mark.asyncio
    async def test_handler_bad_request_response(self):
        """
        Test handler returns 400 Bad Request response.

        Expected Behavior:
            - Handler uses self.bad_request() helper
            - Status code is 400
            - Result is_success is False
            - Error message is present

        Related: CommandHandler.bad_request()
        """
        # Arrange
        handler = CreatePizzaTestHandler()
        command = CreatePizzaTestCommand(name="", price=Decimal("12.99"), size="medium")

        # Act
        result = await handler.handle_async(command)

        # Assert
        assert result is not None
        assert not result.is_success
        assert result.status == 400  # Bad Request
        assert result.detail is not None
        assert "required" in result.detail.lower()

    @pytest.mark.asyncio
    async def test_handler_not_found_response(self):
        """
        Test handler returns 404 Not Found response.

        Expected Behavior:
            - Handler uses self.not_found() helper
            - Status code is 404
            - Result is_success is False
            - Error message includes entity type and key

        Related: CommandHandler.not_found()
        """
        # Arrange
        handler = UpdatePizzaTestHandler()
        command = UpdatePizzaTestCommand(pizza_id="nonexistent", name="New Name")

        # Act
        result = await handler.handle_async(command)

        # Assert
        assert result is not None
        assert not result.is_success
        assert result.status == 404  # Not Found
        assert result.detail is not None
        assert "nonexistent" in result.detail

    @pytest.mark.asyncio
    async def test_handler_tracks_commands(self):
        """
        Test handler can track processed commands.

        Expected Behavior:
            - Handler maintains internal state
            - Each command is recorded
            - Command history is accessible
            - State persists across calls

        Related: Handler state management
        """
        # Arrange
        handler = CreatePizzaTestHandler()
        command1 = CreatePizzaTestCommand(name="Pizza 1", price=Decimal("10.00"), size="small")
        command2 = CreatePizzaTestCommand(name="Pizza 2", price=Decimal("15.00"), size="large")

        # Act
        await handler.handle_async(command1)
        await handler.handle_async(command2)

        # Assert
        assert len(handler.commands_handled) == 2
        assert handler.commands_handled[0].name == "Pizza 1"
        assert handler.commands_handled[1].name == "Pizza 2"

    @pytest.mark.asyncio
    async def test_handler_validation_error(self):
        """
        Test handler properly validates input data.

        Expected Behavior:
            - Handler validates command data
            - Invalid data returns bad_request
            - Error message is descriptive
            - No side effects occur

        Related: Input validation patterns
        """
        # Arrange
        handler = CreatePizzaTestHandler()
        command = CreatePizzaTestCommand(name="Pizza", price=Decimal("-5.00"), size="medium")

        # Act
        result = await handler.handle_async(command)

        # Assert
        assert not result.is_success
        assert result.status == 400
        assert "positive" in result.detail.lower()
        assert len(handler.commands_handled) == 1  # Command was tracked even if invalid

    @pytest.mark.asyncio
    async def test_handler_delete_success(self):
        """
        Test delete command handler returns boolean result.

        Expected Behavior:
            - Handler processes delete command
            - Returns boolean true on success
            - Status is 200 OK
            - Result is_success is True

        Related: Boolean result patterns
        """
        # Arrange
        handler = DeletePizzaTestHandler()
        command = DeletePizzaTestCommand(pizza_id="pizza-1")

        # Act
        result = await handler.handle_async(command)

        # Assert
        assert result.is_success
        assert result.status == 200
        assert result.data is True
        assert "pizza-1" not in handler.pizzas


# =============================================================================
# Test Suite: Query Handler Operations
# =============================================================================


@pytest.mark.unit
class TestQueryHandlerOperations:
    """
    Test QueryHandler base class functionality.

    Validates that query handlers:
    - Return data without side effects
    - Use proper status codes
    - Handle missing data gracefully
    - Support filtering and pagination
    - Maintain consistency

    Related: neuroglia.mediation.mediator.QueryHandler
    """

    @pytest.mark.asyncio
    async def test_handler_get_single_entity(self):
        """
        Test query handler retrieves single entity.

        Expected Behavior:
            - Handler returns entity if found
            - Status is 200 OK
            - Data payload matches request
            - No side effects

        Related: QueryHandler single entity retrieval
        """
        # Arrange
        handler = GetPizzaTestHandler()
        query = GetPizzaTestQuery(pizza_id="pizza-1")

        # Act
        result = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert result.status == 200
        assert result.data is not None
        assert result.data["id"] == "pizza-1"
        assert result.data["name"] == "Margherita"

    @pytest.mark.asyncio
    async def test_handler_get_nonexistent_entity(self):
        """
        Test query handler handles missing entity.

        Expected Behavior:
            - Handler returns None for missing entity
            - Status is still 200 OK (not 404)
            - No exception raised
            - Result is_success is True

        Related: Query handler null handling
        """
        # Arrange
        handler = GetPizzaTestHandler()
        query = GetPizzaTestQuery(pizza_id="nonexistent")

        # Act
        result = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert result.status == 200
        assert result.data is None

    @pytest.mark.asyncio
    async def test_handler_list_all_entities(self):
        """
        Test query handler lists all entities.

        Expected Behavior:
            - Handler returns list of entities
            - All matching entities included
            - Limit is respected
            - Order is consistent

        Related: QueryHandler list operations
        """
        # Arrange
        handler = ListPizzasTestHandler()
        query = ListPizzasTestQuery(category=None, limit=10)

        # Act
        result = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert result.status == 200
        assert isinstance(result.data, list)
        assert len(result.data) == 4

    @pytest.mark.asyncio
    async def test_handler_list_with_filter(self):
        """
        Test query handler filters results.

        Expected Behavior:
            - Handler applies filter criteria
            - Only matching entities returned
            - Non-matching entities excluded
            - Empty list if no matches

        Related: Query filtering patterns
        """
        # Arrange
        handler = ListPizzasTestHandler()
        query = ListPizzasTestQuery(category="classic", limit=10)

        # Act
        result = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert len(result.data) == 2
        assert all(p["category"] == "classic" for p in result.data)

    @pytest.mark.asyncio
    async def test_handler_list_with_limit(self):
        """
        Test query handler respects limit parameter.

        Expected Behavior:
            - Handler limits result count
            - Returns at most limit items
            - Limit works with filters
            - Empty list if limit is 0

        Related: Pagination patterns
        """
        # Arrange
        handler = ListPizzasTestHandler()
        query = ListPizzasTestQuery(category=None, limit=2)

        # Act
        result = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert len(result.data) == 2

    @pytest.mark.asyncio
    async def test_handler_search_with_criteria(self):
        """
        Test query handler searches with multiple criteria.

        Expected Behavior:
            - Handler applies all search criteria
            - Results match all conditions
            - Search is case-insensitive
            - Empty list if no matches

        Related: Complex query patterns
        """
        # Arrange
        handler = SearchPizzasTestHandler()
        query = SearchPizzasTestQuery(search_term="pep", min_price=Decimal("10.00"), max_price=Decimal("20.00"))

        # Act
        result = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert len(result.data) == 1
        assert result.data[0]["name"] == "Pepperoni"

    @pytest.mark.asyncio
    async def test_handler_search_no_matches(self):
        """
        Test query handler returns empty list when no matches.

        Expected Behavior:
            - Handler returns empty list
            - Status is still 200 OK
            - No exception raised
            - Result is_success is True

        Related: Empty result handling
        """
        # Arrange
        handler = SearchPizzasTestHandler()
        query = SearchPizzasTestQuery(search_term="NonexistentPizza")

        # Act
        result = await handler.handle_async(query)

        # Assert
        assert result.is_success
        assert result.status == 200
        assert isinstance(result.data, list)
        assert len(result.data) == 0

    @pytest.mark.asyncio
    async def test_handler_tracks_queries(self):
        """
        Test query handler tracks executed queries.

        Expected Behavior:
            - Handler maintains query history
            - Each query is recorded
            - History is accessible
            - No side effects on data

        Related: Query tracking patterns
        """
        # Arrange
        handler = GetPizzaTestHandler()
        query1 = GetPizzaTestQuery(pizza_id="pizza-1")
        query2 = GetPizzaTestQuery(pizza_id="pizza-2")

        # Act
        await handler.handle_async(query1)
        await handler.handle_async(query2)

        # Assert
        assert len(handler.queries_handled) == 2
        assert handler.queries_handled[0].pizza_id == "pizza-1"
        assert handler.queries_handled[1].pizza_id == "pizza-2"


# =============================================================================
# Test Suite: Handler Helper Methods
# =============================================================================


@pytest.mark.unit
class TestHandlerHelperMethods:
    """
    Test RequestHandler helper methods directly.

    Validates that helper methods:
    - Create properly formatted responses
    - Use correct status codes
    - Handle different data types
    - Format error messages consistently
    - Support all HTTP status codes

    Related: neuroglia.mediation.mediator.RequestHandler
    """

    @pytest.mark.asyncio
    async def test_ok_helper_creates_200_response(self):
        """
        Test ok() helper creates 200 OK response.

        Expected Behavior:
            - Status code is 200
            - is_success is True
            - Data payload is intact
            - Title is "OK"

        Related: RequestHandler.ok()
        """
        # Arrange
        handler = GetPizzaTestHandler()
        data = {"id": "test", "name": "Test Pizza"}

        # Act
        result = handler.ok(data)

        # Assert
        assert result.status == 200
        assert result.is_success
        assert result.data == data
        assert result.title == "OK"

    @pytest.mark.asyncio
    async def test_created_helper_creates_201_response(self):
        """
        Test created() helper creates 201 Created response.

        Expected Behavior:
            - Status code is 201
            - is_success is True
            - Data payload is intact
            - Title is "Created"

        Related: RequestHandler.created()
        """
        # Arrange
        handler = CreatePizzaTestHandler()
        data = {"id": "new-pizza", "name": "New Pizza"}

        # Act
        result = handler.created(data)

        # Assert
        assert result.status == 201
        assert result.is_success
        assert result.data == data
        assert result.title == "Created"

    @pytest.mark.asyncio
    async def test_bad_request_helper_creates_400_response(self):
        """
        Test bad_request() helper creates 400 Bad Request response.

        Expected Behavior:
            - Status code is 400
            - is_success is False
            - Error message is present
            - Title is "Bad Request"

        Related: RequestHandler.bad_request()
        """
        # Arrange
        handler = CreatePizzaTestHandler()
        error_message = "Invalid input data"

        # Act
        result = handler.bad_request(error_message)

        # Assert
        assert result.status == 400
        assert not result.is_success
        assert result.detail == error_message
        assert result.title == "Bad Request"

    @pytest.mark.asyncio
    async def test_not_found_helper_creates_404_response(self):
        """
        Test not_found() helper creates 404 Not Found response.

        Expected Behavior:
            - Status code is 404
            - is_success is False
            - Error message includes entity type and key
            - Title is "Not Found"

        Related: RequestHandler.not_found()
        """
        # Arrange
        handler = UpdatePizzaTestHandler()

        # Act
        result = handler.not_found(dict, "pizza_id", "missing-123")

        # Assert
        assert result.status == 404
        assert not result.is_success
        assert "dict" in result.detail
        assert "missing-123" in result.detail
        assert result.title == "Not Found"

    @pytest.mark.asyncio
    async def test_handler_with_none_data(self):
        """
        Test handlers correctly handle None data.

        Expected Behavior:
            - ok() accepts None data
            - Status is 200
            - is_success is True
            - data field is None

        Related: Null data handling
        """
        # Arrange
        handler = GetPizzaTestHandler()

        # Act
        result = handler.ok(None)

        # Assert
        assert result.status == 200
        assert result.is_success
        assert result.data is None

    @pytest.mark.asyncio
    async def test_handler_with_complex_data(self):
        """
        Test handlers handle complex nested data structures.

        Expected Behavior:
            - Nested dictionaries preserved
            - Lists preserved
            - Type safety maintained
            - No data corruption

        Related: Complex data handling
        """
        # Arrange
        handler = CreatePizzaTestHandler()
        complex_data = {"id": "pizza-1", "name": "Supreme", "toppings": ["cheese", "pepperoni", "mushrooms"], "pricing": {"small": 12.99, "medium": 15.99, "large": 18.99}, "metadata": {"created_at": "2025-01-20T10:00:00Z", "updated_at": "2025-01-20T11:00:00Z"}}

        # Act
        result = handler.created(complex_data)

        # Assert
        assert result.is_success
        assert result.data == complex_data
        assert result.data["toppings"] == ["cheese", "pepperoni", "mushrooms"]
        assert result.data["pricing"]["medium"] == 15.99


# =============================================================================
# Test Suite: Handler Independence and Isolation
# =============================================================================


@pytest.mark.unit
class TestHandlerIndependence:
    """
    Test that handlers are independent and properly isolated.

    Validates that:
    - Multiple handler instances don't share state
    - Handlers can execute concurrently
    - Handler state doesn't leak
    - Each handler has its own data

    Related: Handler lifecycle and state management
    """

    @pytest.mark.asyncio
    async def test_multiple_handler_instances_independent(self):
        """
        Test multiple handler instances maintain separate state.

        Expected Behavior:
            - Each handler has its own state
            - Commands don't leak between instances
            - State modifications are isolated
            - No shared mutable state

        Related: Handler isolation
        """
        # Arrange
        handler1 = CreatePizzaTestHandler()
        handler2 = CreatePizzaTestHandler()

        command1 = CreatePizzaTestCommand(name="Pizza 1", price=Decimal("10.00"), size="small")
        command2 = CreatePizzaTestCommand(name="Pizza 2", price=Decimal("15.00"), size="large")

        # Act
        await handler1.handle_async(command1)
        await handler2.handle_async(command2)

        # Assert
        assert len(handler1.commands_handled) == 1
        assert len(handler2.commands_handled) == 1
        assert handler1.commands_handled[0].name == "Pizza 1"
        assert handler2.commands_handled[0].name == "Pizza 2"

    @pytest.mark.asyncio
    async def test_query_handler_no_side_effects(self):
        """
        Test query handlers don't modify data.

        Expected Behavior:
            - Queries don't change underlying data
            - Multiple queries return same results
            - Data consistency maintained
            - Read-only access guaranteed

        Related: CQRS separation of concerns
        """
        # Arrange
        handler = GetPizzaTestHandler()
        query = GetPizzaTestQuery(pizza_id="pizza-1")

        # Act
        result1 = await handler.handle_async(query)
        result2 = await handler.handle_async(query)

        # Assert
        assert result1.data == result2.data
        assert handler.pizzas["pizza-1"]["name"] == "Margherita"  # Unchanged

    @pytest.mark.asyncio
    async def test_command_handler_state_changes(self):
        """
        Test command handlers can maintain state changes.

        Expected Behavior:
            - Commands modify handler state
            - State changes persist
            - Subsequent commands see changes
            - State is isolated to handler instance

        Related: Command handler statefulness
        """
        # Arrange
        handler = UpdatePizzaTestHandler()
        original_name = handler.pizzas["pizza-1"]["name"]

        command = UpdatePizzaTestCommand(pizza_id="pizza-1", name="Updated Pizza")

        # Act
        await handler.handle_async(command)

        # Assert
        assert handler.pizzas["pizza-1"]["name"] != original_name
        assert handler.pizzas["pizza-1"]["name"] == "Updated Pizza"
