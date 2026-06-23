# 🧪 Mario's Pizzeria: Testing & Deployment

> **Quality Assurance Guide** | **Testing Strategy**: Unit, Integration, E2E
> **Deployment**: Docker, CI/CD, Production Monitoring | **Status**: Production Ready

📂 **[View Tests on GitHub](https://github.com/bvandewe/pyneuro/tree/main/samples/mario-pizzeria/tests)**

---

> 💡 **Pattern in Action**: This document demonstrates how **[Repository Pattern](../patterns/repository.md)**, **[Dependency Injection](../patterns/dependency-injection.md)**, and **[Persistence Patterns](../patterns/persistence-patterns.md)** make testing easier with clean mocking strategies and event verification.

---

## 🎯 Testing Overview

Mario's Pizzeria demonstrates comprehensive testing strategies across all application layers. The testing approach leverages **[Dependency Injection](../patterns/dependency-injection.md)** for easy mocking and **[Repository Pattern](../patterns/repository.md)** for test data setup.

**Testing Pyramid**:

- **Unit Tests** (70%): Fast, isolated tests for business logic with mocked dependencies
- **Integration Tests** (20%): API endpoints and data access layer testing
- **End-to-End Tests** (10%): Complete workflow validation

> 🎯 **Why Dependency Injection Helps Testing**: Constructor injection makes it trivial to replace real repositories with mocks! See [DI Benefits](../patterns/dependency-injection.md#what--why-dependency-injection).

---

## 🧪 Unit Testing Strategy

Unit tests focus on individual components in isolation with comprehensive mocking:

### Domain Entity Testing

```python
import pytest
from decimal import Decimal
from datetime import datetime
from mario_pizzeria.domain.entities import Order, Pizza, Kitchen
from mario_pizzeria.domain.enums import OrderStatus, PizzaSize

class TestOrderEntity:
    """Test Order domain entity business logic"""

    def test_order_creation_with_defaults(self):
        """Test order creation with default values"""
        order = Order(
            id="order_001",
            customer_name="Mario Rossi",
            customer_phone="+1-555-0123",
            pizzas=[],
            status="pending",
            order_time=datetime.utcnow()
        )

        assert order.id == "order_001"
        assert order.status == "pending"
        assert order.total_amount == Decimal('0.00')
        assert len(order.pizzas) == 0

    def test_add_pizza_to_order(self):
        """Test adding pizza updates total amount"""
        order = Order(
            id="order_001",
            customer_name="Mario Rossi",
            customer_phone="+1-555-0123",
            pizzas=[],
            status="pending",
            order_time=datetime.utcnow()
        )

        pizza = Pizza(
            id="pizza_001",
            name="Margherita",
            size="large",
            base_price=Decimal('15.99'),
            toppings=["extra cheese"],
            preparation_time_minutes=15
        )

        order.add_pizza(pizza)

        assert len(order.pizzas) == 1
        assert order.total_amount == Decimal('17.49')  # 15.99 + 1.50 topping

    def test_order_status_transitions(self):
        """Test valid order status transitions"""
        order = Order(
            id="order_001",
            customer_name="Mario Rossi",
            customer_phone="+1-555-0123",
            pizzas=[self._create_test_pizza()],
            status="pending",
            order_time=datetime.utcnow()
        )

        # Test valid transitions
        order.confirm_order()
        assert order.status == "confirmed"

        order.start_cooking()
        assert order.status == "cooking"

        order.mark_ready()
        assert order.status == "ready"

    def test_invalid_status_transitions_raise_error(self):
        """Test invalid status transitions raise domain errors"""
        order = Order(
            id="order_001",
            customer_name="Mario Rossi",
            customer_phone="+1-555-0123",
            pizzas=[self._create_test_pizza()],
            status="pending",
            order_time=datetime.utcnow()
        )

        # Cannot start cooking before confirming
        with pytest.raises(InvalidOrderStateError):
            order.start_cooking()

    def _create_test_pizza(self) -> Pizza:
        return Pizza(
            id="pizza_001",
            name="Margherita",
            size="large",
            base_price=Decimal('15.99'),
            toppings=[],
            preparation_time_minutes=15
        )

class TestKitchenEntity:
    """Test Kitchen domain entity capacity management"""

    def test_kitchen_capacity_management(self):
        """Test kitchen capacity tracking"""
        kitchen = Kitchen(
            id="kitchen_001",
            active_orders=[],
            max_concurrent_orders=3
        )

        assert kitchen.current_capacity == 0
        assert kitchen.available_capacity == 3
        assert not kitchen.is_at_capacity

        # Add orders to capacity
        assert kitchen.start_order("order_001") == True
        assert kitchen.start_order("order_002") == True
        assert kitchen.start_order("order_003") == True

        assert kitchen.current_capacity == 3
        assert kitchen.available_capacity == 0
        assert kitchen.is_at_capacity

        # Cannot add more orders when at capacity
        assert kitchen.start_order("order_004") == False

    def test_kitchen_order_completion(self):
        """Test completing orders frees capacity"""
        kitchen = Kitchen(
            id="kitchen_001",
            active_orders=["order_001", "order_002"],
            max_concurrent_orders=3
        )

        kitchen.complete_order("order_001")

        assert kitchen.current_capacity == 1
        assert kitchen.available_capacity == 2
        assert not kitchen.is_at_capacity
```

### Command Handler Testing

```python
from unittest.mock import Mock, AsyncMock
import pytest
from mario_pizzeria.application.handlers import PlaceOrderHandler
from mario_pizzeria.application.commands import PlaceOrderCommand

class TestPlaceOrderHandler:
    """Test PlaceOrderHandler business logic"""

    def setup_method(self):
        # Mock all dependencies
        self.order_repository = Mock()
        self.payment_service = Mock()
        self.kitchen_repository = Mock()
        self.mapper = Mock()

        self.handler = PlaceOrderHandler(
            self.order_repository,
            self.payment_service,
            self.kitchen_repository,
            self.mapper
        )

    @pytest.mark.asyncio
    async def test_place_order_success_scenario(self):
        """Test successful order placement"""
        # Arrange
        command = PlaceOrderCommand(
            customer_name="Mario Rossi",
            customer_phone="+1-555-0123",
            customer_address="123 Main St",
            pizzas=[self._create_test_pizza_dto()],
            payment_method="credit_card"
        )

        # Mock successful payment
        self.payment_service.process_payment_async = AsyncMock(
            return_value=PaymentResult(success=True, transaction_id="txn_123")
        )

        # Mock kitchen availability
        mock_kitchen = Mock()
        mock_kitchen.is_at_capacity = False
        self.kitchen_repository.get_default_kitchen = AsyncMock(return_value=mock_kitchen)

        # Mock repository save
        self.order_repository.save_async = AsyncMock()

        # Act
        result = await self.handler.handle_async(command)

        # Assert
        assert result.is_success
        assert result.status_code == 201
        self.order_repository.save_async.assert_called_once()
        self.payment_service.process_payment_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_place_order_kitchen_at_capacity(self):
        """Test order rejection when kitchen is at capacity"""
        # Arrange
        command = PlaceOrderCommand(
            customer_name="Mario Rossi",
            customer_phone="+1-555-0123",
            customer_address="123 Main St",
            pizzas=[self._create_test_pizza_dto()],
            payment_method="credit_card"
        )

        # Mock kitchen at capacity
        mock_kitchen = Mock()
        mock_kitchen.is_at_capacity = True
        self.kitchen_repository.get_default_kitchen = AsyncMock(return_value=mock_kitchen)

        # Act
        result = await self.handler.handle_async(command)

        # Assert
        assert not result.is_success
        assert result.status_code == 400
        assert "capacity" in result.error_message.lower()

        # Ensure payment was not processed
        self.payment_service.process_payment_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_place_order_payment_failure(self):
        """Test order failure when payment fails"""
        # Arrange
        command = PlaceOrderCommand(
            customer_name="Mario Rossi",
            customer_phone="+1-555-0123",
            customer_address="123 Main St",
            pizzas=[self._create_test_pizza_dto()],
            payment_method="credit_card"
        )

        # Mock kitchen availability
        mock_kitchen = Mock()
        mock_kitchen.is_at_capacity = False
        self.kitchen_repository.get_default_kitchen = AsyncMock(return_value=mock_kitchen)

        # Mock payment failure
        self.payment_service.process_payment_async = AsyncMock(
            return_value=PaymentResult(success=False, error_message="Card declined")
        )

        # Act
        result = await self.handler.handle_async(command)

        # Assert
        assert not result.is_success
        assert result.status_code == 400
        assert "payment failed" in result.error_message.lower()

        # Ensure order was not saved
        self.order_repository.save_async.assert_not_called()
```

## 🔧 Integration Testing

Integration tests validate API endpoints and database interactions:

### Controller Integration Tests

```python
import pytest
from httpx import AsyncClient
from mario_pizzeria.main import create_app

class TestOrdersController:
    """Integration tests for Orders API"""

    @pytest.fixture
    def test_app(self):
        """Create test application with in-memory database"""
        app = create_app()
        app.configure_test_environment()
        return app

    @pytest.fixture
    async def test_client(self, test_app):
        """Create test client"""
        async with AsyncClient(app=test_app, base_url="http://test") as client:
            yield client

    @pytest.mark.integration
    async def test_place_order_success(self, test_client):
        """Test successful order placement via API"""
        order_data = {
            "customer_name": "Mario Rossi",
            "customer_phone": "+1-555-0123",
            "customer_address": "123 Main St",
            "pizzas": [
                {
                    "pizza_id": "margherita",
                    "size": "large",
                    "toppings": ["extra cheese"],
                    "quantity": 1
                }
            ],
            "payment_method": "credit_card"
        }

        response = await test_client.post("/orders", json=order_data)

        assert response.status_code == 201
        data = response.json()

        assert data["customer_name"] == "Mario Rossi"
        assert data["status"] == "confirmed"
        assert len(data["pizzas"]) == 1
        assert "id" in data
        assert "estimated_ready_time" in data

    @pytest.mark.integration
    async def test_place_order_validation_error(self, test_client):
        """Test order placement with invalid data"""
        invalid_order_data = {
            "customer_name": "",  # Invalid: empty name
            "customer_phone": "+1-555-0123",
            "pizzas": []  # Invalid: no pizzas
        }

        response = await test_client.post("/orders", json=invalid_order_data)

        assert response.status_code == 400
        error_data = response.json()
        assert "validation" in error_data["error"].lower()

    @pytest.mark.integration
    async def test_get_order_by_id(self, test_client):
        """Test retrieving order by ID"""
        # First create an order
        order_data = self._create_test_order_data()
        create_response = await test_client.post("/orders", json=order_data)
        order_id = create_response.json()["id"]

        # Then retrieve it
        get_response = await test_client.get(f"/orders/{order_id}")

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == order_id
        assert data["customer_name"] == order_data["customer_name"]

    @pytest.mark.integration
    async def test_get_kitchen_status(self, test_client):
        """Test kitchen status endpoint"""
        response = await test_client.get("/kitchen/status")

        assert response.status_code == 200
        data = response.json()

        assert "current_capacity" in data
        assert "max_concurrent_orders" in data
        assert "active_orders" in data
        assert "is_at_capacity" in data
        assert isinstance(data["current_capacity"], int)

    @pytest.mark.integration
    async def test_start_cooking_order(self, test_client):
        """Test starting cooking process"""
        # Create order first
        order_data = self._create_test_order_data()
        create_response = await test_client.post("/orders", json=order_data)
        order_id = create_response.json()["id"]

        # Start cooking
        cook_response = await test_client.post(
            f"/kitchen/orders/{order_id}/start",
            json={"kitchen_staff_id": "staff_001"}
        )

        assert cook_response.status_code == 200

        # Verify order status changed
        status_response = await test_client.get(f"/orders/{order_id}")
        assert status_response.json()["status"] == "cooking"

    def _create_test_order_data(self):
        return {
            "customer_name": "Test Customer",
            "customer_phone": "+1-555-0123",
            "customer_address": "123 Test St",
            "pizzas": [
                {
                    "pizza_id": "margherita",
                    "size": "medium",
                    "toppings": [],
                    "quantity": 1
                }
            ],
            "payment_method": "credit_card"
        }
```

### Repository Integration Tests

```python
@pytest.mark.integration
class TestOrderRepository:
    """Integration tests for order data access"""

    @pytest.fixture
    async def repository(self, mongo_client):
        """Create repository with test database"""
        return OrderRepository(mongo_client.test_db.orders)

    @pytest.mark.asyncio
    async def test_save_and_retrieve_order(self, repository):
        """Test complete CRUD operations"""
        # Create test order
        order = Order(
            id="test_order_001",
            customer_name="Test Customer",
            customer_phone="+1-555-0123",
            pizzas=[self._create_test_pizza()],
            status="pending",
            order_time=datetime.utcnow()
        )

        # Save order
        await repository.save_async(order)

        # Retrieve order
        retrieved = await repository.get_by_id_async("test_order_001")

        assert retrieved is not None
        assert retrieved.id == order.id
        assert retrieved.customer_name == order.customer_name
        assert retrieved.status == order.status
        assert len(retrieved.pizzas) == len(order.pizzas)

    @pytest.mark.asyncio
    async def test_get_orders_by_status(self, repository):
        """Test filtering orders by status"""
        # Create orders with different statuses
        orders = [
            self._create_test_order("order_001", "pending"),
            self._create_test_order("order_002", "cooking"),
            self._create_test_order("order_003", "ready")
        ]

        for order in orders:
            await repository.save_async(order)

        # Get cooking orders
        cooking_orders = await repository.get_by_status_async("cooking")

        assert len(cooking_orders) == 1
        assert cooking_orders[0].status == "cooking"
```

## 🌐 End-to-End Testing

End-to-end tests validate complete business workflows:

```python
@pytest.mark.e2e
class TestPizzeriaWorkflow:
    """End-to-end workflow tests"""

    @pytest.fixture
    async def test_system(self):
        """Set up complete test system"""
        app = create_app()
        app.configure_test_environment()

        # Start background services
        await app.start_background_services()

        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

        await app.stop_background_services()

    @pytest.mark.asyncio
    async def test_complete_order_workflow(self, test_system):
        """Test complete order-to-delivery workflow"""
        client = test_system

        # Step 1: Customer browses menu
        menu_response = await client.get("/menu/pizzas")
        assert menu_response.status_code == 200
        pizzas = menu_response.json()
        assert len(pizzas) > 0

        # Step 2: Customer places order
        order_data = {
            "customer_name": "Integration Test Customer",
            "customer_phone": "+1-555-9999",
            "customer_address": "123 Test Ave",
            "pizzas": [
                {
                    "pizza_id": pizzas[0]["id"],
                    "size": "large",
                    "toppings": ["pepperoni", "mushrooms"],
                    "quantity": 2
                }
            ],
            "payment_method": "credit_card"
        }

        order_response = await client.post("/orders", json=order_data)
        assert order_response.status_code == 201
        order = order_response.json()
        order_id = order["id"]

        # Verify order is confirmed
        assert order["status"] == "confirmed"
        assert order["customer_name"] == "Integration Test Customer"

        # Step 3: Kitchen views order queue
        queue_response = await client.get("/kitchen/queue")
        assert queue_response.status_code == 200
        queue = queue_response.json()

        # Find our order in queue
        order_in_queue = next((o for o in queue if o["id"] == order_id), None)
        assert order_in_queue is not None

        # Step 4: Kitchen starts cooking
        start_response = await client.post(
            f"/kitchen/orders/{order_id}/start",
            json={"kitchen_staff_id": "test_staff"}
        )
        assert start_response.status_code == 200

        # Verify status changed to cooking
        status_response = await client.get(f"/orders/{order_id}")
        cooking_order = status_response.json()
        assert cooking_order["status"] == "cooking"

        # Step 5: Kitchen completes order
        complete_response = await client.post(
            f"/kitchen/orders/{order_id}/complete"
        )
        assert complete_response.status_code == 200

        # Step 6: Verify final status
        final_response = await client.get(f"/orders/{order_id}")
        final_order = final_response.json()
        assert final_order["status"] == "ready"

        # Step 7: Verify kitchen capacity is freed
        final_status = await client.get("/kitchen/status")
        kitchen_status = final_status.json()

        # Kitchen should have capacity again
        assert not kitchen_status["is_at_capacity"]

    @pytest.mark.asyncio
    async def test_concurrent_order_processing(self, test_system):
        """Test system handles concurrent orders correctly"""
        client = test_system

        # Place multiple concurrent orders
        order_tasks = []
        for i in range(5):
            order_data = self._create_concurrent_order_data(i)
            task = client.post("/orders", json=order_data)
            order_tasks.append(task)

        # Wait for all orders to complete
        responses = await asyncio.gather(*order_tasks)

        # Verify all orders were processed
        successful_orders = 0
        capacity_rejections = 0

        for response in responses:
            if response.status_code == 201:
                successful_orders += 1
            elif response.status_code == 400:
                error_data = response.json()
                if "capacity" in error_data.get("error", "").lower():
                    capacity_rejections += 1

        # Should have processed some orders and rejected others due to capacity
        assert successful_orders > 0
        assert successful_orders + capacity_rejections == 5
```

## 🚀 Deployment & Operations

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/

# Run tests during build
RUN python -m pytest tests/ -v

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.mario_pizzeria.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### CI/CD Pipeline

```yaml
# .github/workflows/ci-cd.yml
name: Mario's Pizzeria CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      mongodb:
        image: mongo:6
        ports:
          - 27017:27017

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=src/mario_pizzeria

      - name: Run integration tests
        run: pytest tests/integration/ -v -m integration

      - name: Run E2E tests
        run: pytest tests/e2e/ -v -m e2e

      - name: Check test coverage
        run: |
          coverage report --fail-under=90
          coverage xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: docker build -t mario-pizzeria:${{ github.sha }} .

      - name: Deploy to staging
        run: |
          # Deploy to staging environment
          echo "Deploying to staging..."

      - name: Run smoke tests
        run: |
          # Run basic smoke tests against staging
          pytest tests/smoke/ -v
```

### Production Monitoring

```python
# monitoring.py
from prometheus_client import Counter, Histogram, generate_latest
from fastapi import Request
import time

# Metrics
REQUEST_COUNT = Counter('pizzeria_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('pizzeria_request_duration_seconds', 'Request duration')
ORDER_COUNT = Counter('pizzeria_orders_total', 'Total orders', ['status'])
KITCHEN_CAPACITY = Histogram('pizzeria_kitchen_capacity', 'Kitchen capacity usage')

class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            start_time = time.time()

            # Process request
            response = await self.app(scope, receive, send)

            # Record metrics
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path
            ).inc()
            REQUEST_DURATION.observe(duration)

            return response

        return await self.app(scope, receive, send)

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")
```

## 🔗 Related Documentation

### Case Study Documents

- [Business Analysis](business-analysis.md) - Requirements and stakeholder analysis
- [Technical Architecture](technical-architecture.md) - System design and infrastructure
- [Domain Design](domain-design.md) - Business logic and data models
- [Implementation Guide](implementation-guide.md) - Development patterns and APIs

### Framework Patterns for Testing

- **[Dependency Injection](../patterns/dependency-injection.md)** - Constructor injection enables easy mocking
- **[Repository Pattern](../patterns/repository.md)** - InMemoryRepository for test data setup
- **[Persistence Patterns](../patterns/persistence-patterns.md)** - Testing event publishing and domain event verification
- **[CQRS Pattern](../patterns/cqrs.md)** - Testing commands and queries separately
- **[Pipeline Behaviors](../patterns/pipeline-behaviors.md)** - Testing validation and logging behaviors

> 💡 **Testing Lesson**: Mario's Pizzeria testing demonstrates why [avoiding Service Locator anti-pattern](../patterns/dependency-injection.md#common-mistakes) makes testing so much easier with constructor injection!

---

_This comprehensive testing and deployment guide ensures Mario's Pizzeria maintains high quality and reliability from development through production._
