"""
Redis-based cache repository implementation for the Neuroglia framework.

This module provides comprehensive Redis caching capabilities with async operations,
distributed locks, and connection pooling.

Uses parameterized generic types in constructor parameters (requires neuroglia v0.4.3+).
"""

import asyncio
import json
import logging
import urllib.parse
from dataclasses import dataclass
from typing import Any, Generic, Optional

from neuroglia.data.abstractions import TEntity, TKey
from neuroglia.data.infrastructure.abstractions import Repository

# Import Redis components
try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore
    REDIS_AVAILABLE = False

try:
    from neuroglia.hosting.abstractions import ApplicationBuilderBase
    from neuroglia.serialization.json import JsonSerializer
except ImportError:
    ApplicationBuilderBase = None  # type: ignore
    JsonSerializer = None  # type: ignore

log = logging.getLogger(__name__)


class CacheRepositoryException(Exception):
    """Exception raised by cache repository operations."""


@dataclass
class CacheRepositoryOptions(Generic[TEntity, TKey]):
    """
    Represents the options used to configure a Redis cache repository.

    Parameterized by entity and key types for type safety.
    """

    host: str
    """Gets the host name of the Redis cluster to use."""

    port: int
    """Gets the port number of the Redis cluster to use."""

    database_name: str = "0"
    """Gets the name of the Redis database to use."""

    connection_string: str = ""
    """Gets the full connection string. Optional."""

    max_connections: int = 20
    """Gets the maximum number of connections in the pool."""


@dataclass
class CacheClientPool(Generic[TEntity, TKey]):
    """
    Redis connection pool wrapper.

    Parameterized by entity and key types for type safety.
    """

    pool: Any  # redis.ConnectionPool when available
    """The redis connection pool to use for the specified entity and key types."""


class AsyncCacheRepository(Generic[TEntity, TKey], Repository[TEntity, TKey]):
    """
    Represents an async Redis cache repository using the asynchronous Redis client.

    Uses parameterized generic types (v0.4.3+) for full type safety.
    Constructor parameters use type variables that are substituted with concrete types
    during dependency injection.
    """

    def __init__(
        self,
        options: CacheRepositoryOptions[TEntity, TKey],  # Parameterized with type variables!
        redis_connection_pool: CacheClientPool[TEntity, TKey],  # Parameterized with type variables!
        serializer: "JsonSerializer",
    ):
        """Initialize a new Redis cache repository."""
        if not REDIS_AVAILABLE:
            raise CacheRepositoryException("Redis is required for cache repository operations. " "Install it with: pip install redis")

        self._options = options
        self._redis_connection_pool = redis_connection_pool
        self._serializer = serializer
        self._entity_type_name = TEntity.__name__ if hasattr(TEntity, "__name__") else "entity"
        self._key_type_name = TKey.__name__ if hasattr(TKey, "__name__") else "key"

        # Initialize Redis client using the connection pool
        self._redis_client = redis.Redis(connection_pool=self._redis_connection_pool.pool)

        # Add a lock to prevent race conditions during pattern searches
        self._search_lock = asyncio.Lock()
        self._started = False

    async def __aenter__(self):
        """Async context manager entry."""
        try:
            # Verify connection health
            await self._redis_client.ping()
            self._started = True
            log.debug(f"Cache repository connected to Redis: {self._options.host}:{self._options.port}")
        except Exception as ex:
            log.error(f"Error connecting to Redis cache: {ex}")
            raise CacheRepositoryException(f"Failed to connect to Redis cache: {ex}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Let the connection pool manage connections
        self._started = False

    async def ping(self) -> bool:
        """Test Redis connection health."""
        try:
            result = await self._redis_client.ping()
            return bool(result)
        except Exception as ex:
            log.error(f"Redis ping failed: {ex}")
            return False

    def info(self) -> dict:
        """Get Redis server information."""
        try:
            return self._redis_client.info()
        except Exception as ex:
            log.error(f"Failed to get Redis info: {ex}")
            return {}

    async def contains_async(self, id: TKey) -> bool:
        """Determine whether the repository contains an entity with the specified id."""
        try:
            key = self._get_key(id)
            log.debug(f"Checking existence of key: {key}")
            result = await self._redis_client.exists(key)
            return bool(result)
        except Exception as ex:
            log.error(f"Error checking key existence for {id}: {ex}")
            return False

    async def get_async(self, id: TKey) -> Optional[TEntity]:
        """Get the entity with the specified id, if any."""
        try:
            key = self._get_key(id)
            data = await self._redis_client.get(key)

            if data is None:
                log.debug(f"No data found for key: {key}")
                return None

            # Pass data directly to serializer - it handles bytes/str conversion
            # The serializer (JsonSerializer.deserialize) expects bytes and will decode internally
            entity = self._serializer.deserialize(data, self._get_entity_type())
            log.debug(f"Retrieved entity for key: {key}")
            return entity

        except Exception as ex:
            log.error(f"Error retrieving entity with id {id}: {ex}")
            return None

    async def add_async(self, entity: TEntity) -> TEntity:
        """Add the specified entity to the cache."""
        try:
            key = self._get_key(entity.id)
            data = self._serializer.serialize(entity)

            await self._redis_client.set(key, data)
            log.debug(f"Added entity to cache with key: {key}")
            return entity

        except Exception as ex:
            log.error(f"Error adding entity to cache: {ex}")
            raise CacheRepositoryException(f"Failed to add entity to cache: {ex}")

    async def update_async(self, entity: TEntity) -> TEntity:
        """Update the specified entity in the cache."""
        # For Redis cache, update is the same as add
        return await self.add_async(entity)

    async def remove_async(self, id: TKey) -> None:
        """Remove the entity with the specified key from the cache."""
        try:
            key = self._get_key(id)
            result = await self._redis_client.delete(key)

            if result:
                log.debug(f"Removed entity from cache with key: {key}")
            else:
                log.debug(f"No entity found to remove with key: {key}")

        except Exception as ex:
            log.error(f"Error removing entity with id {id}: {ex}")
            raise CacheRepositoryException(f"Failed to remove entity from cache: {ex}")

    async def get_all_by_pattern_async(self, pattern: str) -> list[TEntity]:
        """Get all entities matching the specified key pattern."""
        try:
            async with self._search_lock:
                entities = await self._search_by_key_pattern_async(pattern)
                results = []

                for entity_data in entities:
                    try:
                        # Pass data directly to serializer - it handles bytes/str conversion
                        # _search_by_key_pattern_async ensures data is bytes
                        entity = self._serializer.deserialize(entity_data, self._get_entity_type())
                        results.append(entity)
                    except Exception as ex:
                        log.warning(f"Failed to deserialize entity data: {ex}")
                        continue

                log.debug(f"Retrieved {len(results)} entities for pattern: {pattern}")
                return results

        except Exception as ex:
            log.error(f"Error searching entities with pattern {pattern}: {ex}")
            return []

    async def _search_by_key_pattern_async(self, pattern: str) -> list[Any]:
        """Search for keys matching the specified pattern and return their values."""
        try:
            # Ensure pattern has wildcards
            if not pattern.startswith("*"):
                pattern = f"*{pattern}"
            if not pattern.endswith("*"):
                pattern = f"{pattern}*"

            keys = await self._redis_client.keys(pattern)
            if not keys:
                return []

            entities = []
            entity_prefix = self._get_key_prefix()

            for key in keys:
                # Decode key if it's bytes
                if isinstance(key, bytes):
                    key = key.decode("utf-8")

                # Filter to only include entity keys (avoid locks, counters, etc.)
                if not key.startswith(entity_prefix):
                    log.debug(f"Skipping non-entity key: {key}")
                    continue

                entity_data = await self._redis_client.get(key)
                if entity_data:
                    # Ensure entity_data is bytes for consistent handling
                    # Redis client may return str (decode_responses=True) or bytes (decode_responses=False)
                    if isinstance(entity_data, str):
                        entity_data = entity_data.encode("utf-8")
                    entities.append(entity_data)

            return entities

        except Exception as ex:
            log.error(f"Error searching by pattern {pattern}: {ex}")
            return []

    def _get_entity_type(self) -> type:
        """Get the entity type from generic arguments."""
        try:
            return self.__orig_class__.__args__[0]  # type: ignore
        except Exception:
            # Fallback to a generic object type
            return object

    def _get_key_prefix(self) -> str:
        """Get the key prefix for entities of this type."""
        try:
            entity_type = self._get_entity_type()
            return entity_type.__name__.lower()
        except Exception:
            return self._entity_type_name.lower()

    def _get_key(self, id: TKey) -> str:
        """Generate the full Redis key for an entity ID."""
        key_prefix = self._get_key_prefix()
        id_str = str(id)

        # If the id already has the prefix, return as-is
        if id_str.startswith(f"{key_prefix}."):
            return id_str

        return f"{key_prefix}.{id_str}"

    # Distributed lock support methods
    async def set_if_not_exists(self, key: str, value: str, expiry_seconds: int) -> bool:
        """
        Set a key-value pair only if the key doesn't exist, with expiration.
        Returns True if the key was set, False if it already existed.
        """
        try:
            result = await self._redis_client.set(key, value, nx=True, ex=expiry_seconds)
            return bool(result)
        except Exception as ex:
            log.error(f"Error in set_if_not_exists for key {key}: {ex}")
            return False

    async def get_raw(self, key: str) -> Optional[str]:
        """Get a raw value by key."""
        try:
            result = await self._redis_client.get(key)
            return result.decode("utf-8") if result else None
        except Exception as ex:
            log.error(f"Error getting raw key {key}: {ex}")
            return None

    async def delete_raw(self, key: str) -> bool:
        """Delete a raw key. Returns True if the key was deleted, False otherwise."""
        try:
            result = await self._redis_client.delete(key)
            return bool(result)
        except Exception as ex:
            log.error(f"Error deleting raw key {key}: {ex}")
            return False

    async def execute_script(self, script: str, keys: list[str], args: list[str]) -> Any:
        """Execute a Lua script with the given keys and arguments."""
        try:
            result = await self._redis_client.eval(script, len(keys), *keys, *args)
            return result
        except Exception as ex:
            log.error(f"Error executing Lua script: {ex}")
            return None

    async def close(self):
        """Close the Redis connection."""
        try:
            await self._redis_client.aclose()
            self._started = False
            log.debug("Cache repository connection closed")
        except Exception as ex:
            log.error(f"Error closing cache repository connection: {ex}")

    @staticmethod
    def configure(
        builder: "ApplicationBuilderBase",
        entity_type: type,
        key_type: type,
        connection_string_name: str = "redis",
    ) -> "ApplicationBuilderBase":
        """
        Configure the cache repository services in the application builder.

        Registers parameterized singleton services that the DI container can resolve
        with concrete type arguments (requires neuroglia v0.4.3+ with type variable substitution).

        Args:
            builder: The application builder to configure
            entity_type: The concrete entity type (e.g., User)
            key_type: The concrete key type (e.g., str)
            connection_string_name: Name of the Redis connection string in settings

        Returns:
            The configured application builder
        """
        try:
            if not REDIS_AVAILABLE:
                raise CacheRepositoryException("Redis is required for cache repository. " "Install it with: pip install redis")

            # Get Redis connection string from settings
            if not hasattr(builder, "settings"):
                raise CacheRepositoryException("Application builder missing settings")

            connection_strings = getattr(builder.settings, "connection_strings", {})
            connection_string = connection_strings.get(connection_string_name)

            if not connection_string:
                raise CacheRepositoryException(f"Missing '{connection_string_name}' connection string in application settings. " f"Expected format: redis://host:port")

            # Parse Redis connection URL
            parsed_url = urllib.parse.urlparse(connection_string)
            redis_host = parsed_url.hostname
            redis_port = parsed_url.port or 6379
            database_name = parsed_url.path.lstrip("/") or "0"

            if not redis_host:
                raise CacheRepositoryException(f"Invalid Redis connection string '{connection_string}': missing hostname")

            # Build full database URL
            redis_database_url = f"{connection_string.rstrip('/')}/{database_name}"

            # Get max connections from settings or use default
            max_connections = getattr(builder.settings, "redis_max_connections", 20)

            # Create connection pool
            pool = redis.ConnectionPool.from_url(
                redis_database_url,
                max_connections=max_connections,
                decode_responses=False,  # We'll handle decoding manually
            )

            # Register PARAMETERIZED singletons (v0.4.3+ with type variable substitution)
            # The DI container will substitute TEntity/TKey with entity_type/key_type
            options_instance = CacheRepositoryOptions[entity_type, key_type](
                host=redis_host,
                port=redis_port,
                database_name=database_name,
                connection_string=redis_database_url,
                max_connections=max_connections,
            )

            cache_pool_instance = CacheClientPool[entity_type, key_type](pool=pool)

            # Register parameterized singleton services
            # DI will resolve CacheRepositoryOptions[User, str] as the specific type
            builder.services.add_singleton(CacheRepositoryOptions[entity_type, key_type], singleton=options_instance)
            builder.services.add_singleton(CacheClientPool[entity_type, key_type], singleton=cache_pool_instance)

            # Register the parameterized repository types
            builder.services.add_scoped(
                AsyncCacheRepository[entity_type, key_type],
                AsyncCacheRepository[entity_type, key_type],
            )
            builder.services.add_scoped(
                Repository[entity_type, key_type],
                AsyncCacheRepository[entity_type, key_type],
            )

            log.info(f"Redis cache repository configured for {entity_type.__name__}[{key_type.__name__}] at {redis_host}:{redis_port}")
            return builder

        except Exception as ex:
            log.error(f"Error configuring cache repository: {ex}")
            raise CacheRepositoryException(f"Failed to configure cache repository: {ex}")


class AsyncHashCacheRepository(AsyncCacheRepository[TEntity, TKey]):
    """
    Redis Hash-based cache repository implementation.

    Stores entities as Redis hashes, which can be more efficient for entities
    with many fields that are accessed independently.
    """

    async def contains_async(self, id: TKey) -> bool:
        """Determine whether the repository contains a hash entity with the specified id."""
        try:
            key = self._get_key(id)
            result = await self._redis_client.hexists(key, "id")
            return bool(result)
        except Exception as ex:
            log.error(f"Error checking hash key existence for {id}: {ex}")
            return False

    async def get_async(self, id: TKey) -> Optional[TEntity]:
        """
        Get the hash entity with the specified id, if any.

        Note: The resulting entity may not have nested dictionaries,
        as Redis Hash does not support nested structures natively.
        """
        try:
            key = self._get_key(id)
            data = await self._redis_client.hgetall(key)

            if not data:
                log.debug(f"No hash data found for key: {key}")
                return None

            # Convert Redis hash data to entity
            entity_dict = {}
            for field, value in data.items():
                # Decode bytes to strings
                if isinstance(field, bytes):
                    field = field.decode("utf-8")
                if isinstance(value, bytes):
                    value = value.decode("utf-8")

                # Try to parse JSON values
                try:
                    entity_dict[field] = json.loads(value)
                except json.JSONDecodeError:
                    entity_dict[field] = value

            # Serialize the dict back to JSON for the deserializer
            entity_json = json.dumps(entity_dict)
            entity = self._serializer.deserialize(entity_json, self._get_entity_type())

            log.debug(f"Retrieved hash entity for key: {key}")
            return entity

        except Exception as ex:
            log.error(f"Error retrieving hash entity with id {id}: {ex}")
            return None

    async def hget_async(self, id: TKey, field: str) -> Optional[Any]:
        """Get the value of a specific field from the hash entity."""
        try:
            key = self._get_key(id)
            result = await self._redis_client.hget(key, field)

            if result is None:
                return None

            if isinstance(result, bytes):
                result = result.decode("utf-8")

            # Try to parse as JSON
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return result

        except Exception as ex:
            log.error(f"Error getting hash field {field} for id {id}: {ex}")
            return None

    async def add_async(self, entity: TEntity) -> TEntity:
        """Add the specified entity as a Redis hash."""
        try:
            key = self._get_key(entity.id)
            data = self._serializer.serialize(entity)

            # Convert to dictionary
            if isinstance(data, (str, bytes)):
                entity_dict = json.loads(data)
            else:
                entity_dict = data

            # Convert complex values to JSON strings for Redis hash storage
            hash_data = {}
            for field, value in entity_dict.items():
                if isinstance(value, (dict, list)):
                    hash_data[field] = json.dumps(value)
                else:
                    hash_data[field] = str(value)

            await self._redis_client.hset(key, mapping=hash_data)
            log.debug(f"Added hash entity to cache with key: {key}")
            return entity

        except Exception as ex:
            log.error(f"Error adding hash entity to cache: {ex}")
            raise CacheRepositoryException(f"Failed to add hash entity to cache: {ex}")

    async def update_async(self, entity: TEntity) -> TEntity:
        """Update the specified hash entity in the cache."""
        return await self.add_async(entity)

    async def remove_async(self, id: TKey) -> None:
        """Remove the hash entity with the specified key from the cache."""
        try:
            key = self._get_key(id)
            result = await self._redis_client.delete(key)

            if result:
                log.debug(f"Removed hash entity from cache with key: {key}")
            else:
                log.debug(f"No hash entity found to remove with key: {key}")

        except Exception as ex:
            log.error(f"Error removing hash entity with id {id}: {ex}")
            raise CacheRepositoryException(f"Failed to remove hash entity from cache: {ex}")
