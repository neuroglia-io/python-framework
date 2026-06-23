"""Redis-based storage backend for resources.

This module provides a Redis implementation for resource storage
with support for basic CRUD operations.
"""

import logging
from typing import Optional

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

log = logging.getLogger(__name__)


class RedisResourceStore:
    """Redis-based storage backend for resources."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True,
    ):
        if not REDIS_AVAILABLE:
            raise ImportError("redis is required for Redis storage. Install with: pip install redis")

        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses

        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=self.decode_responses,
            )

            # Test connection
            try:
                await self._client.ping()
                log.info(f"Connected to Redis at {self.host}:{self.port}")
            except Exception as e:
                log.error(f"Failed to connect to Redis: {e}")
                raise

        return self._client

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        client = await self._get_client()
        result = await client.exists(key)
        return result > 0

    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis."""
        client = await self._get_client()
        return await client.get(key)

    async def set(self, key: str, value: str) -> None:
        """Set a value in Redis."""
        client = await self._get_client()
        await client.set(key, value)

    async def delete(self, key: str) -> None:
        """Delete a key from Redis."""
        client = await self._get_client()
        await client.delete(key)

    async def keys(self, pattern: str) -> list[str]:
        """Get all keys matching a pattern."""
        client = await self._get_client()
        keys = await client.keys(pattern)
        return [key.decode() if isinstance(key, bytes) else key for key in keys]

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    @staticmethod
    def is_available() -> bool:
        """Check if Redis client is available."""
        return REDIS_AVAILABLE
