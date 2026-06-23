"""
Test configuration and fixtures for Mario's Pizzeria tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock

# Add project root to path
import sys

project_root = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(project_root))

from neuroglia.dependency_injection import ServiceCollection
from neuroglia.mediation import Mediator

# Add samples to path
samples_root = Path(__file__).parent.parent.parent.parent / "samples" / "mario-pizzeria"
sys.path.insert(0, str(samples_root))

from domain.entities import Order, Pizza, Customer, Kitchen
from domain.repositories import (
    IOrderRepository,
    IPizzaRepository,
    ICustomerRepository,
    IKitchenRepository,
)
from integration.repositories import (
    FileOrderRepository,
    FilePizzaRepository,
    FileCustomerRepository,
    FileKitchenRepository,
)


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_customer():
    """Create a test customer"""
    return Customer(
        name="Mario Rossi", phone="+1-555-0123", address="123 Pizza Street, Little Italy"
    )


@pytest.fixture
def test_pizza():
    """Create a test pizza"""
    return Pizza(name="Margherita", size="large", toppings=["extra cheese"])


@pytest.fixture
def test_pizzas():
    """Create a list of test pizzas"""
    return [
        Pizza(name="Margherita", size="large", toppings=["extra cheese"]),
        Pizza(name="Pepperoni", size="medium", toppings=["mushrooms"]),
    ]


@pytest.fixture
def test_order(test_customer, test_pizzas):
    """Create a test order"""
    return Order(customer=test_customer, pizzas=test_pizzas, payment_method="credit_card")


@pytest.fixture
def test_kitchen():
    """Create a test kitchen"""
    return Kitchen(capacity=5)


@pytest.fixture
def mock_order_repository():
    """Mock order repository"""
    repository = Mock(spec=IOrderRepository)
    repository.save_async.return_value = None
    repository.get_by_id_async.return_value = None
    repository.get_all_async.return_value = []
    repository.get_by_status_async.return_value = []
    return repository


@pytest.fixture
def mock_pizza_repository():
    """Mock pizza repository"""
    repository = Mock(spec=IPizzaRepository)
    repository.get_menu_async.return_value = []
    repository.get_by_name_async.return_value = None
    return repository


@pytest.fixture
def mock_customer_repository():
    """Mock customer repository"""
    repository = Mock(spec=ICustomerRepository)
    repository.save_async.return_value = None
    repository.get_by_phone_async.return_value = None
    return repository


@pytest.fixture
def mock_kitchen_repository():
    """Mock kitchen repository"""
    repository = Mock(spec=IKitchenRepository)
    repository.get_status_async.return_value = None
    repository.save_status_async.return_value = None
    return repository


@pytest.fixture
def file_order_repository(temp_data_dir):
    """File-based order repository for integration tests"""
    return FileOrderRepository(str(Path(temp_data_dir) / "orders"))


@pytest.fixture
def file_pizza_repository(temp_data_dir):
    """File-based pizza repository for integration tests"""
    return FilePizzaRepository(str(Path(temp_data_dir) / "menu"))


@pytest.fixture
def file_customer_repository(temp_data_dir):
    """File-based customer repository for integration tests"""
    return FileCustomerRepository(str(Path(temp_data_dir) / "customers"))


@pytest.fixture
def file_kitchen_repository(temp_data_dir):
    """File-based kitchen repository for integration tests"""
    return FileKitchenRepository(str(Path(temp_data_dir) / "kitchen"))


@pytest.fixture
def service_collection():
    """Service collection for dependency injection tests"""
    return ServiceCollection()


@pytest.fixture
def mediator_with_mocks(
    service_collection,
    mock_order_repository,
    mock_pizza_repository,
    mock_customer_repository,
    mock_kitchen_repository,
):
    """Mediator configured with mock repositories"""
    # Register mock repositories
    service_collection.add_singleton(IOrderRepository, lambda: mock_order_repository)
    service_collection.add_singleton(IPizzaRepository, lambda: mock_pizza_repository)
    service_collection.add_singleton(ICustomerRepository, lambda: mock_customer_repository)
    service_collection.add_singleton(IKitchenRepository, lambda: mock_kitchen_repository)

    # Register handlers
    from application.handlers import (
        PlaceOrderCommandHandler,
        StartCookingCommandHandler,
        CompleteOrderCommandHandler,
        GetOrderByIdQueryHandler,
        GetMenuQueryHandler,
        GetKitchenStatusQueryHandler,
    )

    service_collection.add_scoped(PlaceOrderCommandHandler)
    service_collection.add_scoped(StartCookingCommandHandler)
    service_collection.add_scoped(CompleteOrderCommandHandler)
    service_collection.add_scoped(GetOrderByIdQueryHandler)
    service_collection.add_scoped(GetMenuQueryHandler)
    service_collection.add_scoped(GetKitchenStatusQueryHandler)

    # Configure mediator
    Mediator.configure(service_collection, ["application.handlers"])

    # Build service provider
    provider = service_collection.build_provider()
    return provider.get_service(Mediator)


@pytest.fixture
def sample_menu_data():
    """Sample menu data for testing"""
    return [
        {
            "name": "Margherita",
            "base_price": 12.99,
            "available_sizes": {"small": 0.8, "medium": 1.0, "large": 1.3},
            "available_toppings": {
                "extra cheese": 1.50,
                "mushrooms": 1.00,
                "pepperoni": 1.50,
                "olives": 1.00,
            },
        },
        {
            "name": "Pepperoni",
            "base_price": 14.99,
            "available_sizes": {"small": 0.8, "medium": 1.0, "large": 1.3},
            "available_toppings": {
                "extra cheese": 1.50,
                "mushrooms": 1.00,
                "olives": 1.00,
                "peppers": 1.00,
            },
        },
    ]


def create_test_order(customer_name="Test Customer", pizzas_count=1):
    """Helper function to create test orders"""
    customer = Customer(name=customer_name, phone="+1-555-0123", address="123 Test Street")

    pizzas = []
    for i in range(pizzas_count):
        pizzas.append(
            Pizza(name="Margherita", size="medium", toppings=["extra cheese"] if i % 2 == 0 else [])
        )

    return Order(customer=customer, pizzas=pizzas, payment_method="credit_card")


def create_test_pizza(name="Test Pizza", size="medium", toppings=None):
    """Helper function to create test pizzas"""
    if toppings is None:
        toppings = []

    return Pizza(name=name, size=size, toppings=toppings)


def create_test_customer(name="Test Customer", phone="+1-555-0123"):
    """Helper function to create test customers"""
    return Customer(name=name, phone=phone, address="123 Test Street")
