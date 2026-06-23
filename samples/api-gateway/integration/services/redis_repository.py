import logging
import urllib.parse
from dataclasses import dataclass
from typing import Any, Generic, Optional

import redis.asyncio as redis
from neuroglia.data.abstractions import TEntity, TKey
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.serialization.json import JsonSerializer

log = logging.getLogger(__name__)

from typing import Generic


class RedisClientException(Exception):
    pass


@dataclass
class RedisRepositoryOptions(Generic[TEntity, TKey]):
    """Represents the options used to configure a Redis repository"""

    host: str
    """ Gets the host name of the Redis cluster to use """

    port: int
    """ Gets the port number of the Redis cluster to use """

    database_name: str
    """ Gets the name of the Redis database to use """

    connection_string: str = ""
    """ Gets the full connection string. Optional."""


@dataclass
class RedisClientPool(Generic[TEntity, TKey]):
    """Generic Class to specialize a redis.Redis client to the TEntity, TKey."""

    pool: redis.ConnectionPool
    """The redis connection pool to use for the given TEntity, TKey pair."""


class RedisRepository(Generic[TEntity, TKey], Repository[TEntity, TKey]):
    """Represents a Redis implementation of the repository class using the synchronous Redis client"""

    def __init__(self, options: RedisRepositoryOptions[TEntity, TKey], redis_connection_pool: RedisClientPool[TEntity, TKey], serializer: JsonSerializer):
        """Initializes a new Redis repository"""
        self._options = options
        self._redis_connection_pool = redis_connection_pool
        self._serializer = serializer
        self._entity_type = TEntity.__name__
        self._key_type = TKey.__name__

    _options: RedisRepositoryOptions[TEntity, TKey]
    """ Gets the options used to configure the Redis repository """

    _entity_type: type[TEntity]
    """ Gets the type of the Entity to persist """

    _key_type: type[TKey]
    """ Gets the type of the Entity's Key to persist """

    _redis_connection_pool: RedisClientPool

    _redis_client: redis.Redis
    """ Gets the Redis Client """

    _serializer: JsonSerializer
    """ Gets the service used to serialize/deserialize to/from JSON """

    async def __aenter__(self):
        self._redis_client = redis.Redis(connection_pool=self._redis_connection_pool.pool)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._redis_client.close()

    def ping(self) -> Any:
        return self._redis_client.ping()

    def info(self) -> Any:
        return self._redis_client.info()

    async def contains_async(self, id: TKey) -> bool:
        """Determines whether or not the repository contains an entity with the specified id"""
        key = self._get_key(id)
        return await self._redis_client.exists(key)

    async def get_async(self, id: TKey) -> Optional[TEntity]:
        """Gets the entity with the specified id, if any"""
        key = self._get_key(id)
        data = await self._redis_client.get(key)
        if data is None:
            return None
        return self._serializer.deserialize(data, self._get_entity_type())

    async def add_async(self, entity: TEntity) -> TEntity:
        """Adds the specified entity"""
        key = self._get_key(entity.id)
        data = self._serializer.serialize(entity)
        await self._redis_client.set(key, data)
        return entity

    async def update_async(self, entity: TEntity) -> TEntity:
        """Persists the changes that were made to the specified entity"""
        return await self.add_async(entity)  # Update is essentially an add with new data

    async def remove_async(self, id: TKey) -> None:
        """Removes the entity with the specified key"""
        key = self._get_key(id)
        await self._redis_client.delete(key)

    def _get_entity_type(self) -> str:
        return self.__orig_class__.__args__[0]

    def _get_key(self, id: TKey) -> str:
        return str(id)

    async def close(self):
        await self._redis_client.aclose()

    @staticmethod
    def configure(builder: ApplicationBuilderBase, entity_type: type, key_type: type, database_name: int) -> ApplicationBuilderBase:
        connection_string_name = "redis"
        connection_string = builder.settings.connection_strings.get(connection_string_name, None)
        if connection_string is None:
            raise Exception(f"Missing '{connection_string_name}' connection string in application settings (missing env var CONNECTION_STRINGS: {'redis': 'redis://redis:6379'} ?)")

        redis_database_url = f"{connection_string}/{database_name}"
        parsed_url = urllib.parse.urlparse(connection_string)
        redis_host = parsed_url.hostname
        redis_port = parsed_url.port
        if any(item is None for item in [redis_host, redis_port, database_name]):
            raise Exception(f"Issue parsing the connection_string '{connection_string}': host:{redis_host} port:{redis_port}")

        pool = redis.ConnectionPool.from_url(redis_database_url, max_connections=10)
        # redis_client = redis.Redis.from_pool(pool)
        builder.services.try_add_singleton(RedisRepositoryOptions[entity_type, key_type], singleton=RedisRepositoryOptions[entity_type, key_type](host=redis_host, port=redis_port, database_name=str(database_name), connection_string=redis_database_url))
        builder.services.try_add_singleton(RedisClientPool[entity_type, key_type], singleton=RedisClientPool(pool=pool))
        builder.services.try_add_scoped(RedisRepository[entity_type, key_type], RedisRepository[entity_type, key_type])
        builder.services.try_add_scoped(Repository[entity_type, key_type], RedisRepository[entity_type, key_type])
        return builder
