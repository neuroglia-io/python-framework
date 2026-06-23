"""Tests for the Redis Cache Repository module."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from unittest.mock import Mock, patch, AsyncMock
import pytest

from neuroglia.data.abstractions import Identifiable
from neuroglia.integration.cache_repository import (
    AsyncCacheRepository,
    AsyncHashCacheRepository,
    CacheRepositoryOptions,
    CacheClientPool,
    CacheRepositoryException,
)

# Check Redis availability for conditional tests
try:
    import redis.asyncio  # noqa: F401

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class User(Identifiable[str]):
    """Test entity for cache repository testing."""

    id: str
    name: str
    email: str
    age: int
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class MockJsonSerializer:
    """Mock JSON serializer for testing."""

    def serialize(self, obj) -> str:
        """Serialize object to JSON string."""
        if hasattr(obj, "__dict__"):
            # Convert dataclass to dict, handling datetime
            data = {}
            for key, value in obj.__dict__.items():
                if isinstance(value, datetime):
                    data[key] = value.isoformat()
                else:
                    data[key] = value
            return json.dumps(data)
        return json.dumps(obj)

    def deserialize(self, data: str, target_type: type):
        """Deserialize JSON string to object."""
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        obj_dict = json.loads(data)

        # Handle datetime conversion
        if "created_at" in obj_dict and isinstance(obj_dict["created_at"], str):
            try:
                obj_dict["created_at"] = datetime.fromisoformat(obj_dict["created_at"])
            except:
                obj_dict["created_at"] = datetime.now()

        # Create object using dataclass
        if target_type == User:
            return User(**obj_dict)

        return obj_dict


class TestCacheRepositoryOptions:
    """Test CacheRepositoryOptions functionality."""

    def test_options_creation(self):
        """Test creating cache repository options."""
        options = CacheRepositoryOptions[User, str](
            host="localhost",
            port=6379,
            database_name="0",
            connection_string="redis://localhost:6379/0",
            max_connections=10,
        )

        assert options.host == "localhost"
        assert options.port == 6379
        assert options.database_name == "0"
        assert options.max_connections == 10

    def test_options_defaults(self):
        """Test default values in options."""
        options = CacheRepositoryOptions[User, str](host="redis-server", port=6380)

        assert options.database_name == "0"
        assert options.max_connections == 20
        assert options.connection_string == ""


class TestCacheClientPool:
    """Test CacheClientPool functionality."""

    def test_pool_creation(self):
        """Test creating cache client pool."""
        mock_pool = Mock()
        pool = CacheClientPool[User, str](pool=mock_pool)

        assert pool.pool == mock_pool


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
@pytest.mark.asyncio
class TestAsyncCacheRepository:
    """Test AsyncCacheRepository functionality."""

    def setup_method(self):
        """Set up test dependencies."""
        self.options = CacheRepositoryOptions[User, str](
            host="localhost", port=6379, database_name="0"
        )

        # Mock Redis connection pool
        self.mock_pool = Mock()
        self.cache_pool = CacheClientPool[User, str](pool=self.mock_pool)

        # Mock serializer
        self.serializer = MockJsonSerializer()

        # Mock Redis client
        self.mock_redis_client = AsyncMock()
        self.mock_redis_client.ping = AsyncMock(return_value=True)
        self.mock_redis_client.exists = AsyncMock(return_value=1)
        self.mock_redis_client.get = AsyncMock(return_value=None)
        self.mock_redis_client.set = AsyncMock(return_value=True)
        self.mock_redis_client.delete = AsyncMock(return_value=1)
        self.mock_redis_client.keys = AsyncMock(return_value=[])
        self.mock_redis_client.aclose = AsyncMock()

    async def test_repository_creation(self):
        """Test creating a cache repository."""
        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            assert repo._options == self.options
            assert repo._redis_connection_pool == self.cache_pool
            assert repo._serializer == self.serializer

    async def test_context_manager_entry_exit(self):
        """Test async context manager functionality."""
        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            async with repo:
                assert repo._started is True
                self.mock_redis_client.ping.assert_called_once()

            assert repo._started is False

    async def test_ping_success(self):
        """Test successful ping operation."""
        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.ping()

            assert result is True
            self.mock_redis_client.ping.assert_called_once()

    async def test_ping_failure(self):
        """Test ping failure handling."""
        self.mock_redis_client.ping.side_effect = Exception("Connection failed")

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.ping()

            assert result is False

    async def test_contains_async_true(self):
        """Test contains_async when entity exists."""
        self.mock_redis_client.exists.return_value = 1

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.contains_async("test-id")

            assert result is True
            self.mock_redis_client.exists.assert_called_once_with("testuser.test-id")

    async def test_contains_async_false(self):
        """Test contains_async when entity doesn't exist."""
        self.mock_redis_client.exists.return_value = 0

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.contains_async("test-id")

            assert result is False

    async def test_get_async_success(self):
        """Test successful get_async operation."""
        test_user = User(id="test-id", name="John", email="john@example.com", age=30)
        user_json = self.serializer.serialize(test_user)
        self.mock_redis_client.get.return_value = user_json.encode("utf-8")

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.get_async("test-id")

            assert result is not None
            assert result.id == "test-id"
            assert result.name == "John"
            assert result.email == "john@example.com"
            self.mock_redis_client.get.assert_called_once_with("testuser.test-id")

    async def test_get_async_not_found(self):
        """Test get_async when entity not found."""
        self.mock_redis_client.get.return_value = None

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.get_async("nonexistent-id")

            assert result is None

    async def test_add_async_success(self):
        """Test successful add_async operation."""
        test_user = User(id="test-id", name="John", email="john@example.com", age=30)

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.add_async(test_user)

            assert result == test_user
            self.mock_redis_client.set.assert_called_once()

    async def test_update_async_success(self):
        """Test successful update_async operation."""
        test_user = User(id="test-id", name="John Updated", email="john@example.com", age=31)

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.update_async(test_user)

            assert result == test_user
            self.mock_redis_client.set.assert_called_once()

    async def test_remove_async_success(self):
        """Test successful remove_async operation."""
        self.mock_redis_client.delete.return_value = 1

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            await repo.remove_async("test-id")

            self.mock_redis_client.delete.assert_called_once_with("testuser.test-id")

    async def test_remove_async_not_found(self):
        """Test remove_async when entity not found."""
        self.mock_redis_client.delete.return_value = 0

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            # Should not raise exception even if entity not found
            await repo.remove_async("nonexistent-id")

            self.mock_redis_client.delete.assert_called_once()

    async def test_get_all_by_pattern_async(self):
        """Test get_all_by_pattern_async operation."""
        test_users = [
            User(id="user-1", name="John", email="john@example.com", age=30),
            User(id="user-2", name="Jane", email="jane@example.com", age=25),
        ]

        # Mock keys and get operations
        self.mock_redis_client.keys.return_value = [b"testuser.user-1", b"testuser.user-2"]
        self.mock_redis_client.get.side_effect = [
            self.serializer.serialize(test_users[0]).encode("utf-8"),
            self.serializer.serialize(test_users[1]).encode("utf-8"),
        ]

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            results = await repo.get_all_by_pattern_async("user-*")

            assert len(results) == 2
            assert results[0].name == "John"
            assert results[1].name == "Jane"

    async def test_distributed_lock_set_if_not_exists(self):
        """Test set_if_not_exists for distributed locking."""
        self.mock_redis_client.set.return_value = True

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.set_if_not_exists("lock-key", "lock-value", 60)

            assert result is True
            self.mock_redis_client.set.assert_called_once_with(
                "lock-key", "lock-value", nx=True, ex=60
            )

    async def test_get_raw(self):
        """Test get_raw operation."""
        self.mock_redis_client.get.return_value = b"raw-value"

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.get_raw("raw-key")

            assert result == "raw-value"

    async def test_delete_raw(self):
        """Test delete_raw operation."""
        self.mock_redis_client.delete.return_value = 1

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.delete_raw("raw-key")

            assert result is True

    async def test_execute_script(self):
        """Test Lua script execution."""
        self.mock_redis_client.eval.return_value = "script-result"

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.execute_script("return 'test'", ["key1"], ["arg1"])

            assert result == "script-result"
            self.mock_redis_client.eval.assert_called_once()

    async def test_close(self):
        """Test close operation."""
        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            await repo.close()

            self.mock_redis_client.aclose.assert_called_once()
            assert repo._started is False

    def test_key_generation(self):
        """Test Redis key generation."""
        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncCacheRepository(self.options, self.cache_pool, self.serializer)

            # Test basic key generation
            key = repo._get_key("test-id")
            assert key == "testuser.test-id"

            # Test key with existing prefix
            key_with_prefix = repo._get_key("testuser.existing-id")
            assert key_with_prefix == "testuser.existing-id"


@pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available")
@pytest.mark.asyncio
class TestAsyncHashCacheRepository:
    """Test AsyncHashCacheRepository functionality."""

    def setup_method(self):
        """Set up test dependencies."""
        self.options = CacheRepositoryOptions[User, str](host="localhost", port=6379)

        self.mock_pool = Mock()
        self.cache_pool = CacheClientPool[User, str](pool=self.mock_pool)
        self.serializer = MockJsonSerializer()

        # Mock Redis client with hash operations
        self.mock_redis_client = AsyncMock()
        self.mock_redis_client.ping = AsyncMock(return_value=True)
        self.mock_redis_client.hexists = AsyncMock(return_value=True)
        self.mock_redis_client.hgetall = AsyncMock(return_value={})
        self.mock_redis_client.hget = AsyncMock(return_value=None)
        self.mock_redis_client.hset = AsyncMock(return_value=1)
        self.mock_redis_client.delete = AsyncMock(return_value=1)
        self.mock_redis_client.aclose = AsyncMock()

    async def test_hash_contains_async(self):
        """Test hash-based contains_async."""
        self.mock_redis_client.hexists.return_value = True

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncHashCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.contains_async("test-id")

            assert result is True
            self.mock_redis_client.hexists.assert_called_once_with("testuser.test-id", "id")

    async def test_hash_get_async_success(self):
        """Test successful hash get_async."""
        hash_data = {
            b"id": b"test-id",
            b"name": b"John",
            b"email": b"john@example.com",
            b"age": b"30",
        }
        self.mock_redis_client.hgetall.return_value = hash_data

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncHashCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.get_async("test-id")

            assert result is not None
            assert result.id == "test-id"
            assert result.name == "John"

    async def test_hash_hget_async(self):
        """Test hash field get operation."""
        self.mock_redis_client.hget.return_value = b"John"

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncHashCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.hget_async("test-id", "name")

            assert result == "John"
            self.mock_redis_client.hget.assert_called_once_with("testuser.test-id", "name")

    async def test_hash_add_async(self):
        """Test hash add operation."""
        test_user = User(id="test-id", name="John", email="john@example.com", age=30)

        with patch(
            "neuroglia.integration.cache_repository.redis.Redis",
            return_value=self.mock_redis_client,
        ):
            repo = AsyncHashCacheRepository(self.options, self.cache_pool, self.serializer)

            result = await repo.add_async(test_user)

            assert result == test_user
            self.mock_redis_client.hset.assert_called_once()


class TestCacheRepositoryConfiguration:
    """Test cache repository configuration."""

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not available for configuration test")
    def test_configure_success(self):
        """Test successful cache repository configuration."""
        # Mock builder
        mock_builder = Mock()
        mock_builder.services = Mock()
        mock_builder.services.try_add_singleton = Mock()
        mock_builder.services.add_scoped = Mock()

        # Mock settings
        mock_builder.settings = Mock()
        mock_builder.settings.connection_strings = {"redis": "redis://localhost:6379"}
        mock_builder.settings.redis_max_connections = 10

        with patch(
            "neuroglia.integration.cache_repository.redis.ConnectionPool"
        ) as mock_connection_pool:
            # Mock connection pool
            mock_pool = Mock()
            mock_connection_pool.from_url.return_value = mock_pool

            result = AsyncCacheRepository.configure(mock_builder, User, str)

            assert result == mock_builder
            mock_builder.services.try_add_singleton.assert_called()
            mock_builder.services.add_scoped.assert_called()

    def test_configure_missing_redis(self):
        """Test configuration failure when Redis not available."""
        mock_builder = Mock()

        with patch("neuroglia.integration.cache_repository.REDIS_AVAILABLE", False):
            with pytest.raises(CacheRepositoryException) as exc_info:
                AsyncCacheRepository.configure(mock_builder, User, str)

            assert "Redis is required" in str(exc_info.value)

    def test_configure_missing_connection_string(self):
        """Test configuration failure with missing connection string."""
        mock_builder = Mock()
        mock_builder.settings = Mock()
        mock_builder.settings.connection_strings = {}

        with patch("neuroglia.integration.cache_repository.REDIS_AVAILABLE", True):
            with pytest.raises(CacheRepositoryException) as exc_info:
                AsyncCacheRepository.configure(mock_builder, User, str)

            assert "Missing 'redis' connection string" in str(exc_info.value)


@pytest.mark.skipif(REDIS_AVAILABLE, reason="Testing without Redis")
class TestCacheRepositoryWithoutRedis:
    """Test cache repository behavior when Redis is not available."""

    def test_repository_creation_without_redis(self):
        """Test repository creation fails without Redis."""
        options = CacheRepositoryOptions[User, str](host="localhost", port=6379)
        cache_pool = CacheClientPool[User, str](pool=Mock())
        serializer = MockJsonSerializer()

        with pytest.raises(CacheRepositoryException) as exc_info:
            AsyncCacheRepository(options, cache_pool, serializer)

        assert "Redis is required" in str(exc_info.value)
