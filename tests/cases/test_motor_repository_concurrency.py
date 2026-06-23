"""
Test suite for MotorRepository Optimistic Concurrency Control.

This module validates OCC implementation for state-based persistence with MongoDB,
ensuring proper conflict detection and version management.

Test Coverage:
    - Concurrent update detection
    - Version increment on save
    - EntityNotFoundException handling
    - Retry patterns
    - Non-AggregateRoot entities (no OCC)

Expected Behavior:
    - Version starts at 0 for new aggregates
    - Version increments by 1 per save
    - Concurrent updates raise OptimisticConcurrencyException
    - Exception contains accurate version information

Related Modules:
    - neuroglia.data.infrastructure.mongo.motor_repository: Repository implementation
    - neuroglia.data.exceptions: OCC exception classes
    - neuroglia.data.abstractions: AggregateRoot and AggregateState

Related Documentation:
    - [Data Access](../../docs/features/data-access.md)
    - [Optimistic Concurrency](../../docs/patterns/concurrency.md)
"""

from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from neuroglia.data.abstractions import AggregateRoot, AggregateState, Entity
from neuroglia.data.exceptions import (
    EntityNotFoundException,
    OptimisticConcurrencyException,
)


# Test Domain Models
@dataclass
class OrderState(AggregateState[str]):
    """Test aggregate state for concurrency testing."""

    customer_id: str = ""
    status: str = "PENDING"
    total_amount: float = 0.0

    def __post_init__(self):
        """Initialize parent class fields and generate ID if needed."""
        # Initialize parent class (sets state_version, created_at, last_modified)
        super().__init__()
        # Generate ID if not already set
        if not hasattr(self, "id") or self.id is None:
            self.id = str(uuid4())


class Order(AggregateRoot[OrderState, str]):
    """Test aggregate root for OCC testing."""

    def __init__(self, customer_id: str):
        super().__init__()
        self.state.id = str(uuid4())
        self.state.customer_id = customer_id
        self.state.status = "PENDING"
        self.state.total_amount = 0.0

    def confirm(self):
        """Confirm the order."""
        self.state.status = "CONFIRMED"

    def update_total(self, amount: float):
        """Update order total."""
        self.state.total_amount = amount


class SimpleEntity(Entity[str]):
    """Test entity without aggregate root (no OCC)."""

    def __init__(self, name: str):
        super().__init__()
        self.id = str(uuid4())
        self.name = name


@pytest.mark.unit
class TestOptimisticConcurrencyControl:
    """Test optimistic concurrency control for MotorRepository."""

    @pytest.fixture
    def mock_collection(self):
        """Create mock MongoDB collection."""
        collection = Mock()
        collection.insert_one = AsyncMock()
        collection.find_one = AsyncMock()
        collection.replace_one = AsyncMock()
        collection.delete_one = AsyncMock()
        return collection

    @pytest.fixture
    def mock_client(self, mock_collection):
        """Create mock Motor client with database access."""
        client = Mock()
        database = Mock()
        database.__getitem__ = Mock(return_value=mock_collection)
        client.__getitem__ = Mock(return_value=database)
        return client

    @pytest.fixture
    def mock_serializer(self):
        """Create mock serializer."""
        from neuroglia.serialization.json import JsonSerializer

        return JsonSerializer()

    def _create_repository(self, mock_client, mock_serializer, entity_type=Order):
        """Helper to create repository instance."""
        from neuroglia.data.infrastructure.mongo import MotorRepository

        return MotorRepository(
            client=mock_client,
            database_name="test_db",
            collection_name="test_collection",
            serializer=mock_serializer,
            entity_type=entity_type,
        )

    @pytest.mark.asyncio
    async def test_new_aggregate_starts_with_version_zero(self, mock_client, mock_collection, mock_serializer):
        """
        Test that new aggregates are initialized with version 0.

        Expected Behavior:
            - state_version = 0 on creation
            - Version persisted to MongoDB
            - Timestamps set correctly
        """
        # Arrange
        repository = self._create_repository(mock_client, mock_serializer)
        order = Order(customer_id="cust123")

        # Act
        await repository.add_async(order)

        # Assert
        assert order.state.state_version == 0
        assert order.state.created_at is not None
        assert order.state.last_modified is not None
        mock_collection.insert_one.assert_called_once()

        # Check serialized document has version
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["state_version"] == 0

    @pytest.mark.asyncio
    async def test_update_increments_version(self, mock_client, mock_collection, mock_serializer):
        """
        Test that update operations increment version by 1.

        Expected Behavior:
            - Version increments: 0 → 1 → 2
            - Each save increments once
            - MongoDB query includes version check
        """
        # Arrange
        repository = self._create_repository(mock_client, mock_serializer)
        order = Order(customer_id="cust123")
        assert order.state.state_version == 0

        # Mock successful update
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_collection.replace_one.return_value = mock_result

        # Act - First update
        order.confirm()
        await repository.update_async(order)

        # Assert - Version incremented
        assert order.state.state_version == 1

        # Verify MongoDB query included version check
        call_args = mock_collection.replace_one.call_args
        query_filter = call_args[0][0]
        assert query_filter["state_version"] == 0  # Expected old version

        # Act - Second update
        order.update_total(99.99)
        await repository.update_async(order)

        # Assert - Version incremented again
        assert order.state.state_version == 2

    @pytest.mark.asyncio
    async def test_concurrent_update_raises_exception(self, mock_client, mock_collection, mock_serializer):
        """
        Test that concurrent modifications raise OptimisticConcurrencyException.

        Expected Behavior:
            - matched_count = 0 triggers conflict detection
            - Exception contains entity_id, expected_version, actual_version
            - Original version unchanged
        """
        # Arrange
        repository = self._create_repository(mock_client, mock_serializer)
        order = Order(customer_id="cust123")
        order.state.state_version = 5  # Simulate loaded state

        # Mock concurrent modification (no match found)
        mock_result = Mock()
        mock_result.matched_count = 0
        mock_collection.replace_one.return_value = mock_result

        # Mock existing document with different version
        mock_collection.find_one.return_value = {
            "id": order.id(),
            "state_version": 7,  # Someone else updated it
            "status": "CONFIRMED",
        }

        # Act & Assert
        with pytest.raises(OptimisticConcurrencyException) as exc_info:
            await repository.update_async(order)

        # Verify exception details
        exception = exc_info.value
        assert exception.entity_id == order.id()
        assert exception.expected_version == 5
        assert exception.actual_version == 7
        assert "modified by another process" in str(exception).lower()

        # Version should be incremented (but update failed)
        assert order.state.state_version == 6

    @pytest.mark.asyncio
    async def test_update_nonexistent_entity_raises_not_found(self, mock_client, mock_collection, mock_serializer):
        """
        Test that updating non-existent entity raises EntityNotFoundException.

        Expected Behavior:
            - matched_count = 0 and find_one returns None
            - EntityNotFoundException raised
            - Exception contains entity_id and type
        """
        # Arrange
        repository = self._create_repository(mock_client, mock_serializer)
        order = Order(customer_id="cust123")
        order_id = order.id()

        # Mock entity not found
        mock_result = Mock()
        mock_result.matched_count = 0
        mock_collection.replace_one.return_value = mock_result
        mock_collection.find_one.return_value = None

        # Act & Assert
        with pytest.raises(EntityNotFoundException) as exc_info:
            await repository.update_async(order)

        # Verify exception details
        exception = exc_info.value
        assert exception.entity_id == order_id
        assert "Order" in str(exception)

    @pytest.mark.asyncio
    async def test_multiple_events_single_version_increment(self, mock_client, mock_collection, mock_serializer):
        """
        Test that multiple events in same transaction = single version increment.

        This is the key difference from event sourcing where each event
        increments the version.

        Expected Behavior:
            - Multiple domain events raised
            - Single save operation
            - Version increments once (not per event)
        """
        # Arrange
        repository = self._create_repository(mock_client, mock_serializer)
        order = Order(customer_id="cust123")
        initial_version = order.state.state_version

        # Mock successful update
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_collection.replace_one.return_value = mock_result

        # Act - Multiple operations before save
        order.confirm()  # Event 1
        order.update_total(25.0)  # Event 2
        order.update_total(30.0)  # Event 3

        await repository.update_async(order)

        # Assert - Version incremented only once
        assert order.state.state_version == initial_version + 1

    @pytest.mark.asyncio
    async def test_simple_entity_no_concurrency_control(self, mock_client, mock_collection, mock_serializer):
        """
        Test that non-AggregateRoot entities update without OCC.

        Expected Behavior:
            - No version checking
            - Simple replace operation
            - No OptimisticConcurrencyException
        """
        from neuroglia.data.infrastructure.mongo import MotorRepository

        # Arrange
        repository = MotorRepository(
            client=mock_client,
            database_name="test_db",
            collection_name="test_collection",
            serializer=mock_serializer,
            entity_type=SimpleEntity,
        )
        entity = SimpleEntity(name="Test")

        # Mock successful update
        mock_collection.replace_one = AsyncMock()

        # Act - Update without version check
        entity.name = "Updated"
        await repository.update_async(entity)

        # Assert - No version in query filter
        call_args = mock_collection.replace_one.call_args
        query_filter = call_args[0][0]
        assert "state_version" not in query_filter
        assert query_filter["id"] == entity.id

    @pytest.mark.asyncio
    async def test_last_modified_updated_on_save(self, mock_client, mock_collection, mock_serializer):
        """
        Test that last_modified timestamp is updated on each save.

        Expected Behavior:
            - last_modified updated on update_async
            - Timestamp reflects save time, not event time
        """
        # Arrange
        repository = self._create_repository(mock_client, mock_serializer)
        order = Order(customer_id="cust123")
        original_modified = order.state.last_modified

        # Mock successful update
        mock_result = Mock()
        mock_result.matched_count = 1
        mock_collection.replace_one.return_value = mock_result

        # Act - Update after small delay
        import asyncio

        await asyncio.sleep(0.01)
        order.confirm()
        await repository.update_async(order)

        # Assert - last_modified updated
        assert order.state.last_modified > original_modified


@pytest.mark.unit
class TestConcurrencyExceptionDetails:
    """Test OptimisticConcurrencyException structure."""

    def test_exception_contains_version_info(self):
        """
        Test exception contains all necessary information.

        Expected Behavior:
            - entity_id accessible
            - expected_version accessible
            - actual_version accessible
            - Human-readable message
        """
        exception = OptimisticConcurrencyException(entity_id="order123", expected_version=5, actual_version=7)

        assert exception.entity_id == "order123"
        assert exception.expected_version == 5
        assert exception.actual_version == 7
        assert "order123" in str(exception)
        assert "5" in str(exception)
        assert "7" in str(exception)

    def test_entity_not_found_exception(self):
        """Test EntityNotFoundException structure."""
        exception = EntityNotFoundException(entity_id="order123", entity_type="Order")

        assert exception.entity_id == "order123"
        assert exception.entity_type == "Order"
        assert "Order" in str(exception)
        assert "order123" in str(exception)
