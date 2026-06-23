"""
Tests for AsyncCacheRepository pattern search deserialization fix (v0.4.7)

This test suite verifies the fix for the critical bug where get_all_by_pattern_async()
was failing with 'str' object has no attribute 'decode' error.

Bug Report: Redis client may return str or bytes depending on decode_responses setting.
Fix: Normalize entity_data to bytes in _search_by_key_pattern_async().
"""

from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from neuroglia.data.abstractions import Identifiable
from neuroglia.integration.cache_repository import AsyncCacheRepository


@dataclass
class TestEntity(Identifiable[str]):
    """Test entity for cache repository testing"""

    id: str
    name: str
    value: int
    description: Optional[str] = None

    def __eq__(self, other):
        if not isinstance(other, TestEntity):
            return False
        return self.id == other.id and self.name == other.name and self.value == other.value


class TestAsyncCacheRepositoryPatternSearchFix:
    """Test the pattern search deserialization fix"""

    @pytest.fixture
    def mock_redis_client_str_mode(self):
        """Mock Redis client that returns strings (decode_responses=True)"""
        client = MagicMock()
        client.keys = AsyncMock()
        client.get = AsyncMock()
        return client

    @pytest.fixture
    def mock_redis_client_bytes_mode(self):
        """Mock Redis client that returns bytes (decode_responses=False)"""
        client = MagicMock()
        client.keys = AsyncMock()
        client.get = AsyncMock()
        return client

    @pytest.fixture
    def mock_serializer(self):
        """Mock JSON serializer"""
        serializer = MagicMock()
        serializer.deserialize = MagicMock()
        return serializer

    @pytest.fixture
    def mock_redis_pool(self):
        """Mock Redis connection pool"""
        pool = MagicMock()
        pool.pool = MagicMock()
        return pool

    @pytest.mark.asyncio
    async def test_pattern_search_with_string_response(self, mock_redis_client_str_mode, mock_serializer, mock_redis_pool):
        """
        Test pattern search when Redis returns strings (decode_responses=True).
        This was causing the original bug.
        """
        # Arrange
        entity1_json = '{"id": "test-001", "name": "Entity 1", "value": 100}'
        entity2_json = '{"id": "test-002", "name": "Entity 2", "value": 200}'

        # Mock Redis responses - returning STRINGS (the bug scenario)
        mock_redis_client_str_mode.keys.return_value = [
            "testentity.test-001",
            "testentity.test-002",
        ]
        mock_redis_client_str_mode.get.side_effect = [entity1_json, entity2_json]

        # Mock serializer to return entities
        entity1 = TestEntity(id="test-001", name="Entity 1", value=100)
        entity2 = TestEntity(id="test-002", name="Entity 2", value=200)
        mock_serializer.deserialize.side_effect = [entity1, entity2]

        # Create repository
        repo = AsyncCacheRepository[TestEntity, str](
            options=MagicMock(key_prefix="testentity", ttl=3600),
            pool=mock_redis_pool,
            serializer=mock_serializer,
        )
        repo._redis_client = mock_redis_client_str_mode

        # Act
        results = await repo.get_all_by_pattern_async("test-*")

        # Assert
        assert len(results) == 2
        assert results[0] == entity1
        assert results[1] == entity2

        # Verify serializer received STRINGS (after our fix converts str->bytes->str)
        # The fix ensures entity_data is bytes before returning from _search_by_key_pattern_async
        # Then get_all_by_pattern_async decodes it to string before passing to deserializer
        assert mock_serializer.deserialize.call_count == 2
        # First call should receive string data
        first_call_arg = mock_serializer.deserialize.call_args_list[0][0][0]
        assert isinstance(first_call_arg, str)
        assert first_call_arg == entity1_json

    @pytest.mark.asyncio
    async def test_pattern_search_with_bytes_response(self, mock_redis_client_bytes_mode, mock_serializer, mock_redis_pool):
        """
        Test pattern search when Redis returns bytes (decode_responses=False).
        This should continue to work after the fix.
        """
        # Arrange
        entity1_json = '{"id": "test-001", "name": "Entity 1", "value": 100}'
        entity2_json = '{"id": "test-002", "name": "Entity 2", "value": 200}'

        # Mock Redis responses - returning BYTES (original expected behavior)
        mock_redis_client_bytes_mode.keys.return_value = [
            b"testentity.test-001",
            b"testentity.test-002",
        ]
        mock_redis_client_bytes_mode.get.side_effect = [
            entity1_json.encode("utf-8"),
            entity2_json.encode("utf-8"),
        ]

        # Mock serializer to return entities
        entity1 = TestEntity(id="test-001", name="Entity 1", value=100)
        entity2 = TestEntity(id="test-002", name="Entity 2", value=200)
        mock_serializer.deserialize.side_effect = [entity1, entity2]

        # Create repository
        repo = AsyncCacheRepository[TestEntity, str](
            options=MagicMock(key_prefix="testentity", ttl=3600),
            pool=mock_redis_pool,
            serializer=mock_serializer,
        )
        repo._redis_client = mock_redis_client_bytes_mode

        # Act
        results = await repo.get_all_by_pattern_async("test-*")

        # Assert
        assert len(results) == 2
        assert results[0] == entity1
        assert results[1] == entity2

        # Verify serializer received strings (bytes were decoded)
        assert mock_serializer.deserialize.call_count == 2
        first_call_arg = mock_serializer.deserialize.call_args_list[0][0][0]
        assert isinstance(first_call_arg, str)

    @pytest.mark.asyncio
    async def test_pattern_search_mixed_responses(self, mock_redis_client_str_mode, mock_serializer, mock_redis_pool):
        """
        Test pattern search handles mixed string and bytes responses gracefully.
        Edge case that shouldn't happen but we should handle it.
        """
        # Arrange
        entity1_json = '{"id": "test-001", "name": "Entity 1", "value": 100}'
        entity2_json_bytes = b'{"id": "test-002", "name": "Entity 2", "value": 200}'

        # Mock Redis responses - MIXED (unlikely but possible)
        mock_redis_client_str_mode.keys.return_value = [
            "testentity.test-001",
            "testentity.test-002",
        ]
        mock_redis_client_str_mode.get.side_effect = [entity1_json, entity2_json_bytes]  # Mixed!

        # Mock serializer to return entities
        entity1 = TestEntity(id="test-001", name="Entity 1", value=100)
        entity2 = TestEntity(id="test-002", name="Entity 2", value=200)
        mock_serializer.deserialize.side_effect = [entity1, entity2]

        # Create repository
        repo = AsyncCacheRepository[TestEntity, str](
            options=MagicMock(key_prefix="testentity", ttl=3600),
            pool=mock_redis_pool,
            serializer=mock_serializer,
        )
        repo._redis_client = mock_redis_client_str_mode

        # Act
        results = await repo.get_all_by_pattern_async("test-*")

        # Assert - should handle both types
        assert len(results) == 2
        assert results[0] == entity1
        assert results[1] == entity2

    @pytest.mark.asyncio
    async def test_pattern_search_empty_results(self, mock_redis_client_str_mode, mock_serializer, mock_redis_pool):
        """Test pattern search with no matching keys"""
        # Arrange
        mock_redis_client_str_mode.keys.return_value = []

        # Create repository
        repo = AsyncCacheRepository[TestEntity, str](
            options=MagicMock(key_prefix="testentity", ttl=3600),
            pool=mock_redis_pool,
            serializer=mock_serializer,
        )
        repo._redis_client = mock_redis_client_str_mode

        # Act
        results = await repo.get_all_by_pattern_async("nonexistent-*")

        # Assert
        assert len(results) == 0
        mock_serializer.deserialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_pattern_search_filters_non_entity_keys(self, mock_redis_client_str_mode, mock_serializer, mock_redis_pool):
        """Test that pattern search filters out non-entity keys (locks, counters, etc.)"""
        # Arrange
        entity_json = '{"id": "test-001", "name": "Entity 1", "value": 100}'

        # Mock Redis responses - includes non-entity keys
        mock_redis_client_str_mode.keys.return_value = [
            "testentity.test-001",  # Valid entity key
            "lock:testentity",  # Lock key (should be filtered)
            "counter:testentity",  # Counter key (should be filtered)
            "testentity.test-002.lock",  # Another lock (should be filtered)
        ]

        # Only the valid entity key returns data
        def get_side_effect(key):
            if key == "testentity.test-001":
                return entity_json
            return None

        mock_redis_client_str_mode.get.side_effect = get_side_effect

        # Mock serializer
        entity1 = TestEntity(id="test-001", name="Entity 1", value=100)
        mock_serializer.deserialize.return_value = entity1

        # Create repository
        repo = AsyncCacheRepository[TestEntity, str](
            options=MagicMock(key_prefix="testentity", ttl=3600),
            pool=mock_redis_pool,
            serializer=mock_serializer,
        )
        repo._redis_client = mock_redis_client_str_mode

        # Act
        results = await repo.get_all_by_pattern_async("test*")

        # Assert - should only get the valid entity
        assert len(results) == 1
        assert results[0] == entity1

        # Verify only valid entity key was processed
        assert mock_serializer.deserialize.call_count == 1

    @pytest.mark.asyncio
    async def test_pattern_search_handles_deserialization_errors(self, mock_redis_client_str_mode, mock_serializer, mock_redis_pool):
        """Test that pattern search continues processing when one entity fails to deserialize"""
        # Arrange
        entity1_json = '{"id": "test-001", "name": "Entity 1", "value": 100}'
        entity2_json = '{"invalid json'  # Malformed JSON
        entity3_json = '{"id": "test-003", "name": "Entity 3", "value": 300}'

        # Mock Redis responses
        mock_redis_client_str_mode.keys.return_value = [
            "testentity.test-001",
            "testentity.test-002",
            "testentity.test-003",
        ]
        mock_redis_client_str_mode.get.side_effect = [entity1_json, entity2_json, entity3_json]

        # Mock serializer - second one throws error
        entity1 = TestEntity(id="test-001", name="Entity 1", value=100)
        entity3 = TestEntity(id="test-003", name="Entity 3", value=300)
        mock_serializer.deserialize.side_effect = [
            entity1,
            Exception("Deserialization error"),
            entity3,
        ]

        # Create repository
        repo = AsyncCacheRepository[TestEntity, str](
            options=MagicMock(key_prefix="testentity", ttl=3600),
            pool=mock_redis_pool,
            serializer=mock_serializer,
        )
        repo._redis_client = mock_redis_client_str_mode

        # Act
        results = await repo.get_all_by_pattern_async("test-*")

        # Assert - should get 2 entities (skipped the failed one)
        assert len(results) == 2
        assert results[0] == entity1
        assert results[1] == entity3

    @pytest.mark.asyncio
    async def test_pattern_search_with_complex_pattern(self, mock_redis_client_str_mode, mock_serializer, mock_redis_pool):
        """
        Test pattern search with complex pattern (real-world scenario from bug report).
        Pattern: mozartsession.*.stg-dev-exam-ccie-test-*
        """
        # Arrange
        session1_json = '{"id": "session-001", "name": "CCIE Lab 1", "value": 1}'
        session2_json = '{"id": "session-002", "name": "CCIE Lab 2", "value": 2}'

        # Mock Redis responses with complex keys
        mock_redis_client_str_mode.keys.return_value = [
            "mozartsession.user123.stg-dev-exam-ccie-test-001",
            "mozartsession.user456.stg-dev-exam-ccie-test-002",
        ]
        mock_redis_client_str_mode.get.side_effect = [session1_json, session2_json]

        # Mock serializer
        session1 = TestEntity(id="session-001", name="CCIE Lab 1", value=1)
        session2 = TestEntity(id="session-002", name="CCIE Lab 2", value=2)
        mock_serializer.deserialize.side_effect = [session1, session2]

        # Create repository with mozartsession prefix
        repo = AsyncCacheRepository[TestEntity, str](
            options=MagicMock(key_prefix="mozartsession", ttl=3600),
            pool=mock_redis_pool,
            serializer=mock_serializer,
        )
        repo._redis_client = mock_redis_client_str_mode

        # Act
        results = await repo.get_all_by_pattern_async("*.stg-dev-exam-ccie-test-*")

        # Assert
        assert len(results) == 2
        assert results[0] == session1
        assert results[1] == session2


class TestAsyncCacheRepositoryRegressions:
    """Ensure the fix doesn't break existing functionality"""

    @pytest.mark.asyncio
    async def test_get_by_id_still_works_with_string_response(self):
        """Verify get_by_id_async continues to work after the fix"""
        # This test would need actual Redis or more complex mocking
        # Just documenting the requirement

    @pytest.mark.asyncio
    async def test_add_async_still_works(self):
        """Verify add_async continues to work after the fix"""
        # This test would need actual Redis or more complex mocking
        # Just documenting the requirement

    @pytest.mark.asyncio
    async def test_update_async_still_works(self):
        """Verify update_async continues to work after the fix"""
        # This test would need actual Redis or more complex mocking
        # Just documenting the requirement
