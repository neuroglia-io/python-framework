"""
Test suite for EventSourcingRepository deletion modes.

This module validates that the EventSourcingRepository properly handles:
1. DISABLED mode: Raises NotImplementedError (default behavior)
2. SOFT mode: Delegates to aggregate's mark_as_deleted() method
3. HARD mode: Physically deletes the event stream

Design Philosophy:
------------------
- DISABLED is default (event sourcing best practice: immutable history)
- SOFT delegates to aggregate (DDD principle: aggregate controls behavior)
- HARD is for compliance (GDPR) or data cleanup
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from neuroglia.data.abstractions import AggregateRoot, AggregateState, DomainEvent
from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    Aggregator,
    DeleteMode,
    EventDescriptor,
    EventStore,
)
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepository,
    EventSourcingRepositoryOptions,
)

# Test Domain: Task Management


@dataclass
class TaskState(AggregateState):
    """Task aggregate state"""

    id: str = ""
    title: str = ""
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None


class TaskDeletedDomainEvent(DomainEvent):
    """Domain event for task deletion"""

    def __init__(self, aggregate_id: str, title: str):
        super().__init__(aggregate_id)
        self.title = title
        self.deleted_at = datetime.now(timezone.utc)


class Task(AggregateRoot[TaskState, str]):
    """Task aggregate with soft delete support"""

    def __init__(self, task_id: str, title: str):
        super().__init__()
        self.state.id = task_id
        self.state.title = title

    def id(self) -> str:
        return self.state.id

    def mark_as_deleted(self) -> None:
        """Mark the task as deleted by registering a deletion event."""
        self.state.is_deleted = True
        self.state.deleted_at = datetime.now(timezone.utc)
        event = TaskDeletedDomainEvent(self.id(), self.state.title)
        self.register_event(event)


class TaskWithoutDeleteMethod(AggregateRoot[TaskState, str]):
    """Task aggregate WITHOUT delete method (to test error handling)"""

    def __init__(self, task_id: str, title: str):
        super().__init__()
        self.state.id = task_id
        self.state.title = title

    def id(self) -> str:
        return self.state.id

    # Intentionally missing mark_as_deleted() method


# Test Fixtures


@pytest.fixture
def mock_eventstore():
    """Create mock event store"""
    eventstore = Mock(spec=EventStore)
    eventstore.append_async = AsyncMock()
    eventstore.delete_async = AsyncMock()
    eventstore.read_async = AsyncMock(return_value=[])
    return eventstore


@pytest.fixture
def mock_aggregator():
    """Create mock aggregator"""
    return Mock(spec=Aggregator)


@pytest.fixture
def test_task():
    """Create test task"""
    return Task(task_id=str(uuid4()), title="Test Task")


# Test Cases: DISABLED Mode (Default)


@pytest.mark.asyncio
class TestDeleteModeDisabled:
    """Test deletion when mode is DISABLED (default behavior)"""

    async def test_default_options_delete_raises_not_implemented(self, mock_eventstore, mock_aggregator):
        """
        Test that deletion with default options raises NotImplementedError.

        This is the default behavior: event sourcing repositories preserve
        immutable history and do not support deletion by default.
        """
        # Arrange
        repo = EventSourcingRepository[Task, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
        )

        # Act & Assert
        with pytest.raises(NotImplementedError) as exc_info:
            await repo.remove_async("task-123")

        assert "Deletion is disabled" in str(exc_info.value)
        assert "delete_mode=DeleteMode.SOFT" in str(exc_info.value)
        assert "delete_mode=DeleteMode.HARD" in str(exc_info.value)

    async def test_explicit_disabled_mode_raises_not_implemented(self, mock_eventstore, mock_aggregator):
        """Test that explicitly setting DISABLED mode raises NotImplementedError"""
        # Arrange
        options = EventSourcingRepositoryOptions[Task, str](delete_mode=DeleteMode.DISABLED)
        repo = EventSourcingRepository[Task, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
            options=options,
        )

        # Act & Assert
        with pytest.raises(NotImplementedError) as exc_info:
            await repo.remove_async("task-123")

        assert "Deletion is disabled" in str(exc_info.value)


# Test Cases: SOFT Delete Mode


@pytest.mark.asyncio
class TestDeleteModeSoft:
    """Test soft deletion mode (delegates to aggregate)"""

    async def test_soft_delete_calls_aggregate_mark_as_deleted(self, mock_eventstore, mock_aggregator, test_task):
        """
        Test that soft delete loads aggregate, calls mark_as_deleted(), and persists.

        Expected Flow:
        1. Repository loads aggregate via get_async()
        2. Repository calls aggregate.mark_as_deleted()
        3. Aggregate registers TaskDeletedDomainEvent
        4. Repository persists via _do_update_async()
        """
        # Arrange
        options = EventSourcingRepositoryOptions[Task, str](delete_mode=DeleteMode.SOFT)
        repo = EventSourcingRepository[Task, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
            options=options,
        )

        # Mock get_async to return our test task
        repo.get_async = AsyncMock(return_value=test_task)

        # Act
        await repo.remove_async(test_task.id())

        # Assert - aggregate state updated
        assert test_task.state.is_deleted is True
        assert test_task.state.deleted_at is not None

        # Assert - event persisted to event store
        mock_eventstore.append_async.assert_called_once()
        call_args = mock_eventstore.append_async.call_args
        stream_id = call_args[0][0]
        events = call_args[0][1]

        assert stream_id == f"task-{test_task.id()}"
        assert len(events) == 1
        assert isinstance(events[0], EventDescriptor)

    async def test_soft_delete_with_custom_method_name(self, mock_eventstore, mock_aggregator):
        """Test soft delete with custom deletion method name"""

        # Arrange
        class CustomTask(Task):
            def mark_deleted(self) -> None:  # Different method name
                self.mark_as_deleted()

        task = CustomTask(task_id=str(uuid4()), title="Custom Task")

        options = EventSourcingRepositoryOptions[CustomTask, str](delete_mode=DeleteMode.SOFT, soft_delete_method_name="mark_deleted")
        repo = EventSourcingRepository[CustomTask, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
            options=options,
        )

        repo.get_async = AsyncMock(return_value=task)

        # Act
        await repo.remove_async(task.id())

        # Assert - deletion succeeded
        assert task.state.is_deleted is True
        mock_eventstore.append_async.assert_called_once()

    async def test_soft_delete_raises_when_aggregate_lacks_method(self, mock_eventstore, mock_aggregator):
        """
        Test that soft delete raises ValueError if aggregate lacks deletion method.

        This ensures developers get clear feedback when they configure SOFT mode
        but forget to implement the deletion method on their aggregate.
        """
        # Arrange
        task = TaskWithoutDeleteMethod(task_id=str(uuid4()), title="No Delete Method")

        options = EventSourcingRepositoryOptions[TaskWithoutDeleteMethod, str](delete_mode=DeleteMode.SOFT)
        repo = EventSourcingRepository[TaskWithoutDeleteMethod, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
            options=options,
        )

        repo.get_async = AsyncMock(return_value=task)

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await repo.remove_async(task.id())

        error_message = str(exc_info.value)
        assert "TaskWithoutDeleteMethod" in error_message
        assert "mark_as_deleted()" in error_message or "mark_deleted()" in error_message
        assert "Soft delete requires the aggregate to implement deletion logic" in error_message

    async def test_soft_delete_raises_when_aggregate_not_found(self, mock_eventstore, mock_aggregator):
        """Test that soft delete raises exception if aggregate doesn't exist"""
        # Arrange
        options = EventSourcingRepositoryOptions[Task, str](delete_mode=DeleteMode.SOFT)
        repo = EventSourcingRepository[Task, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
            options=options,
        )

        # Mock get_async to return None (aggregate not found)
        repo.get_async = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await repo.remove_async("nonexistent-task")

        assert "not found" in str(exc_info.value).lower()


# Test Cases: HARD Delete Mode


@pytest.mark.asyncio
class TestDeleteModeHard:
    """Test hard deletion mode (physical stream deletion)"""

    async def test_hard_delete_calls_eventstore_delete_async(self, mock_eventstore, mock_aggregator):
        """
        Test that hard delete physically deletes the event stream.

        WARNING: This is irreversible and removes all history.
        Use for GDPR compliance or data cleanup.
        """
        # Arrange
        task_id = str(uuid4())

        options = EventSourcingRepositoryOptions[Task, str](delete_mode=DeleteMode.HARD)
        repo = EventSourcingRepository[Task, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
            options=options,
        )

        # Act
        await repo.remove_async(task_id)

        # Assert - event store delete called with correct stream ID
        mock_eventstore.delete_async.assert_called_once()
        call_args = mock_eventstore.delete_async.call_args
        stream_id = call_args[0][0]

        assert stream_id == f"task-{task_id}"

    async def test_hard_delete_does_not_load_aggregate(self, mock_eventstore, mock_aggregator):
        """
        Test that hard delete does NOT load the aggregate.

        Hard delete operates directly on the stream without loading the aggregate,
        which is more efficient and appropriate for compliance scenarios.
        """
        # Arrange
        task_id = str(uuid4())

        options = EventSourcingRepositoryOptions[Task, str](delete_mode=DeleteMode.HARD)
        repo = EventSourcingRepository[Task, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
            options=options,
        )

        # Mock get_async to track if it's called
        repo.get_async = AsyncMock(return_value=None)

        # Act
        await repo.remove_async(task_id)

        # Assert - get_async was NOT called (no aggregate loading)
        repo.get_async.assert_not_called()

        # Assert - delete_async WAS called
        mock_eventstore.delete_async.assert_called_once()


# Test Cases: Configuration


@pytest.mark.asyncio
class TestRepositoryConfiguration:
    """Test repository configuration options"""

    async def test_repository_without_options_uses_defaults(self, mock_eventstore, mock_aggregator):
        """Test that repository without options uses default configuration"""
        # Arrange
        repo = EventSourcingRepository[Task, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
        )

        # Assert - default options applied
        assert repo._options.delete_mode == DeleteMode.DISABLED
        assert repo._options.soft_delete_method_name == "mark_as_deleted"

    async def test_repository_with_options_uses_provided_config(self, mock_eventstore, mock_aggregator):
        """Test that repository uses provided configuration"""
        # Arrange
        options = EventSourcingRepositoryOptions[Task, str](delete_mode=DeleteMode.SOFT, soft_delete_method_name="mark_deleted")
        repo = EventSourcingRepository[Task, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
            options=options,
        )

        # Assert - custom options applied
        assert repo._options.delete_mode == DeleteMode.SOFT
        assert repo._options.soft_delete_method_name == "mark_deleted"


# Integration Test Scenarios


@pytest.mark.asyncio
class TestDeleteIntegrationScenarios:
    """Integration test scenarios for deletion"""

    async def test_soft_delete_preserves_history_for_audit(self, mock_eventstore, mock_aggregator, test_task):
        """
        Soft delete scenario: Task deleted but history preserved.

        Scenario:
        1. Task created
        2. Task assigned to user
        3. Task marked as deleted
        4. All events preserved in stream for audit

        This is the recommended pattern for most business scenarios.
        """
        # Arrange
        options = EventSourcingRepositoryOptions[Task, str](delete_mode=DeleteMode.SOFT)
        repo = EventSourcingRepository[Task, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
            options=options,
        )

        repo.get_async = AsyncMock(return_value=test_task)

        # Act - Soft delete
        await repo.remove_async(test_task.id())

        # Assert - Event appended (not stream deleted)
        mock_eventstore.append_async.assert_called_once()
        mock_eventstore.delete_async.assert_not_called()

        # Assert - Aggregate state updated
        assert test_task.state.is_deleted is True
        assert test_task.state.deleted_at is not None

    async def test_hard_delete_for_gdpr_compliance(self, mock_eventstore, mock_aggregator):
        """
        Hard delete scenario: User requests data deletion (GDPR).

        Scenario:
        1. User exercises "right to be forgotten"
        2. All personal data must be permanently deleted
        3. Event stream is physically removed

        This is appropriate for compliance requirements.
        """
        # Arrange
        user_task_id = "user-data-12345"

        options = EventSourcingRepositoryOptions[Task, str](delete_mode=DeleteMode.HARD)
        repo = EventSourcingRepository[Task, str](
            eventstore=mock_eventstore,
            aggregator=mock_aggregator,
            options=options,
        )

        # Act - Hard delete
        await repo.remove_async(user_task_id)

        # Assert - Stream physically deleted
        mock_eventstore.delete_async.assert_called_once_with(f"task-{user_task_id}")
        mock_eventstore.append_async.assert_not_called()
