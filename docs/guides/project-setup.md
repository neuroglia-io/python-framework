# 🚀 Project Setup Guide

!!! warning "🚧 Under Construction"
This guide is currently being developed with comprehensive setup procedures and troubleshooting tips. More detailed examples and best practices are being added.

Complete guide for setting up new Neuroglia Python Framework projects, from initial creation to deployment-ready applications.

## 🎯 Overview

This guide walks you through creating a new Neuroglia project using the Mario's Pizzeria example, covering project structure, dependency management, and initial configuration.

## 📋 Prerequisites

Before starting, ensure you have:

- **Python 3.9+** installed
- **Poetry** for dependency management
- **Git** for version control
- **VS Code** or preferred IDE

```bash
# Verify Python version
python --version  # Should be 3.9 or higher

# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Verify Poetry installation
poetry --version
```

## 🏗️ Creating a New Project

### Option 1: Using PyNeuroctl (Recommended)

```bash
# Install the CLI tool
pip install neuroglia-cli

# Create new project from pizzeria template
pyneuroctl new my-pizzeria --template pizzeria
cd my-pizzeria

# Install dependencies
poetry install

# Run the application
poetry run python main.py
```

### Option 2: Manual Setup

```bash
# Create project directory
mkdir my-pizzeria && cd my-pizzeria

# Initialize Poetry project
poetry init --name my-pizzeria --description "Pizza ordering system"

# Add Neuroglia framework
poetry add neuroglia

# Add development dependencies
poetry add --group dev pytest pytest-asyncio httpx

# Create project structure
mkdir -p src/{api,application,domain,integration}
mkdir -p tests/{unit,integration}
```

## 📁 Project Structure

Create the clean architecture structure:

```
my-pizzeria/
├── pyproject.toml              # Project configuration
├── main.py                     # Application entry point
├── README.md                   # Project documentation
├── .env                        # Environment variables
├── .gitignore                  # Git ignore patterns
├── src/
│   ├── __init__.py
│   ├── api/                    # 🌐 API Layer
│   │   ├── __init__.py
│   │   ├── controllers/        # REST endpoints
│   │   └── dtos/              # Request/response models
│   ├── application/            # 💼 Application Layer
│   │   ├── __init__.py
│   │   ├── commands/          # Write operations
│   │   ├── queries/           # Read operations
│   │   ├── handlers/          # Business logic
│   │   └── services/          # Application services
│   ├── domain/                # 🏛️ Domain Layer
│   │   ├── __init__.py
│   │   ├── entities/          # Business entities
│   │   ├── events/            # Domain events
│   │   └── repositories/      # Repository interfaces
│   └── integration/           # 🔌 Integration Layer
│       ├── __init__.py
│       ├── repositories/      # Data access implementations
│       └── services/          # External service integrations
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Test configuration
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
└── docs/                     # Project documentation
```

## ⚙️ Configuration Setup

### 1. Environment Configuration

Create `.env` file:

```env
# Application Settings
APP_NAME=My Pizzeria
APP_VERSION=1.0.0
DEBUG=true

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Database Configuration
DATABASE_TYPE=mongodb
MONGODB_CONNECTION_STRING=mongodb://localhost:27017/pizzeria

# External Services
SMS_SERVICE_API_KEY=your_sms_api_key
EMAIL_SERVICE_API_KEY=your_email_api_key
PAYMENT_GATEWAY_API_KEY=your_payment_api_key

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 2. Project Configuration

Update `pyproject.toml`:

```toml
[tool.poetry]
name = "my-pizzeria"
version = "1.0.0"
description = "Pizza ordering system built with Neuroglia"
authors = ["Your Name <your.email@example.com>"]
packages = [{include = "src"}]

[tool.poetry.dependencies]
python = "^3.9"
neuroglia = "^0.3.0"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"
motor = "^3.3.0"  # MongoDB async driver
pydantic-settings = "^2.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
httpx = "^0.25.0"
pytest-cov = "^4.1.0"
black = "^23.0.0"
isort = "^5.12.0"
mypy = "^1.6.0"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]

[tool.black]
line-length = 100
target-version = ['py39']

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 100

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

## 🍕 Initial Implementation

### 1. Application Entry Point

Create `main.py`:

```python
import asyncio
from src.startup import create_app

async def main():
    """Application entry point"""
    app = await create_app()

    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True  # Development only
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Application Startup

Create `src/startup.py`:

```python
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.dependency_injection import ServiceCollection
from src.api.controllers.orders_controller import OrdersController
from src.application.handlers.place_order_handler import PlaceOrderHandler
from src.integration.repositories.mongo_order_repository import MongoOrderRepository

async def create_app():
    """Configure and build the application"""
    builder = WebApplicationBuilder()

    # Configure services
    configure_services(builder.services)

    # Build application
    app = builder.build()

    # Configure core services
    configure_services(builder)

    # Configure middleware
    configure_middleware(app)

    return app

def configure_services(builder: WebApplicationBuilder):
    """Configure dependency injection"""
    # Configure framework services
    Mediator.configure(builder, ["application.commands", "application.queries"])
    Mapper.configure(builder, ["application.mapping", "api.dtos", "domain.entities"])

    # Add SubApp with controllers
    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            controllers=["src.api.controllers"]
        )
    )

    # Add repositories
    builder.services.add_scoped(MongoOrderRepository)

    # Add external services
    # builder.services.add_scoped(SMSService)
    # builder.services.add_scoped(PaymentService)

def configure_middleware(app):
    """Configure application middleware"""
    # Add CORS if needed
    # app.add_middleware(CORSMiddleware, ...)

    # Add authentication if needed
    # app.add_middleware(AuthenticationMiddleware, ...)

    pass
```

### 3. First Domain Entity

Create `src/domain/entities/order.py`:

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from enum import Enum
from neuroglia.domain import Entity
from src.domain.events.order_events import OrderPlacedEvent

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

@dataclass
class OrderItem:
    pizza_name: str
    size: str
    quantity: int
    price: Decimal

class Order(Entity):
    def __init__(self,
                 customer_id: str,
                 items: List[OrderItem],
                 delivery_address: str,
                 special_instructions: Optional[str] = None):
        super().__init__()
        self.customer_id = customer_id
        self.items = items
        self.delivery_address = delivery_address
        self.special_instructions = special_instructions
        self.status = OrderStatus.PENDING
        self.total = self._calculate_total()
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at

        # Raise domain event
        self.raise_event(OrderPlacedEvent(
            order_id=self.id,
            customer_id=customer_id,
            total=self.total,
            items=items
        ))

    def _calculate_total(self) -> Decimal:
        """Calculate order total with tax"""
        subtotal = sum(item.price * item.quantity for item in self.items)
        tax = subtotal * Decimal('0.08')  # 8% tax
        return subtotal + tax

    def confirm(self):
        """Confirm the order"""
        if self.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be confirmed")
        self.status = OrderStatus.CONFIRMED
        self.updated_at = datetime.now(timezone.utc)
```

### 4. First Command Handler

Create `src/application/handlers/place_order_handler.py`:

```python
from dataclasses import dataclass
from typing import List
from neuroglia.mediation import Command, CommandHandler
from neuroglia.core import OperationResult
from src.domain.entities.order import Order, OrderItem
from src.api.dtos.order_dto import OrderDto

@dataclass
class PlaceOrderCommand(Command[OperationResult[OrderDto]]):
    customer_id: str
    items: List[OrderItem]
    delivery_address: str
    special_instructions: str = None

class PlaceOrderHandler(CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]):
    def __init__(self, order_repository):
        self._repository = order_repository

    async def handle_async(self, command: PlaceOrderCommand) -> OperationResult[OrderDto]:
        try:
            # Create domain entity
            order = Order(
                customer_id=command.customer_id,
                items=command.items,
                delivery_address=command.delivery_address,
                special_instructions=command.special_instructions
            )

            # Persist order
            await self._repository.save_async(order)

            # Return success result
            dto = OrderDto(
                id=order.id,
                customer_id=order.customer_id,
                total=order.total,
                status=order.status.value,
                created_at=order.created_at
            )

            return self.created(dto)

        except Exception as ex:
            return self.internal_server_error(f"Failed to place order: {str(ex)}")
```

### 5. First Controller

Create `src/api/controllers/orders_controller.py`:

```python
from fastapi import HTTPException
from neuroglia.mvc import ControllerBase
from classy_fastapi import post
from src.application.handlers.place_order_handler import PlaceOrderCommand
from src.api.dtos.place_order_request import PlaceOrderRequest
from src.api.dtos.order_dto import OrderDto

class OrdersController(ControllerBase):

    @post("/orders", response_model=OrderDto, status_code=201)
    async def place_order(self, request: PlaceOrderRequest) -> OrderDto:
        """Place a new pizza order"""
        command = PlaceOrderCommand(
            customer_id=request.customer_id,
            items=request.items,
            delivery_address=request.delivery_address,
            special_instructions=request.special_instructions
        )

        result = await self.mediator.execute_async(command)

        if result.is_success:
            return result.data
        else:
            raise HTTPException(
                status_code=result.status_code,
                detail=result.error_message
            )
```

## 🧪 Testing Setup

### 1. Test Configuration

Create `tests/conftest.py`:

```python
import pytest
from unittest.mock import Mock
from neuroglia.dependency_injection import ServiceCollection
from src.startup import configure_services

@pytest.fixture
def service_collection():
    """Provide a configured service collection for testing"""
    services = ServiceCollection()
    configure_services(services)
    return services

@pytest.fixture
def mock_order_repository():
    """Provide a mocked order repository"""
    return Mock()

@pytest.fixture
def sample_order_items():
    """Provide sample order items for testing"""
    from src.domain.entities.order import OrderItem
    from decimal import Decimal

    return [
        OrderItem(
            pizza_name="Margherita",
            size="Large",
            quantity=1,
            price=Decimal('15.99')
        ),
        OrderItem(
            pizza_name="Pepperoni",
            size="Medium",
            quantity=2,
            price=Decimal('12.99')
        )
    ]
```

### 2. First Unit Test

Create `tests/unit/test_place_order_handler.py`:

```python
import pytest
from decimal import Decimal
from src.application.handlers.place_order_handler import PlaceOrderHandler, PlaceOrderCommand

class TestPlaceOrderHandler:
    def setup_method(self):
        self.mock_repository = Mock()
        self.handler = PlaceOrderHandler(self.mock_repository)

    @pytest.mark.asyncio
    async def test_place_order_success(self, sample_order_items):
        # Arrange
        command = PlaceOrderCommand(
            customer_id="123",
            items=sample_order_items,
            delivery_address="123 Pizza St"
        )

        # Act
        result = await self.handler.handle_async(command)

        # Assert
        assert result.is_success
        assert result.data.customer_id == "123"
        self.mock_repository.save_async.assert_called_once()
```

## 🚀 Running the Application

### Development Mode

```bash
# Install dependencies
poetry install

# Run with hot reload
poetry run python main.py

# Or using uvicorn directly
poetry run uvicorn src.main:app --reload
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src

# Run specific test file
poetry run pytest tests/unit/test_place_order_handler.py -v
```

### Code Quality

```bash
# Format code
poetry run black src tests

# Sort imports
poetry run isort src tests

# Type checking
poetry run mypy src
```

## 🔧 Next Steps

After basic setup, consider:

1. **[API Development Guide](api-development.md)** - Add more endpoints
2. **[Testing Guide](testing-setup.md)** - Comprehensive testing strategies
3. **[Database Integration Guide](database-integration.md)** - Connect to real databases
4. **[Deployment Guide](deployment.md)** - Deploy to production

## 🆘 Troubleshooting

### Common Issues

**Import Errors**

```bash
# Ensure proper Python path
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
```

**Poetry Issues**

```bash
# Reset poetry environment
poetry env remove python
poetry install
```

**Missing Dependencies**

```bash
# Update lock file
poetry update
```

## 🔗 Related Guides

- **[Testing Setup](testing-setup.md)** - Comprehensive testing strategies
- **[API Development](api-development.md)** - Building REST endpoints
- **[Database Integration](database-integration.md)** - Data persistence setup

---

_This guide provides the foundation for building production-ready Neuroglia applications using proven architectural patterns._ 🚀
