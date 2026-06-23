"""
Tests for ReadModelReconciliator sequential event processing.

This test module verifies that the ReadModelReconciliator correctly processes
events from the same aggregate sequentially to prevent race conditions in
read model projections.

The bug scenario being tested:
1. Aggregate emits ToolGroupCreatedDomainEvent followed by SelectorAddedDomainEvent
2. Both events are persisted atomically to EventStoreDB
3. ReadModelReconciliator picks up both events
4. Without sequential processing: handlers run concurrently, causing race condition
5. With sequential processing: handlers run in order, SelectorAddedHandler waits for
   ToolGroupCreatedHandler to complete

Related: neuroglia.data.infrastructure.event_sourcing.read_model_reconciliator
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from neuroglia.data.abstractions import DomainEvent
from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    EventStore,
    EventStoreOptions,
)
from neuroglia.data.infrastructure.event_sourcing.read_model_reconciliator import (
    AggregateEventQueue,
    ReadModelConciliationOptions,
    ReadModelReconciliator,
)
from neuroglia.mediation import Mediator

# ============================================================================
# Test Domain Events
# ============================================================================


@dataclass
class ToolGroupCreatedDomainEvent(DomainEvent):
    """Event raised when a new ToolGroup is created."""

    aggregate_id: str
    name: str
    description: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SelectorAddedDomainEvent(DomainEvent):
    """Event raised when a selector is added to a ToolGroup."""

    aggregate_id: str
    selector_id: str
    name_pattern: str
    added_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AnotherAggregateCreatedEvent(DomainEvent):
    """Event from a different aggregate type."""

    aggregate_id: str
    data: str


# ============================================================================
# Test Event Record
# ============================================================================


class MockEventRecord:
    """Mock event record for testing."""

    def __init__(self, data: DomainEvent, stream_id: str | None = None):
        self.data = data
        self.stream_id = stream_id or f"toolgroup-{getattr(data, 'aggregate_id', 'unknown')}"


class MockAckableEventRecord(MockEventRecord):
    """Mock ackable event record for testing acknowledgment."""

    def __init__(self, data: DomainEvent, stream_id: str | None = None):
        super().__init__(data, stream_id)
        self.acked = False
        self.nacked = False

    async def ack_async(self):
        self.acked = True

    async def nack_async(self):
        self.nacked = True


# Make it pass isinstance check
MockAckableEventRecord.__bases__ = (MockEventRecord,)


# ============================================================================
# AggregateEventQueue Tests
# ============================================================================


@pytest.mark.unit
class TestAggregateEventQueue:
    """
    Tests for the AggregateEventQueue that ensures sequential event processing.

    Expected Behavior:
        - Events from the same aggregate are processed sequentially
        - Events from different aggregates can be processed concurrently
        - Queue processors are started lazily and cleaned up after timeout
        - Processing errors don't break the queue
    """

    @pytest.mark.asyncio
    async def test_events_from_same_aggregate_processed_sequentially(self):
        """
        Test that events from the same aggregate are processed in order.

        Expected Behavior:
            - Event1 starts processing
            - Event2 waits until Event1 completes
            - Processing order matches enqueue order
        """
        # Arrange
        queue = AggregateEventQueue()
        processing_order: list[str] = []
        processing_lock = asyncio.Lock()

        async def slow_process(event_record):
            """Simulate slow processing to verify ordering."""
            event_name = type(event_record.data).__name__
            async with processing_lock:
                processing_order.append(f"start:{event_name}")

            # Simulate processing time - enough to cause race condition if not sequential
            await asyncio.sleep(0.1)

            async with processing_lock:
                processing_order.append(f"end:{event_name}")

        aggregate_id = "agg-123"
        event1 = MockEventRecord(ToolGroupCreatedDomainEvent(aggregate_id=aggregate_id, name="Test", description="Test desc"))
        event2 = MockEventRecord(SelectorAddedDomainEvent(aggregate_id=aggregate_id, selector_id="sel-1", name_pattern="*"))

        # Act
        await queue.enqueue(aggregate_id, event1, slow_process)
        await queue.enqueue(aggregate_id, event2, slow_process)

        # Wait for processing to complete
        await asyncio.sleep(0.3)

        # Assert - events should be processed sequentially
        assert processing_order == [
            "start:ToolGroupCreatedDomainEvent",
            "end:ToolGroupCreatedDomainEvent",
            "start:SelectorAddedDomainEvent",
            "end:SelectorAddedDomainEvent",
        ]

        # Cleanup
        await queue.shutdown()

    @pytest.mark.asyncio
    async def test_events_from_different_aggregates_processed_concurrently(self):
        """
        Test that events from different aggregates can be processed in parallel.

        Expected Behavior:
            - Events from aggregate A and B start at roughly the same time
            - Total processing time is ~100ms, not ~200ms
        """
        # Arrange
        queue = AggregateEventQueue()
        processing_starts: dict[str, float] = {}
        start_time = asyncio.get_event_loop().time()

        async def timed_process(event_record):
            """Track when processing starts."""
            agg_id = event_record.data.aggregate_id
            processing_starts[agg_id] = asyncio.get_event_loop().time() - start_time
            await asyncio.sleep(0.1)

        event1 = MockEventRecord(ToolGroupCreatedDomainEvent(aggregate_id="agg-1", name="Test1", description=""))
        event2 = MockEventRecord(ToolGroupCreatedDomainEvent(aggregate_id="agg-2", name="Test2", description=""))

        # Act
        await queue.enqueue("agg-1", event1, timed_process)
        await queue.enqueue("agg-2", event2, timed_process)

        # Wait for processing
        await asyncio.sleep(0.15)

        # Assert - both should start within 50ms of each other (concurrent)
        start_diff = abs(processing_starts.get("agg-1", 0) - processing_starts.get("agg-2", 0))
        assert start_diff < 0.05, f"Events should start concurrently, but diff was {start_diff}s"

        # Cleanup
        await queue.shutdown()

    @pytest.mark.asyncio
    async def test_processing_error_does_not_break_queue(self):
        """
        Test that errors in processing don't break subsequent events.

        Expected Behavior:
            - First event processing fails with exception
            - Second event is still processed successfully
        """
        # Arrange
        queue = AggregateEventQueue()
        processed_events: list[str] = []

        async def failing_then_succeeding_process(event_record):
            event_name = type(event_record.data).__name__
            if "Created" in event_name:
                raise ValueError("Simulated processing error")
            processed_events.append(event_name)

        aggregate_id = "agg-123"
        event1 = MockEventRecord(ToolGroupCreatedDomainEvent(aggregate_id=aggregate_id, name="Test", description=""))
        event2 = MockEventRecord(SelectorAddedDomainEvent(aggregate_id=aggregate_id, selector_id="sel-1", name_pattern="*"))

        # Act
        await queue.enqueue(aggregate_id, event1, failing_then_succeeding_process)
        await queue.enqueue(aggregate_id, event2, failing_then_succeeding_process)

        # Wait for processing
        await asyncio.sleep(0.1)

        # Assert - second event should still be processed
        assert "SelectorAddedDomainEvent" in processed_events

        # Cleanup
        await queue.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_cancels_processors(self):
        """
        Test that shutdown properly cancels all processing tasks.

        Expected Behavior:
            - Shutdown completes without errors
            - All processor tasks are cancelled
        """
        # Arrange
        queue = AggregateEventQueue()

        async def slow_process(event_record):
            await asyncio.sleep(10)  # Very slow

        event = MockEventRecord(ToolGroupCreatedDomainEvent(aggregate_id="agg-1", name="Test", description=""))

        await queue.enqueue("agg-1", event, slow_process)

        # Act - should not hang
        await asyncio.wait_for(queue.shutdown(), timeout=1.0)

        # Assert - no exception means success


# ============================================================================
# ReadModelReconciliator Tests
# ============================================================================


@pytest.mark.unit
class TestReadModelReconciliatorSequentialProcessing:
    """
    Tests for ReadModelReconciliator's sequential event processing mode.

    Expected Behavior:
        - With sequential_processing=True (default), events from the same
          aggregate are processed in order
        - With sequential_processing=False, events may be processed concurrently
        - Aggregate ID is correctly extracted from various event formats
    """

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_mediator = MagicMock(spec=Mediator)
        self.mock_mediator.publish_async = AsyncMock()

        self.mock_event_store = MagicMock(spec=EventStore)
        self.mock_event_store.observe_async = AsyncMock(return_value=MagicMock())

        self.mock_event_store_options = EventStoreOptions(database_name="test-db", consumer_group="test-group")

        self.mock_service_provider = MagicMock()

    @pytest.mark.asyncio
    async def test_default_options_enable_sequential_processing(self):
        """
        Test that sequential processing is enabled by default.

        Expected Behavior:
            - Default ReadModelConciliationOptions has sequential_processing=True
            - ReadModelReconciliator creates event queue when sequential_processing=True
        """
        # Arrange
        options = ReadModelConciliationOptions(consumer_group="test")

        # Assert
        assert options.sequential_processing is True

        # Arrange
        reconciliator = ReadModelReconciliator(self.mock_service_provider, self.mock_mediator, self.mock_event_store_options, self.mock_event_store, options)

        # Assert - event queue should be created
        assert reconciliator._event_queue is not None

    @pytest.mark.asyncio
    async def test_parallel_processing_option_disables_queue(self):
        """
        Test that parallel processing mode disables the event queue.

        Expected Behavior:
            - When sequential_processing=False, no event queue is created
        """
        # Arrange
        options = ReadModelConciliationOptions(consumer_group="test", sequential_processing=False)

        reconciliator = ReadModelReconciliator(self.mock_service_provider, self.mock_mediator, self.mock_event_store_options, self.mock_event_store, options)

        # Assert - no event queue
        assert reconciliator._event_queue is None

    @pytest.mark.asyncio
    async def test_extract_aggregate_id_from_event_data(self):
        """
        Test aggregate ID extraction from event data's aggregate_id attribute.

        Expected Behavior:
            - If event.data.aggregate_id exists, use it
        """
        # Arrange
        options = ReadModelConciliationOptions(consumer_group="test")
        reconciliator = ReadModelReconciliator(self.mock_service_provider, self.mock_mediator, self.mock_event_store_options, self.mock_event_store, options)

        event = MockEventRecord(ToolGroupCreatedDomainEvent(aggregate_id="my-agg-id", name="Test", description=""), stream_id="toolgroup-different-id")

        # Act
        aggregate_id = reconciliator._extract_aggregate_id(event)

        # Assert
        assert aggregate_id == "my-agg-id"

    @pytest.mark.asyncio
    async def test_extract_aggregate_id_from_stream_id(self):
        """
        Test aggregate ID extraction from stream_id when event data lacks aggregate_id.

        Expected Behavior:
            - Falls back to parsing stream_id (format: type-id)
        """
        # Arrange
        options = ReadModelConciliationOptions(consumer_group="test")
        reconciliator = ReadModelReconciliator(self.mock_service_provider, self.mock_mediator, self.mock_event_store_options, self.mock_event_store, options)

        # Create event without aggregate_id in data
        @dataclass
        class SimpleEvent:
            value: str

        event = MagicMock()
        event.data = SimpleEvent(value="test")
        event.stream_id = "myaggregate-uuid-1234-5678"

        # Act
        aggregate_id = reconciliator._extract_aggregate_id(event)

        # Assert
        assert aggregate_id == "uuid-1234-5678"

    @pytest.mark.asyncio
    async def test_sequential_processing_with_mediator_publish(self):
        """
        Test that events are published to mediator in order when using sequential processing.

        Expected Behavior:
            - Events are awaited sequentially via the event queue
            - Mediator.publish_async is called in order for same aggregate
        """
        # Arrange
        publish_order: list[str] = []
        publish_times: list[float] = []
        start_time = asyncio.get_event_loop().time()

        async def mock_publish(event):
            event_name = type(event).__name__
            publish_order.append(f"start:{event_name}")
            publish_times.append(asyncio.get_event_loop().time() - start_time)

            # Simulate slow handler
            await asyncio.sleep(0.05)

            publish_order.append(f"end:{event_name}")

        self.mock_mediator.publish_async = mock_publish

        options = ReadModelConciliationOptions(consumer_group="test")
        reconciliator = ReadModelReconciliator(self.mock_service_provider, self.mock_mediator, self.mock_event_store_options, self.mock_event_store, options)

        # Initialize the event loop reference
        reconciliator._loop = asyncio.get_event_loop()

        aggregate_id = "test-agg-123"
        event1 = MockEventRecord(ToolGroupCreatedDomainEvent(aggregate_id=aggregate_id, name="Test", description=""))
        event2 = MockEventRecord(SelectorAddedDomainEvent(aggregate_id=aggregate_id, selector_id="sel-1", name_pattern="*"))

        # Act - handle events through the sequential processing path
        await reconciliator._handle_event_async(event1)
        await reconciliator._handle_event_async(event2)

        # Wait for queue processing
        await asyncio.sleep(0.2)

        # Assert - sequential order
        assert publish_order == [
            "start:ToolGroupCreatedDomainEvent",
            "end:ToolGroupCreatedDomainEvent",
            "start:SelectorAddedDomainEvent",
            "end:SelectorAddedDomainEvent",
        ]

        # Cleanup
        await reconciliator.stop_async()

    @pytest.mark.asyncio
    async def test_ackable_event_acknowledged_on_success(self):
        """
        Test that ackable events are acknowledged after successful processing.

        Expected Behavior:
            - After successful mediator.publish_async, ack_async is called
        """
        # Arrange
        self.mock_mediator.publish_async = AsyncMock()

        options = ReadModelConciliationOptions(consumer_group="test")
        reconciliator = ReadModelReconciliator(self.mock_service_provider, self.mock_mediator, self.mock_event_store_options, self.mock_event_store, options)

        event = MockAckableEventRecord(ToolGroupCreatedDomainEvent(aggregate_id="agg-1", name="Test", description=""))

        # Act - duck typing will call ack_async if it exists
        await reconciliator.on_event_record_stream_next_async(event)  # type: ignore[arg-type]

        # Assert
        assert event.acked is True
        assert event.nacked is False

    @pytest.mark.asyncio
    async def test_ackable_event_nacked_on_failure(self):
        """
        Test that ackable events are negative-acknowledged on processing failure.

        Expected Behavior:
            - When mediator.publish_async raises, nack_async is called
        """
        # Arrange
        self.mock_mediator.publish_async = AsyncMock(side_effect=ValueError("Test error"))

        options = ReadModelConciliationOptions(consumer_group="test")
        reconciliator = ReadModelReconciliator(self.mock_service_provider, self.mock_mediator, self.mock_event_store_options, self.mock_event_store, options)

        event = MockAckableEventRecord(ToolGroupCreatedDomainEvent(aggregate_id="agg-1", name="Test", description=""))

        # Act - pass the event (isinstance check will be based on duck typing)
        await reconciliator.on_event_record_stream_next_async(event)  # type: ignore[arg-type]

        # Assert
        assert event.acked is False
        assert event.nacked is True


# ============================================================================
# Integration-Style Tests (Verifying the Full Race Condition Scenario)
# ============================================================================


@pytest.mark.unit
class TestRaceConditionPrevention:
    """
    Tests that verify the race condition from the bug report is prevented.

    The specific scenario:
    1. ToolGroup aggregate created (emits ToolGroupCreatedDomainEvent)
    2. Selector added (emits SelectorAddedDomainEvent)
    3. Both events persisted atomically
    4. ReadModelReconciliator processes events
    5. ToolGroupCreatedProjectionHandler must complete before SelectorAddedProjectionHandler starts
    """

    @pytest.mark.asyncio
    async def test_projection_handlers_execute_in_order(self):
        """
        Test the exact scenario from the bug report.

        Expected Behavior:
            - ToolGroupCreatedProjectionHandler completes (creates document)
            - THEN SelectorAddedProjectionHandler runs (updates document)
            - No "document not found" errors
        """
        # Arrange - simulate MongoDB-like read model
        read_model: dict[str, dict] = {}
        handler_log: list[str] = []

        async def mock_created_handler(event: ToolGroupCreatedDomainEvent):
            """Simulates creating document in MongoDB."""
            handler_log.append(f"Creating ToolGroup: {event.aggregate_id}")
            await asyncio.sleep(0.05)  # Simulate DB latency
            read_model[event.aggregate_id] = {"id": event.aggregate_id, "name": event.name, "selectors": []}
            handler_log.append("✅ Projected ToolGroupCreated to Read Model")

        async def mock_selector_handler(event: SelectorAddedDomainEvent):
            """Simulates updating document in MongoDB."""
            handler_log.append(f"Adding selector to ToolGroup: {event.aggregate_id}")

            # This is where the race condition would occur
            if event.aggregate_id not in read_model:
                handler_log.append("⚠️ ToolGroup not found in Read Model for selector add!")
                raise ValueError(f"ToolGroup {event.aggregate_id} not found")

            read_model[event.aggregate_id]["selectors"].append({"id": event.selector_id, "pattern": event.name_pattern})
            handler_log.append("✅ Projected SelectorAdded to Read Model")

        async def mock_publish(event):
            """Route events to appropriate handlers."""
            if isinstance(event, ToolGroupCreatedDomainEvent):
                await mock_created_handler(event)
            elif isinstance(event, SelectorAddedDomainEvent):
                await mock_selector_handler(event)

        mock_mediator = MagicMock(spec=Mediator)
        mock_mediator.publish_async = mock_publish

        mock_event_store = MagicMock(spec=EventStore)
        mock_event_store.observe_async = AsyncMock(return_value=MagicMock())

        mock_event_store_options = EventStoreOptions(database_name="test-db", consumer_group="test-group")

        options = ReadModelConciliationOptions(consumer_group="test")
        reconciliator = ReadModelReconciliator(MagicMock(), mock_mediator, mock_event_store_options, mock_event_store, options)
        reconciliator._loop = asyncio.get_event_loop()

        # Create events as they would be emitted from aggregate
        aggregate_id = "toolgroup-a2165ca2-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        created_event = MockEventRecord(ToolGroupCreatedDomainEvent(aggregate_id=aggregate_id, name="My Tool Group", description="Test description"))
        selector_event = MockEventRecord(SelectorAddedDomainEvent(aggregate_id=aggregate_id, selector_id="selector-001", name_pattern="*.tool"))

        # Act - process events through reconciliator
        await reconciliator._handle_event_async(created_event)
        await reconciliator._handle_event_async(selector_event)

        # Wait for queue processing
        await asyncio.sleep(0.2)

        # Assert - no race condition errors
        assert "⚠️ ToolGroup not found" not in " ".join(handler_log), f"Race condition occurred! Log: {handler_log}"

        # Assert - correct order
        assert "✅ Projected ToolGroupCreated to Read Model" in handler_log
        assert "✅ Projected SelectorAdded to Read Model" in handler_log

        # Assert - read model correctly populated
        assert aggregate_id in read_model
        assert len(read_model[aggregate_id]["selectors"]) == 1
        assert read_model[aggregate_id]["selectors"][0]["id"] == "selector-001"

        # Cleanup
        await reconciliator.stop_async()

    @pytest.mark.asyncio
    async def test_parallel_mode_can_cause_race_condition(self):
        """
        Test that parallel processing mode can cause the race condition.

        This test documents the race condition behavior when sequential
        processing is disabled.

        Expected Behavior:
            - With sequential_processing=False, events MAY be processed out of order
            - This can cause "document not found" errors
        """
        # Arrange
        read_model: dict[str, dict] = {}
        race_condition_occurred = False

        async def mock_created_handler(event: ToolGroupCreatedDomainEvent):
            await asyncio.sleep(0.1)  # Slow enough to cause race
            read_model[event.aggregate_id] = {"id": event.aggregate_id, "selectors": []}

        async def mock_selector_handler(event: SelectorAddedDomainEvent):
            nonlocal race_condition_occurred
            if event.aggregate_id not in read_model:
                race_condition_occurred = True
                return
            read_model[event.aggregate_id]["selectors"].append(event.selector_id)

        async def mock_publish(event):
            if isinstance(event, ToolGroupCreatedDomainEvent):
                await mock_created_handler(event)
            elif isinstance(event, SelectorAddedDomainEvent):
                await mock_selector_handler(event)

        mock_mediator = MagicMock(spec=Mediator)
        mock_mediator.publish_async = mock_publish

        mock_event_store_options = EventStoreOptions(database_name="test-db", consumer_group="test-group")

        # Parallel mode
        options = ReadModelConciliationOptions(consumer_group="test", sequential_processing=False)

        reconciliator = ReadModelReconciliator(MagicMock(), mock_mediator, mock_event_store_options, MagicMock(spec=EventStore), options)
        reconciliator._loop = asyncio.get_event_loop()

        aggregate_id = "test-agg"
        created_event = MockEventRecord(ToolGroupCreatedDomainEvent(aggregate_id=aggregate_id, name="Test", description=""))
        selector_event = MockEventRecord(SelectorAddedDomainEvent(aggregate_id=aggregate_id, selector_id="sel-1", name_pattern="*"))

        # Act - fire both handlers concurrently (simulating parallel processing)
        await asyncio.gather(reconciliator._handle_event_async(created_event), reconciliator._handle_event_async(selector_event))

        # Assert - race condition should occur in parallel mode
        # Note: This test documents the bug behavior, not desired behavior
        assert race_condition_occurred, "Expected race condition to occur in parallel mode"


# ============================================================================
# Additional Edge Case Tests
# ============================================================================


@pytest.mark.unit
class TestEdgeCases:
    """Edge case tests for the sequential processing feature."""

    @pytest.mark.asyncio
    async def test_unknown_aggregate_id_fallback(self):
        """
        Test that events without extractable aggregate_id fall back to 'unknown'.

        Expected Behavior:
            - All events without aggregate_id go to same queue
            - They are processed sequentially (safe default)
        """
        # Arrange
        options = ReadModelConciliationOptions(consumer_group="test")
        reconciliator = ReadModelReconciliator(MagicMock(), MagicMock(spec=Mediator), EventStoreOptions(database_name="test", consumer_group="test"), MagicMock(spec=EventStore), options)

        # Create event with no aggregate_id
        @dataclass
        class SimpleEvent:
            value: str

        event = MagicMock()
        event.data = SimpleEvent(value="test")
        event.stream_id = None

        # Act
        aggregate_id = reconciliator._extract_aggregate_id(event)

        # Assert
        assert aggregate_id == "unknown"

    @pytest.mark.asyncio
    async def test_multiple_aggregates_interleaved(self):
        """
        Test processing events from multiple aggregates in interleaved order.

        Expected Behavior:
            - Events from aggregate A are sequential
            - Events from aggregate B are sequential
            - A and B can proceed concurrently
        """
        # Arrange
        queue = AggregateEventQueue()
        processing_log: list[str] = []

        async def log_process(event_record):
            agg_id = event_record.data.aggregate_id
            event_type = type(event_record.data).__name__
            processing_log.append(f"{agg_id}:{event_type}:start")
            await asyncio.sleep(0.03)
            processing_log.append(f"{agg_id}:{event_type}:end")

        # Create interleaved events
        events = [
            ("agg-A", ToolGroupCreatedDomainEvent(aggregate_id="agg-A", name="A", description="")),
            ("agg-B", ToolGroupCreatedDomainEvent(aggregate_id="agg-B", name="B", description="")),
            ("agg-A", SelectorAddedDomainEvent(aggregate_id="agg-A", selector_id="1", name_pattern="*")),
            ("agg-B", SelectorAddedDomainEvent(aggregate_id="agg-B", selector_id="2", name_pattern="*")),
        ]

        # Act
        for agg_id, event_data in events:
            await queue.enqueue(agg_id, MockEventRecord(event_data), log_process)

        await asyncio.sleep(0.2)

        # Assert - within each aggregate, events are sequential
        # Extract logs per aggregate
        agg_a_logs = [log_entry for log_entry in processing_log if log_entry.startswith("agg-A")]
        agg_b_logs = [log_entry for log_entry in processing_log if log_entry.startswith("agg-B")]

        # For A: Created must end before Selector starts
        created_end_idx = agg_a_logs.index("agg-A:ToolGroupCreatedDomainEvent:end")
        selector_start_idx = agg_a_logs.index("agg-A:SelectorAddedDomainEvent:start")
        assert created_end_idx < selector_start_idx, "A's events should be sequential"

        # Same for B
        created_end_idx = agg_b_logs.index("agg-B:ToolGroupCreatedDomainEvent:end")
        selector_start_idx = agg_b_logs.index("agg-B:SelectorAddedDomainEvent:start")
        assert created_end_idx < selector_start_idx, "B's events should be sequential"

        # Cleanup
        await queue.shutdown()
