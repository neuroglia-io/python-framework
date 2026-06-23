"""
Unit tests for data access functionality.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from neuroglia.data.abstractions import (
    AggregateRoot,
    AggregateState,
    DomainEvent,
    Entity,
)
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepository,
)
from neuroglia.data.infrastructure.memory.memory_repository import MemoryRepository
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepository

# Test entities and aggregates


@dataclass
class TestProduct(Entity[str]):
    """Test product entity"""

    id: str
    name: str
    price: float
    category: str
    is_available: bool = True
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class TestOrder(Entity[str]):
    """Test order entity"""

    id: str
    customer_name: str
    items: list[dict[str, Any]]
    total_amount: float
    status: str = "pending"
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


# Test domain events


@dataclass
class ProductCreatedEvent(DomainEvent):
    """Product created domain event"""

    product_id: str
    name: str
    price: float
    category: str
    created_at: datetime


@dataclass
class ProductPriceChangedEvent(DomainEvent):
    """Product price changed domain event"""

    product_id: str
    old_price: float
    new_price: float
    changed_at: datetime


@dataclass
class OrderPlacedEvent(DomainEvent):
    """Order placed domain event"""

    order_id: str
    customer_name: str
    total_amount: float
    placed_at: datetime


# Test aggregate root


class ProductAggregateState(AggregateState[str]):
    name: str
    price: float


class ProductAggregate(AggregateRoot[ProductAggregateState, str]):
    """Test product aggregate for event sourcing"""

    def __init__(self, id: str = None):
        super().__init__(id or str(uuid4()))
        self.name = None
        self.price = None
        self.category = None
        self.is_available = True
        self.created_at = None

    def create_product(self, name: str, price: float, category: str):
        """Create a new product"""
        if not name or not name.strip():
            raise ValueError("Product name is required")

        if price <= 0:
            raise ValueError("Price must be positive")

        if not category or not category.strip():
            raise ValueError("Category is required")

        event = ProductCreatedEvent(
            product_id=self.id,
            name=name,
            price=price,
            category=category,
            created_at=datetime.utcnow(),
        )
        self.apply(event)

    def change_price(self, new_price: float):
        """Change product price"""
        if new_price <= 0:
            raise ValueError("Price must be positive")

        if new_price == self.price:
            return  # No change

        old_price = self.price
        event = ProductPriceChangedEvent(
            product_id=self.id,
            old_price=old_price,
            new_price=new_price,
            changed_at=datetime.utcnow(),
        )
        self.apply(event)

    def discontinue(self):
        """Discontinue the product"""
        self.is_available = False

    # Event handlers
    def on_product_created(self, event: ProductCreatedEvent):
        self.name = event.name
        self.price = event.price
        self.category = event.category
        self.created_at = event.created_at

    def on_product_price_changed(self, event: ProductPriceChangedEvent):
        self.price = event.new_price


class OrderAggregateState(AggregateState[str]):
    customer_name: str
    items: list
    total_amount: float


class OrderAggregate(AggregateRoot[OrderAggregateState, str]):
    """Test order aggregate for event sourcing"""

    def __init__(self, id: str = None):
        super().__init__(id or str(uuid4()))
        self.customer_name = None
        self.items = []
        self.total_amount = 0.0
        self.status = "draft"
        self.placed_at = None

    def place_order(self, customer_name: str, items: list[dict[str, Any]]):
        """Place a new order"""
        if not customer_name or not customer_name.strip():
            raise ValueError("Customer name is required")

        if not items:
            raise ValueError("Order must have at least one item")

        total = sum(item.get("price", 0) * item.get("quantity", 0) for item in items)
        if total <= 0:
            raise ValueError("Order total must be positive")

        event = OrderPlacedEvent(
            order_id=self.id,
            customer_name=customer_name,
            total_amount=total,
            placed_at=datetime.utcnow(),
        )
        self.apply(event)

    def on_order_placed(self, event: OrderPlacedEvent):
        self.customer_name = event.customer_name
        self.total_amount = event.total_amount
        self.status = "placed"
        self.placed_at = event.placed_at


# Test Entity base class


class TestEntity:
    def test_entity_creation(self):
        """Test creating entity with ID"""
        product = TestProduct(id="prod_123", name="Test Product", price=29.99, category="Electronics")

        assert product.id == "prod_123"
        assert product.name == "Test Product"
        assert product.price == 29.99
        assert product.category == "Electronics"
        assert product.is_available is True
        assert product.created_at is not None

    def test_entity_equality(self):
        """Test entity equality based on ID"""
        product1 = TestProduct(id="prod_123", name="Product 1", price=10.0, category="A")

        product2 = TestProduct(id="prod_123", name="Product 2", price=20.0, category="B")

        product3 = TestProduct(id="prod_456", name="Product 1", price=10.0, category="A")

        # Same ID should be equal
        assert product1 == product2

        # Different ID should not be equal
        assert product1 != product3

    def test_entity_hash(self):
        """Test entity hashing based on ID"""
        product1 = TestProduct(id="prod_123", name="Product", price=10.0, category="A")
        product2 = TestProduct(id="prod_123", name="Different", price=20.0, category="B")

        # Same ID should have same hash
        assert hash(product1) == hash(product2)

        # Can be used in sets/dicts
        product_set = {product1, product2}
        assert len(product_set) == 1  # Only one unique product by ID


# Test AggregateRoot base class


class TestAggregateRoot:
    def test_aggregate_creation(self):
        """Test creating aggregate root"""
        aggregate = ProductAggregate("prod_123")

        assert aggregate.id == "prod_123"
        assert len(aggregate.get_uncommitted_events()) == 0
        assert aggregate.version == 0

    def test_aggregate_apply_event(self):
        """Test applying events to aggregate"""
        aggregate = ProductAggregate()

        # Create product (should apply event)
        aggregate.create_product("Test Product", 29.99, "Electronics")

        # Check state was updated
        assert aggregate.name == "Test Product"
        assert aggregate.price == 29.99
        assert aggregate.category == "Electronics"

        # Check event was added
        events = aggregate.get_uncommitted_events()
        assert len(events) == 1
        assert isinstance(events[0], ProductCreatedEvent)
        assert events[0].product_id == aggregate.id

    def test_aggregate_multiple_events(self):
        """Test applying multiple events"""
        aggregate = ProductAggregate()

        # Create product
        aggregate.create_product("Test Product", 29.99, "Electronics")

        # Change price
        aggregate.change_price(39.99)

        # Check final state
        assert aggregate.name == "Test Product"
        assert aggregate.price == 39.99

        # Check events
        events = aggregate.get_uncommitted_events()
        assert len(events) == 2
        assert isinstance(events[0], ProductCreatedEvent)
        assert isinstance(events[1], ProductPriceChangedEvent)
        assert events[1].old_price == 29.99
        assert events[1].new_price == 39.99

    def test_aggregate_mark_events_committed(self):
        """Test marking events as committed"""
        aggregate = ProductAggregate()
        aggregate.create_product("Test Product", 29.99, "Electronics")

        # Should have uncommitted events
        assert len(aggregate.get_uncommitted_events()) == 1

        # Mark as committed
        aggregate.mark_events_as_committed()

        # Should have no uncommitted events
        assert len(aggregate.get_uncommitted_events()) == 0

    def test_aggregate_business_rule_validation(self):
        """Test business rule validation in aggregate"""
        aggregate = ProductAggregate()

        # Test validation errors
        with pytest.raises(ValueError, match="Product name is required"):
            aggregate.create_product("", 29.99, "Electronics")

        with pytest.raises(ValueError, match="Price must be positive"):
            aggregate.create_product("Test", -10.0, "Electronics")

        with pytest.raises(ValueError, match="Category is required"):
            aggregate.create_product("Test", 29.99, "")

    def test_aggregate_idempotent_operations(self):
        """Test idempotent operations don't create duplicate events"""
        aggregate = ProductAggregate()
        aggregate.create_product("Test Product", 29.99, "Electronics")

        # Change to same price should not create event
        initial_event_count = len(aggregate.get_uncommitted_events())
        aggregate.change_price(29.99)

        assert len(aggregate.get_uncommitted_events()) == initial_event_count


# Test InMemoryRepository


class TestInMemoryRepository:
    def setup_method(self):
        """Set up test repository"""
        self.repository = MemoryRepository[TestProduct, str]()

    @pytest.mark.asyncio
    async def test_add_and_get_by_id(self):
        """Test adding and retrieving entity by ID"""
        product = TestProduct(id="prod_123", name="Test Product", price=29.99, category="Electronics")

        # Add product
        added_product = await self.repository.add_async(product)
        assert added_product == product

        # Get by ID
        retrieved_product = await self.repository.get_by_id_async("prod_123")
        assert retrieved_product == product
        assert retrieved_product.name == "Test Product"

    @pytest.mark.asyncio
    async def test_get_nonexistent_entity(self):
        """Test getting entity that doesn't exist"""
        result = await self.repository.get_by_id_async("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_entity(self):
        """Test updating entity"""
        product = TestProduct(id="prod_123", name="Original Product", price=29.99, category="Electronics")

        await self.repository.add_async(product)

        # Update product
        product.name = "Updated Product"
        product.price = 39.99

        updated_product = await self.repository.update_async(product)
        assert updated_product.name == "Updated Product"
        assert updated_product.price == 39.99

        # Verify update in repository
        retrieved = await self.repository.get_by_id_async("prod_123")
        assert retrieved.name == "Updated Product"
        assert retrieved.price == 39.99

    @pytest.mark.asyncio
    async def test_update_nonexistent_entity(self):
        """Test updating entity that doesn't exist"""
        product = TestProduct(id="nonexistent", name="Test Product", price=29.99, category="Electronics")

        with pytest.raises(ValueError, match="not found"):
            await self.repository.update_async(product)

    @pytest.mark.asyncio
    async def test_remove_entity(self):
        """Test removing entity"""
        product = TestProduct(id="prod_123", name="Test Product", price=29.99, category="Electronics")

        await self.repository.add_async(product)

        # Verify it exists
        assert await self.repository.get_by_id_async("prod_123") is not None

        # Remove it
        await self.repository.remove_async(product)

        # Verify it's gone
        assert await self.repository.get_by_id_async("prod_123") is None

    @pytest.mark.asyncio
    async def test_find_with_predicate(self):
        """Test finding entities with predicate"""
        products = [
            TestProduct(id="1", name="Product A", price=10.0, category="Electronics"),
            TestProduct(id="2", name="Product B", price=20.0, category="Books"),
            TestProduct(id="3", name="Product C", price=30.0, category="Electronics"),
            TestProduct(id="4", name="Product D", price=40.0, category="Clothing"),
        ]

        for product in products:
            await self.repository.add_async(product)

        # Find electronics products
        electronics = await self.repository.find_async(lambda p: p.category == "Electronics")
        assert len(electronics) == 2
        assert all(p.category == "Electronics" for p in electronics)

        # Find products over $25
        expensive = await self.repository.find_async(lambda p: p.price > 25.0)
        assert len(expensive) == 2
        assert all(p.price > 25.0 for p in expensive)

        # Find non-existent category
        none_found = await self.repository.find_async(lambda p: p.category == "NonExistent")
        assert len(none_found) == 0


# Test MongoRepository (mocked)


class TestMongoRepository:
    @pytest.mark.asyncio
    async def test_mongo_repository_get_by_id(self):
        """Test MongoRepository get_by_id with mocked MongoDB"""
        with patch("neuroglia.data.mongo_repository.AsyncIOMotorClient") as mock_client:
            # Mock MongoDB collection
            mock_collection = Mock()
            mock_client.return_value.__getitem__.return_value.__getitem__.return_value = mock_collection

            # Mock find_one result
            mock_collection.find_one = AsyncMock(
                return_value={
                    "_id": "prod_123",
                    "name": "Test Product",
                    "price": 29.99,
                    "category": "Electronics",
                    "is_available": True,
                }
            )

            # Create repository
            repository = MongoRepository[TestProduct, str](
                connection_string="mongodb://localhost:27017",
                database_name="test_db",
                collection_name="products",
                entity_type=TestProduct,
            )

            # Get entity
            result = await repository.get_by_id_async("prod_123")

            # Verify result
            assert result is not None
            assert result.id == "prod_123"
            assert result.name == "Test Product"
            assert result.price == 29.99

            # Verify MongoDB was called correctly
            mock_collection.find_one.assert_called_once_with({"_id": "prod_123"})

    @pytest.mark.asyncio
    async def test_mongo_repository_add(self):
        """Test MongoRepository add with mocked MongoDB"""
        with patch("neuroglia.data.mongo_repository.AsyncIOMotorClient") as mock_client:
            # Mock MongoDB collection
            mock_collection = Mock()
            mock_client.return_value.__getitem__.return_value.__getitem__.return_value = mock_collection

            # Mock insert_one result
            mock_result = Mock()
            mock_result.inserted_id = "prod_123"
            mock_collection.insert_one = AsyncMock(return_value=mock_result)

            # Create repository
            repository = MongoRepository[TestProduct, str](
                connection_string="mongodb://localhost:27017",
                database_name="test_db",
                collection_name="products",
                entity_type=TestProduct,
            )

            # Add entity
            product = TestProduct(id="prod_123", name="Test Product", price=29.99, category="Electronics")

            result = await repository.add_async(product)

            # Verify result
            assert result == product

            # Verify MongoDB was called
            mock_collection.insert_one.assert_called_once()
            call_args = mock_collection.insert_one.call_args[0][0]
            assert call_args["_id"] == "prod_123"
            assert call_args["name"] == "Test Product"


# Test EventSourcingRepository (mocked)


class TestEventSourcingRepository:
    @pytest.mark.asyncio
    async def test_event_sourcing_repository_save_aggregate(self):
        """Test saving aggregate with events"""
        with patch("neuroglia.data.event_sourcing_repository.EventStore") as mock_event_store:
            # Mock event store
            mock_store_instance = Mock()
            mock_event_store.return_value = mock_store_instance
            mock_store_instance.append_to_stream = AsyncMock()

            # Create repository
            repository = EventSourcingRepository[ProductAggregate](event_store=mock_store_instance, aggregate_type=ProductAggregate)

            # Create aggregate with events
            aggregate = ProductAggregate("prod_123")
            aggregate.create_product("Test Product", 29.99, "Electronics")
            aggregate.change_price(39.99)

            # Save aggregate
            await repository.save_async(aggregate)

            # Verify events were saved
            mock_store_instance.append_to_stream.assert_called_once()
            call_args = mock_store_instance.append_to_stream.call_args
            stream_name = call_args[0][0]
            events = call_args[0][1]

            assert stream_name == f"ProductAggregate-prod_123"
            assert len(events) == 2

    @pytest.mark.asyncio
    async def test_event_sourcing_repository_load_aggregate(self):
        """Test loading aggregate from events"""
        with patch("neuroglia.data.event_sourcing_repository.EventStore") as mock_event_store:
            # Mock event store
            mock_store_instance = Mock()
            mock_event_store.return_value = mock_store_instance

            # Mock events from store
            mock_events = [
                ProductCreatedEvent(
                    product_id="prod_123",
                    name="Test Product",
                    price=29.99,
                    category="Electronics",
                    created_at=datetime.utcnow(),
                ),
                ProductPriceChangedEvent(
                    product_id="prod_123",
                    old_price=29.99,
                    new_price=39.99,
                    changed_at=datetime.utcnow(),
                ),
            ]

            mock_store_instance.read_stream = AsyncMock(return_value=mock_events)

            # Create repository
            repository = EventSourcingRepository[ProductAggregate](event_store=mock_store_instance, aggregate_type=ProductAggregate)

            # Load aggregate
            aggregate = await repository.get_by_id_async("prod_123")

            # Verify aggregate state
            assert aggregate is not None
            assert aggregate.id == "prod_123"
            assert aggregate.name == "Test Product"
            assert aggregate.price == 39.99
            assert aggregate.category == "Electronics"

            # Verify no uncommitted events
            assert len(aggregate.get_uncommitted_events()) == 0


# Integration tests


class TestDataAccessIntegration:
    @pytest.mark.asyncio
    async def test_repository_with_multiple_entity_types(self):
        """Test repository with different entity types"""
        product_repo = MemoryRepository[TestProduct, str]()
        order_repo = MemoryRepository[TestOrder, str]()

        # Add products
        product1 = TestProduct(id="1", name="Product 1", price=10.0, category="A")
        product2 = TestProduct(id="2", name="Product 2", price=20.0, category="B")

        await product_repo.add_async(product1)
        await product_repo.add_async(product2)

        # Add orders
        order1 = TestOrder(
            id="order_1",
            customer_name="John Doe",
            items=[{"product_id": "1", "quantity": 2, "price": 10.0}],
            total_amount=20.0,
        )

        await order_repo.add_async(order1)

        # Verify separation
        products = await product_repo.find_async(lambda p: True)
        orders = await order_repo.find_async(lambda o: True)

        assert len(products) == 2
        assert len(orders) == 1
        assert all(isinstance(p, TestProduct) for p in products)
        assert all(isinstance(o, TestOrder) for o in orders)

    @pytest.mark.asyncio
    async def test_aggregate_event_sourcing_workflow(self):
        """Test complete event sourcing workflow"""
        # Create aggregate
        aggregate = ProductAggregate("prod_123")

        # Apply business operations
        aggregate.create_product("Test Product", 29.99, "Electronics")
        aggregate.change_price(39.99)
        aggregate.change_price(49.99)

        # Verify state
        assert aggregate.name == "Test Product"
        assert aggregate.price == 49.99
        assert aggregate.category == "Electronics"

        # Verify events
        events = aggregate.get_uncommitted_events()
        assert len(events) == 3

        # Verify event types and order
        assert isinstance(events[0], ProductCreatedEvent)
        assert isinstance(events[1], ProductPriceChangedEvent)
        assert isinstance(events[2], ProductPriceChangedEvent)

        # Verify event data
        assert events[1].old_price == 29.99
        assert events[1].new_price == 39.99
        assert events[2].old_price == 39.99
        assert events[2].new_price == 49.99

        # Simulate saving and reloading
        aggregate.mark_events_as_committed()
        assert len(aggregate.get_uncommitted_events()) == 0

    def test_domain_model_validation(self):
        """Test domain model business rule validation"""
        # Test product validation
        product_aggregate = ProductAggregate()

        # Invalid product creation
        with pytest.raises(ValueError):
            product_aggregate.create_product("", 10.0, "Category")  # Empty name

        with pytest.raises(ValueError):
            product_aggregate.create_product("Product", -10.0, "Category")  # Negative price

        with pytest.raises(ValueError):
            product_aggregate.create_product("Product", 10.0, "")  # Empty category

        # Valid product creation
        product_aggregate.create_product("Valid Product", 29.99, "Electronics")
        assert product_aggregate.name == "Valid Product"

        # Test order validation
        order_aggregate = OrderAggregate()

        # Invalid order creation
        with pytest.raises(ValueError):
            order_aggregate.place_order("", [])  # Empty customer name

        with pytest.raises(ValueError):
            order_aggregate.place_order("Customer", [])  # No items

        invalid_items = [{"name": "Item", "price": 10.0, "quantity": 0}]
        with pytest.raises(ValueError):
            order_aggregate.place_order("Customer", invalid_items)  # Zero total

        # Valid order creation
        valid_items = [{"name": "Item", "price": 10.0, "quantity": 2}]
        order_aggregate.place_order("John Doe", valid_items)
        assert order_aggregate.customer_name == "John Doe"
        assert order_aggregate.total_amount == 20.0
