"""
Tests for EventStore tombstone and system event handling.

This test suite validates that the EventStore correctly handles:
1. Tombstone events (streams prefixed with $$) created by hard deletes
2. System events (types prefixed with $) from EventStoreDB internals
3. Events with invalid/empty JSON data
4. Acknowledgment of skipped events to continue processing

Background:
When EventStoreDB hard-deletes a stream using delete_stream(), it:
- Deletes all events from the stream
- Creates a tombstone marker with $$ prefix (e.g., $$my-stream-123)
- The tombstone appears in category projections (e.g., $ce-myapp)

The ReadModelReconciliator subscribes to category streams and must handle
these special events gracefully without crashing the subscription.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from kurrentdbclient import RecordedEvent
from rx.subject import Subject

from neuroglia.data.infrastructure.event_sourcing.abstractions import EventStoreOptions
from neuroglia.data.infrastructure.event_sourcing.event_store.event_store import (
    ESEventStore,
)
from neuroglia.serialization import JsonSerializer


# Helper for async iteration mocking
class AsyncIteratorMock:
    """Mock async iterator for testing async for loops"""

    def __init__(self, items):
        self.items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.items)
        except StopIteration:
            raise StopAsyncIteration


# Test Domain Event
@dataclass
class TaskCreatedEvent:
    """Test domain event for task creation"""

    task_id: str
    title: str
    created_at: datetime


@pytest.fixture
def serializer():
    """JSON serializer for event data"""
    return JsonSerializer()


@pytest.fixture
def eventstore_options():
    """EventStore configuration options"""
    return EventStoreOptions(
        database_name="test_app",
        consumer_group="test_group",
    )


@pytest.fixture
def mock_eventstore_client():
    """Mock EventStoreDB client"""
    return Mock()


@pytest.fixture
def eventstore(serializer, eventstore_options, mock_eventstore_client):
    """ESEventStore instance with mocked client"""
    store = ESEventStore(eventstore_options, mock_eventstore_client, serializer)
    return store


# Test Cases: Tombstone Event Handling


class TestTombstoneEventHandling:
    """Test that tombstone events are skipped gracefully"""

    @pytest.mark.asyncio
    async def test_tombstone_event_skipped_and_acknowledged(self, eventstore, serializer, eventstore_options):
        """
        Test that tombstone events ($$-prefixed streams) are skipped and acknowledged.

        Scenario:
        1. Subscription receives tombstone event from $$my-stream-123
        2. EventStore skips decoding (tombstones have invalid JSON)
        3. Event is acknowledged to continue processing
        4. No event emitted to observable
        """
        # Arrange
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        # Mock subscription with tombstone event
        tombstone_event = Mock(spec=RecordedEvent)
        tombstone_event.stream_name = "$$test_app-task-123"  # Tombstone prefix
        tombstone_event.type = "$metadata"
        tombstone_event.id = uuid4()
        tombstone_event.ack_id = tombstone_event.id
        tombstone_event.stream_position = 0
        tombstone_event.data = b""  # Empty data (typical for tombstones)
        tombstone_event.metadata = b"{}"

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([tombstone_event]))
        mock_subscription.ack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert - tombstone skipped
        assert len(events_received) == 0, "Tombstone event should not be emitted"

        # Assert - tombstone acknowledged
        mock_subscription.ack.assert_called_once_with(tombstone_event.id)

    @pytest.mark.asyncio
    async def test_multiple_tombstones_skipped(self, eventstore):
        """Test that multiple tombstone events are all skipped"""
        # Arrange
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        # Mock subscription with multiple tombstones
        tombstone1 = Mock(spec=RecordedEvent)
        tombstone1.stream_name = "$$test_app-task-123"
        tombstone1.type = "$metadata"
        tombstone1.id = uuid4()
        tombstone1.data = b""
        tombstone1.metadata = b"{}"

        tombstone2 = Mock(spec=RecordedEvent)
        tombstone2.stream_name = "$$test_app-order-456"
        tombstone2.type = "$metadata"
        tombstone2.id = uuid4()
        tombstone2.data = b""
        tombstone2.metadata = b"{}"

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([tombstone1, tombstone2]))
        mock_subscription.ack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert
        assert len(events_received) == 0
        assert mock_subscription.ack.call_count == 2


# Test Cases: System Event Handling


class TestSystemEventHandling:
    """Test that system events ($-prefixed types) are skipped"""

    @pytest.mark.asyncio
    async def test_system_event_skipped_and_acknowledged(self, eventstore):
        """
        Test that system events ($-prefixed types) are skipped and acknowledged.

        System events are EventStoreDB internal events like:
        - $metadata: Stream metadata events
        - $stream-deleted: Stream deletion markers
        - $>: System stream events
        """
        # Arrange
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        # Mock subscription with system event
        system_event = Mock(spec=RecordedEvent)
        system_event.stream_name = "test_app-task-123"  # Regular stream
        system_event.type = "$metadata"  # System event type
        system_event.id = uuid4()
        system_event.ack_id = system_event.id
        system_event.stream_position = 0
        system_event.data = b'{"key": "value"}'
        system_event.metadata = b"{}"

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([system_event]))
        mock_subscription.ack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert
        assert len(events_received) == 0
        mock_subscription.ack.assert_called_once_with(system_event.id)

    @pytest.mark.asyncio
    async def test_multiple_system_event_types_skipped(self, eventstore):
        """Test various system event types are all skipped"""
        # Arrange
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        # Mock subscription with different system event types
        system_events = []
        for event_type in ["$metadata", "$stream-deleted", "$>", "$settings"]:
            event = Mock(spec=RecordedEvent)
            event.stream_name = "test_app-task-123"
            event.type = event_type
            event.id = uuid4()
            event.data = b"{}"
            event.metadata = b"{}"
            system_events.append(event)

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock(system_events))
        mock_subscription.ack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert
        assert len(events_received) == 0
        assert mock_subscription.ack.call_count == 4


# Test Cases: Invalid Event Data Handling


class TestInvalidEventDataHandling:
    """Test that events with invalid data are handled gracefully"""

    @pytest.mark.asyncio
    async def test_invalid_json_event_skipped_and_acknowledged(self, eventstore):
        """
        Test that events with invalid JSON are skipped and acknowledged.

        This prevents the subscription from crashing on corrupt event data.
        """
        # Arrange
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        # Mock subscription with invalid JSON event
        invalid_event = Mock(spec=RecordedEvent)
        invalid_event.stream_name = "test_app-task-123"
        invalid_event.type = "TaskCreatedEvent"
        invalid_event.id = uuid4()
        invalid_event.ack_id = invalid_event.id
        invalid_event.stream_position = 0
        invalid_event.data = b"INVALID JSON DATA"  # Not valid JSON
        invalid_event.metadata = b'{"clr-type": "tests.cases.test_event_store_tombstone_handling.TaskCreatedEvent"}'

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([invalid_event]))
        mock_subscription.ack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert - invalid event skipped
        assert len(events_received) == 0

        # Assert - invalid event acknowledged (not parked)
        mock_subscription.ack.assert_called_once_with(invalid_event.id)

    @pytest.mark.asyncio
    async def test_empty_event_data_handled(self, eventstore):
        """Test that events with empty data are handled gracefully"""
        # Arrange
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        empty_event = Mock(spec=RecordedEvent)
        empty_event.stream_name = "test_app-task-123"
        empty_event.type = "EmptyEvent"
        empty_event.id = uuid4()
        empty_event.ack_id = empty_event.id
        empty_event.stream_position = 0
        empty_event.data = b""  # Empty data
        empty_event.metadata = b'{"clr-type": "tests.cases.test_event_store_tombstone_handling.TaskCreatedEvent"}'

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([empty_event]))
        mock_subscription.ack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert
        assert len(events_received) == 0
        mock_subscription.ack.assert_called_once_with(empty_event.id)


# Test Cases: Mixed Event Stream Handling


class TestMixedEventStreamHandling:
    """Test that processing continues despite encountering tombstones/system events"""

    @pytest.mark.asyncio
    async def test_tombstone_does_not_stop_subscription(self, eventstore):
        """
        Test that encountering a tombstone does not stop the subscription.

        Scenario:
        1. Subscription receives multiple events including tombstones
        2. Tombstones are skipped and acknowledged
        3. Subscription processes all events without stopping
        4. No exceptions raised
        """
        # Arrange
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        # Create mix of tombstones and system events
        tombstone1 = Mock(spec=RecordedEvent)
        tombstone1.stream_name = "$$test_app-task-1"
        tombstone1.type = "$metadata"
        tombstone1.id = uuid4()
        tombstone1.data = b""
        tombstone1.metadata = b"{}"

        system_event = Mock(spec=RecordedEvent)
        system_event.stream_name = "test_app-task-2"
        system_event.type = "$metadata"
        system_event.id = uuid4()
        system_event.ack_id = system_event.id
        system_event.data = b"{}"
        system_event.metadata = b"{}"

        tombstone2 = Mock(spec=RecordedEvent)
        tombstone2.stream_name = "$$test_app-task-3"
        tombstone2.type = "$metadata"
        tombstone2.id = uuid4()
        tombstone2.data = b""
        tombstone2.metadata = b"{}"

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([tombstone1, system_event, tombstone2]))
        mock_subscription.ack = AsyncMock()

        # Act - should not raise exception
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert - all special events acknowledged
        assert mock_subscription.ack.call_count == 3

        # Assert - no events emitted (all were skipped)
        assert len(events_received) == 0

    @pytest.mark.asyncio
    async def test_invalid_json_does_not_stop_subscription(self, eventstore):
        """Test that invalid JSON does not stop subscription processing"""
        # Arrange
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        # Create multiple events with invalid JSON
        invalid1 = Mock(spec=RecordedEvent)
        invalid1.stream_name = "test_app-task-1"
        invalid1.type = "TaskEvent"
        invalid1.id = uuid4()
        invalid1.stream_position = 0
        invalid1.data = b"NOT JSON"
        invalid1.metadata = b'{"type": "test.TaskEvent"}'

        invalid2 = Mock(spec=RecordedEvent)
        invalid2.stream_name = "test_app-task-2"
        invalid2.type = "OrderEvent"
        invalid2.id = uuid4()
        invalid2.stream_position = 1
        invalid2.data = b""
        invalid2.metadata = b'{"type": "test.OrderEvent"}'

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([invalid1, invalid2]))
        mock_subscription.ack = AsyncMock()

        # Act - should not raise exception
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert - both events acknowledged despite decode failures
        assert mock_subscription.ack.call_count == 2

        # Assert - no events emitted (all failed to decode)
        assert len(events_received) == 0


# Test Cases: Logging Behavior


class TestLoggingBehavior:
    """Test that appropriate log messages are generated"""

    @pytest.mark.asyncio
    async def test_tombstone_logged_at_debug_level(self, eventstore, caplog):
        """Test that tombstone skips are logged at DEBUG level"""
        # Arrange
        caplog.set_level(logging.DEBUG)
        subject = Subject()

        tombstone = Mock(spec=RecordedEvent)
        tombstone.stream_name = "$$test_app-task-123"
        tombstone.type = "$metadata"
        tombstone.id = uuid4()
        tombstone.ack_id = tombstone.id
        tombstone.data = b""
        tombstone.metadata = b"{}"

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([tombstone]))
        mock_subscription.ack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert
        assert any("Skipping tombstone event" in record.message for record in caplog.records)
        assert any(record.levelname == "DEBUG" for record in caplog.records)

    @pytest.mark.asyncio
    async def test_system_event_logged_at_debug_level(self, eventstore, caplog):
        """Test that system event skips are logged at DEBUG level"""
        # Arrange
        caplog.set_level(logging.DEBUG)
        subject = Subject()

        system_event = Mock(spec=RecordedEvent)
        system_event.stream_name = "test_app-task-123"
        system_event.type = "$metadata"
        system_event.id = uuid4()
        system_event.ack_id = system_event.id
        system_event.data = b"{}"
        system_event.metadata = b"{}"

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([system_event]))
        mock_subscription.ack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert
        assert any("Skipping system event type" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_invalid_json_logged_at_warning_level(self, eventstore, caplog):
        """Test that decode failures are logged at WARNING level"""
        # Arrange
        caplog.set_level(logging.WARNING)
        subject = Subject()

        invalid_event = Mock(spec=RecordedEvent)
        invalid_event.stream_name = "test_app-task-123"
        invalid_event.type = "TaskCreatedEvent"
        invalid_event.id = uuid4()
        invalid_event.ack_id = invalid_event.id
        invalid_event.stream_position = 0
        invalid_event.data = b"INVALID"
        invalid_event.metadata = b'{"clr-type": "tests.cases.test_event_store_tombstone_handling.TaskCreatedEvent"}'

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([invalid_event]))
        mock_subscription.ack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert
        assert any("Could not decode event" in record.message for record in caplog.records)
        assert any(record.levelname == "WARNING" for record in caplog.records)
