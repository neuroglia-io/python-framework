# 🏗️ Python Modular Code Reference

Understanding modular code organization is essential for working with the Neuroglia framework, which emphasizes clean architecture and separation of concerns.

## 🎯 What is Modular Code?

Modular code organizes functionality into separate, reusable components (modules) that have clear responsibilities and well-defined interfaces. This makes code easier to understand, test, maintain, and extend.

### The Pizza Kitchen Analogy

Think of a pizzeria kitchen:

```python
# ❌ Everything in one big file (messy kitchen):
# pizza_chaos.py - 2000+ lines doing everything

def make_dough():
    pass

def prepare_sauce():
    pass

def add_toppings():
    pass

def bake_pizza():
    pass

def take_order():
    pass

def process_payment():
    pass

def manage_inventory():
    pass

# ... 1900+ more lines

# ✅ Organized into modules (specialized stations):

# dough_station.py
def make_dough(flour_type: str, water_amount: float) -> Dough:
    """Specialized dough preparation."""
    pass

# sauce_station.py
def prepare_marinara() -> Sauce:
    """Specialized sauce preparation."""
    pass

# assembly_station.py
def assemble_pizza(dough: Dough, sauce: Sauce, toppings: List[str]) -> Pizza:
    """Specialized pizza assembly."""
    pass

# order_management.py
def take_order(customer: Customer, items: List[str]) -> Order:
    """Specialized order handling."""
    pass
```

## 🔧 Python Module Basics

### What is a Module?

A module is simply a Python file containing code. When you create a `.py` file, you've created a module.

```python
# math_utils.py - This is a module
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b

def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

PI = 3.14159

# Using the module in another file:
# main.py
import math_utils

result = math_utils.add(5, 3)
circle_area = math_utils.PI * radius ** 2
```

### Packages - Modules Organized in Directories

A package is a directory containing multiple modules:

```
mario_pizzeria/
├── __init__.py          # Makes this a package
├── pizza.py             # Pizza-related code
├── customer.py          # Customer-related code
└── order.py             # Order-related code
```

```python
# __init__.py - Package initialization
"""Mario's Pizzeria - A delicious pizza ordering system."""

__version__ = "1.0.0"
__author__ = "Mario"

# pizza.py
from dataclasses import dataclass
from typing import List

@dataclass
class Pizza:
    name: str
    price: float
    ingredients: List[str]

def create_margherita() -> Pizza:
    return Pizza(
        name="Margherita",
        price=12.99,
        ingredients=["tomato", "mozzarella", "basil"]
    )

# Using the package:
from mario_pizzeria.pizza import Pizza, create_margherita
from mario_pizzeria import __version__

margherita = create_margherita()
print(f"Using Mario's Pizzeria v{__version__}")
```

## 🏛️ Neuroglia Framework Architecture

The Neuroglia framework follows a layered architecture with clear module organization:

### Directory Structure

```
src/
├── neuroglia/                    # Framework core
│   ├── __init__.py
│   ├── dependency_injection/     # DI container modules
│   │   ├── __init__.py
│   │   ├── service_collection.py
│   │   ├── service_provider.py
│   │   └── extensions.py
│   ├── mediation/               # CQRS pattern modules
│   │   ├── __init__.py
│   │   ├── mediator.py
│   │   ├── commands.py
│   │   ├── queries.py
│   │   └── handlers.py
│   ├── mvc/                     # MVC pattern modules
│   │   ├── __init__.py
│   │   ├── controller_base.py
│   │   └── routing.py
│   └── data/                    # Data access modules
│       ├── __init__.py
│       ├── repository.py
│       └── mongo_repository.py
└── mario_pizzeria/              # Application code
    ├── __init__.py
    ├── api/                     # API layer
    │   ├── __init__.py
    │   ├── controllers/
    │   │   ├── __init__.py
    │   │   └── pizza_controller.py
    │   └── dtos/
    │       ├── __init__.py
    │       └── pizza_dto.py
    ├── application/             # Application layer
    │   ├── __init__.py
    │   ├── commands/
    │   │   ├── __init__.py
    │   │   └── create_pizza_command.py
    │   ├── queries/
    │   │   ├── __init__.py
    │   │   └── get_pizza_query.py
    │   └── handlers/
    │       ├── __init__.py
    │       ├── create_pizza_handler.py
    │       └── get_pizza_handler.py
    ├── domain/                  # Domain layer
    │   ├── __init__.py
    │   ├── entities/
    │   │   ├── __init__.py
    │   │   └── pizza.py
    │   └── repositories/
    │       ├── __init__.py
    │       └── pizza_repository.py
    └── integration/             # Integration layer
        ├── __init__.py
        └── repositories/
            ├── __init__.py
            └── mongo_pizza_repository.py
```

### Module Organization Principles

#### 1. Single Responsibility Principle

Each module should have one clear purpose:

```python
# ✅ Good - pizza.py focuses only on Pizza entity
from dataclasses import dataclass
from typing import List
from datetime import datetime

@dataclass
class Pizza:
    """Represents a pizza entity."""
    id: str
    name: str
    price: float
    ingredients: List[str]
    created_at: datetime
    is_available: bool = True

    def add_ingredient(self, ingredient: str) -> None:
        """Add an ingredient to the pizza."""
        if ingredient not in self.ingredients:
            self.ingredients.append(ingredient)

    def calculate_cost(self) -> float:
        """Calculate base cost based on ingredients."""
        base_cost = 8.0
        return base_cost + (len(self.ingredients) * 0.50)

# ❌ Bad - pizza_everything.py tries to do too much
class Pizza:
    # Pizza logic...
    pass

class Customer:  # Should be in customer.py
    pass

class Order:     # Should be in order.py
    pass

def send_email():    # Should be in notification.py
    pass

def connect_to_database():  # Should be in database.py
    pass
```

#### 2. High Cohesion, Low Coupling

Related functionality stays together, unrelated functionality is separated:

```python
# High cohesion - pizza_operations.py
from typing import List, Optional
from .pizza import Pizza

class PizzaService:
    """Service for pizza-related operations."""

    def __init__(self, repository: 'PizzaRepository'):
        self._repository = repository

    async def create_pizza(self, name: str, price: float, ingredients: List[str]) -> Pizza:
        """Create a new pizza."""
        pizza = Pizza(
            id=self._generate_id(),
            name=name,
            price=price,
            ingredients=ingredients,
            created_at=datetime.now()
        )
        await self._repository.save_async(pizza)
        return pizza

    async def get_available_pizzas(self) -> List[Pizza]:
        """Get all available pizzas."""
        all_pizzas = await self._repository.get_all_async()
        return [pizza for pizza in all_pizzas if pizza.is_available]

    def _generate_id(self) -> str:
        """Generate unique pizza ID."""
        return str(uuid.uuid4())

# Low coupling - separate concerns into different modules
# customer_service.py
class CustomerService:
    """Service for customer-related operations."""
    pass

# order_service.py
class OrderService:
    """Service for order-related operations."""
    pass
```

## 📦 Import Strategies

### Absolute vs Relative Imports

```python
# Project structure:
mario_pizzeria/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── pizza.py
│   │   └── customer.py
│   └── services/
│       ├── __init__.py
│       └── pizza_service.py
└── infrastructure/
    ├── __init__.py
    └── repositories/
        ├── __init__.py
        └── pizza_repository.py

# ✅ Absolute imports (preferred for clarity):
# In pizza_service.py
from mario_pizzeria.domain.entities.pizza import Pizza
from mario_pizzeria.domain.entities.customer import Customer
from mario_pizzeria.infrastructure.repositories.pizza_repository import PizzaRepository

# ✅ Relative imports (good for internal package references):
# In pizza_service.py
from ..entities.pizza import Pizza
from ..entities.customer import Customer
from ...infrastructure.repositories.pizza_repository import PizzaRepository

# ❌ Avoid mixing styles in the same file
```

### Import Organization

Organize imports in a standard order:

```python
# Standard library imports
import os
import sys
from datetime import datetime
from typing import List, Optional, Dict

# Third-party imports
import fastapi
from pydantic import BaseModel
import pymongo

# Local application imports
from neuroglia.dependency_injection import ServiceProvider
from neuroglia.mediation import Mediator, Command, Query

# Local relative imports
from .pizza import Pizza
from .customer import Customer
from ..repositories.pizza_repository import PizzaRepository
```

### Controlling What Gets Imported

Use `__init__.py` files to control the public API:

```python
# domain/entities/__init__.py
"""Domain entities for Mario's Pizzeria."""

from .pizza import Pizza
from .customer import Customer
from .order import Order

# Make only specific classes available when importing the package
__all__ = ['Pizza', 'Customer', 'Order']

# Usage - clean imports for users:
from mario_pizzeria.domain.entities import Pizza, Customer
# Instead of:
# from mario_pizzeria.domain.entities.pizza import Pizza
# from mario_pizzeria.domain.entities.customer import Customer
```

### Lazy Loading for Performance

Load expensive modules only when needed:

```python
# heavy_analytics.py - expensive to import
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def generate_sales_report() -> pd.DataFrame:
    # Expensive analytics operations
    pass

# pizza_service.py - lazy loading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Import only for type checking, not at runtime
    from .heavy_analytics import generate_sales_report

class PizzaService:
    def get_basic_stats(self) -> dict:
        """Fast operation - no heavy imports needed."""
        return {"total_pizzas": 42}

    def get_detailed_analytics(self) -> 'pd.DataFrame':
        """Load analytics module only when needed."""
        from .heavy_analytics import generate_sales_report
        return generate_sales_report()
```

## 🎨 Advanced Modular Patterns

### Factory Pattern with Modules

Organize related creation logic:

```python
# factories/__init__.py
from .pizza_factory import PizzaFactory
from .customer_factory import CustomerFactory

__all__ = ['PizzaFactory', 'CustomerFactory']

# factories/pizza_factory.py
from typing import List
from ..domain.entities.pizza import Pizza

class PizzaFactory:
    """Factory for creating different types of pizzas."""

    @staticmethod
    def create_margherita() -> Pizza:
        return Pizza(
            id=PizzaFactory._generate_id(),
            name="Margherita",
            price=12.99,
            ingredients=["tomato sauce", "mozzarella", "basil"],
            created_at=datetime.now()
        )

    @staticmethod
    def create_pepperoni() -> Pizza:
        return Pizza(
            id=PizzaFactory._generate_id(),
            name="Pepperoni",
            price=14.99,
            ingredients=["tomato sauce", "mozzarella", "pepperoni"],
            created_at=datetime.now()
        )

    @staticmethod
    def create_custom(name: str, ingredients: List[str]) -> Pizza:
        base_price = 10.0
        price = base_price + (len(ingredients) * 1.50)

        return Pizza(
            id=PizzaFactory._generate_id(),
            name=name,
            price=price,
            ingredients=ingredients,
            created_at=datetime.now()
        )

    @staticmethod
    def _generate_id() -> str:
        return str(uuid.uuid4())

# Usage:
from mario_pizzeria.factories import PizzaFactory

margherita = PizzaFactory.create_margherita()
custom_pizza = PizzaFactory.create_custom("Veggie Supreme",
                                         ["tomato", "mozzarella", "mushrooms", "peppers"])
```

### Plugin Architecture with Modules

Create extensible systems using module discovery:

```python
# plugins/__init__.py
"""Plugin system for Mario's Pizzeria."""

import importlib
import pkgutil
from typing import List, Type
from abc import ABC, abstractmethod

class PizzaPlugin(ABC):
    """Base class for pizza plugins."""

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def create_pizza(self) -> Pizza:
        pass

def discover_plugins() -> List[Type[PizzaPlugin]]:
    """Discover all available pizza plugins."""
    plugins = []

    # Discover plugins in the plugins package
    for finder, name, ispkg in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f'{__name__}.{name}')

        # Find all plugin classes in the module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                issubclass(attr, PizzaPlugin) and
                attr is not PizzaPlugin):
                plugins.append(attr)

    return plugins

# plugins/italian_classics.py
from . import PizzaPlugin
from ..domain.entities.pizza import Pizza

class MargheritaPlugin(PizzaPlugin):
    def get_name(self) -> str:
        return "Margherita"

    def create_pizza(self) -> Pizza:
        return Pizza(
            id=str(uuid.uuid4()),
            name="Margherita",
            price=12.99,
            ingredients=["tomato", "mozzarella", "basil"]
        )

class QuattroStagioniPlugin(PizzaPlugin):
    def get_name(self) -> str:
        return "Quattro Stagioni"

    def create_pizza(self) -> Pizza:
        return Pizza(
            id=str(uuid.uuid4()),
            name="Quattro Stagioni",
            price=16.99,
            ingredients=["tomato", "mozzarella", "ham", "mushrooms", "artichokes", "olives"]
        )

# plugins/american_style.py
from . import PizzaPlugin
from ..domain.entities.pizza import Pizza

class PepperoniPlugin(PizzaPlugin):
    def get_name(self) -> str:
        return "Pepperoni"

    def create_pizza(self) -> Pizza:
        return Pizza(
            id=str(uuid.uuid4()),
            name="Pepperoni",
            price=14.99,
            ingredients=["tomato", "mozzarella", "pepperoni"]
        )

# Usage:
from mario_pizzeria.plugins import discover_plugins

# Automatically discover all pizza plugins
available_plugins = discover_plugins()
for plugin_class in available_plugins:
    plugin = plugin_class()
    print(f"Available: {plugin.get_name()}")
    pizza = plugin.create_pizza()
```

### Configuration Modules

Organize configuration in modules:

```python
# config/__init__.py
from .database import DatabaseConfig
from .api import ApiConfig
from .logging import LoggingConfig

# config/database.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    host: str = "localhost"
    port: int = 27017
    database: str = "mario_pizzeria"
    username: Optional[str] = None
    password: Optional[str] = None
    connection_timeout: int = 30

    @property
    def connection_string(self) -> str:
        """Generate MongoDB connection string."""
        if self.username and self.password:
            return f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        return f"mongodb://{self.host}:{self.port}/{self.database}"

# config/api.py
@dataclass
class ApiConfig:
    """API configuration settings."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: List[str] = None
    api_prefix: str = "/api/v1"

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["http://localhost:3000"]

# config/logging.py
import logging
from typing import Dict

@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers: List[str] = None

    def __post_init__(self):
        if self.handlers is None:
            self.handlers = ["console", "file"]

    def get_level(self) -> int:
        """Convert string level to logging constant."""
        return getattr(logging, self.level.upper(), logging.INFO)

# Usage:
from mario_pizzeria.config import DatabaseConfig, ApiConfig, LoggingConfig

db_config = DatabaseConfig(host="production-mongo", database="pizzeria_prod")
api_config = ApiConfig(port=8080, debug=False)
log_config = LoggingConfig(level="WARNING")

print(f"Database: {db_config.connection_string}")
print(f"API will run on: {api_config.host}:{api_config.port}")
print(f"Log level: {log_config.get_level()}")
```

## 🧪 Testing Modular Code

Organize tests to mirror your module structure:

```
tests/
├── __init__.py
├── conftest.py              # Shared test fixtures
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── test_pizza.py
│   │   └── test_customer.py
│   ├── application/
│   │   ├── __init__.py
│   │   └── test_pizza_service.py
│   └── infrastructure/
│       ├── __init__.py
│       └── test_pizza_repository.py
├── integration/             # Integration tests
│   ├── __init__.py
│   ├── test_api_endpoints.py
│   └── test_database_integration.py
└── fixtures/               # Test data
    ├── __init__.py
    ├── pizza_fixtures.py
    └── customer_fixtures.py
```

```python
# tests/conftest.py - Shared fixtures
import pytest
from mario_pizzeria.domain.entities.pizza import Pizza
from mario_pizzeria.infrastructure.repositories.in_memory_pizza_repository import InMemoryPizzaRepository

@pytest.fixture
def sample_pizza() -> Pizza:
    """Create a sample pizza for testing."""
    return Pizza(
        id="test-pizza-1",
        name="Test Margherita",
        price=12.99,
        ingredients=["tomato", "mozzarella", "basil"]
    )

@pytest.fixture
def pizza_repository() -> InMemoryPizzaRepository:
    """Create an in-memory pizza repository for testing."""
    return InMemoryPizzaRepository()

# tests/unit/domain/test_pizza.py
import pytest
from mario_pizzeria.domain.entities.pizza import Pizza

class TestPizza:
    def test_pizza_creation(self, sample_pizza):
        """Test pizza entity creation."""
        assert sample_pizza.name == "Test Margherita"
        assert sample_pizza.price == 12.99
        assert "tomato" in sample_pizza.ingredients

    def test_add_ingredient(self, sample_pizza):
        """Test adding ingredient to pizza."""
        sample_pizza.add_ingredient("oregano")
        assert "oregano" in sample_pizza.ingredients

    def test_calculate_cost(self, sample_pizza):
        """Test pizza cost calculation."""
        cost = sample_pizza.calculate_cost()
        expected_cost = 8.0 + (3 * 0.50)  # base + (3 ingredients * 0.50)
        assert cost == expected_cost

# tests/fixtures/pizza_fixtures.py
from typing import List
from mario_pizzeria.domain.entities.pizza import Pizza

class PizzaFixtures:
    """Factory for creating test pizza data."""

    @staticmethod
    def create_margherita() -> Pizza:
        return Pizza(
            id="margherita-1",
            name="Margherita",
            price=12.99,
            ingredients=["tomato", "mozzarella", "basil"]
        )

    @staticmethod
    def create_pizza_list() -> List[Pizza]:
        return [
            PizzaFixtures.create_margherita(),
            Pizza("pepperoni-1", "Pepperoni", 14.99, ["tomato", "mozzarella", "pepperoni"]),
            Pizza("hawaiian-1", "Hawaiian", 13.49, ["tomato", "mozzarella", "ham", "pineapple"])
        ]
```

## 🚀 Best Practices for Modular Code

### 1. Use Meaningful Module Names

```python
# ✅ Good - clear, descriptive names:
pizza_service.py
customer_repository.py
order_validation.py
payment_processing.py

# ❌ Bad - vague or abbreviated names:
util.py
helper.py
stuff.py
ps.py (pizza service?)
```

### 2. Keep Modules Focused and Small

```python
# ✅ Good - focused pizza entity module (50-100 lines):
# domain/entities/pizza.py
from dataclasses import dataclass
from typing import List
from datetime import datetime

@dataclass
class Pizza:
    id: str
    name: str
    price: float
    ingredients: List[str]
    created_at: datetime
    is_available: bool = True

    def add_ingredient(self, ingredient: str) -> None:
        if ingredient not in self.ingredients:
            self.ingredients.append(ingredient)

    def remove_ingredient(self, ingredient: str) -> None:
        if ingredient in self.ingredients:
            self.ingredients.remove(ingredient)

    def calculate_cost(self) -> float:
        base_cost = 8.0
        return base_cost + (len(self.ingredients) * 0.50)

# ❌ Bad - trying to do everything in one module (1000+ lines)
```

### 3. Use Dependency Injection for Module Coupling

```python
# ✅ Good - dependency injection reduces coupling:
class PizzaService:
    def __init__(self,
                 repository: PizzaRepository,
                 validator: PizzaValidator,
                 notifier: NotificationService):
        self._repository = repository
        self._validator = validator
        self._notifier = notifier

    async def create_pizza(self, pizza_data: dict) -> Pizza:
        # Use injected dependencies
        if not self._validator.is_valid(pizza_data):
            raise ValidationError("Invalid pizza data")

        pizza = Pizza(**pizza_data)
        await self._repository.save_async(pizza)
        await self._notifier.notify_pizza_created(pizza)
        return pizza

# ❌ Bad - tight coupling with direct imports:
class PizzaService:
    def __init__(self):
        self._repository = MongoPizzaRepository()  # Tightly coupled
        self._validator = PizzaValidator()         # Hard to test
        self._notifier = EmailNotifier()          # Can't swap implementations
```

### 4. Design Clear Module Interfaces

```python
# ✅ Good - clear, well-defined interface:
# repositories/pizza_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from ..domain.entities.pizza import Pizza

class PizzaRepository(ABC):
    """Interface for pizza data access operations."""

    @abstractmethod
    async def get_by_id_async(self, pizza_id: str) -> Optional[Pizza]:
        """Get pizza by ID, returns None if not found."""
        pass

    @abstractmethod
    async def get_by_name_async(self, name: str) -> List[Pizza]:
        """Get all pizzas matching the given name."""
        pass

    @abstractmethod
    async def save_async(self, pizza: Pizza) -> None:
        """Save pizza to storage."""
        pass

    @abstractmethod
    async def delete_async(self, pizza_id: str) -> bool:
        """Delete pizza, returns True if deleted."""
        pass

    @abstractmethod
    async def get_available_pizzas_async(self) -> List[Pizza]:
        """Get all available pizzas."""
        pass

# Concrete implementation:
class MongoPizzaRepository(PizzaRepository):
    """MongoDB implementation of pizza repository."""

    def __init__(self, collection):
        self._collection = collection

    async def get_by_id_async(self, pizza_id: str) -> Optional[Pizza]:
        # MongoDB-specific implementation
        pass

    # ... implement other methods
```

### 5. Use Module-Level Constants and Configuration

```python
# constants/pizza_constants.py
"""Constants for pizza-related operations."""

# Pizza sizes
SMALL_SIZE = "small"
MEDIUM_SIZE = "medium"
LARGE_SIZE = "large"

PIZZA_SIZES = [SMALL_SIZE, MEDIUM_SIZE, LARGE_SIZE]

# Price multipliers by size
SIZE_MULTIPLIERS = {
    SMALL_SIZE: 0.8,
    MEDIUM_SIZE: 1.0,
    LARGE_SIZE: 1.3
}

# Ingredient categories
CHEESE_INGREDIENTS = ["mozzarella", "parmesan", "ricotta", "goat cheese"]
MEAT_INGREDIENTS = ["pepperoni", "sausage", "ham", "bacon", "chicken"]
VEGETABLE_INGREDIENTS = ["mushrooms", "peppers", "onions", "tomatoes", "spinach"]

# Business rules
MAX_INGREDIENTS_PER_PIZZA = 8
MIN_PIZZA_PRICE = 8.99
MAX_PIZZA_PRICE = 29.99

# Usage in other modules:
from mario_pizzeria.constants.pizza_constants import (
    PIZZA_SIZES,
    SIZE_MULTIPLIERS,
    MAX_INGREDIENTS_PER_PIZZA
)

class PizzaValidator:
    def validate_ingredients(self, ingredients: List[str]) -> bool:
        return len(ingredients) <= MAX_INGREDIENTS_PER_PIZZA

    def validate_size(self, size: str) -> bool:
        return size in PIZZA_SIZES
```

### 6. Document Module Purposes and APIs

```python
# services/pizza_service.py
"""
Pizza Service Module

This module provides business logic for pizza operations including creation,
validation, pricing, and management. It serves as the main interface between
the API layer and the domain/data layers.

Classes:
    PizzaService: Main service class for pizza operations
    PizzaValidator: Validation logic for pizza data
    PricingCalculator: Pricing logic for pizzas

Dependencies:
    - domain.entities.pizza: Pizza entity
    - repositories.pizza_repository: Data access interface
    - services.notification_service: Notification capabilities

Example:
    >>> from mario_pizzeria.services import PizzaService
    >>> service = PizzaService(repository, validator, notifier)
    >>> pizza = await service.create_pizza({
    ...     "name": "Margherita",
    ...     "ingredients": ["tomato", "mozzarella", "basil"]
    ... })
"""

from typing import List, Optional, Dict, Any
from ..domain.entities.pizza import Pizza
from ..repositories.pizza_repository import PizzaRepository

class PizzaService:
    """
    Service class for pizza business operations.

    This service handles pizza creation, validation, pricing calculations,
    and coordinates with repositories and notification services.

    Attributes:
        _repository: Pizza data access repository
        _validator: Pizza validation service
        _notifier: Notification service for pizza events
    """

    def __init__(self,
                 repository: PizzaRepository,
                 validator: 'PizzaValidator',
                 notifier: 'NotificationService'):
        """
        Initialize the pizza service.

        Args:
            repository: Repository for pizza data access
            validator: Service for validating pizza data
            notifier: Service for sending notifications
        """
        self._repository = repository
        self._validator = validator
        self._notifier = notifier

    async def create_pizza(self, pizza_data: Dict[str, Any]) -> Pizza:
        """
        Create a new pizza with validation and notification.

        Args:
            pizza_data: Dictionary containing pizza information with keys:
                - name (str): Pizza name
                - price (float): Pizza price
                - ingredients (List[str]): List of ingredients

        Returns:
            Pizza: The created pizza entity

        Raises:
            ValidationError: If pizza data is invalid
            RepositoryError: If save operation fails

        Example:
            >>> pizza_data = {
            ...     "name": "Margherita",
            ...     "price": 12.99,
            ...     "ingredients": ["tomato", "mozzarella", "basil"]
            ... }
            >>> pizza = await service.create_pizza(pizza_data)
        """
        # Implementation here...
        pass
```

## 🔗 Related Documentation

- [Python Object-Oriented Programming](python_object_oriented.md) - Classes and inheritance in modular design
- [Python Typing Guide](python_typing_guide.md) - Type safety, generics, and modular programming patterns
- [Dependency Injection](../patterns/dependency-injection.md) - Managing dependencies between modules
- [CQRS & Mediation](../patterns/cqrs.md) - Organizing commands and queries in modules

## 📚 Further Reading

- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Python Module Documentation](https://docs.python.org/3/tutorial/modules.html)
- [Clean Architecture by Robert Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Python Package Discovery](https://docs.python.org/3/library/pkgutil.html)
