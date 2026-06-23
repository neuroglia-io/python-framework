"""
Test FileSystemRepository with unified JsonSerializer approach.

This test validates that FileSystemRepository now:
1. Works directly with Repository base interface (not StateBasedRepository)
2. Uses JsonSerializer for automatic state extraction (not AggregateSerializer)
3. Stores clean state JSON without metadata wrappers
4. Handles both Entity and AggregateRoot transparently
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import pytest

from neuroglia.data.abstractions import AggregateRoot, AggregateState, Entity
from neuroglia.data.infrastructure.filesystem import FileSystemRepository


# Test Entities
class Customer(Entity[str]):
    """Simple Entity for testing."""

    def __init__(self, name: str, email: str):
        super().__init__()
        self.name = name
        self.email = email


# Test AggregateRoot
class OrderState(AggregateState[str]):
    """State object for Order aggregate."""

    # Class-level type annotations (required for JsonSerializer)
    id: str
    customer_id: str
    total: float
    status: str

    def __init__(self):
        super().__init__()
        self.id = ""
        self.customer_id = ""
        self.total = 0.0
        self.status = "PENDING"


class Order(AggregateRoot[OrderState, str]):
    """AggregateRoot for testing."""

    def __init__(self, customer_id: Optional[str] = None):
        super().__init__()
        # State is created automatically, now set fields
        if customer_id:
            self.state.customer_id = customer_id
        self.state.total = 0.0
        self.state.status = "PENDING"

    def add_item(self, price: float):
        """Add an item to the order."""
        self.state.total += price

    def confirm(self):
        """Confirm the order."""
        self.state.status = "CONFIRMED"


class TestFileSystemRepositoryUnified:
    """Test suite for unified FileSystemRepository."""

    @pytest.mark.asyncio
    async def test_entity_storage_produces_clean_json(self):
        """Verify Entity storage produces clean JSON without metadata."""
        with TemporaryDirectory() as temp_dir:
            repo = FileSystemRepository[Customer, str](data_directory=temp_dir, entity_type=Customer, key_type=str)

            # Create and save entity
            customer = Customer(name="John Doe", email="john@example.com")
            saved = await repo.add_async(customer)

            # Check file contents
            entity_dir = Path(temp_dir) / "customer"
            json_file = entity_dir / f"{saved.id}.json"
            assert json_file.exists()

            # Verify clean JSON (no metadata wrapper)
            with open(json_file) as f:
                stored_data = json.load(f)

            # Should have entity fields directly, not wrapped
            assert "id" in stored_data
            assert "name" in stored_data
            assert "email" in stored_data
            assert stored_data["name"] == "John Doe"
            assert stored_data["email"] == "john@example.com"

            # Should NOT have metadata wrapper
            assert "aggregate_type" not in stored_data
            assert "state" not in stored_data or isinstance(stored_data.get("state"), str)

    @pytest.mark.asyncio
    async def test_aggregate_storage_produces_clean_state_json(self):
        """Verify AggregateRoot storage produces clean state JSON without metadata."""
        with TemporaryDirectory() as temp_dir:
            repo = FileSystemRepository[Order, str](data_directory=temp_dir, entity_type=Order, key_type=str)

            # Create and save aggregate
            order = Order(customer_id="c123")
            order.add_item(29.99)
            order.add_item(19.99)
            order.confirm()

            saved = await repo.add_async(order)

            # Check file contents
            entity_dir = Path(temp_dir) / "order"
            json_file = entity_dir / f"{saved.id()}.json"
            assert json_file.exists()

            # Verify clean state JSON (no metadata wrapper)
            with open(json_file) as f:
                stored_data = json.load(f)

            # Should have state fields directly, not wrapped
            assert "id" in stored_data
            assert "customer_id" in stored_data
            assert "total" in stored_data
            assert "status" in stored_data
            assert stored_data["customer_id"] == "c123"
            assert stored_data["total"] == 49.98
            assert stored_data["status"] == "CONFIRMED"

            # Should NOT have metadata wrapper
            assert "aggregate_type" not in stored_data
            assert "state" not in stored_data or isinstance(stored_data.get("state"), (str, dict))

    @pytest.mark.asyncio
    async def test_entity_crud_operations(self):
        """Test complete CRUD workflow for Entity."""
        with TemporaryDirectory() as temp_dir:
            repo = FileSystemRepository[Customer, str](data_directory=temp_dir, entity_type=Customer, key_type=str)

            # Create
            customer = Customer(name="Jane Smith", email="jane@example.com")
            created = await repo.add_async(customer)
            assert created.id is not None
            assert created.name == "Jane Smith"

            # Read
            retrieved = await repo.get_async(created.id)
            assert retrieved is not None
            assert retrieved.name == "Jane Smith"
            assert retrieved.email == "jane@example.com"

            # Update
            retrieved.email = "jane.smith@example.com"
            updated = await repo.update_async(retrieved)
            assert updated.email == "jane.smith@example.com"

            # Verify update persisted
            re_retrieved = await repo.get_async(created.id)
            assert re_retrieved.email == "jane.smith@example.com"

            # Delete
            await repo.remove_async(created.id)

            # Verify deletion
            deleted = await repo.get_async(created.id)
            assert deleted is None

    @pytest.mark.asyncio
    async def test_aggregate_crud_operations(self):
        """Test complete CRUD workflow for AggregateRoot."""
        with TemporaryDirectory() as temp_dir:
            repo = FileSystemRepository[Order, str](data_directory=temp_dir, entity_type=Order, key_type=str)

            # Create
            order = Order(customer_id="c456")
            order.add_item(99.99)
            created = await repo.add_async(order)
            assert created.id() is not None
            assert created.state.total == 99.99
            assert created.state.status == "PENDING"

            # Read
            retrieved = await repo.get_async(created.id())
            assert retrieved is not None
            assert retrieved.state.customer_id == "c456"
            assert retrieved.state.total == 99.99
            assert retrieved.state.status == "PENDING"

            # Update
            retrieved.add_item(50.00)
            retrieved.confirm()
            updated = await repo.update_async(retrieved)
            assert updated.state.total == 149.99
            assert updated.state.status == "CONFIRMED"

            # Verify update persisted
            re_retrieved = await repo.get_async(created.id())
            assert re_retrieved.state.total == 149.99
            assert re_retrieved.state.status == "CONFIRMED"

            # Delete
            await repo.remove_async(created.id())

            # Verify deletion
            deleted = await repo.get_async(created.id())
            assert deleted is None

    @pytest.mark.asyncio
    async def test_entity_without_id_gets_generated_id(self):
        """Test that entities without IDs get automatic ID generation."""
        with TemporaryDirectory() as temp_dir:
            repo = FileSystemRepository[Customer, str](data_directory=temp_dir, entity_type=Customer, key_type=str)

            # Create entity without setting ID
            customer = Customer(name="Auto ID", email="auto@example.com")
            assert not hasattr(customer, "id") or customer.id is None

            # Save should generate ID
            saved = await repo.add_async(customer)
            assert saved.id is not None
            assert isinstance(saved.id, str)

            # Should be retrievable
            retrieved = await repo.get_async(saved.id)
            assert retrieved is not None
            assert retrieved.name == "Auto ID"

    @pytest.mark.asyncio
    async def test_aggregate_without_id_gets_generated_id(self):
        """Test that aggregates without IDs get automatic ID generation."""
        with TemporaryDirectory() as temp_dir:
            repo = FileSystemRepository[Order, str](data_directory=temp_dir, entity_type=Order, key_type=str)

            # Create aggregate without setting ID
            order = Order(customer_id="c789")
            # Empty string is treated as "no ID"
            assert order.id() == "" or order.id() is None

            # Save should generate ID
            saved = await repo.add_async(order)
            assert saved.id() is not None
            assert saved.id() != ""
            assert isinstance(saved.id(), str)

            # Should be retrievable
            retrieved = await repo.get_async(saved.id())
            assert retrieved is not None
            assert retrieved.state.customer_id == "c789"

    @pytest.mark.asyncio
    async def test_file_organization_by_entity_type(self):
        """Test that files are organized by entity type."""
        with TemporaryDirectory() as temp_dir:
            # Create repositories for different types
            customer_repo = FileSystemRepository[Customer, str](data_directory=temp_dir, entity_type=Customer, key_type=str)
            order_repo = FileSystemRepository[Order, str](data_directory=temp_dir, entity_type=Order, key_type=str)

            # Save entities
            customer = Customer(name="Test", email="test@example.com")
            order = Order(customer_id="c1")

            saved_customer = await customer_repo.add_async(customer)
            saved_order = await order_repo.add_async(order)

            # Verify directory structure
            base_dir = Path(temp_dir)
            customer_dir = base_dir / "customer"
            order_dir = base_dir / "order"

            assert customer_dir.exists()
            assert order_dir.exists()

            # Verify files in correct directories
            customer_file = customer_dir / f"{saved_customer.id}.json"
            order_file = order_dir / f"{saved_order.id()}.json"

            assert customer_file.exists()
            assert order_file.exists()

    @pytest.mark.asyncio
    async def test_repository_uses_json_serializer_not_aggregate_serializer(self):
        """Verify repository uses JsonSerializer (unified approach)."""
        with TemporaryDirectory() as temp_dir:
            repo = FileSystemRepository[Order, str](data_directory=temp_dir, entity_type=Order, key_type=str)

            # Check serializer type
            from neuroglia.serialization.json import JsonSerializer

            assert isinstance(repo.serializer, JsonSerializer)

            # Save aggregate and verify format
            order = Order(customer_id="c999")
            saved = await repo.add_async(order)

            # Read raw JSON
            json_file = Path(temp_dir) / "order" / f"{saved.id()}.json"
            with open(json_file) as f:
                stored_data = json.load(f)

            # Should be clean state (JsonSerializer format)
            assert "customer_id" in stored_data
            assert stored_data["customer_id"] == "c999"

            # Should NOT be wrapped (old AggregateSerializer format)
            assert "aggregate_type" not in stored_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
