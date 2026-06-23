"""
Tests for EventStore persistent subscription ACK delivery.

This test suite validates that acknowledgments are properly delivered to
EventStoreDB for persistent subscriptions, preventing the 30-second redelivery loop.

Background:
The esdbclient library uses gRPC bidirectional streaming for persistent subscriptions.
ACKs are queued when subscription.ack() is called, but must be actively sent by the
gRPC request stream. Without proper handling, ACKs accumulate without being sent,
causing EventStoreDB to redeliver events after messageTimeout (default 30s).

Key Issues Addressed:
1. ACKs queued but never sent to EventStoreDB
2. Events redelivered every 30 seconds
3. Events eventually parked after maxRetryCount
4. Checkpoint never advances in subscription info
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from kurrentdbclient import RecordedEvent
from rx.subject import Subject

from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    AckableEventRecord,
    EventStoreOptions,
)
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
class OrderPlacedEvent:
    """Test domain event for order placement"""

    order_id: str
    customer_id: str
    total: float
    placed_at: datetime


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


# Test Cases: Persistent Subscription ACK Delivery


class TestPersistentSubscriptionAckDelivery:
    """Test that ACKs are properly queued and delivered to EventStoreDB"""

    @pytest.mark.asyncio
    async def test_ack_delegate_calls_subscription_ack(self, eventstore, serializer):
        """
        Test that the ACK delegate properly calls subscription.ack().

        This is the first step in ACK delivery - ensuring that when the
        handler calls ack_async(), it translates to subscription.ack(event_id).
        """
        # Arrange
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        # Create persistent subscription mock
        event = Mock(spec=RecordedEvent)
        event.stream_name = "test_app-order-123"
        event.type = "OrderPlacedEvent"
        event.id = uuid4()
        event.ack_id = event.id
        event.stream_position = 0
        event.commit_position = 100
        event.recorded_at = datetime.now(timezone.utc)
        event.data = serializer.serialize_to_text(
            OrderPlacedEvent(
                order_id="order-123",
                customer_id="customer-456",
                total=99.99,
                placed_at=datetime.now(timezone.utc),
            )
        ).encode()
        event.metadata = b'{"type": "tests.cases.test_persistent_subscription_ack_delivery.OrderPlacedEvent"}'

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([event]))
        mock_subscription.ack = AsyncMock()
        mock_subscription.nack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert - event received
        assert len(events_received) == 1
        assert isinstance(events_received[0], AckableEventRecord)

        # Act - call ACK delegate
        ackable_event = events_received[0]
        await ackable_event.ack_async()

        # Assert - subscription.ack() was called
        mock_subscription.ack.assert_called_once_with(event.id)

    @pytest.mark.asyncio
    async def test_nack_delegate_calls_subscription_nack(self, eventstore, serializer):
        """Test that the NACK delegate properly calls subscription.nack()"""
        # Arrange
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        event = Mock(spec=RecordedEvent)
        event.stream_name = "test_app-order-123"
        event.type = "OrderPlacedEvent"
        event.id = uuid4()
        event.ack_id = event.id
        event.stream_position = 0
        event.commit_position = 100
        event.recorded_at = datetime.now(timezone.utc)
        event.data = serializer.serialize_to_text(
            OrderPlacedEvent(
                order_id="order-123",
                customer_id="customer-456",
                total=99.99,
                placed_at=datetime.now(timezone.utc),
            )
        ).encode()
        event.metadata = b'{"type": "tests.cases.test_persistent_subscription_ack_delivery.OrderPlacedEvent"}'

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([event]))
        mock_subscription.ack = AsyncMock()
        mock_subscription.nack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert - event received
        assert len(events_received) == 1
        ackable_event = events_received[0]

        # Act - call NACK delegate with park action
        await ackable_event.nack_async()

        # Assert - subscription.nack() was called
        mock_subscription.nack.assert_called_once()

    @pytest.mark.asyncio
    async def test_tombstone_events_acknowledged_immediately(self, eventstore):
        """
        Test that tombstone events are ACKed immediately without handler involvement.

        Tombstones should be ACKed automatically to prevent blocking subscription.
        """
        # Arrange
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        tombstone = Mock(spec=RecordedEvent)
        tombstone.stream_name = "$$test_app-order-deleted"
        tombstone.type = "$metadata"
        tombstone.id = uuid4()
        tombstone.ack_id = tombstone.id
        tombstone.data = b""
        tombstone.metadata = b"{}"

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([tombstone]))
        mock_subscription.ack = AsyncMock()
        mock_subscription.nack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert - tombstone skipped (not emitted)
        assert len(events_received) == 0

        # Assert - tombstone ACKed immediately
        mock_subscription.ack.assert_called_once_with(tombstone.id)

    @pytest.mark.asyncio
    async def test_multiple_events_all_ackable(self, eventstore, serializer):
        """Test that multiple events from persistent subscription are all ackable"""
        # Arrange
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        # Create multiple events
        events = []
        for i in range(5):
            event = Mock(spec=RecordedEvent)
            event.stream_name = f"test_app-order-{i}"
            event.type = "OrderPlacedEvent"
            event.id = uuid4()
            event.stream_position = i
            event.commit_position = 100 + i
            event.recorded_at = datetime.now(timezone.utc)
            event.data = serializer.serialize_to_text(
                OrderPlacedEvent(
                    order_id=f"order-{i}",
                    customer_id="customer-456",
                    total=99.99 + i,
                    placed_at=datetime.now(timezone.utc),
                )
            ).encode()
            event.metadata = b'{"type": "tests.cases.test_persistent_subscription_ack_delivery.OrderPlacedEvent"}'
            events.append(event)

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock(events))
        mock_subscription.ack = AsyncMock()
        mock_subscription.nack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)

        # Assert - all events received
        assert len(events_received) == 5

        # Assert - all events are ackable
        for ackable_event in events_received:
            assert isinstance(ackable_event, AckableEventRecord)
            assert hasattr(ackable_event, "ack_async")
            assert hasattr(ackable_event, "nack_async")


# Test Cases: ACK Configuration


class TestAckConfiguration:
    """Test that subscription is created with optimal ACK settings"""

    @pytest.mark.asyncio
    async def test_subscription_created_with_checkpoint_counts(self, eventstore_options, mock_eventstore_client, serializer):
        """
        Test that persistent subscription is created with min/max checkpoint count of 1.

        This ensures ACKs are sent immediately rather than being batched,
        which is critical for preventing the redelivery loop.
        """
        # Arrange
        store = ESEventStore(eventstore_options, mock_eventstore_client, serializer)
        mock_eventstore_client.create_subscription_to_stream = AsyncMock()
        mock_eventstore_client.read_subscription_to_stream = AsyncMock(return_value=AsyncIteratorMock([]))

        # Act
        await store.observe_async(stream_id="order-stream", consumer_group="test_group", offset=0)

        # Give async task time to start
        await asyncio.sleep(0.1)

        # Assert - create_subscription_to_stream called with correct parameters
        mock_eventstore_client.create_subscription_to_stream.assert_called_once()
        call_kwargs = mock_eventstore_client.create_subscription_to_stream.call_args[1]

        assert call_kwargs["min_checkpoint_count"] == 1
        assert call_kwargs["max_checkpoint_count"] == 1
        assert call_kwargs["message_timeout"] == 60.0

    @pytest.mark.asyncio
    async def test_catchup_subscription_no_ack(self, eventstore, serializer):
        """
        Test that catchup subscriptions (no consumer group) emit regular EventRecords.

        Catchup subscriptions don't support ACK/NACK, so events should be
        regular EventRecord objects, not AckableEventRecord.
        """
        # Arrange
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        event = Mock(spec=RecordedEvent)
        event.stream_name = "test_app-order-123"
        event.type = "OrderPlacedEvent"
        event.id = uuid4()
        event.ack_id = event.id
        event.stream_position = 0
        event.commit_position = 100
        event.recorded_at = datetime.now(timezone.utc)
        event.data = serializer.serialize_to_text(
            OrderPlacedEvent(
                order_id="order-123",
                customer_id="customer-456",
                total=99.99,
                placed_at=datetime.now(timezone.utc),
            )
        ).encode()
        event.metadata = b'{"type": "tests.cases.test_persistent_subscription_ack_delivery.OrderPlacedEvent"}'

        # Mock catchup subscription (no ack/nack methods)
        mock_subscription = Mock(spec=["__aiter__", "stop"])
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([event]))

        # Act
        await eventstore._consume_events_async("test_app-order", subject, mock_subscription)

        # Assert - event received but NOT ackable
        assert len(events_received) == 1
        assert not isinstance(events_received[0], AckableEventRecord)
        assert not hasattr(events_received[0], "ack_async")


# Test Cases: Logging and Monitoring


class TestAckLoggingAndMonitoring:
    """Test that ACK delivery is properly logged for debugging"""

    @pytest.mark.asyncio
    async def test_ack_queuing_logged_at_debug_level(self, eventstore, serializer, caplog):
        """Test that ACK queuing is logged at DEBUG level"""
        # Arrange
        caplog.set_level(logging.DEBUG)
        subject = Subject()
        events_received = []
        subject.subscribe(lambda e: events_received.append(e))

        event = Mock(spec=RecordedEvent)
        event.stream_name = "test_app-order-123"
        event.type = "OrderPlacedEvent"
        event.id = uuid4()
        event.ack_id = event.id
        event.stream_position = 0
        event.commit_position = 100
        event.recorded_at = datetime.now(timezone.utc)
        event.data = serializer.serialize_to_text(
            OrderPlacedEvent(
                order_id="order-123",
                customer_id="customer-456",
                total=99.99,
                placed_at=datetime.now(timezone.utc),
            )
        ).encode()
        event.metadata = b'{"type": "tests.cases.test_persistent_subscription_ack_delivery.OrderPlacedEvent"}'

        mock_subscription = AsyncMock()
        mock_subscription.__aiter__ = Mock(return_value=AsyncIteratorMock([event]))
        mock_subscription.ack = AsyncMock()
        mock_subscription.nack = AsyncMock()

        # Act
        await eventstore._consume_events_async("$ce-test_app", subject, mock_subscription)
        ackable_event = events_received[0]
        await ackable_event.ack_async()

        # Assert
        assert any("ACK sent for event" in record.message for record in caplog.records)
        assert any(record.levelname == "DEBUG" for record in caplog.records)
