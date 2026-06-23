import json
import logging
import urllib.parse
from dataclasses import dataclass
from typing import Any, Awaitable, Generic, Optional

import redis.asyncio as redis
from neuroglia.data.abstractions import TEntity, TKey
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.serialization.json import JsonSerializer

from integration import IntegrationException

log = logging.getLogger(__name__)


class CacheDbClientException(Exception):
    pass


@dataclass
class CacheRepositoryOptions(Generic[TEntity, TKey]):
    """Represents the options used to configure a Redis repository"""

    host: str
    """ Gets the host name of the Redis cluster to use """

    port: int
    """ Gets the port number of the Redis cluster to use """

    database_name: str = "0"
    """ Gets the name of the Redis database to use """

    connection_string: str = ""
    """ Gets the full connection string. Optional."""


@dataclass
class CacheClientPool(Generic[TEntity, TKey]):
    """Generic Class to specialize a redis.Redis client to the TEntity, TKey."""

    pool: redis.ConnectionPool
    """The redis connection pool to use for the given TEntity, TKey pair."""


class AsyncCacheRepository(Generic[TEntity, TKey], Repository[TEntity, TKey]):
    """Represents a async interface of the redis Repository using the synchronous Redis client"""

    def __init__(self, options: CacheRepositoryOptions[TEntity, TKey], redis_connection_pool: CacheClientPool[TEntity, TKey], serializer: JsonSerializer):
        """Initializes a new Redis repository"""
        self._options = options
        self._redis_connection_pool = redis_connection_pool
        self._serializer = serializer
        self._entity_type = TEntity.__name__
        self._key_type = TKey.__name__

    _options: CacheRepositoryOptions[TEntity, TKey]
    """ Gets the options used to configure the Redis repository """

    _entity_type: type[TEntity]
    """ Gets the type of the Entity to persist """

    _key_type: type[TKey]
    """ Gets the type of the Entity's Key to persist """

    _redis_connection_pool: CacheClientPool

    _redis_client: redis.Redis
    """ Gets the Redis Client """

    _serializer: JsonSerializer
    """ Gets the service used to serialize/deserialize to/from JSON """

    async def __aenter__(self):
        try:
            self._redis_client = redis.Redis(connection_pool=self._redis_connection_pool.pool)

        except (redis.ConnectionError, redis.ResponseError) as er:
            log.error(f"Error connecting to Cache DB: {er}")
            raise IntegrationException(f"Error connecting to Cache DB: {er}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            await self._redis_client.close()

        except (redis.ConnectionError, redis.ResponseError) as er:
            log.error(f"Error connecting to Cache DB: {er} {exc_type}, {exc_val}, {exc_tb}")
            raise IntegrationException(f"Error connecting to Cache DB: {er} {exc_type}, {exc_val}, {exc_tb}")

    async def ping(self) -> Any:
        return await self._redis_client.ping()

    def info(self) -> Any:
        return self._redis_client.info()

    async def contains_async(self, id: TKey) -> bool:
        """Determines whether or not the repository contains an entity with the specified id"""
        # key = f"{self._get_key_prefix()}.{self._get_key(id)}"
        key = self._get_key(id)
        log.debug(f"Searching for {key}")
        return await self._redis_client.exists(key)

    def _get_entity_type(self) -> str:
        return self.__orig_class__.__args__[0]

    def _get_key_prefix(self) -> str:
        return self._get_entity_type().__qualname__.split(".")[-1].lower()  # type: ignore

    def _get_key(self, id: TKey) -> str:
        key_prefix = self._get_key_prefix()
        if str(id).startswith(key_prefix):
            return str(id)
        return f"{key_prefix}.{str(id)}"

    async def close(self):
        await self._redis_client.aclose()


class AsyncStringCacheRepository(AsyncCacheRepository[TEntity, TKey]):
    """Represents an implementation of the AsyncCacheRepository for string objects."""

    def __init__(self, options: CacheRepositoryOptions[TEntity, TKey], redis_connection_pool: CacheClientPool[TEntity, TKey], serializer: JsonSerializer):
        """Initializes a new Cache repository"""
        super().__init__(options, redis_connection_pool, serializer)

    async def get_async(self, id: TKey) -> Optional[TEntity]:
        """Gets the entity with the specified id, if any"""
        # if "*" not in str(id):
        #     key = self._get_key(id)
        #     data = await self._redis_client.get(key)
        # else:
        #     key = str(id)
        #     data = await self.get_by_key_pattern_async(key)
        # if data is None:
        #     return None
        # return self._serializer.deserialize(data, self._get_entity_type())
        if "." not in str(id):
            data = await self._get_one_by_key_pattern_async(f"*{id}*")
        else:
            data = await self._get_one_by_redis_key(str(id))
        if data is None:
            return None
        return self._serializer.deserialize(data, self._get_entity_type())

    async def get_all_by_key_pattern_async(self, key: str) -> list[TEntity]:
        """Gets all entities with the specified id pattern"""
        entities = await self._search_by_key_pattern_async(key)
        return [self._serializer.deserialize(entity, self._get_entity_type()) for entity in entities]

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
        if "." not in str(id):
            entity = await self._get_one_by_key_pattern_async(f"*{id}")
            key = entity.id if entity else self._get_key(id)
        else:
            key = self._get_key(id)
        await self._redis_client.delete(key)

    async def _get_one_by_key_pattern_async(self, key: str) -> Optional[Any]:
        """Gets the entity with the specified id pattern, if any"""
        entities = await self._search_by_key_pattern_async(key)
        if len(entities) != 1:
            raise CacheDbClientException(f"Expected 1 entity, but found {len(entities)}")
        return entities[0]

    async def _search_by_key_pattern_async(self, pattern: str) -> list[Any]:
        pattern = f"*{pattern}" if pattern[0] != "*" else pattern
        pattern = f"{pattern}*" if pattern[-1] != "*" else pattern
        keys = await self._redis_client.keys(pattern)
        if not keys:
            return []
        entities = []
        for key in keys:
            # log.debug(f"{key} {type(key)}")
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            entity = await self._redis_client.get(key)
            if entity:
                entities.append(entity)
        return entities

    async def _get_one_by_redis_key(self, key: str) -> Optional[TEntity]:
        """Gets the entity with the specified id pattern, if any"""
        return await self._redis_client.get(key)

    @staticmethod
    def configure(builder: ApplicationBuilderBase, entity_type: type, key_type: type) -> ApplicationBuilderBase:
        connection_string_name = "redis"
        connection_string = builder.settings.connection_strings.get(connection_string_name, None)
        if connection_string is None:
            raise IntegrationException(f"Missing '{connection_string_name}' connection string in application settings (missing env var CONNECTION_STRINGS: {'redis': 'redis://redis:6379'} ?)")

        redis_database_url = f"{connection_string}/0"
        parsed_url = urllib.parse.urlparse(connection_string)
        redis_host = parsed_url.hostname
        redis_port = parsed_url.port
        if any(item is None for item in [redis_host, redis_port]):
            raise IntegrationException(f"Issue parsing the connection_string '{connection_string}': host:{redis_host} port:{redis_port} database_name: 0")

        pool = redis.ConnectionPool.from_url(redis_database_url, max_connections=builder.settings.redis_max_connections)  # type: ignore
        builder.services.try_add_singleton(CacheRepositoryOptions[entity_type, key_type], singleton=CacheRepositoryOptions[entity_type, key_type](host=redis_host, port=redis_port, connection_string=redis_database_url))  # type: ignore
        builder.services.try_add_singleton(CacheClientPool[entity_type, key_type], singleton=CacheClientPool(pool=pool))  # type: ignore
        builder.services.add_scoped(AsyncStringCacheRepository[entity_type, key_type], AsyncStringCacheRepository[entity_type, key_type])  # type: ignore
        builder.services.add_transient(AsyncStringCacheRepository[entity_type, key_type], AsyncStringCacheRepository[entity_type, key_type])  # type: ignore
        # builder.services.add_scoped(Repository[entity_type, key_type], AsyncStringCacheRepository[entity_type, key_type])
        return builder


class AsyncHashCacheRepository(AsyncStringCacheRepository[TEntity, TKey]):
    """Represents an implementation extension of the AsyncCacheRepository for hash/dict objects."""

    def __init__(self, options: CacheRepositoryOptions[TEntity, TKey], redis_connection_pool: CacheClientPool[TEntity, TKey], serializer: JsonSerializer):
        """Initializes a new Cache repository"""
        super().__init__(options, redis_connection_pool, serializer)

    async def contains_async(self, id: TKey) -> bool:
        """Determines whether or not the repository contains an entity with the specified id"""
        # key = f"{self._get_key_prefix()}.{self._get_key(id)}"
        key = self._get_key(id)
        log.debug(f"Searching for {key}")
        result = self._redis_client.hexists(key, "id")
        if isinstance(result, Awaitable):
            data = await result
        else:
            data = result
        return data

    async def get_async(self, id: TKey) -> Optional[TEntity]:
        """Gets the entity with the specified id, if any
        WARNING: The resulting serialized Entity may not have '2-level' nested dictionaries,
        as the Redis Hash does not support it.
        """
        if "*" not in str(id):
            key = self._get_key(id)
        else:
            key = str(id)
        result = self._redis_client.hgetall(key)
        if isinstance(result, Awaitable):
            data = await result
        else:
            data = result
        if data is None:
            return None
        entity_dict = {}
        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(key, bytes):
                    decoded_key = key.decode("utf-8")
                else:
                    decoded_key = key
                if isinstance(val, bytes):
                    decoded_val = val.decode("utf-8")
                    try:
                        entity_dict[decoded_key] = json.loads(decoded_val)
                    except json.JSONDecodeError:
                        entity_dict[decoded_key] = decoded_val
                else:
                    entity_dict[key] = val
        entity_dict_str = json.dumps(entity_dict).encode("utf-8")
        return self._serializer.deserialize(entity_dict_str, self._get_entity_type())  # type: ignore

    async def hget_async(self, id: TKey, attribute: str) -> Optional[TEntity]:
        """Gets the value of the attribute of the given entity with the specified id, if any"""
        if "*" not in str(id):
            key = self._get_key(id)
        else:
            key = str(id)
        result = self._redis_client.hget(key, attribute)
        if isinstance(result, Awaitable):
            data = await result
        else:
            data = result
        if data is None:
            return None
        return self._serializer.deserialize(data, self._get_entity_type())  # type: ignore

    async def add_async(self, entity: TEntity) -> TEntity:
        """Adds the specified entity"""
        id = self._get_key(entity.id)
        data = self._serializer.serialize(entity)
        # convert bytearrays to dict
        data_dict = self._serializer.deserialize_from_text(data, dict)
        for key, val in data_dict.items():
            if isinstance(val, dict):
                data_dict[key] = json.dumps(val)
            if isinstance(val, list):
                data_dict[key] = json.dumps(val)
        # serialized_data = json.dumps(data_dict)
        result = self._redis_client.hset(id, mapping=data_dict)
        if isinstance(result, Awaitable):
            data = await result
        else:
            data = result
        return entity

    async def update_async(self, entity: TEntity) -> TEntity:
        """Persists the changes that were made to the specified entity"""
        return await self.add_async(entity)  # Update is essentially an add with new data

    async def remove_async(self, id: TKey) -> None:
        """Removes the entity with the specified key"""
        key = self._get_key(id)
        await self._redis_client.delete(key)

    @staticmethod
    def configure(builder: ApplicationBuilderBase, entity_type: type, key_type: type) -> ApplicationBuilderBase:
        connection_string_name = "redis"
        connection_string = builder.settings.connection_strings.get(connection_string_name, None)
        if connection_string is None:
            raise IntegrationException(f"Missing '{connection_string_name}' connection string in application settings (missing env var CONNECTION_STRINGS: {'redis': 'redis://redis:6379'} ?)")

        redis_database_url = f"{connection_string}/0"
        parsed_url = urllib.parse.urlparse(connection_string)
        redis_host = parsed_url.hostname
        redis_port = parsed_url.port
        if any(item is None for item in [redis_host, redis_port]):
            raise IntegrationException(f"Issue parsing the connection_string '{connection_string}': host:{redis_host} port:{redis_port} database_name: 0")

        pool = redis.ConnectionPool.from_url(redis_database_url, max_connections=builder.settings.redis_max_connections)  # type: ignore
        builder.services.try_add_singleton(CacheRepositoryOptions[entity_type, key_type], singleton=CacheRepositoryOptions[entity_type, key_type](host=redis_host, port=redis_port, connection_string=redis_database_url))  # type: ignore
        builder.services.try_add_singleton(CacheClientPool[entity_type, key_type], singleton=CacheClientPool(pool=pool))  # type: ignore
        builder.services.add_scoped(AsyncStringCacheRepository[entity_type, key_type], AsyncStringCacheRepository[entity_type, key_type])  # type: ignore
        # builder.services.add_scoped(Repository[entity_type, key_type], AsyncHashCacheRepository[entity_type, key_type])
        return builder
