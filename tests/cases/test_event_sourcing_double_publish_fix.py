"""
Test suite to verify that event sourcing repositories do not double-publish events.

This test validates the fix for the double CloudEvent emission issue where:
- EventSourcingRepository would try to publish events via base Repository._publish_domain_events()
- ReadModelReconciliator would also publish the same events from EventStore subscription
- Result: 2 CloudEvents per domain event (BROKEN)

After fix:
- EventSourcingRepository overrides _publish_domain_events() to do nothing
- Only ReadModelReconciliator publishes events from EventStore
- Result: 1 CloudEvent per domain event (CORRECT)
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from neuroglia.data.abstractions import AggregateRoot, AggregateState, DomainEvent
from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    Aggregator,
    EventStore,
)
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepository,
)
from neuroglia.mediation.mediator import Mediator


# Test fixtures
class TestAggregateState(AggregateState):
    """Test aggregate state"""

    def __init__(self):
        super().__init__()
        self.id = "test-123"
        self.name = "Test"


class TestDomainEvent(DomainEvent):
    """Test domain event"""

    def __init__(self, aggregate_id: str, message: str):
        super().__init__(aggregate_id)
        self.message = message


class TestAggregate(AggregateRoot[TestAggregateState, str]):
    """Test aggregate that raises domain events"""

    def id(self) -> str:
        return self.state.id

    def do_something(self, message: str):
        """Business method that raises a domain event"""
        event = TestDomainEvent(self.id(), message)
        self.register_event(event)


class TestEventSourcingRepositoryEventPublishing:
    """Test that EventSourcingRepository does not publish events directly"""

    @pytest.mark.asyncio
    async def test_event_sourcing_repository_does_not_call_mediator_publish(self):
        """
        Verify EventSourcingRepository does NOT publish events via mediator.

        This prevents double publishing since ReadModelReconciliator will
        publish events from the EventStore subscription.
        """
        # Arrange
        mock_eventstore = Mock(spec=EventStore)
        mock_eventstore.append_async = AsyncMock()

        mock_aggregator = Mock(spec=Aggregator)

        mock_mediator = Mock(spec=Mediator)
        mock_mediator.publish_async = AsyncMock()

        repo = EventSourcingRepository[TestAggregate, str](eventstore=mock_eventstore, aggregator=mock_aggregator, mediator=mock_mediator)

        # Create aggregate with domain event
        aggregate = TestAggregate()
        aggregate.do_something("test message")

        # Verify aggregate has pending events
        assert len(aggregate._pending_events) == 1
        assert isinstance(aggregate._pending_events[0], TestDomainEvent)

        # Act - save aggregate (which persists events to EventStore)
        with patch.object(repo, "_build_stream_id_for", return_value="test-stream"):
            await repo.add_async(aggregate)

        # Assert - Mediator.publish_async should NOT be called
        # (ReadModelReconciliator handles event publishing from EventStore)
        mock_mediator.publish_async.assert_not_called()

        # Verify events were persisted to EventStore
        mock_eventstore.append_async.assert_called_once()

        # Verify events were cleared from aggregate
        assert len(aggregate._pending_events) == 0

    @pytest.mark.asyncio
    async def test_event_sourcing_repository_update_does_not_call_mediator_publish(self):
        """
        Verify EventSourcingRepository does NOT publish events on update.

        Same logic as add - prevents double publishing.
        """
        # Arrange
        mock_eventstore = Mock(spec=EventStore)
        mock_eventstore.append_async = AsyncMock()

        mock_aggregator = Mock(spec=Aggregator)

        mock_mediator = Mock(spec=Mediator)
        mock_mediator.publish_async = AsyncMock()

        repo = EventSourcingRepository[TestAggregate, str](eventstore=mock_eventstore, aggregator=mock_aggregator, mediator=mock_mediator)

        # Create aggregate with domain event
        aggregate = TestAggregate()
        aggregate.state.state_version = 5  # Simulate existing aggregate
        aggregate.do_something("update message")

        # Act - update aggregate
        with patch.object(repo, "_build_stream_id_for", return_value="test-stream"):
            await repo.update_async(aggregate)

        # Assert - Mediator.publish_async should NOT be called
        mock_mediator.publish_async.assert_not_called()

        # Verify events were persisted with expected version
        mock_eventstore.append_async.assert_called_once()
        call_args = mock_eventstore.append_async.call_args
        # expected_version is the 3rd positional argument (stream_id, events, expected_version)
        assert call_args[0][2] == 5  # Optimistic concurrency

    @pytest.mark.asyncio
    async def test_event_sourcing_repository_with_no_mediator_still_works(self):
        """
        Verify EventSourcingRepository works without mediator (testing scenario).

        This is important for backward compatibility and testing.
        """
        # Arrange
        mock_eventstore = Mock(spec=EventStore)
        mock_eventstore.append_async = AsyncMock()

        mock_aggregator = Mock(spec=Aggregator)

        # No mediator provided (mediator=None)
        repo = EventSourcingRepository[TestAggregate, str](eventstore=mock_eventstore, aggregator=mock_aggregator, mediator=None)

        # Create aggregate with domain event
        aggregate = TestAggregate()
        aggregate.do_something("test message")

        # Act - should not raise any exceptions
        with patch.object(repo, "_build_stream_id_for", return_value="test-stream"):
            result = await repo.add_async(aggregate)

        # Assert - no errors, events persisted
        assert result is not None
        mock_eventstore.append_async.assert_called_once()
        assert len(aggregate._pending_events) == 0

    @pytest.mark.asyncio
    async def test_event_sourcing_repository_multiple_events_no_duplicate_publishing(self):
        """
        Verify that multiple domain events do not cause multiple publishes.

        All events are persisted to EventStore, but none are published directly.
        """
        # Arrange
        mock_eventstore = Mock(spec=EventStore)
        mock_eventstore.append_async = AsyncMock()

        mock_aggregator = Mock(spec=Aggregator)

        mock_mediator = Mock(spec=Mediator)
        mock_mediator.publish_async = AsyncMock()

        repo = EventSourcingRepository[TestAggregate, str](eventstore=mock_eventstore, aggregator=mock_aggregator, mediator=mock_mediator)

        # Create aggregate with multiple domain events
        aggregate = TestAggregate()
        aggregate.do_something("event 1")
        aggregate.do_something("event 2")
        aggregate.do_something("event 3")

        # Verify aggregate has 3 pending events
        assert len(aggregate._pending_events) == 3

        # Act - save aggregate
        with patch.object(repo, "_build_stream_id_for", return_value="test-stream"):
            await repo.add_async(aggregate)

        # Assert - Mediator.publish_async should NOT be called (not even once)
        mock_mediator.publish_async.assert_not_called()

        # Verify all 3 events were persisted to EventStore
        mock_eventstore.append_async.assert_called_once()
        call_args = mock_eventstore.append_async.call_args
        events = call_args[0][1]  # Second positional argument is events list
        assert len(events) == 3

        # Verify events were cleared
        assert len(aggregate._pending_events) == 0


class TestEventSourcingRepositoryMethodOverride:
    """Test that _publish_domain_events is correctly overridden"""

    def test_publish_domain_events_method_exists(self):
        """Verify EventSourcingRepository has _publish_domain_events method"""
        assert hasattr(EventSourcingRepository, "_publish_domain_events")
        assert callable(getattr(EventSourcingRepository, "_publish_domain_events"))

    @pytest.mark.asyncio
    async def test_publish_domain_events_is_noop(self):
        """Verify _publish_domain_events does nothing (override implementation)"""
        # Arrange
        mock_eventstore = Mock(spec=EventStore)
        mock_aggregator = Mock(spec=Aggregator)
        mock_mediator = Mock(spec=Mediator)

        repo = EventSourcingRepository[TestAggregate, str](eventstore=mock_eventstore, aggregator=mock_aggregator, mediator=mock_mediator)

        aggregate = TestAggregate()
        aggregate.do_something("test")

        # Act - call _publish_domain_events directly
        await repo._publish_domain_events(aggregate)

        # Assert - should do nothing (no mediator calls)
        mock_mediator.publish_async.assert_not_called()

        # Events should still be in aggregate (not cleared by this method)
        assert len(aggregate._pending_events) == 1


class TestBackwardCompatibilityWithStateBased:
    """
    Test that state-based repositories still work correctly.

    This ensures the fix doesn't break existing state-based persistence.
    """

    @pytest.mark.asyncio
    async def test_state_based_repository_still_publishes_events(self):
        """
        Verify state-based repositories continue to publish events.

        This test documents the expected behavior for comparison.
        State-based repositories inherit the base Repository._publish_domain_events()
        which DOES publish events (unlike EventSourcingRepository override).
        """
        # This is a documentation test showing the difference:
        # - EventSourcingRepository: _publish_domain_events() does nothing
        # - State-based Repository: _publish_domain_events() publishes events

        # The actual state-based repository tests are in their respective test files
        # (e.g., test_motor_repository.py, test_mongo_repository.py)

        pass  # Documented pattern, actual tests elsewhere


# Integration test documentation
class TestEventPublishingIntegrationPattern:
    """
    Documentation of the complete event publishing flow.

    This class documents how event publishing works end-to-end:

    1. Command Handler creates/modifies aggregate
    2. Aggregate raises domain events
    3. Repository persists changes:
       a. EventSourcingRepository → EventStore (does NOT publish)
       b. State-based Repository → Database (DOES publish)
    4. For event sourcing only:
       - ReadModelReconciliator subscribes to EventStore
       - Publishes events via Mediator
       - DomainEventCloudEventBehavior converts to CloudEvents
       - Single CloudEvent emitted per domain event ✅

    See: notes/fixes/EVENT_SOURCING_DOUBLE_PUBLISH_FIX.md
    """
