from unittest.mock import Mock

from neuroglia.data.abstractions import AggregateRoot, DomainEvent
from neuroglia.data.unit_of_work import IUnitOfWork, UnitOfWork


class TestDomainEvent(DomainEvent):
    """Test domain event for unit testing."""

    def __init__(self, message: str):
        super().__init__()
        self.message = message


class TestAggregateRoot(AggregateRoot):
    """Test aggregate root for unit testing."""

    def __init__(self, id: str):
        super().__init__()
        self._id = id

    @property
    def id(self):
        return self._id

    def raise_test_event(self, message: str):
        """Raises a test domain event."""
        event = TestDomainEvent(message)
        if not hasattr(self, "_pending_events"):
            self._pending_events = []
        self._pending_events.append(event)
        return event


class TestUnitOfWork:
    """Tests for the UnitOfWork implementation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.unit_of_work = UnitOfWork()

    def test_unit_of_work_initialization(self):
        """Test that UnitOfWork initializes with empty state."""
        assert not self.unit_of_work.has_changes()
        assert len(self.unit_of_work.get_domain_events()) == 0

    def test_register_aggregate_adds_to_tracking(self):
        """Test that registering an aggregate adds it to tracking."""
        aggregate = TestAggregateRoot("test-id-1")

        self.unit_of_work.register_aggregate(aggregate)

        # Should not have changes until events are raised
        assert not self.unit_of_work.has_changes()

    def test_register_none_aggregate_ignored(self):
        """Test that registering None aggregate is safely ignored."""
        self.unit_of_work.register_aggregate(None)

        assert not self.unit_of_work.has_changes()
        assert len(self.unit_of_work.get_domain_events()) == 0

    def test_has_changes_detects_domain_events(self):
        """Test that has_changes detects aggregates with domain events."""
        aggregate = TestAggregateRoot("test-id-1")
        aggregate.raise_test_event("test event")

        self.unit_of_work.register_aggregate(aggregate)

        assert self.unit_of_work.has_changes()

    def test_get_domain_events_collects_from_all_aggregates(self):
        """Test that domain events are collected from all registered aggregates."""
        aggregate1 = TestAggregateRoot("test-id-1")
        aggregate1.raise_test_event("event from aggregate 1")

        aggregate2 = TestAggregateRoot("test-id-2")
        aggregate2.raise_test_event("event from aggregate 2")
        aggregate2.raise_test_event("second event from aggregate 2")

        self.unit_of_work.register_aggregate(aggregate1)
        self.unit_of_work.register_aggregate(aggregate2)

        events = self.unit_of_work.get_domain_events()

        assert len(events) == 3
        event_messages = [e.message for e in events]
        assert "event from aggregate 1" in event_messages
        assert "event from aggregate 2" in event_messages
        assert "second event from aggregate 2" in event_messages

    def test_get_domain_events_handles_empty_aggregates(self):
        """Test that aggregates without events don't contribute to event collection."""
        aggregate_with_events = TestAggregateRoot("test-id-1")
        aggregate_with_events.raise_test_event("test event")

        aggregate_without_events = TestAggregateRoot("test-id-2")

        self.unit_of_work.register_aggregate(aggregate_with_events)
        self.unit_of_work.register_aggregate(aggregate_without_events)

        events = self.unit_of_work.get_domain_events()

        assert len(events) == 1
        assert events[0].message == "test event"

    def test_clear_removes_all_aggregates_and_events(self):
        """Test that clear removes all tracked aggregates and their events."""
        aggregate = TestAggregateRoot("test-id-1")
        aggregate.raise_test_event("test event")

        self.unit_of_work.register_aggregate(aggregate)

        # Verify we have changes before clearing
        assert self.unit_of_work.has_changes()
        assert len(self.unit_of_work.get_domain_events()) == 1

        # Clear and verify state is reset
        self.unit_of_work.clear()

        assert not self.unit_of_work.has_changes()
        assert len(self.unit_of_work.get_domain_events()) == 0

        # Verify events were cleared from the aggregate too
        assert len(aggregate._pending_events) == 0

    def test_clear_handles_aggregates_without_clear_method(self):
        """Test that clear handles aggregates that don't have clear_pending_events method."""
        # Create a mock aggregate that doesn't have clear_pending_events
        aggregate = Mock()
        aggregate._pending_events = [TestDomainEvent("test")]

        self.unit_of_work.register_aggregate(aggregate)

        # Should not raise an exception
        self.unit_of_work.clear()

        assert not self.unit_of_work.has_changes()

    def test_register_same_aggregate_multiple_times(self):
        """Test that registering the same aggregate multiple times works correctly."""
        aggregate = TestAggregateRoot("test-id-1")
        aggregate.raise_test_event("first event")

        self.unit_of_work.register_aggregate(aggregate)

        # Add another event and register again
        aggregate.raise_test_event("second event")
        self.unit_of_work.register_aggregate(aggregate)

        events = self.unit_of_work.get_domain_events()

        # Should get both events (no duplication of aggregates in set)
        assert len(events) == 2

    def test_domain_events_property_compatibility(self):
        """Test compatibility with aggregates using domain_events property."""
        # Create a mock aggregate with domain_events property
        aggregate = Mock()
        test_events = [TestDomainEvent("test event 1"), TestDomainEvent("test event 2")]
        aggregate.domain_events = test_events

        self.unit_of_work.register_aggregate(aggregate)

        events = self.unit_of_work.get_domain_events()

        assert len(events) == 2
        assert events == test_events

    def test_get_uncommitted_events_compatibility(self):
        """Test compatibility with aggregates using get_uncommitted_events method."""
        # Create a mock aggregate with get_uncommitted_events method
        aggregate = Mock()
        test_events = [TestDomainEvent("uncommitted event")]
        aggregate.get_uncommitted_events.return_value = test_events

        self.unit_of_work.register_aggregate(aggregate)

        events = self.unit_of_work.get_domain_events()

        assert len(events) == 1
        assert events[0].message == "uncommitted event"
        aggregate.get_uncommitted_events.assert_called_once()

    def test_has_changes_with_domain_events_property(self):
        """Test has_changes detection with domain_events property."""
        aggregate = Mock()
        aggregate.domain_events = [TestDomainEvent("test")]

        self.unit_of_work.register_aggregate(aggregate)

        assert self.unit_of_work.has_changes()

    def test_has_changes_with_get_uncommitted_events(self):
        """Test has_changes detection with get_uncommitted_events method."""
        aggregate = Mock()
        aggregate.get_uncommitted_events.return_value = [TestDomainEvent("test")]

        self.unit_of_work.register_aggregate(aggregate)

        assert self.unit_of_work.has_changes()

    def test_interface_compliance(self):
        """Test that UnitOfWork implements IUnitOfWork interface correctly."""
        assert isinstance(self.unit_of_work, IUnitOfWork)

        # Test all interface methods are implemented
        assert hasattr(self.unit_of_work, "register_aggregate")
        assert hasattr(self.unit_of_work, "get_domain_events")
        assert hasattr(self.unit_of_work, "clear")
        assert hasattr(self.unit_of_work, "has_changes")

    def test_multiple_aggregates_with_mixed_event_patterns(self):
        """Test handling multiple aggregates with different event access patterns."""
        # Standard aggregate with _pending_events
        standard_aggregate = TestAggregateRoot("standard")
        standard_aggregate.raise_test_event("standard event")

        # Mock aggregate with domain_events property
        property_aggregate = Mock()
        property_aggregate.domain_events = [TestDomainEvent("property event")]

        # Mock aggregate with get_uncommitted_events method
        method_aggregate = Mock()
        method_aggregate.get_uncommitted_events.return_value = [TestDomainEvent("method event")]

        # Register all aggregates
        self.unit_of_work.register_aggregate(standard_aggregate)
        self.unit_of_work.register_aggregate(property_aggregate)
        self.unit_of_work.register_aggregate(method_aggregate)

        # Verify all events are collected
        events = self.unit_of_work.get_domain_events()
        assert len(events) == 3

        event_messages = [e.message for e in events]
        assert "standard event" in event_messages
        assert "property event" in event_messages
        assert "method event" in event_messages
