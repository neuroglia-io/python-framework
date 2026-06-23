"""Tests for Aggregator.aggregate method ensuring _pending_events is properly initialized."""

from unittest.mock import Mock

from neuroglia.data.abstractions import AggregateRoot, AggregateState, DomainEvent
from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    Aggregator,
    EventRecord,
)


class TestAggregateState(AggregateState):
    """Test aggregate state."""

    def __init__(self):
        super().__init__()
        self.value = 0

    def on(self, event: DomainEvent):
        """Apply event to state."""
        if hasattr(event, "increment"):
            self.value += event.increment


class TestDomainEvent(DomainEvent):
    """Test domain event."""

    def __init__(self, aggregate_id: str, increment: int):
        super().__init__(aggregate_id=aggregate_id)
        self.increment = increment
        self.aggregate_version = 1  # Set version as a field after __init__


class TestAggregate(AggregateRoot[TestAggregateState, str]):
    """Test aggregate for event reconstitution."""

    def __init__(self):
        super().__init__()


class TestAggregatorInitialization:
    """Test Aggregator properly initializes aggregates from events."""

    def test_aggregate_initializes_pending_events_list(self):
        """Test that aggregate() initializes _pending_events to empty list."""
        # Arrange
        aggregator = Aggregator()
        event_data = TestDomainEvent("test-id", 5)
        event_record = Mock(spec=EventRecord)
        event_record.data = event_data

        # Act
        aggregate = aggregator.aggregate([event_record], TestAggregate)

        # Assert
        assert hasattr(aggregate, "_pending_events"), "_pending_events attribute should exist"
        assert isinstance(aggregate._pending_events, list), "_pending_events should be a list"
        assert len(aggregate._pending_events) == 0, "_pending_events should be empty after reconstitution"

    def test_aggregate_does_not_raise_attribute_error(self):
        """Test that accessing _pending_events doesn't raise AttributeError."""
        # Arrange
        aggregator = Aggregator()
        event_data = TestDomainEvent("test-id", 10)
        event_record = Mock(spec=EventRecord)
        event_record.data = event_data

        # Act
        aggregate = aggregator.aggregate([event_record], TestAggregate)

        # Assert - should not raise AttributeError
        try:
            _ = aggregate._pending_events
            pending_events_accessible = True
        except AttributeError:
            pending_events_accessible = False

        assert pending_events_accessible, "_pending_events should be accessible without AttributeError"

    def test_aggregate_replays_events_correctly(self):
        """Test that aggregate() replays events to rebuild state."""
        # Arrange
        aggregator = Aggregator()
        event1 = TestDomainEvent("test-id", 3)
        event2 = TestDomainEvent("test-id", 7)

        record1 = Mock(spec=EventRecord)
        record1.data = event1
        record2 = Mock(spec=EventRecord)
        record2.data = event2

        # Act
        aggregate = aggregator.aggregate([record1, record2], TestAggregate)

        # Assert
        assert aggregate.state.value == 10, "State should be sum of all increments (3 + 7)"
        assert len(aggregate._pending_events) == 0, "No new events should be pending"

    def test_aggregate_can_register_new_events_after_reconstitution(self):
        """Test that reconstituted aggregate can register new events."""
        # Arrange
        aggregator = Aggregator()
        event_data = TestDomainEvent("test-id", 5)
        event_record = Mock(spec=EventRecord)
        event_record.data = event_data

        # Act
        aggregate = aggregator.aggregate([event_record], TestAggregate)

        # Register a new event after reconstitution
        new_event = TestDomainEvent("test-id", 2)
        aggregate.register_event(new_event)

        # Assert
        assert len(aggregate._pending_events) == 1, "Should have one pending event"
        assert aggregate._pending_events[0] == new_event, "Pending event should be the new event"

    def test_aggregate_domain_events_property_works(self):
        """Test that domain_events property works on reconstituted aggregate."""
        # Arrange
        aggregator = Aggregator()
        event_data = TestDomainEvent("test-id", 5)
        event_record = Mock(spec=EventRecord)
        event_record.data = event_data

        # Act
        aggregate = aggregator.aggregate([event_record], TestAggregate)

        # Assert - should not raise AttributeError
        events = aggregate.domain_events
        assert isinstance(events, list), "domain_events should return a list"
        assert len(events) == 0, "Should have no domain events initially"

    def test_aggregate_clear_pending_events_works(self):
        """Test that clear_pending_events() works on reconstituted aggregate."""
        # Arrange
        aggregator = Aggregator()
        event_data = TestDomainEvent("test-id", 5)
        event_record = Mock(spec=EventRecord)
        event_record.data = event_data

        aggregate = aggregator.aggregate([event_record], TestAggregate)

        # Register and then clear
        new_event = TestDomainEvent("test-id", 2)
        aggregate.register_event(new_event)

        # Act - should not raise AttributeError
        aggregate.clear_pending_events()

        # Assert
        assert len(aggregate._pending_events) == 0, "Pending events should be cleared"

    def test_aggregate_with_empty_event_list(self):
        """Test that aggregate() handles empty event list correctly."""
        # Arrange
        aggregator = Aggregator()

        # Act
        aggregate = aggregator.aggregate([], TestAggregate)

        # Assert
        assert hasattr(aggregate, "_pending_events"), "_pending_events should exist"
        assert len(aggregate._pending_events) == 0, "_pending_events should be empty"
        assert aggregate.state.value == 0, "State should be at initial value"
