"""
Comprehensive test configuration and fixtures for the Neuroglia framework test suite.

This module provides:
- Global test fixtures for dependency injection, mediation, repositories
- Mario's Pizzeria-inspired test data factories for realistic scenarios
- Pytest configuration for async tests, markers, and test categorization
- Shared utilities for common test patterns

References:
    - Framework Documentation: docs/getting-started.md
    - Test Architecture: tests/TEST_ARCHITECTURE.md
    - Sample Application: samples/mario-pizzeria/
"""

import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Test configuration
TEST_DATABASE_URL = "mongodb://localhost:27017/neuroglia_test"
TEST_EVENTSTOREDB_URL = "esdb://localhost:2113?tls=false"
TEST_LOG_LEVEL = "DEBUG"


# =============================================================================
# Pytest Configuration
# =============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for the test session.

    This fixture provides a single event loop for all async tests in the session,
    ensuring proper cleanup and avoiding event loop conflicts.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def pytest_configure(config):
    """
    Configure pytest with custom markers for test categorization.

    Markers allow selective test execution:
        - pytest -m unit: Run only unit tests
        - pytest -m "not slow": Skip slow tests
        - pytest -m "integration and database": Run database integration tests
    """
    markers = ["unit: marks tests as unit tests (fast, isolated, no external dependencies)", "integration: marks tests as integration tests (requires databases, services)", "slow: marks tests as slow running (> 1 second)", "database: marks tests that require MongoDB or other databases", "eventstore: marks tests that require EventStoreDB", "external: marks tests that require external services (Redis, HTTP APIs)", "e2e: marks tests as end-to-end (complete workflows across all layers)"]
    for marker in markers:
        config.addinivalue_line("markers", marker)


# Test collection configuration
collect_ignore = ["setup.py", "build", "dist", ".tox", ".git", "__pycache__"]


# =============================================================================
# Environment Validation
# =============================================================================


def check_python_version():
    """Check minimum Python version requirement (3.8+)."""
    if sys.version_info < (3, 8):
        raise RuntimeError("Python 3.8 or higher is required for Neuroglia tests")


def check_dependencies():
    """Check that required test dependencies are available."""
    required_packages = ["pytest", "pytest_asyncio"]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        raise RuntimeError(f"Missing required test packages: {', '.join(missing_packages)}. " f"Install with: pip install {' '.join(missing_packages)}")


# Initialize test environment
check_python_version()
check_dependencies()


# =============================================================================
# Core Framework Fixtures
# =============================================================================


@pytest.fixture
def service_collection():
    """
    Provide a fresh ServiceCollection for dependency injection tests.

    Usage:
        def test_di_registration(service_collection):
            service_collection.add_singleton(MyService)
            provider = service_collection.build()
            service = provider.get_service(MyService)
            assert service is not None

    Related Documentation:
        - docs/patterns/dependency-injection.md
    """
    from neuroglia.dependency_injection import ServiceCollection

    return ServiceCollection()


@pytest.fixture
def service_provider(service_collection):
    """
    Provide a built ServiceProvider with common framework services registered.

    Includes:
        - Mediator for CQRS
        - Mapper for object mapping
        - In-memory repositories for testing

    Usage:
        def test_with_mediator(service_provider):
            mediator = service_provider.get_service(Mediator)
            result = await mediator.execute_async(command)

    Related Documentation:
        - docs/patterns/dependency-injection.md
        - docs/features/simple-cqrs.md
    """
    from neuroglia.mapping import Mapper
    from neuroglia.mediation import Mediator

    service_collection.add_singleton(Mediator)
    service_collection.add_singleton(Mapper)
    return service_collection.build()


@pytest.fixture
def mediator(service_provider):
    """
    Provide a configured Mediator instance for CQRS tests.

    The mediator is ready to execute commands, queries, and publish events.
    Handlers must be registered separately in tests.

    Usage:
        def test_command_execution(mediator):
            result = await mediator.execute_async(MyCommand())
            assert result.is_success

    Related Documentation:
        - docs/features/simple-cqrs.md
        - docs/patterns/cqrs.md
    """
    from neuroglia.mediation import Mediator

    return service_provider.get_service(Mediator)


@pytest.fixture
def mapper():
    """
    Provide a Mapper instance for object mapping tests.

    The mapper supports automatic property mapping between types,
    including domain entities to DTOs and vice versa.

    Usage:
        def test_entity_to_dto_mapping(mapper):
            dto = mapper.map(entity, EntityDto)
            assert dto.id == entity.id()

    Related Documentation:
        - docs/features/object-mapping.md
    """
    from neuroglia.mapping import Mapper

    return Mapper()


@pytest.fixture
def json_serializer():
    """
    Provide a configured JsonSerializer for serialization tests.

    The serializer handles complex types including:
        - Enums (by value)
        - Decimals
        - Datetime objects
        - Nested dataclasses
        - AggregateRoot state separation

    Usage:
        def test_serialization(json_serializer):
            json_text = json_serializer.serialize_to_text(entity)
            restored = json_serializer.deserialize_from_text(json_text, EntityType)

    Related Documentation:
        - docs/features/serialization.md
    """
    from neuroglia.serialization.json import JsonSerializer

    return JsonSerializer()


# =============================================================================
# Mario's Pizzeria Test Data Factories
# =============================================================================


@pytest.fixture
def pizza_size_enum():
    """Provide PizzaSize enum for tests."""
    from enum import Enum

    class PizzaSize(Enum):
        SMALL = "small"
        MEDIUM = "medium"
        LARGE = "large"

    return PizzaSize


@pytest.fixture
def order_status_enum():
    """Provide OrderStatus enum for tests."""
    from enum import Enum

    class OrderStatus(Enum):
        PENDING = "pending"
        CONFIRMED = "confirmed"
        COOKING = "cooking"
        READY = "ready"
        DELIVERING = "delivering"
        DELIVERED = "delivered"
        CANCELLED = "cancelled"

    return OrderStatus


@pytest.fixture
def margherita_pizza_data():
    """
    Provide test data for a Margherita pizza.

    This fixture returns a dict with realistic pizza data that can be used
    to construct Pizza entities or test serialization.

    Usage:
        def test_pizza_creation(margherita_pizza_data):
            pizza = Pizza(**margherita_pizza_data)
            assert pizza.name == "Margherita"

    Related: samples/mario-pizzeria/domain/entities/pizza.py
    """
    return {"name": "Margherita", "base_price": Decimal("12.99"), "size": "medium", "description": "Classic Italian pizza with tomato, mozzarella, and fresh basil", "toppings": ["mozzarella", "tomato sauce", "fresh basil", "olive oil"]}


@pytest.fixture
def pepperoni_pizza_data():
    """Provide test data for a Pepperoni pizza."""
    return {"name": "Pepperoni", "base_price": Decimal("14.99"), "size": "large", "description": "American favorite with pepperoni and extra cheese", "toppings": ["mozzarella", "tomato sauce", "pepperoni", "oregano"]}


@pytest.fixture
def supreme_pizza_data():
    """Provide test data for a Supreme pizza."""
    return {"name": "Supreme", "base_price": Decimal("17.99"), "size": "large", "description": "Loaded with meats and vegetables", "toppings": ["mozzarella", "tomato sauce", "pepperoni", "sausage", "bell peppers", "onions", "mushrooms", "olives"]}


@pytest.fixture
def customer_data():
    """
    Provide realistic customer test data.

    Usage:
        def test_customer_creation(customer_data):
            customer = Customer(**customer_data)
            assert customer.phone == "+1-555-0123"

    Related: samples/mario-pizzeria/domain/entities/customer.py
    """
    return {"name": "John Doe", "phone": "+1-555-0123", "email": "john.doe@email.com", "address": "123 Main Street, Apt 4B, Springfield, IL 62701", "customer_id": str(uuid4())}


@pytest.fixture
def order_data(customer_data, margherita_pizza_data):
    """
    Provide realistic order test data.

    Creates an order with one Margherita pizza for testing.

    Usage:
        def test_order_workflow(order_data):
            order = Order(customer_id=order_data["customer_id"])
            # Add pizzas, confirm order, etc.

    Related: samples/mario-pizzeria/domain/entities/order.py
    """
    return {"customer_id": customer_data["customer_id"], "order_time": datetime.now(timezone.utc), "pizzas": [margherita_pizza_data], "payment_method": "credit_card", "notes": "Please ring doorbell twice"}


@pytest.fixture
def command_test_data():
    """
    Provide test data for command tests.

    Returns dict with common command parameters used across multiple tests.

    Usage:
        def test_place_order_command(command_test_data):
            command = PlaceOrderCommand(**command_test_data["place_order"])

    Related: samples/mario-pizzeria/application/commands/
    """
    return {
        "place_order": {"customer_name": "John Doe", "customer_phone": "+1-555-0123", "customer_email": "john.doe@email.com", "customer_address": "123 Main St, Springfield", "pizzas": [{"name": "Margherita", "size": "medium", "toppings": ["extra_cheese"]}], "payment_method": "credit_card", "notes": "Please deliver by 7 PM"},
        "update_order_status": {"order_id": str(uuid4()), "new_status": "cooking", "user_id": str(uuid4()), "user_name": "Chef Mario"},
        "add_pizza": {"name": "Pepperoni", "base_price": Decimal("14.99"), "size": "large", "description": "Spicy pepperoni pizza"},
    }


@pytest.fixture
def query_test_data():
    """
    Provide test data for query tests.

    Returns dict with common query parameters.

    Usage:
        def test_get_order_query(query_test_data):
            query = GetOrderByIdQuery(**query_test_data["get_order"])

    Related: samples/mario-pizzeria/application/queries/
    """
    return {"get_order": {"order_id": str(uuid4())}, "get_orders_by_customer": {"customer_id": str(uuid4()), "limit": 10}, "get_orders_by_status": {"status": "pending", "limit": 20}, "get_menu": {"include_unavailable": False}}


# =============================================================================
# Repository Fixtures
# =============================================================================


@pytest.fixture
def memory_repository():
    """
    Provide an in-memory repository for fast unit tests.

    The in-memory repository implements the Repository interface
    but stores data in memory, making tests fast and isolated.

    Usage:
        @pytest.mark.asyncio
        async def test_repository_add(memory_repository):
            entity = MyEntity()
            await memory_repository.add_async(entity)
            retrieved = await memory_repository.get_async(entity.id)
            assert retrieved == entity

    Related Documentation:
        - docs/features/data-access.md
    """
    from neuroglia.data.infrastructure.memory import MemoryRepository

    return MemoryRepository()


# =============================================================================
# Mock Service Fixtures
# =============================================================================


@pytest.fixture
def mock_event_bus():
    """
    Provide a mock event bus for testing event publishing.

    The mock allows verification that events were published
    without requiring real event infrastructure.

    Usage:
        def test_order_raises_event(mock_event_bus):
            order = Order()
            order.confirm()
            mock_event_bus.publish_async.assert_called_once()
    """
    from unittest.mock import AsyncMock, Mock

    mock = Mock()
    mock.publish_async = AsyncMock()
    return mock


@pytest.fixture
def mock_http_client():
    """
    Provide a mock HTTP client for testing external API calls.

    Usage:
        def test_payment_service(mock_http_client):
            mock_http_client.post_async.return_value = {"status": "success"}
            result = await payment_service.process_payment(amount)
    """
    from unittest.mock import AsyncMock, Mock

    mock = Mock()
    mock.get_async = AsyncMock()
    mock.post_async = AsyncMock()
    mock.put_async = AsyncMock()
    mock.delete_async = AsyncMock()
    return mock


# =============================================================================
# Test Utilities
# =============================================================================


@pytest.fixture
def assert_valid_operation_result():
    """
    Provide a helper function to assert OperationResult validity.

    Usage:
        def test_command_success(assert_valid_operation_result):
            result = await mediator.execute_async(command)
            assert_valid_operation_result(result, expected_status=200)
    """

    def _assert_valid(result, expected_status=200, expected_data=None):
        """
        Assert that an OperationResult is valid and matches expectations.

        Args:
            result: The OperationResult to validate
            expected_status: Expected HTTP status code (default: 200)
            expected_data: Optional expected data value
        """
        assert result is not None, "OperationResult should not be None"
        assert result.status == expected_status, f"Expected status {expected_status}, got {result.status}"

        if expected_data is not None:
            assert result.data == expected_data, f"Expected data {expected_data}, got {result.data}"

        if expected_status >= 200 and expected_status < 300:
            assert result.is_success, f"Result with status {expected_status} should be successful"
        else:
            assert not result.is_success, f"Result with status {expected_status} should not be successful"

    return _assert_valid


@pytest.fixture
def create_test_app():
    """
    Provide a factory function to create test FastAPI applications.

    This fixture creates a minimal FastAPI app with the Neuroglia
    framework properly configured for testing.

    Usage:
        def test_controller_endpoint(create_test_app):
            app = create_test_app(controllers=[MyController])
            client = TestClient(app)
            response = client.get("/api/my/endpoint")
            assert response.status_code == 200

    Related Documentation:
        - docs/features/mvc-controllers.md
        - docs/guides/local-development.md
    """

    def _create_app(controllers=None, services=None):
        """
        Create a test application with specified controllers and services.

        Args:
            controllers: List of controller classes to register
            services: Dict of service registrations {ServiceType: implementation}

        Returns:
            Configured FastAPI application instance
        """
        from neuroglia.hosting.web import WebApplicationBuilder
        from neuroglia.mapping import Mapper
        from neuroglia.mvc import ControllerBase

        builder = WebApplicationBuilder()

        # Register services
        if services:
            for service_type, implementation in services.items():
                builder.services.add_singleton(service_type, implementation)

        # Always add mediator and mapper
        builder.services.add_mediator()
        builder.services.add_singleton(Mapper)

        # Register controllers
        if controllers:
            for controller in controllers:
                builder.services.add_singleton(ControllerBase, controller)

        # Build app
        app = builder.build(auto_mount_controllers=True)
        return app

    return _create_app
