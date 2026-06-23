"""PostgreSQL-based storage backend for resources.

This module provides a PostgreSQL implementation for resource storage
with support for basic CRUD operations.
"""

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import asyncpg

try:
    import asyncpg

    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

log = logging.getLogger(__name__)


class PostgresResourceStore:
    """PostgreSQL-based storage backend for resources."""

    def __init__(self, connection_string: str, table_name: str = "resources"):
        if not POSTGRES_AVAILABLE:
            raise ImportError("asyncpg is required for PostgreSQL storage. Install with: pip install asyncpg")

        self.connection_string = connection_string
        self.table_name = table_name
        self._pool: Optional["asyncpg.Pool"] = None

    async def _get_pool(self) -> "asyncpg.Pool":
        """Get or create connection pool."""
        if self._pool is None:
            try:
                self._pool = await asyncpg.create_pool(self.connection_string)

                # Ensure table exists
                await self._ensure_table_exists()

                log.info("Connected to PostgreSQL")
            except Exception as e:
                log.error(f"Failed to connect to PostgreSQL: {e}")
                raise

        return self._pool

    async def _ensure_table_exists(self) -> None:
        """Ensure the resources table exists."""
        pool = await self._get_pool()

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            key VARCHAR(255) PRIMARY KEY,
            value TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        async with pool.acquire() as connection:
            await connection.execute(create_table_sql)

    async def exists(self, key: str) -> bool:
        """Check if a key exists in PostgreSQL."""
        pool = await self._get_pool()

        sql = f"SELECT 1 FROM {self.table_name} WHERE key = $1"

        async with pool.acquire() as connection:
            result = await connection.fetchval(sql, key)
            return result is not None

    async def get(self, key: str) -> Optional[str]:
        """Get a value from PostgreSQL."""
        pool = await self._get_pool()

        sql = f"SELECT value FROM {self.table_name} WHERE key = $1"

        async with pool.acquire() as connection:
            return await connection.fetchval(sql, key)

    async def set(self, key: str, value: str) -> None:
        """Set a value in PostgreSQL."""
        pool = await self._get_pool()

        sql = f"""
        INSERT INTO {self.table_name} (key, value, created_at, updated_at)
        VALUES ($1, $2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (key)
        DO UPDATE SET value = $2, updated_at = CURRENT_TIMESTAMP
        """

        async with pool.acquire() as connection:
            await connection.execute(sql, key, value)

    async def delete(self, key: str) -> None:
        """Delete a key from PostgreSQL."""
        pool = await self._get_pool()

        sql = f"DELETE FROM {self.table_name} WHERE key = $1"

        async with pool.acquire() as connection:
            await connection.execute(sql, key)

    async def keys(self, pattern: str) -> list[str]:
        """Get all keys matching a pattern (using LIKE)."""
        pool = await self._get_pool()

        # Convert shell pattern to SQL LIKE pattern
        like_pattern = pattern.replace("*", "%").replace("?", "_")
        sql = f"SELECT key FROM {self.table_name} WHERE key LIKE $1"

        async with pool.acquire() as connection:
            rows = await connection.fetch(sql, like_pattern)
            return [row["key"] for row in rows]

    async def close(self) -> None:
        """Close the PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    @staticmethod
    def is_available() -> bool:
        """Check if PostgreSQL client is available."""
        return POSTGRES_AVAILABLE
