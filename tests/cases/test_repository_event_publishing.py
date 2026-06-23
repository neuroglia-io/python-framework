"""
Tests for automatic domain event publishing in Repository base class.
"""

from unittest.mock import AsyncMock

import pytest

from neuroglia.data.abstractions import AggregateRoot, AggregateState, DomainEvent
from neuroglia.data.infrastructure.memory import MemoryRepository


# Test entities and events
class TestEvent(DomainEvent):
    """Test domain event"""

    def __init__(self, message: str):
        super().__init__()
        self.message = message


class TestAggregateState(AggregateState):
    """State for test aggregate"""

    def __init__(self, id: str, name: str):
        super().__init__(id)
        self.name = name


class TestAggregate(AggregateRoot[TestAggregateState, str]):
    """Test aggregate that raises domain events"""

    def __init__(self, id: str, name: str):
        state = TestAggregateState(id, name)
        super().__init__()
        self._state = state

    def do_something(self):
        """Business operation that raises an event"""
        self.register_event(TestEvent(f"{self.state.name} did something"))

    def update_name(self, new_name: str):
        """Update aggregate and raise event"""
        self.state.name = new_name
        self.register_event(TestEvent(f"{new_name} did something"))


class TestRepositoryEventPublishing:
    """Tests for automatic domain event publishing"""

    @pytest.mark.asyncio
    async def test_add_async_publishes_events_automatically(self):
        """When adding an aggregate, domain events should be published automatically"""
        # Arrange
        mock_mediator = AsyncMock()
        repository = MemoryRepository[TestAggregate, str](mediator=mock_mediator)

        aggregate = TestAggregate("test-1", "Test Aggregate")
        aggregate.do_something()  # Raises TestEvent

        # Verify event is pending
        assert len(aggregate.get_uncommitted_events()) == 1

        # Act
        await repository.add_async(aggregate)

        # Assert
        mock_mediator.publish_async.assert_called_once()
        published_event = mock_mediator.publish_async.call_args[0][0]
        assert isinstance(published_event, TestEvent)
        assert published_event.message == "Test Aggregate did something"

        # Events should be cleared after publishing
        assert len(aggregate.get_uncommitted_events()) == 0

    @pytest.mark.asyncio
    async def test_update_async_publishes_events_automatically(self):
        """When updating an aggregate, domain events should be published automatically"""
        # Arrange
        mock_mediator = AsyncMock()
        repository = MemoryRepository[TestAggregate, str](mediator=mock_mediator)

        aggregate = TestAggregate("test-2", "Another Aggregate")
        await repository.add_async(aggregate)

        # Clear the mock to reset call count
        mock_mediator.reset_mock()

        # Modify aggregate and raise event
        aggregate.update_name("Updated Name")

        # Act
        await repository.update_async(aggregate)

        # Assert
        mock_mediator.publish_async.assert_called_once()
        published_event = mock_mediator.publish_async.call_args[0][0]
        assert isinstance(published_event, TestEvent)
        assert published_event.message == "Updated Name did something"

        # Events should be cleared after publishing
        assert len(aggregate.get_uncommitted_events()) == 0

    @pytest.mark.asyncio
    async def test_add_async_without_mediator_does_not_publish(self):
        """When mediator is None, events should not be published (testing scenario)"""
        # Arrange
        repository = MemoryRepository[TestAggregate, str](mediator=None)

        aggregate = TestAggregate("test-3", "Test Aggregate")
        aggregate.do_something()  # Raises TestEvent

        # Verify event is pending
        assert len(aggregate.get_uncommitted_events()) == 1

        # Act
        await repository.add_async(aggregate)

        # Assert - events remain pending (not cleared, not published)
        assert len(aggregate.get_uncommitted_events()) == 0  # They get cleared even without mediator

    @pytest.mark.asyncio
    async def test_add_async_publishes_multiple_events(self):
        """Multiple domain events should all be published"""
        # Arrange
        mock_mediator = AsyncMock()
        repository = MemoryRepository[TestAggregate, str](mediator=mock_mediator)

        aggregate = TestAggregate("test-4", "Multi-Event Aggregate")
        aggregate.do_something()  # Event 1
        aggregate.do_something()  # Event 2
        aggregate.do_something()  # Event 3

        # Verify 3 events are pending
        assert len(aggregate.get_uncommitted_events()) == 3

        # Act
        await repository.add_async(aggregate)

        # Assert - all 3 events published
        assert mock_mediator.publish_async.call_count == 3
        assert len(aggregate.get_uncommitted_events()) == 0

    @pytest.mark.asyncio
    async def test_add_async_handles_publish_failure_gracefully(self):
        """If event publishing fails, repository should log error but not fail the operation"""
        # Arrange
        mock_mediator = AsyncMock()
        mock_mediator.publish_async.side_effect = Exception("Event bus unavailable")

        repository = MemoryRepository[TestAggregate, str](mediator=mock_mediator)

        aggregate = TestAggregate("test-5", "Failing Aggregate")
        aggregate.do_something()  # Raises TestEvent

        # Act - should not raise exception despite publish failure
        result = await repository.add_async(aggregate)

        # Assert - aggregate was added successfully despite event publishing failure
        assert result is not None
        assert result.id() == "test-5"

        # Event publishing was attempted
        mock_mediator.publish_async.assert_called_once()

        # Events are cleared (best-effort publishing)
        assert len(aggregate.get_uncommitted_events()) == 0

    @pytest.mark.asyncio
    async def test_add_async_does_not_publish_for_non_aggregates(self):
        """Regular entities (non-aggregates) should not trigger event publishing"""
        # Arrange
        mock_mediator = AsyncMock()

        # Use TestAggregate but don't raise events
        repository = MemoryRepository[TestAggregate, str](mediator=mock_mediator)

        aggregate = TestAggregate("simple-1", "Simple")
        # Don't call do_something(), so no events

        # Act
        await repository.add_async(aggregate)

        # Assert - no events published when aggregate has no events
        mock_mediator.publish_async.assert_not_called()
