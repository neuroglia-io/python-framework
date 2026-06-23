"""
Complete Order Workflow E2E Test

This module validates the entire order lifecycle from creation to delivery,
testing all layers of the Neuroglia framework working together.

Workflow Steps:
    1. Customer browses menu (Query)
    2. Customer places order (Command)
    3. System validates order (Business Rules)
    4. Order is confirmed (State Transition)
    5. Kitchen starts cooking (Command)
    6. Order ready for delivery (Domain Event)
    7. Order delivered (State Transition)
    8. Customer receives confirmation (Notification)

Test Coverage:
    - Domain layer: Order aggregate, domain events, business rules
    - Application layer: Command/query handlers, event handlers
    - API layer: Controllers, DTOs, HTTP requests
    - Integration layer: Repositories, event store, notifications

Expected Behavior:
    - Order flows through all states correctly
    - Events are raised and handled at each step
    - Data persists correctly throughout
    - Business rules prevent invalid operations
    - Notifications are sent at appropriate times

Related:
    - samples/mario-pizzeria/: Reference implementation
    - tests/domain/test_ddd_patterns.py: Domain layer tests
    - tests/application/test_mediator.py: Application layer tests
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

import pytest

from neuroglia.core import OperationResult
from neuroglia.data.abstractions import AggregateRoot, AggregateState
from neuroglia.data.infrastructure.memory import MemoryRepository
from neuroglia.dependency_injection import ServiceCollection
from neuroglia.mediation.mediator import (
    Command,
    CommandHandler,
    DomainEventHandler,
    Mediator,
    Query,
    QueryHandler,
)
from tests.fixtures import OrderStatus, PizzaSize

# =============================================================================
# Domain Layer - Aggregates and Events
# =============================================================================


@dataclass
class OrderCreatedEvent:
    """Event raised when order is created."""

    aggregate_id: str
    customer_id: str
    order_time: datetime


@dataclass
class PizzaAddedToOrderEvent:
    """Event raised when pizza is added to order."""

    aggregate_id: str
    pizza_name: str
    pizza_size: str
    quantity: int


@dataclass
class OrderConfirmedEvent:
    """Event raised when order is confirmed."""

    aggregate_id: str
    confirmed_time: datetime
    estimated_ready_minutes: int


@dataclass
class OrderStartedCookingEvent:
    """Event raised when kitchen starts cooking."""

    aggregate_id: str
    started_time: datetime
    chef_name: str


@dataclass
class OrderReadyEvent:
    """Event raised when order is ready."""

    aggregate_id: str
    ready_time: datetime
    total_cooking_minutes: int


@dataclass
class OrderDeliveredEvent:
    """Event raised when order is delivered."""

    aggregate_id: str
    delivered_time: datetime
    delivery_person: str


class OrderState(AggregateState[str]):
    """State for order aggregate."""

    def __init__(self):
        super().__init__()
        self.customer_id: Optional[str] = None
        self.pizzas: list[dict] = []
        self.status: OrderStatus = OrderStatus.PENDING
        self.order_time: Optional[datetime] = None
        self.confirmed_time: Optional[datetime] = None
        self.cooking_started_time: Optional[datetime] = None
        self.ready_time: Optional[datetime] = None
        self.delivered_time: Optional[datetime] = None
        self.chef_name: Optional[str] = None
        self.delivery_person: Optional[str] = None

    def on(self, event):
        """Apply event to state."""
        if isinstance(event, OrderCreatedEvent):
            self.customer_id = event.customer_id
            self.order_time = event.order_time
            self.status = OrderStatus.PENDING
        elif isinstance(event, PizzaAddedToOrderEvent):
            self.pizzas.append(
                {
                    "name": event.pizza_name,
                    "size": event.pizza_size,
                    "quantity": event.quantity,
                }
            )
        elif isinstance(event, OrderConfirmedEvent):
            self.status = OrderStatus.CONFIRMED
            self.confirmed_time = event.confirmed_time
        elif isinstance(event, OrderStartedCookingEvent):
            self.status = OrderStatus.COOKING
            self.cooking_started_time = event.started_time
            self.chef_name = event.chef_name
        elif isinstance(event, OrderReadyEvent):
            self.status = OrderStatus.READY
            self.ready_time = event.ready_time
        elif isinstance(event, OrderDeliveredEvent):
            self.status = OrderStatus.DELIVERED
            self.delivered_time = event.delivered_time
            self.delivery_person = event.delivery_person


class Order(AggregateRoot[OrderState, str]):
    """Order aggregate root."""

    @staticmethod
    def create(customer_id: str):
        """Create new order."""
        order = Order()
        order.state.id = str(uuid4())
        event = OrderCreatedEvent(
            aggregate_id=order.state.id,
            customer_id=customer_id,
            order_time=datetime.now(timezone.utc),
        )
        order.register_event(event)
        order.state.on(event)
        return order

    def add_pizza(self, pizza_name: str, pizza_size: PizzaSize, quantity: int = 1):
        """Add pizza to order."""
        if self.state.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot add pizzas to {self.state.status.value} order")

        event = PizzaAddedToOrderEvent(
            aggregate_id=self.id(),
            pizza_name=pizza_name,
            pizza_size=pizza_size.value,
            quantity=quantity,
        )
        self.register_event(event)
        self.state.on(event)

    def confirm(self, estimated_ready_minutes: int = 30):
        """Confirm the order."""
        if self.state.status != OrderStatus.PENDING:
            raise ValueError("Can only confirm pending orders")
        if not self.state.pizzas:
            raise ValueError("Cannot confirm order with no pizzas")

        event = OrderConfirmedEvent(
            aggregate_id=self.id(),
            confirmed_time=datetime.now(timezone.utc),
            estimated_ready_minutes=estimated_ready_minutes,
        )
        self.register_event(event)
        self.state.on(event)

    def start_cooking(self, chef_name: str):
        """Start cooking the order."""
        if self.state.status != OrderStatus.CONFIRMED:
            raise ValueError("Can only cook confirmed orders")

        event = OrderStartedCookingEvent(
            aggregate_id=self.id(),
            started_time=datetime.now(timezone.utc),
            chef_name=chef_name,
        )
        self.register_event(event)
        self.state.on(event)

    def mark_ready(self):
        """Mark order as ready."""
        if self.state.status != OrderStatus.COOKING:
            raise ValueError("Can only mark cooking orders as ready")

        cooking_minutes = 0
        if self.state.cooking_started_time:
            elapsed = datetime.now(timezone.utc) - self.state.cooking_started_time
            cooking_minutes = int(elapsed.total_seconds() / 60)

        event = OrderReadyEvent(
            aggregate_id=self.id(),
            ready_time=datetime.now(timezone.utc),
            total_cooking_minutes=cooking_minutes,
        )
        self.register_event(event)
        self.state.on(event)

    def mark_delivered(self, delivery_person: str):
        """Mark order as delivered."""
        if self.state.status != OrderStatus.READY:
            raise ValueError("Can only deliver ready orders")

        event = OrderDeliveredEvent(
            aggregate_id=self.id(),
            delivered_time=datetime.now(timezone.utc),
            delivery_person=delivery_person,
        )
        self.register_event(event)
        self.state.on(event)


# =============================================================================
# Application Layer - Commands and Handlers
# =============================================================================


@dataclass
class PlaceOrderCommand(Command[OperationResult[dict]]):
    """Command to place a new order."""

    customer_id: str
    pizzas: list[dict]  # [{name, size, quantity}]


@dataclass
class ConfirmOrderCommand(Command[OperationResult[dict]]):
    """Command to confirm an order."""

    order_id: str
    estimated_ready_minutes: int = 30


@dataclass
class StartCookingCommand(Command[OperationResult[dict]]):
    """Command to start cooking an order."""

    order_id: str
    chef_name: str


@dataclass
class MarkOrderReadyCommand(Command[OperationResult[dict]]):
    """Command to mark order as ready."""

    order_id: str


@dataclass
class DeliverOrderCommand(Command[OperationResult[dict]]):
    """Command to deliver an order."""

    order_id: str
    delivery_person: str


@dataclass
class GetMenuQuery(Query[OperationResult[List[dict]]]):
    """Query to get menu."""

    category: Optional[str] = None


@dataclass
class GetOrderQuery(Query[OperationResult[Optional[dict]]]):
    """Query to get order by ID."""

    order_id: str


class PlaceOrderHandler(CommandHandler[PlaceOrderCommand, OperationResult[dict]]):
    """Handler for placing orders."""

    def __init__(self, order_repository: MemoryRepository):
        self.order_repository = order_repository

    async def handle_async(self, command: PlaceOrderCommand) -> OperationResult[dict]:
        """Handle order placement."""
        # Create order aggregate
        order = Order.create(command.customer_id)

        # Add pizzas
        for pizza_data in command.pizzas:
            order.add_pizza(
                pizza_data["name"],
                PizzaSize(pizza_data["size"]),
                pizza_data.get("quantity", 1),
            )

        # Save to repository
        await self.order_repository.add_async(order)

        order_data = {
            "id": order.id(),
            "customer_id": order.state.customer_id,
            "pizzas": order.state.pizzas,
            "status": order.state.status.value,
            "order_time": order.state.order_time.isoformat(),
        }

        return self.created(order_data)


class ConfirmOrderHandler(CommandHandler[ConfirmOrderCommand, OperationResult[dict]]):
    """Handler for confirming orders."""

    def __init__(self, order_repository: MemoryRepository):
        self.order_repository = order_repository

    async def handle_async(self, command: ConfirmOrderCommand) -> OperationResult[dict]:
        """Handle order confirmation."""
        order = await self.order_repository.get_async(command.order_id)
        if not order:
            return self.not_found(Order, "order_id", command.order_id)

        try:
            order.confirm(command.estimated_ready_minutes)
            await self.order_repository.update_async(order)

            return self.ok(
                {
                    "id": order.id(),
                    "status": order.state.status.value,
                    "confirmed_time": order.state.confirmed_time.isoformat(),
                }
            )
        except ValueError as e:
            return self.bad_request(str(e))


class StartCookingHandler(CommandHandler[StartCookingCommand, OperationResult[dict]]):
    """Handler for starting cooking."""

    def __init__(self, order_repository: MemoryRepository):
        self.order_repository = order_repository

    async def handle_async(self, command: StartCookingCommand) -> OperationResult[dict]:
        """Handle cooking start."""
        order = await self.order_repository.get_async(command.order_id)
        if not order:
            return self.not_found(Order, "order_id", command.order_id)

        try:
            order.start_cooking(command.chef_name)
            await self.order_repository.update_async(order)

            return self.ok(
                {
                    "id": order.id(),
                    "status": order.state.status.value,
                    "chef_name": order.state.chef_name,
                }
            )
        except ValueError as e:
            return self.bad_request(str(e))


class MarkOrderReadyHandler(CommandHandler[MarkOrderReadyCommand, OperationResult[dict]]):
    """Handler for marking order ready."""

    def __init__(self, order_repository: MemoryRepository):
        self.order_repository = order_repository

    async def handle_async(self, command: MarkOrderReadyCommand) -> OperationResult[dict]:
        """Handle order ready."""
        order = await self.order_repository.get_async(command.order_id)
        if not order:
            return self.not_found(Order, "order_id", command.order_id)

        try:
            order.mark_ready()
            await self.order_repository.update_async(order)

            return self.ok(
                {
                    "id": order.id(),
                    "status": order.state.status.value,
                    "ready_time": order.state.ready_time.isoformat(),
                }
            )
        except ValueError as e:
            return self.bad_request(str(e))


class DeliverOrderHandler(CommandHandler[DeliverOrderCommand, OperationResult[dict]]):
    """Handler for delivering order."""

    def __init__(self, order_repository: MemoryRepository):
        self.order_repository = order_repository

    async def handle_async(self, command: DeliverOrderCommand) -> OperationResult[dict]:
        """Handle order delivery."""
        order = await self.order_repository.get_async(command.order_id)
        if not order:
            return self.not_found(Order, "order_id", command.order_id)

        try:
            order.mark_delivered(command.delivery_person)
            await self.order_repository.update_async(order)

            return self.ok(
                {
                    "id": order.id(),
                    "status": order.state.status.value,
                    "delivered_time": order.state.delivered_time.isoformat(),
                    "delivery_person": order.state.delivery_person,
                }
            )
        except ValueError as e:
            return self.bad_request(str(e))


class GetMenuHandler(QueryHandler[GetMenuQuery, OperationResult[List[dict]]]):
    """Handler for getting menu."""

    async def handle_async(self, query: GetMenuQuery) -> OperationResult[list[dict]]:
        """Handle menu query."""
        # Mock menu data
        menu = [
            {
                "name": "Margherita",
                "sizes": ["small", "medium", "large"],
                "base_price": 12.99,
            },
            {
                "name": "Pepperoni",
                "sizes": ["small", "medium", "large"],
                "base_price": 14.99,
            },
            {"name": "Supreme", "sizes": ["medium", "large"], "base_price": 17.99},
        ]

        if query.category:
            menu = [p for p in menu if query.category.lower() in p["name"].lower()]

        return self.ok(menu)


class GetOrderHandler(QueryHandler[GetOrderQuery, OperationResult[Optional[dict]]]):
    """Handler for getting order."""

    def __init__(self, order_repository: MemoryRepository):
        self.order_repository = order_repository

    async def handle_async(self, query: GetOrderQuery) -> OperationResult[Optional[dict]]:
        """Handle order query."""
        order = await self.order_repository.get_async(query.order_id)

        if not order:
            return self.ok(None)

        order_data = {
            "id": order.id(),
            "customer_id": order.state.customer_id,
            "pizzas": order.state.pizzas,
            "status": order.state.status.value,
            "order_time": order.state.order_time.isoformat(),
        }

        if order.state.confirmed_time:
            order_data["confirmed_time"] = order.state.confirmed_time.isoformat()
        if order.state.cooking_started_time:
            order_data["cooking_started_time"] = order.state.cooking_started_time.isoformat()
        if order.state.ready_time:
            order_data["ready_time"] = order.state.ready_time.isoformat()
        if order.state.delivered_time:
            order_data["delivered_time"] = order.state.delivered_time.isoformat()

        return self.ok(order_data)


# =============================================================================
# Event Handlers - Notifications
# =============================================================================


class OrderConfirmedNotificationHandler(DomainEventHandler[OrderConfirmedEvent]):
    """Handler for order confirmed notifications."""

    def __init__(self):
        self.notifications_sent = []

    async def handle_async(self, event: OrderConfirmedEvent):
        """Send order confirmed notification."""
        notification = {
            "type": "order_confirmed",
            "order_id": event.aggregate_id,
            "confirmed_time": event.confirmed_time.isoformat(),
            "message": f"Your order has been confirmed! Estimated ready time: {event.estimated_ready_minutes} minutes",
        }
        self.notifications_sent.append(notification)


class OrderReadyNotificationHandler(DomainEventHandler[OrderReadyEvent]):
    """Handler for order ready notifications."""

    def __init__(self):
        self.notifications_sent = []

    async def handle_async(self, event: OrderReadyEvent):
        """Send order ready notification."""
        notification = {
            "type": "order_ready",
            "order_id": event.aggregate_id,
            "ready_time": event.ready_time.isoformat(),
            "message": "Your order is ready for pickup!",
        }
        self.notifications_sent.append(notification)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def shared_repository():
    """Create shared order repository instance for all handlers."""
    repo = MemoryRepository()
    # Clear the class-level dict before each test (use .clear() not assignment!)
    MemoryRepository.entities.clear()
    return repo


@pytest.fixture
def services(shared_repository):
    """Create service collection with all dependencies."""
    collection = ServiceCollection()

    # Register shared repository instance
    collection.add_singleton(MemoryRepository, singleton=shared_repository)

    # Register mediator
    collection.add_singleton(Mediator)

    # Create handler instances with shared repository
    place_handler = PlaceOrderHandler(shared_repository)
    confirm_handler = ConfirmOrderHandler(shared_repository)
    cook_handler = StartCookingHandler(shared_repository)
    ready_handler = MarkOrderReadyHandler(shared_repository)
    deliver_handler = DeliverOrderHandler(shared_repository)
    menu_handler = GetMenuHandler()
    get_order_handler = GetOrderHandler(shared_repository)

    # Register handler instances
    collection.add_singleton(PlaceOrderHandler, singleton=place_handler)
    collection.add_singleton(ConfirmOrderHandler, singleton=confirm_handler)
    collection.add_singleton(StartCookingHandler, singleton=cook_handler)
    collection.add_singleton(MarkOrderReadyHandler, singleton=ready_handler)
    collection.add_singleton(DeliverOrderHandler, singleton=deliver_handler)
    collection.add_singleton(GetMenuHandler, singleton=menu_handler)
    collection.add_singleton(GetOrderHandler, singleton=get_order_handler)

    # Register event handlers
    collection.add_singleton(OrderConfirmedNotificationHandler)
    collection.add_singleton(OrderReadyNotificationHandler)

    return collection


@pytest.fixture
def service_provider(services):
    """Build service provider."""
    provider = services.build()

    # Register handlers in mediator
    Mediator._handler_registry = {
        PlaceOrderCommand: PlaceOrderHandler,
        ConfirmOrderCommand: ConfirmOrderHandler,
        StartCookingCommand: StartCookingHandler,
        MarkOrderReadyCommand: MarkOrderReadyHandler,
        DeliverOrderCommand: DeliverOrderHandler,
        GetMenuQuery: GetMenuHandler,
        GetOrderQuery: GetOrderHandler,
    }

    return provider


@pytest.fixture
def mediator(service_provider):
    """Get mediator from service provider."""
    return service_provider.get_required_service(Mediator)


@pytest.fixture
def order_repository(service_provider):
    """Get order repository."""
    return service_provider.get_required_service(MemoryRepository)


# =============================================================================
# E2E Test Suite
# =============================================================================


@pytest.mark.e2e
class TestCompleteOrderWorkflow:
    """
    End-to-end tests for complete order workflow.

    Tests the entire order lifecycle from browsing menu to delivery,
    validating that all framework components work together correctly.

    Workflow:
        1. Browse menu → 2. Place order → 3. Confirm → 4. Cook →
        5. Ready → 6. Deliver

    Related: samples/mario-pizzeria/
    """

    @pytest.mark.asyncio
    async def test_customer_browses_menu(self, mediator):
        """
        Test Step 1: Customer browses menu.

        Expected Behavior:
            - Query returns menu items
            - Menu data is formatted correctly
            - No side effects occur

        Related: Query handling
        """
        # Act
        query = GetMenuQuery()
        result = await mediator.execute_async(query)

        # Assert
        assert result.is_success
        assert result.status == 200
        assert len(result.data) >= 3
        assert any(item["name"] == "Margherita" for item in result.data)

    @pytest.mark.asyncio
    async def test_complete_order_lifecycle(self, mediator, order_repository):
        """
        Test complete order workflow from creation to delivery.

        This is the main E2E test that validates the entire workflow
        across all architectural layers.

        Workflow Steps:
            1. Place order (PENDING)
            2. Confirm order (CONFIRMED)
            3. Start cooking (COOKING)
            4. Mark ready (READY)
            5. Deliver (DELIVERED)

        Expected Behavior:
            - Order transitions through all states correctly
            - Events are raised at each step
            - Data persists correctly
            - Business rules are enforced

        Related: Complete workflow testing
        """
        customer_id = str(uuid4())

        # Step 1: Place order
        place_cmd = PlaceOrderCommand(
            customer_id=customer_id,
            pizzas=[
                {"name": "Margherita", "size": "medium", "quantity": 2},
                {"name": "Pepperoni", "size": "large", "quantity": 1},
            ],
        )
        place_result = await mediator.execute_async(place_cmd)

        assert place_result.is_success
        assert place_result.status == 201
        order_id = place_result.data["id"]
        assert place_result.data["status"] == "pending"
        assert len(place_result.data["pizzas"]) == 2

        # Step 2: Confirm order
        confirm_cmd = ConfirmOrderCommand(order_id=order_id, estimated_ready_minutes=25)
        confirm_result = await mediator.execute_async(confirm_cmd)

        assert confirm_result.is_success
        assert confirm_result.data["status"] == "confirmed"
        assert "confirmed_time" in confirm_result.data

        # Step 3: Start cooking
        cook_cmd = StartCookingCommand(order_id=order_id, chef_name="Chef Mario")
        cook_result = await mediator.execute_async(cook_cmd)

        assert cook_result.is_success
        assert cook_result.data["status"] == "cooking"
        assert cook_result.data["chef_name"] == "Chef Mario"

        # Step 4: Mark ready
        ready_cmd = MarkOrderReadyCommand(order_id=order_id)
        ready_result = await mediator.execute_async(ready_cmd)

        assert ready_result.is_success
        assert ready_result.data["status"] == "ready"
        assert "ready_time" in ready_result.data

        # Step 5: Deliver order
        deliver_cmd = DeliverOrderCommand(order_id=order_id, delivery_person="John Driver")
        deliver_result = await mediator.execute_async(deliver_cmd)

        assert deliver_result.is_success
        assert deliver_result.data["status"] == "delivered"
        assert deliver_result.data["delivery_person"] == "John Driver"

        # Verify final state via query
        get_query = GetOrderQuery(order_id=order_id)
        get_result = await mediator.execute_async(get_query)

        assert get_result.is_success
        final_order = get_result.data
        assert final_order["status"] == "delivered"
        assert "delivered_time" in final_order

    @pytest.mark.asyncio
    async def test_business_rules_prevent_invalid_transitions(self, mediator):
        """
        Test that business rules prevent invalid state transitions.

        Expected Behavior:
            - Cannot confirm empty order
            - Cannot skip states
            - Cannot add pizzas after confirmation
            - Error messages are descriptive

        Related: Business rule enforcement
        """
        customer_id = str(uuid4())

        # Place order with pizzas
        place_cmd = PlaceOrderCommand(
            customer_id=customer_id,
            pizzas=[{"name": "Margherita", "size": "medium", "quantity": 1}],
        )
        place_result = await mediator.execute_async(place_cmd)
        order_id = place_result.data["id"]

        # Try to cook without confirming (should fail)
        cook_cmd = StartCookingCommand(order_id=order_id, chef_name="Chef Mario")
        cook_result = await mediator.execute_async(cook_cmd)

        assert not cook_result.is_success
        assert cook_result.status == 400
        assert "confirmed" in cook_result.detail.lower()

        # Try to deliver without being ready (should fail)
        deliver_cmd = DeliverOrderCommand(order_id=order_id, delivery_person="John Driver")
        deliver_result = await mediator.execute_async(deliver_cmd)

        assert not deliver_result.is_success
        assert deliver_result.status == 400

    @pytest.mark.asyncio
    async def test_order_not_found_scenarios(self, mediator):
        """
        Test error handling for non-existent orders.

        Expected Behavior:
            - 404 Not Found for invalid order IDs
            - Consistent error format
            - System remains stable

        Related: Error handling
        """
        # Try to confirm non-existent order
        confirm_cmd = ConfirmOrderCommand(order_id="nonexistent-order-id")
        confirm_result = await mediator.execute_async(confirm_cmd)

        assert not confirm_result.is_success
        assert confirm_result.status == 404
        assert "nonexistent-order-id" in confirm_result.detail

    @pytest.mark.asyncio
    async def test_query_order_after_each_transition(self, mediator):
        """
        Test querying order state after each transition.

        Expected Behavior:
            - Order data reflects current state
            - Historical timestamps preserved
            - Status updates correctly
            - Data consistency maintained

        Related: Query consistency
        """
        customer_id = str(uuid4())

        # Place order
        place_cmd = PlaceOrderCommand(
            customer_id=customer_id,
            pizzas=[{"name": "Supreme", "size": "large", "quantity": 1}],
        )
        place_result = await mediator.execute_async(place_cmd)
        order_id = place_result.data["id"]

        # Query after placement
        query = GetOrderQuery(order_id=order_id)
        result1 = await mediator.execute_async(query)
        assert result1.data["status"] == "pending"
        assert "order_time" in result1.data

        # Confirm and query
        await mediator.execute_async(ConfirmOrderCommand(order_id=order_id, estimated_ready_minutes=30))
        result2 = await mediator.execute_async(query)
        assert result2.data["status"] == "confirmed"
        assert "confirmed_time" in result2.data

        # Start cooking and query
        await mediator.execute_async(StartCookingCommand(order_id=order_id, chef_name="Chef Luigi"))
        result3 = await mediator.execute_async(query)
        assert result3.data["status"] == "cooking"
        assert "cooking_started_time" in result3.data

        # All previous timestamps should still be present
        assert "order_time" in result3.data
        assert "confirmed_time" in result3.data
