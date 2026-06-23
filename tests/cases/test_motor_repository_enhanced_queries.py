"""Tests for MotorRepository enhanced query methods (find_async with pagination, count_async, exists_async)."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from neuroglia.data.infrastructure.mongo.motor_repository import MotorRepository
from neuroglia.serialization.json import JsonSerializer


@dataclass
class SampleEntity:
    """Test entity for repository operations."""

    id: str
    name: str
    email: str
    is_active: bool


class SampleEntityRepository(MotorRepository[SampleEntity, str]):
    """Concrete repository for testing."""


@pytest.fixture
def mock_motor_client():
    """Create a mock Motor client."""
    return AsyncMock(spec=AsyncIOMotorClient)


@pytest.fixture
def mock_collection():
    """Create a mock Motor collection."""
    return Mock()


@pytest.fixture
def repository(mock_motor_client, mock_collection):
    """Create a repository instance with mocked dependencies."""
    mock_motor_client.__getitem__.return_value.__getitem__.return_value = mock_collection

    repo = SampleEntityRepository(client=mock_motor_client, database_name="test_db", collection_name="sample_entities", serializer=JsonSerializer())
    return repo


class TestMotorRepositoryFindAsyncEnhanced:
    """Test enhanced find_async with sorting, pagination, and projection."""

    @pytest.mark.asyncio
    async def test_find_async_basic_filter_only(self, repository, mock_collection):
        """Test find_async with only filter parameter (backward compatibility)."""
        # Setup mock data
        mock_documents = [
            {"_id": "1", "id": "1", "name": "Alice", "email": "alice@test.com", "is_active": True},
            {"_id": "2", "id": "2", "name": "Bob", "email": "bob@test.com", "is_active": True},
        ]

        # Create async iterator for cursor
        async def async_iter():
            for doc in mock_documents:
                yield doc

        mock_cursor = AsyncMock()
        mock_cursor.__aiter__ = lambda self: async_iter()
        mock_collection.find.return_value = mock_cursor

        # Execute
        results = await repository.find_async({"is_active": True})

        # Verify
        assert len(results) == 2
        assert results[0].name == "Alice"
        assert results[1].name == "Bob"
        mock_collection.find.assert_called_once_with({"is_active": True}, None)

    @pytest.mark.asyncio
    async def test_find_async_with_sorting(self, repository, mock_collection):
        """Test find_async with sort parameter."""
        mock_documents = [
            {"_id": "1", "id": "1", "name": "Alice", "email": "alice@test.com", "is_active": True},
        ]

        async def async_iter():
            for doc in mock_documents:
                yield doc

        mock_cursor = AsyncMock()
        mock_cursor.__aiter__ = lambda self: async_iter()
        mock_cursor.sort = Mock(return_value=mock_cursor)
        mock_collection.find.return_value = mock_cursor

        # Execute with sorting
        results = await repository.find_async({"is_active": True}, sort=[("name", 1), ("email", -1)])

        # Verify cursor.sort was called with correct parameters
        mock_cursor.sort.assert_called_once_with([("name", 1), ("email", -1)])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_find_async_with_limit(self, repository, mock_collection):
        """Test find_async with limit parameter."""
        mock_documents = [{"_id": "1", "id": "1", "name": "Alice", "email": "alice@test.com", "is_active": True}]

        async def async_iter():
            for doc in mock_documents:
                yield doc

        mock_cursor = AsyncMock()
        mock_cursor.__aiter__ = lambda self: async_iter()
        mock_cursor.limit = Mock(return_value=mock_cursor)
        mock_collection.find.return_value = mock_cursor

        # Execute with limit
        results = await repository.find_async({"is_active": True}, limit=10)

        # Verify cursor.limit was called
        mock_cursor.limit.assert_called_once_with(10)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_find_async_with_skip(self, repository, mock_collection):
        """Test find_async with skip parameter."""
        mock_documents = [{"_id": "3", "id": "3", "name": "Charlie", "email": "charlie@test.com", "is_active": True}]

        async def async_iter():
            for doc in mock_documents:
                yield doc

        mock_cursor = AsyncMock()
        mock_cursor.__aiter__ = lambda self: async_iter()
        mock_cursor.skip = Mock(return_value=mock_cursor)
        mock_collection.find.return_value = mock_cursor

        # Execute with skip
        results = await repository.find_async({"is_active": True}, skip=20)

        # Verify cursor.skip was called
        mock_cursor.skip.assert_called_once_with(20)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_find_async_with_projection(self, repository, mock_collection):
        """Test find_async with projection parameter."""
        mock_documents = [
            {"_id": "1", "id": "1", "name": "Alice", "email": "alice@test.com"}
            # Note: is_active excluded by projection
        ]

        async def async_iter():
            for doc in mock_documents:
                yield doc

        mock_cursor = AsyncMock()
        mock_cursor.__aiter__ = lambda self: async_iter()
        mock_collection.find.return_value = mock_cursor

        # Execute with projection
        projection = {"name": 1, "email": 1}
        results = await repository.find_async({"is_active": True}, projection=projection)

        # Verify find was called with projection
        mock_collection.find.assert_called_once_with({"is_active": True}, projection)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_find_async_with_all_parameters(self, repository, mock_collection):
        """Test find_async with all optional parameters (pagination + sorting + projection)."""
        mock_documents = [{"_id": "2", "id": "2", "name": "Bob", "email": "bob@test.com"}]

        async def async_iter():
            for doc in mock_documents:
                yield doc

        mock_cursor = AsyncMock()
        mock_cursor.__aiter__ = lambda self: async_iter()
        mock_cursor.sort = Mock(return_value=mock_cursor)
        mock_cursor.skip = Mock(return_value=mock_cursor)
        mock_cursor.limit = Mock(return_value=mock_cursor)
        mock_collection.find.return_value = mock_cursor

        # Execute with all parameters
        results = await repository.find_async(
            filter_dict={"is_active": True},
            sort=[("name", 1)],
            skip=10,
            limit=5,
            projection={"name": 1, "email": 1},
        )

        # Verify all cursor methods were called in correct order
        mock_collection.find.assert_called_once_with({"is_active": True}, {"name": 1, "email": 1})
        mock_cursor.sort.assert_called_once_with([("name", 1)])
        mock_cursor.skip.assert_called_once_with(10)
        mock_cursor.limit.assert_called_once_with(5)
        assert len(results) == 1


class TestMotorRepositoryCountAsync:
    """Test count_async method."""

    @pytest.mark.asyncio
    async def test_count_async_with_filter(self, repository, mock_collection):
        """Test count_async with a filter."""
        mock_collection.count_documents = AsyncMock(return_value=42)

        count = await repository.count_async({"is_active": True})

        assert count == 42
        mock_collection.count_documents.assert_called_once_with({"is_active": True})

    @pytest.mark.asyncio
    async def test_count_async_without_filter(self, repository, mock_collection):
        """Test count_async without filter (count all)."""
        mock_collection.count_documents = AsyncMock(return_value=100)

        count = await repository.count_async()

        assert count == 100
        mock_collection.count_documents.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_count_async_with_empty_dict(self, repository, mock_collection):
        """Test count_async with explicit empty dict."""
        mock_collection.count_documents = AsyncMock(return_value=100)

        count = await repository.count_async({})

        assert count == 100
        mock_collection.count_documents.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_count_async_returns_zero_when_no_matches(self, repository, mock_collection):
        """Test count_async returns 0 when no documents match."""
        mock_collection.count_documents = AsyncMock(return_value=0)

        count = await repository.count_async({"non_existent_field": "value"})

        assert count == 0


class TestMotorRepositoryExistsAsync:
    """Test exists_async method."""

    @pytest.mark.asyncio
    async def test_exists_async_returns_true_when_documents_exist(self, repository, mock_collection):
        """Test exists_async returns True when documents match filter."""
        mock_collection.count_documents = AsyncMock(return_value=1)

        exists = await repository.exists_async({"email": "alice@test.com"})

        assert exists is True
        mock_collection.count_documents.assert_called_once_with({"email": "alice@test.com"}, limit=1)

    @pytest.mark.asyncio
    async def test_exists_async_returns_false_when_no_documents_exist(self, repository, mock_collection):
        """Test exists_async returns False when no documents match filter."""
        mock_collection.count_documents = AsyncMock(return_value=0)

        exists = await repository.exists_async({"email": "nonexistent@test.com"})

        assert exists is False
        mock_collection.count_documents.assert_called_once_with({"email": "nonexistent@test.com"}, limit=1)

    @pytest.mark.asyncio
    async def test_exists_async_uses_limit_for_efficiency(self, repository, mock_collection):
        """Test exists_async uses limit=1 for efficiency."""
        mock_collection.count_documents = AsyncMock(return_value=1)

        await repository.exists_async({"is_active": True})

        # Verify limit=1 is passed for efficiency (stops after finding first match)
        call_args = mock_collection.count_documents.call_args
        assert call_args.kwargs.get("limit") == 1


class TestMotorRepositoryEnhancedQueriesIntegration:
    """Integration-style tests demonstrating real-world usage patterns."""

    @pytest.mark.asyncio
    async def test_pagination_workflow(self, repository, mock_collection):
        """Test typical pagination workflow: count total, then fetch page."""
        # Setup: 100 total active users
        mock_collection.count_documents = AsyncMock(return_value=100)

        # Mock paginated results (page 3, 10 items per page)
        page_3_docs = [{"_id": str(i), "id": str(i), "name": f"User{i}", "email": f"user{i}@test.com", "is_active": True} for i in range(20, 30)]

        async def async_iter():
            for doc in page_3_docs:
                yield doc

        mock_cursor = AsyncMock()
        mock_cursor.__aiter__ = lambda self: async_iter()
        mock_cursor.sort = Mock(return_value=mock_cursor)
        mock_cursor.skip = Mock(return_value=mock_cursor)
        mock_cursor.limit = Mock(return_value=mock_cursor)
        mock_collection.find.return_value = mock_cursor

        # Execute pagination workflow
        filter_query = {"is_active": True}
        page_size = 10
        page_number = 3

        # Step 1: Count total for pagination metadata
        total_count = await repository.count_async(filter_query)

        # Step 2: Fetch specific page
        results = await repository.find_async(filter_query, sort=[("name", 1)], skip=(page_number - 1) * page_size, limit=page_size)

        # Verify
        assert total_count == 100
        assert len(results) == 10
        assert results[0].name == "User20"  # First item on page 3

    @pytest.mark.asyncio
    async def test_existence_check_before_insert(self, repository, mock_collection):
        """Test checking if entity exists before insertion."""
        # Simulate email already exists
        mock_collection.count_documents = AsyncMock(return_value=1)

        email_to_check = "existing@test.com"
        already_exists = await repository.exists_async({"email": email_to_check})

        assert already_exists is True
        # In real code, this would prevent duplicate insertion
        # if already_exists: raise ValueError("Email already registered")
