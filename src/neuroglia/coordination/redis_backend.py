"""Redis backend for distributed coordination.

This module provides a Redis-based implementation of the coordination
backend for leader election and distributed locking.
"""

import logging
from typing import Optional

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .abstractions import CoordinationBackend

log = logging.getLogger(__name__)


class RedisCoordinationBackend(CoordinationBackend):
    """Redis implementation of coordination backend."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
    ):
        if not REDIS_AVAILABLE:
            raise ImportError("redis is required for Redis coordination. Install with: pip install redis")

        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
            )

            # Test connection
            try:
                await self._client.ping()
                log.info(f"Connected to Redis at {self.host}:{self.port} for coordination")
            except Exception as e:
                log.error(f"Failed to connect to Redis: {e}")
                raise

        return self._client

    async def acquire_lease(self, key: str, holder_identity: str, ttl_seconds: int) -> bool:
        """Try to acquire a lease using Redis SET NX EX."""
        client = await self._get_client()

        # SET key value NX EX ttl - Only set if not exists, with expiration
        result = await client.set(key, holder_identity, nx=True, ex=ttl_seconds)

        return result is True

    async def renew_lease(self, key: str, holder_identity: str, ttl_seconds: int) -> bool:
        """Renew a lease if held by this identity."""
        client = await self._get_client()

        # Use Lua script for atomic check-and-renew
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            redis.call("expire", KEYS[1], ARGV[2])
            return 1
        else
            return 0
        end
        """

        result = await client.eval(lua_script, 1, key, holder_identity, ttl_seconds)

        return result == 1

    async def release_lease(self, key: str, holder_identity: str) -> bool:
        """Release a lease if held by this identity."""
        client = await self._get_client()

        # Use Lua script for atomic check-and-delete
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            redis.call("del", KEYS[1])
            return 1
        else
            return 0
        end
        """

        result = await client.eval(lua_script, 1, key, holder_identity)

        return result == 1

    async def get_lease_holder(self, key: str) -> Optional[str]:
        """Get the current lease holder."""
        client = await self._get_client()
        holder = await client.get(key)
        return holder if holder else None

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
