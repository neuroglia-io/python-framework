"""In-memory storage backend for resources.

This provides a simple in-memory storage implementation for testing and development.
"""

import logging
from typing import Any, Optional

log = logging.getLogger(__name__)


class InMemoryStorageBackend:
    """In-memory storage backend for resources."""

    def __init__(self):
        self._data: dict[str, str] = {}  # resource_id -> serialized_data
        self._metadata: dict[str, dict[str, Any]] = {}  # resource_id -> metadata

    async def store_async(self, key: str, data: str, metadata: Optional[dict[str, Any]] = None) -> None:
        """Store data with key."""
        self._data[key] = data
        if metadata:
            self._metadata[key] = metadata
        log.debug(f"Stored resource with key: {key}")

    async def retrieve_async(self, key: str) -> Optional[str]:
        """Retrieve data by key."""
        data = self._data.get(key)
        log.debug(f"Retrieved resource with key: {key}, found: {data is not None}")
        return data

    async def delete_async(self, key: str) -> bool:
        """Delete data by key."""
        deleted = key in self._data
        if deleted:
            del self._data[key]
            if key in self._metadata:
                del self._metadata[key]
        log.debug(f"Deleted resource with key: {key}, existed: {deleted}")
        return deleted

    async def list_keys_async(self, prefix: Optional[str] = None) -> list[str]:
        """List all keys, optionally filtered by prefix."""
        keys = list(self._data.keys())
        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]
        log.debug(f"Listed keys with prefix '{prefix}': {len(keys)} found")
        return keys

    async def exists_async(self, key: str) -> bool:
        """Check if key exists."""
        exists = key in self._data
        log.debug(f"Checked existence of key: {key}, exists: {exists}")
        return exists

    def get_metadata(self, key: str) -> Optional[dict[str, Any]]:
        """Get metadata for a key."""
        return self._metadata.get(key)

    def clear(self) -> None:
        """Clear all data."""
        self._data.clear()
        self._metadata.clear()
        log.debug("Cleared all data from in-memory storage")

    def size(self) -> int:
        """Get number of stored items."""
        return len(self._data)

    def get_all_data(self) -> dict[str, str]:
        """Get all stored data (for debugging)."""
        return self._data.copy()
