"""Tests for EventSourcingRepository.get_async method handling non-existent streams."""

from unittest.mock import AsyncMock, Mock

import pytest

from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    Aggregator,
    EventStore,
    StreamReadDirection,
)
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepository,
)
from tests.data import User


class TestEventSourcingRepositoryGetAsync:
    """Test EventSourcingRepository.get_async behavior with non-existent streams."""

    @pytest.mark.asyncio
    async def test_get_async_returns_none_when_stream_does_not_exist(self):
        """Test that get_async returns None when the event stream doesn't exist."""
        # Arrange
        mock_eventstore = Mock(spec=EventStore)
        # Simulate stream not found - raises exception (typical EventStoreDB behavior)
        mock_eventstore.read_async = AsyncMock(side_effect=Exception("Stream not found"))

        mock_aggregator = Mock(spec=Aggregator)

        repository = EventSourcingRepository[User, str](mock_eventstore, mock_aggregator)

        # Act
        result = await repository.get_async("nonexistent-user-id")

        # Assert
        assert result is None
        mock_eventstore.read_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async_returns_none_when_stream_is_empty(self):
        """Test that get_async returns None when the event stream exists but has no events."""
        # Arrange
        mock_eventstore = Mock(spec=EventStore)
        # Stream exists but returns empty list
        mock_eventstore.read_async = AsyncMock(return_value=[])

        mock_aggregator = Mock(spec=Aggregator)

        repository = EventSourcingRepository[User, str](mock_eventstore, mock_aggregator)

        # Act
        result = await repository.get_async("empty-stream-id")

        # Assert
        assert result is None
        mock_eventstore.read_async.assert_called_once()
        # Aggregator should NOT be called for empty streams
        mock_aggregator.aggregate.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_async_returns_aggregate_when_stream_exists(self):
        """Test that get_async returns the aggregate when stream exists with events."""
        # Arrange
        mock_eventstore = Mock(spec=EventStore)
        mock_events = [Mock(), Mock()]  # Simulate some events
        mock_eventstore.read_async = AsyncMock(return_value=mock_events)

        mock_aggregator = Mock(spec=Aggregator)
        expected_user = User("John Doe", "john@example.com")
        mock_aggregator.aggregate = Mock(return_value=expected_user)

        repository = EventSourcingRepository[User, str](mock_eventstore, mock_aggregator)

        # Act
        result = await repository.get_async("existing-user-id")

        # Assert
        assert result == expected_user
        mock_eventstore.read_async.assert_called_once()
        mock_aggregator.aggregate.assert_called_once_with(mock_events, User)

    @pytest.mark.asyncio
    async def test_get_async_calls_read_async_with_correct_parameters(self):
        """Test that get_async calls read_async with correct stream_id and parameters."""
        # Arrange
        mock_eventstore = Mock(spec=EventStore)
        mock_eventstore.read_async = AsyncMock(return_value=[])

        mock_aggregator = Mock(spec=Aggregator)

        repository = EventSourcingRepository[User, str](mock_eventstore, mock_aggregator)

        # Act
        await repository.get_async("test-user-123")

        # Assert
        # Verify read_async was called with correct parameters
        mock_eventstore.read_async.assert_called_once_with(
            "user-test-user-123",  # stream_id format
            StreamReadDirection.FORWARDS,
            0,  # offset
        )
