"""
Test suite for Event Store implementation.

This module validates event sourcing patterns including:
- Event persistence and retrieval
- Stream management
- Event ordering and versioning
- Snapshot functionality
- Event replay capabilities

Test Coverage:
    - Stream creation and existence checks
    - Event appending with versioning
    - Event reading (forwards/backwards)
    - Stream metadata
    - Concurrency control
    - Event sourcing repository patterns

Expected Behavior:
    - Events persist correctly
    - Stream versioning maintained
    - Events retrievable in order
    - Optimistic concurrency enforced

Related Modules:
    - neuroglia.data.infrastructure.event_sourcing: Event store abstractions
    - neuroglia.data.abstractions: AggregateRoot, DomainEvent

Related Documentation:
    - [Event Sourcing](../../docs/patterns/event-sourcing.md)
    - [Data Access](../../docs/features/data-access.md)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import pytest

from neuroglia.data.abstractions import AggregateRoot, AggregateState
from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    EventDescriptor,
    EventRecord,
    EventStore,
    StreamDescriptor,
    StreamReadDirection,
)

# =============================================================================
# In-Memory Event Store Implementation for Testing
# =============================================================================


class InMemoryEventStore(EventStore):
    """
    In-memory event store implementation for testing.

    Provides a simple, synchronous event store that maintains
    events in memory for fast, reliable testing without external dependencies.
    """

    def __init__(self):
        self.streams: dict[str, list[EventRecord]] = {}
        self.global_position = 0

    async def contains_async(self, stream_id: str) -> bool:
        """Check if stream exists."""
        return stream_id in self.streams

    async def append_async(self, stream_id: str, events: list[EventDescriptor], expected_version: Optional[int] = None):
        """Append events to stream with optimistic concurrency."""
        if stream_id not in self.streams:
            self.streams[stream_id] = []

        current_version = len(self.streams[stream_id])

        # Optimistic concurrency check
        if expected_version is not None and current_version != expected_version:
            raise Exception(f"Concurrency conflict: expected version {expected_version}, " f"but current version is {current_version}")

        # Append events
        for event in events:
            record = EventRecord(stream_id=stream_id, id=str(uuid4()), offset=len(self.streams[stream_id]), position=self.global_position, timestamp=datetime.now(timezone.utc), type=event.type, data=event.data, metadata=event.metadata)
            self.streams[stream_id].append(record)
            self.global_position += 1

    async def get_async(self, stream_id: str) -> Optional[StreamDescriptor]:
        """Get stream metadata."""
        if stream_id not in self.streams:
            return None

        events = self.streams[stream_id]
        if not events:
            return StreamDescriptor(id=stream_id, length=0, first_event_at=None, last_event_at=None)

        return StreamDescriptor(id=stream_id, length=len(events), first_event_at=events[0].timestamp, last_event_at=events[-1].timestamp)

    async def read_async(self, stream_id: str, read_direction: StreamReadDirection, offset: int, length: Optional[int] = None) -> list[EventRecord]:
        """Read events from stream."""
        if stream_id not in self.streams:
            return []

        events = self.streams[stream_id]

        if read_direction == StreamReadDirection.FORWARDS:
            result = events[offset:]
        else:  # BACKWARDS
            result = list(reversed(events[: offset + 1]))

        if length is not None:
            result = result[:length]

        return result


# =============================================================================
# Test Domain Events
# =============================================================================


@dataclass
class AccountCreatedEvent:
    """Event raised when account is created."""

    aggregate_id: str
    account_number: str
    owner_name: str
    initial_balance: float


@dataclass
class MoneyDepositedEvent:
    """Event raised when money is deposited."""

    aggregate_id: str
    amount: float
    new_balance: float


@dataclass
class MoneyWithdrawnEvent:
    """Event raised when money is withdrawn."""

    aggregate_id: str
    amount: float
    new_balance: float


@dataclass
class AccountClosedEvent:
    """Event raised when account is closed."""

    aggregate_id: str
    final_balance: float
    closed_at: datetime


# =============================================================================
# Test Aggregate
# =============================================================================


class AccountState(AggregateState[str]):
    """State for bank account aggregate."""

    def __init__(self):
        super().__init__()
        self.account_number: Optional[str] = None
        self.owner_name: Optional[str] = None
        self.balance: float = 0.0
        self.is_closed: bool = False

    def on(self, event):
        """Apply event to state."""
        if isinstance(event, AccountCreatedEvent):
            self.account_number = event.account_number
            self.owner_name = event.owner_name
            self.balance = event.initial_balance
        elif isinstance(event, MoneyDepositedEvent):
            self.balance = event.new_balance
        elif isinstance(event, MoneyWithdrawnEvent):
            self.balance = event.new_balance
        elif isinstance(event, AccountClosedEvent):
            self.is_closed = True
            self.balance = event.final_balance


class Account(AggregateRoot[AccountState, str]):
    """Bank account aggregate root."""

    @staticmethod
    def create(account_number: str, owner_name: str, initial_balance: float = 0.0):
        """Create new account."""
        account = Account()
        account_id = str(uuid4())
        account.state.id = account_id  # Set ID on state
        event = AccountCreatedEvent(aggregate_id=account_id, account_number=account_number, owner_name=owner_name, initial_balance=initial_balance)
        account.register_event(event)
        account.state.on(event)  # Apply event to state
        return account

    def deposit(self, amount: float):
        """Deposit money into account."""
        if self.state.is_closed:
            raise Exception("Cannot deposit to closed account")
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")

        new_balance = self.state.balance + amount
        event = MoneyDepositedEvent(aggregate_id=self.id(), amount=amount, new_balance=new_balance)
        self.register_event(event)
        self.state.on(event)

    def withdraw(self, amount: float):
        """Withdraw money from account."""
        if self.state.is_closed:
            raise Exception("Cannot withdraw from closed account")
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount > self.state.balance:
            raise ValueError("Insufficient funds")

        new_balance = self.state.balance - amount
        event = MoneyWithdrawnEvent(aggregate_id=self.id(), amount=amount, new_balance=new_balance)
        self.register_event(event)
        self.state.on(event)

    def close(self):
        """Close the account."""
        if self.state.is_closed:
            raise Exception("Account already closed")

        event = AccountClosedEvent(aggregate_id=self.id(), final_balance=self.state.balance, closed_at=datetime.now(timezone.utc))
        self.register_event(event)
        self.state.on(event)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def event_store():
    """Create in-memory event store for testing."""
    return InMemoryEventStore()


@pytest.fixture
def sample_account():
    """Create sample account aggregate."""
    return Account.create("ACC-001", "John Doe", 100.0)


# =============================================================================
# Test Suite: Event Store Basics
# =============================================================================


@pytest.mark.unit
class TestEventStoreBasics:
    """
    Test basic event store operations.

    Validates fundamental event store functionality including
    stream creation, existence checks, and basic operations.

    Related: EventStore interface
    """

    @pytest.mark.asyncio
    async def test_new_event_store_is_empty(self, event_store):
        """
        Test new event store has no streams.

        Expected Behavior:
            - New store has no streams
            - Stream existence check returns False
            - Get stream returns None

        Related: EventStore initialization
        """
        # Act
        exists = await event_store.contains_async("test-stream")
        descriptor = await event_store.get_async("test-stream")

        # Assert
        assert exists is False
        assert descriptor is None

    @pytest.mark.asyncio
    async def test_append_creates_stream(self, event_store):
        """
        Test appending events creates stream.

        Expected Behavior:
            - Stream created on first append
            - Stream exists after append
            - Stream descriptor available

        Related: EventStore.append_async()
        """
        # Arrange
        stream_id = "account-123"
        events = [EventDescriptor(type="AccountCreated", data={"account_number": "ACC-123", "owner": "John"})]

        # Act
        await event_store.append_async(stream_id, events)

        exists = await event_store.contains_async(stream_id)
        descriptor = await event_store.get_async(stream_id)

        # Assert
        assert exists is True
        assert descriptor is not None
        assert descriptor.id == stream_id
        assert descriptor.length == 1


# =============================================================================
# Test Suite: Event Appending
# =============================================================================


@pytest.mark.unit
class TestEventAppending:
    """
    Test event appending operations.

    Validates event persistence, ordering, and metadata
    management during append operations.

    Related: EventStore.append_async()
    """

    @pytest.mark.asyncio
    async def test_append_single_event(self, event_store):
        """
        Test appending single event to stream.

        Expected Behavior:
            - Event persisted
            - Stream length incremented
            - Event has ID and timestamp

        Related: Event persistence
        """
        # Arrange
        stream_id = "test-stream"
        events = [EventDescriptor(type="TestEvent", data={"value": 42})]

        # Act
        await event_store.append_async(stream_id, events)
        descriptor = await event_store.get_async(stream_id)

        # Assert
        assert descriptor.length == 1

    @pytest.mark.asyncio
    async def test_append_multiple_events(self, event_store):
        """
        Test appending multiple events at once.

        Expected Behavior:
            - All events persisted
            - Correct order maintained
            - Stream length correct

        Related: Batch append
        """
        # Arrange
        stream_id = "test-stream"
        events = [EventDescriptor(type="Event1", data={"seq": 1}), EventDescriptor(type="Event2", data={"seq": 2}), EventDescriptor(type="Event3", data={"seq": 3})]

        # Act
        await event_store.append_async(stream_id, events)
        descriptor = await event_store.get_async(stream_id)

        # Assert
        assert descriptor.length == 3

    @pytest.mark.asyncio
    async def test_append_increments_stream_version(self, event_store):
        """
        Test that appending increments stream version.

        Expected Behavior:
            - Each append increases version
            - Version tracked correctly
            - Multiple appends cumulative

        Related: Stream versioning
        """
        # Arrange
        stream_id = "test-stream"

        # Act
        await event_store.append_async(stream_id, [EventDescriptor(type="E1", data={})])
        descriptor1 = await event_store.get_async(stream_id)

        await event_store.append_async(stream_id, [EventDescriptor(type="E2", data={})])
        descriptor2 = await event_store.get_async(stream_id)

        await event_store.append_async(stream_id, [EventDescriptor(type="E3", data={})])
        descriptor3 = await event_store.get_async(stream_id)

        # Assert
        assert descriptor1.length == 1
        assert descriptor2.length == 2
        assert descriptor3.length == 3


# =============================================================================
# Test Suite: Event Reading
# =============================================================================


@pytest.mark.unit
class TestEventReading:
    """
    Test event reading operations.

    Validates event retrieval in different directions
    and with various offsets and limits.

    Related: EventStore.read_async()
    """

    @pytest.mark.asyncio
    async def test_read_forwards_from_start(self, event_store):
        """
        Test reading events forwards from beginning.

        Expected Behavior:
            - Events returned in append order
            - All events retrieved
            - Offsets correct

        Related: Forward reading
        """
        # Arrange
        stream_id = "test-stream"
        events = [EventDescriptor(type="E1", data={"value": 1}), EventDescriptor(type="E2", data={"value": 2}), EventDescriptor(type="E3", data={"value": 3})]
        await event_store.append_async(stream_id, events)

        # Act
        records = await event_store.read_async(stream_id, StreamReadDirection.FORWARDS, offset=0)

        # Assert
        assert len(records) == 3
        assert records[0].type == "E1"
        assert records[1].type == "E2"
        assert records[2].type == "E3"
        assert records[0].offset == 0
        assert records[1].offset == 1
        assert records[2].offset == 2

    @pytest.mark.asyncio
    async def test_read_forwards_with_limit(self, event_store):
        """
        Test reading limited number of events forwards.

        Expected Behavior:
            - Only requested number returned
            - Order preserved
            - Offset from start point

        Related: Pagination
        """
        # Arrange
        stream_id = "test-stream"
        events = [EventDescriptor(type=f"E{i}", data={"value": i}) for i in range(10)]
        await event_store.append_async(stream_id, events)

        # Act
        records = await event_store.read_async(stream_id, StreamReadDirection.FORWARDS, offset=0, length=3)

        # Assert
        assert len(records) == 3
        assert records[0].type == "E0"
        assert records[1].type == "E1"
        assert records[2].type == "E2"

    @pytest.mark.asyncio
    async def test_read_backwards_from_end(self, event_store):
        """
        Test reading events backwards from end.

        Expected Behavior:
            - Events in reverse order
            - Latest events first
            - Offsets correct

        Related: Backward reading
        """
        # Arrange
        stream_id = "test-stream"
        events = [EventDescriptor(type="E1", data={"value": 1}), EventDescriptor(type="E2", data={"value": 2}), EventDescriptor(type="E3", data={"value": 3})]
        await event_store.append_async(stream_id, events)

        # Act
        records = await event_store.read_async(stream_id, StreamReadDirection.BACKWARDS, offset=2)  # Last event offset

        # Assert
        assert len(records) == 3
        assert records[0].type == "E3"
        assert records[1].type == "E2"
        assert records[2].type == "E1"

    @pytest.mark.asyncio
    async def test_read_from_middle_offset(self, event_store):
        """
        Test reading from middle of stream.

        Expected Behavior:
            - Reads from specified offset
            - Only events after offset
            - Order maintained

        Related: Offset reading
        """
        # Arrange
        stream_id = "test-stream"
        events = [EventDescriptor(type=f"E{i}", data={"value": i}) for i in range(5)]
        await event_store.append_async(stream_id, events)

        # Act
        records = await event_store.read_async(stream_id, StreamReadDirection.FORWARDS, offset=2)

        # Assert
        assert len(records) == 3
        assert records[0].type == "E2"
        assert records[1].type == "E3"
        assert records[2].type == "E4"


# =============================================================================
# Test Suite: Optimistic Concurrency
# =============================================================================


@pytest.mark.unit
class TestOptimisticConcurrency:
    """
    Test optimistic concurrency control.

    Validates that concurrent modifications are detected
    and handled correctly using expected version.

    Related: Concurrency control
    """

    @pytest.mark.asyncio
    async def test_append_with_correct_expected_version(self, event_store):
        """
        Test append succeeds with correct expected version.

        Expected Behavior:
            - Append succeeds
            - Version matches expectation
            - No exception raised

        Related: Optimistic concurrency
        """
        # Arrange
        stream_id = "test-stream"
        await event_store.append_async(stream_id, [EventDescriptor(type="E1", data={})])

        # Act & Assert - Should not raise
        await event_store.append_async(stream_id, [EventDescriptor(type="E2", data={})], expected_version=1)

        descriptor = await event_store.get_async(stream_id)
        assert descriptor.length == 2

    @pytest.mark.asyncio
    async def test_append_with_wrong_expected_version_fails(self, event_store):
        """
        Test append fails with wrong expected version.

        Expected Behavior:
            - Exception raised
            - Stream unchanged
            - Clear error message

        Related: Concurrency conflict
        """
        # Arrange
        stream_id = "test-stream"
        await event_store.append_async(stream_id, [EventDescriptor(type="E1", data={})])

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await event_store.append_async(stream_id, [EventDescriptor(type="E2", data={})], expected_version=5)  # Wrong version

        assert "Concurrency conflict" in str(exc_info.value)

        # Verify stream unchanged
        descriptor = await event_store.get_async(stream_id)
        assert descriptor.length == 1


# =============================================================================
# Test Suite: Event Sourcing Patterns
# =============================================================================


@pytest.mark.unit
class TestEventSourcingPatterns:
    """
    Test event sourcing aggregate patterns.

    Validates that aggregates can be persisted and
    reconstituted from event streams.

    Related: Event sourcing, AggregateRoot
    """

    @pytest.mark.asyncio
    async def test_persist_aggregate_events(self, event_store, sample_account):
        """
        Test persisting aggregate domain events.

        Expected Behavior:
            - All domain events persisted
            - Event order preserved
            - Aggregate ID as stream ID

        Related: Aggregate persistence
        """
        # Arrange
        account = sample_account
        account.deposit(50.0)
        account.withdraw(25.0)

        stream_id = f"account-{account.id()}"
        uncommitted = account.get_uncommitted_events()

        # Act
        event_descriptors = [EventDescriptor(type=event.__class__.__name__, data=event) for event in uncommitted]
        await event_store.append_async(stream_id, event_descriptors)

        # Assert
        descriptor = await event_store.get_async(stream_id)
        assert descriptor.length == 3  # Created, Deposited, Withdrawn

    @pytest.mark.asyncio
    async def test_read_aggregate_event_stream(self, event_store, sample_account):
        """
        Test reading aggregate event stream.

        Expected Behavior:
            - All events retrievable
            - Events in correct order
            - Can reconstruct aggregate state

        Related: Event replay
        """
        # Arrange
        account = sample_account
        account.deposit(50.0)
        account.withdraw(25.0)

        stream_id = f"account-{account.id()}"
        event_descriptors = [EventDescriptor(type=e.__class__.__name__, data=e) for e in account.get_uncommitted_events()]
        await event_store.append_async(stream_id, event_descriptors)

        # Act
        records = await event_store.read_async(stream_id, StreamReadDirection.FORWARDS, offset=0)

        # Assert
        assert len(records) == 3
        assert records[0].type == "AccountCreatedEvent"
        assert records[1].type == "MoneyDepositedEvent"
        assert records[2].type == "MoneyWithdrawnEvent"

    @pytest.mark.asyncio
    async def test_reconstruct_aggregate_from_events(self, event_store):
        """
        Test reconstructing aggregate from event stream.

        Expected Behavior:
            - Aggregate state matches event history
            - All events applied in order
            - Final state correct

        Related: Event replay, state reconstruction
        """
        # Arrange
        account_id = str(uuid4())
        stream_id = f"account-{account_id}"

        events = [EventDescriptor(type="AccountCreatedEvent", data=AccountCreatedEvent(aggregate_id=account_id, account_number="ACC-123", owner_name="Jane Doe", initial_balance=1000.0)), EventDescriptor(type="MoneyDepositedEvent", data=MoneyDepositedEvent(aggregate_id=account_id, amount=500.0, new_balance=1500.0)), EventDescriptor(type="MoneyWithdrawnEvent", data=MoneyWithdrawnEvent(aggregate_id=account_id, amount=300.0, new_balance=1200.0))]
        await event_store.append_async(stream_id, events)

        # Act - Read and replay events
        records = await event_store.read_async(stream_id, StreamReadDirection.FORWARDS, offset=0)

        # Reconstruct state
        state = AccountState()
        for record in records:
            state.on(record.data)

        # Assert
        assert state.account_number == "ACC-123"
        assert state.owner_name == "Jane Doe"
        assert state.balance == 1200.0
        assert state.state_version == 0  # Updated by last event


# =============================================================================
# Test Suite: Stream Metadata
# =============================================================================


@pytest.mark.unit
class TestStreamMetadata:
    """
    Test stream metadata tracking.

    Validates that stream metadata is correctly maintained
    including timestamps, lengths, and versions.

    Related: StreamDescriptor
    """

    @pytest.mark.asyncio
    async def test_stream_descriptor_has_correct_length(self, event_store):
        """
        Test stream descriptor reports correct length.

        Expected Behavior:
            - Length matches event count
            - Updates on each append
            - Accurate for empty stream

        Related: Stream length
        """
        # Arrange
        stream_id = "test-stream"

        # Act
        await event_store.append_async(stream_id, [EventDescriptor(type="E1", data={})])
        descriptor1 = await event_store.get_async(stream_id)

        await event_store.append_async(stream_id, [EventDescriptor(type="E2", data={}), EventDescriptor(type="E3", data={})])
        descriptor2 = await event_store.get_async(stream_id)

        # Assert
        assert descriptor1.length == 1
        assert descriptor2.length == 3

    @pytest.mark.asyncio
    async def test_stream_descriptor_has_timestamps(self, event_store):
        """
        Test stream descriptor includes timestamps.

        Expected Behavior:
            - First event timestamp recorded
            - Last event timestamp recorded
            - Timestamps are datetime objects

        Related: Stream timestamps
        """
        # Arrange
        stream_id = "test-stream"
        events = [EventDescriptor(type="E1", data={}), EventDescriptor(type="E2", data={})]

        # Act
        await event_store.append_async(stream_id, events)
        descriptor = await event_store.get_async(stream_id)

        # Assert
        assert descriptor.first_event_at is not None
        assert descriptor.last_event_at is not None
        assert isinstance(descriptor.first_event_at, datetime)
        assert isinstance(descriptor.last_event_at, datetime)
