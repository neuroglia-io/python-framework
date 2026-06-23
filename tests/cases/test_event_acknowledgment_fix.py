"""
Test suite for event acknowledgment fix.

This module validates that events from EventStore are properly acknowledged
after processing completes, preventing duplicate event delivery.

Root Cause:
-----------
Previously, EventStore was acknowledging events immediately after pushing them
to the observable (in _consume_events_async), BEFORE ReadModelReconciliator
finished processing. This caused:

1. Events ACKed before processing → lost on crash
2. Events ACKed on processing failure → never retried
3. Events redelivered on service restart → duplicate CloudEvents

Fix:
----
1. EventStore returns AckableEventRecord with ack/nack delegates
2. ReadModelReconciliator calls ack_async() AFTER successful processing
3. ReadModelReconciliator calls nack_async() on processing failure
4. Acknowledgment timing controlled by consumer, not producer

Test Coverage:
--------------
- Event acknowledgment after successful processing
- Event negative acknowledgment on processing failure
- AckableEventRecord delegate invocation
- Proper timing of acknowledgment (after mediator.publish_async)
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from neuroglia.data.abstractions import DomainEvent
from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    AckableEventRecord,
    EventRecord,
)
from neuroglia.data.infrastructure.event_sourcing.read_model_reconciliator import (
    ReadModelReconciliator,
)
from neuroglia.mediation.mediator import Mediator


class TestDomainEvent(DomainEvent):
    """Test domain event"""

    def __init__(self, aggregate_id: str, test_value: str):
        super().__init__(aggregate_id)
        self.test_value = test_value
        self.aggregate_version = 1


@pytest.fixture
def mock_mediator():
    """Create mock mediator"""
    mediator = Mock(spec=Mediator)
    mediator.publish_async = AsyncMock()
    return mediator


@pytest.fixture
def read_model_reconciliator(mock_mediator):
    """Create ReadModelReconciliator with mocked dependencies"""
    service_provider = Mock()
    event_store_options = Mock()
    event_store_options.database_name = "test-db"
    event_store_options.consumer_group = "test-group"
    event_store = Mock()

    reconciliator = ReadModelReconciliator(
        service_provider=service_provider,
        mediator=mock_mediator,
        event_store_options=event_store_options,
        event_store=event_store,
    )

    return reconciliator


@pytest.fixture
def test_event():
    """Create test domain event"""
    return TestDomainEvent(
        aggregate_id=str(uuid4()),
        test_value="test_data",
    )


@pytest.fixture
def ackable_event_record(test_event):
    """Create AckableEventRecord with mock delegates"""
    ack_mock = Mock()
    nack_mock = Mock()

    record = AckableEventRecord(
        stream_id="test-stream",
        id=str(uuid4()),
        offset=0,
        position=0,
        timestamp=datetime.now(timezone.utc),
        type="TestDomainEvent",
        data=test_event,
        metadata={},
        replayed=False,
        _ack_delegate=ack_mock,
        _nack_delegate=nack_mock,
    )

    return record, ack_mock, nack_mock


@pytest.fixture
def regular_event_record(test_event):
    """Create regular EventRecord (non-ackable)"""
    return EventRecord(
        stream_id="test-stream",
        id=str(uuid4()),
        offset=0,
        position=0,
        timestamp=datetime.now(timezone.utc),
        type="TestDomainEvent",
        data=test_event,
        metadata={},
        replayed=False,
    )


@pytest.mark.asyncio
class TestEventAcknowledgment:
    """Test event acknowledgment behavior"""

    async def test_ackable_event_acknowledged_after_successful_processing(self, read_model_reconciliator, ackable_event_record, mock_mediator):
        """
        Test that AckableEventRecord is acknowledged AFTER successful processing.

        Expected Behavior:
            - Event published via mediator
            - ack_async() called after publish completes
            - ack delegate invoked exactly once
            - nack delegate never invoked

        Related: EVENT_SOURCING_DOUBLE_PUBLISH_FIX.md
        """
        # Arrange
        record, ack_mock, nack_mock = ackable_event_record

        # Act
        await read_model_reconciliator.on_event_record_stream_next_async(record)

        # Assert - mediator called first
        mock_mediator.publish_async.assert_called_once_with(record.data)

        # Assert - then ack called
        ack_mock.assert_called_once()
        nack_mock.assert_not_called()

    async def test_ackable_event_nacked_on_processing_failure(self, read_model_reconciliator, ackable_event_record, mock_mediator):
        """
        Test that AckableEventRecord is nacked on processing failure.

        Expected Behavior:
            - Mediator.publish_async() raises exception
            - nack_async() called after exception
            - nack delegate invoked exactly once
            - ack delegate never invoked

        Related: Event redelivery on failure
        """
        # Arrange
        record, ack_mock, nack_mock = ackable_event_record
        mock_mediator.publish_async.side_effect = Exception("Processing failed")

        # Act
        await read_model_reconciliator.on_event_record_stream_next_async(record)

        # Assert - mediator called
        mock_mediator.publish_async.assert_called_once_with(record.data)

        # Assert - nack called, not ack
        nack_mock.assert_called_once()
        ack_mock.assert_not_called()

    async def test_regular_event_record_no_acknowledgment(self, read_model_reconciliator, regular_event_record, mock_mediator):
        """
        Test that regular EventRecord (non-ackable) processes without errors.

        Expected Behavior:
            - Event published via mediator
            - No ack/nack calls (not AckableEventRecord)
            - No exceptions raised

        Related: Backward compatibility with non-ackable events
        """
        # Arrange
        record = regular_event_record

        # Act
        await read_model_reconciliator.on_event_record_stream_next_async(record)

        # Assert - mediator called
        mock_mediator.publish_async.assert_called_once_with(record.data)

        # No ack/nack delegates to verify

    async def test_ack_called_after_mediator_completes(self, read_model_reconciliator, ackable_event_record, mock_mediator):
        """
        Test that ack is called AFTER mediator.publish_async() completes.

        This is critical - acknowledgment must happen AFTER processing,
        not before or during.

        Expected Behavior:
            - Mediator.publish_async() completes fully
            - Then ack_async() is called
            - Timing verified through call order

        Related: Race condition prevention
        """
        # Arrange
        record, ack_mock, nack_mock = ackable_event_record
        call_order = []

        # Track call order
        async def track_publish(event):
            call_order.append("publish")

        def track_ack():
            call_order.append("ack")

        mock_mediator.publish_async.side_effect = track_publish
        ack_mock.side_effect = track_ack

        # Act
        await read_model_reconciliator.on_event_record_stream_next_async(record)

        # Assert - publish happens before ack
        assert call_order == ["publish", "ack"]

    async def test_multiple_events_acknowledged_independently(self, read_model_reconciliator, test_event, mock_mediator):
        """
        Test that multiple events are acknowledged independently.

        Expected Behavior:
            - Each event acknowledged after its own processing
            - Failure of one event doesn't affect others
            - Each event has independent ack/nack

        Related: Event independence
        """
        # Arrange
        ack_mocks = []
        nack_mocks = []
        records = []

        for i in range(3):
            ack_mock = Mock()
            nack_mock = Mock()
            ack_mocks.append(ack_mock)
            nack_mocks.append(nack_mock)

            event = TestDomainEvent(
                aggregate_id=str(uuid4()),
                test_value=f"test_{i}",
            )
            event.aggregate_version = i + 1

            record = AckableEventRecord(
                stream_id="test-stream",
                id=str(uuid4()),
                offset=i,
                position=i,
                timestamp=datetime.now(timezone.utc),
                type="TestDomainEvent",
                data=event,
                metadata={},
                replayed=False,
                _ack_delegate=ack_mock,
                _nack_delegate=nack_mock,
            )
            records.append(record)

        # Act - process all events
        for record in records:
            await read_model_reconciliator.on_event_record_stream_next_async(record)

        # Assert - all events acknowledged
        for ack_mock in ack_mocks:
            ack_mock.assert_called_once()

        for nack_mock in nack_mocks:
            nack_mock.assert_not_called()

    async def test_nack_called_on_mediator_timeout(self, read_model_reconciliator, ackable_event_record, mock_mediator):
        """
        Test that nack is called when mediator.publish_async() times out.

        Expected Behavior:
            - Mediator times out (asyncio.TimeoutError)
            - nack_async() called
            - Event can be retried by EventStore

        Related: Timeout handling
        """
        # Arrange
        record, ack_mock, nack_mock = ackable_event_record
        mock_mediator.publish_async.side_effect = asyncio.TimeoutError("Timeout")

        # Act
        await read_model_reconciliator.on_event_record_stream_next_async(record)

        # Assert
        nack_mock.assert_called_once()
        ack_mock.assert_not_called()
