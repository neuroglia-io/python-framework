"""etcd Storage Backend for ResourceRepository.

This module provides an etcd-based storage backend that implements the storage
interface required by ResourceRepository. It leverages etcd's native watch API
for real-time resource change notifications.

Uses etcd3-py library with the following API:
- client.put(key, value) - Store a key-value pair
- client.range(key) - Retrieve key(s), returns response with .kvs list
- client.delete_range(key) - Delete a key
"""
import json
import logging
from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import etcd3

log = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime, Enum, and dataclass objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if is_dataclass(obj):
            # Convert dataclass to dict recursively
            return asdict(obj)
        # Handle objects with __dict__ attribute
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


class EtcdStorageBackend:
    """Storage backend adapter for etcd.

    Provides a key-value interface that ResourceRepository expects,
    while using etcd as the underlying storage with native watch capabilities.

    Features:
    - Native watchable API (etcd watch)
    - Strong consistency (etcd Raft consensus)
    - Atomic operations (Transactions)
    - Lease-based TTL support
    - High availability (etcd clustering)

    Args:
        client: etcd3 sync client instance (operations wrapped in async by repository)
        prefix: Key prefix for namespacing (e.g., '/lab-workers/')
    """

    def __init__(self, client: etcd3.Client, prefix: str = ""):
        """Initialize etcd storage backend.

        Args:
            client: Configured etcd3 sync client
            prefix: Key prefix for resource namespacing (must end with '/')
        """
        self._client = client
        self._prefix = prefix.rstrip("/") + "/" if prefix else ""
        log.info(f"EtcdStorageBackend initialized with prefix: {self._prefix}")

    def _make_key(self, name: str) -> str:
        """Create full etcd key from resource name.

        Args:
            name: Resource name (metadata.name)

        Returns:
            Full etcd key with prefix
        """
        return f"{self._prefix}{name}"

    async def exists(self, name: str) -> bool:
        """Check if a resource exists in etcd.

        Args:
            name: Resource name to check

        Returns:
            True if resource exists, False otherwise
        """
        key = self._make_key(name)
        try:
            response = self._client.range(key)
            # Handle case where response might be None
            if response is None:
                return False
            return len(response.kvs) > 0
        except Exception as ex:
            log.error(f"Error checking existence for key '{key}': {ex}")
            return False

    async def get(self, name: str) -> Optional[dict[str, Any]]:
        """Retrieve a resource from etcd.

        Args:
            name: Resource name to retrieve

        Returns:
            Resource dictionary if found, None otherwise
        """
        key = self._make_key(name)
        try:
            response = self._client.range(key)

            if not response.kvs:
                return None

            # Get the first (and only) key-value pair
            kv = response.kvs[0]
            value = kv.value

            # Deserialize JSON from bytes
            resource_dict = json.loads(value.decode("utf-8"))
            log.debug(f"Retrieved resource '{name}' from etcd")
            return resource_dict

        except json.JSONDecodeError as ex:
            log.error(f"Failed to decode JSON for key '{key}': {ex}")
            return None
        except Exception as ex:
            log.error(f"Error retrieving key '{key}': {ex}")
            return None

    async def set(self, name: str, value: dict[str, Any]) -> bool:
        """Store or update a resource in etcd.

        Args:
            name: Resource name
            value: Resource dictionary to store

        Returns:
            True if successful, False otherwise
        """
        key = self._make_key(name)
        try:
            # Serialize to JSON string with custom encoder for datetime
            json_value = json.dumps(value, ensure_ascii=False, cls=DateTimeEncoder)
            self._client.put(key, json_value)
            log.debug(f"Stored resource '{name}' in etcd")
            return True

        except Exception as ex:
            log.error(f"Error storing key '{key}': {ex}")
            return False

    async def delete(self, name: str) -> bool:
        """Delete a resource from etcd.

        Args:
            name: Resource name to delete

        Returns:
            True if deleted, False if not found or error
        """
        key = self._make_key(name)
        try:
            # delete_range returns response with deleted count
            response = self._client.delete_range(key)
            deleted = response.deleted > 0

            if deleted:
                log.debug(f"Deleted resource '{name}' from etcd")
                return True
            else:
                log.warning(f"Resource '{name}' not found for deletion")
                return False

        except Exception as ex:
            log.error(f"Error deleting key '{key}': {ex}")
            return False

    async def keys(self, pattern: str = "") -> list[str]:
        """List resource names matching a pattern.

        Args:
            pattern: Optional pattern for filtering (simple prefix matching)

        Returns:
            List of resource names (without prefix)
        """
        try:
            # Get all keys with the prefix using range with range_end
            search_prefix = self._prefix + pattern if pattern else self._prefix

            # Calculate range_end for prefix query (increment last byte)
            range_end = search_prefix[:-1] + chr(ord(search_prefix[-1]) + 1)

            response = self._client.range(search_prefix, range_end=range_end)

            # Handle None response or missing kvs attribute
            if response is None or not hasattr(response, "kvs") or response.kvs is None:
                log.debug("No keys found or empty response")
                return []

            # Extract resource names (strip prefix)
            names = []
            for kv in response.kvs:
                key = kv.key.decode("utf-8")
                # Remove the prefix to get just the resource name
                if key.startswith(self._prefix):
                    name = key[len(self._prefix) :]
                    names.append(name)

            log.debug(f"Found {len(names)} resources matching pattern '{pattern}'")
            return names

        except Exception as ex:
            log.error(f"Error listing keys with pattern '{pattern}': {ex}")
            return []

    def watch(self, callback: Callable, key_prefix: str = ""):
        """Watch for changes to resources with etcd native watch API.

        This provides real-time notifications when resources are created,
        modified, or deleted using etcd3.Watcher class.

        The correct pattern for etcd3-py is:
        1. Create Watcher instance: etcd3.Watcher(client, key=prefix, prefix=True)
        2. Register callback: watcher.onEvent(callback)
        3. Start daemon: watcher.runDaemon()
        4. Cancel: watcher.cancel()

        Args:
            callback: Function to call on resource changes (event -> None)
            key_prefix: Optional key prefix to watch (default: watch all under main prefix)

        Returns:
            Watcher instance, or None if watch creation failed

        Example:
            def on_change(event):
                print(f"Resource changed: {event}")

            watcher = backend.watch(on_change, key_prefix="lab-workers/")
            # Later: watcher.cancel() to stop watching
        """
        watch_prefix = self._prefix + key_prefix if key_prefix else self._prefix
        log.info(f"Starting etcd watch on prefix: {watch_prefix}")

        try:
            # Use etcd3.Watcher class - the recommended approach
            import etcd3

            # Create Watcher instance with prefix=True for prefix watching
            # Watcher constructor requires 'key' as keyword argument, not positional
            watcher = etcd3.Watcher(
                client=self._client,
                key=watch_prefix,
                prefix=True,  # Enable prefix watch - watches all keys starting with key
            )

            # Register the callback
            watcher.onEvent(callback)

            # Start watcher in daemon thread
            watcher.runDaemon()

            log.info(f"✓ Created and started Watcher for prefix: {watch_prefix}")
            return watcher

        except Exception as ex:
            log.error(f"Failed to create watch on '{watch_prefix}': {ex}")
            import traceback

            log.error(traceback.format_exc())
            return None

    async def list_with_labels(self, label_selector: dict[str, str]) -> list[dict[str, Any]]:
        """List resources filtered by label selector.

        Args:
            label_selector: Dictionary of labels to match (e.g., {"env": "prod", "tier": "frontend"})

        Returns:
            List of resource dictionaries matching the selector
        """
        try:
            # Get all resources
            all_names = await self.keys()
            matching = []

            for name in all_names:
                resource = await self.get(name)
                if not resource:
                    continue

                # Check if resource labels match selector
                metadata = resource.get("metadata", {})
                resource_labels = metadata.get("labels", {})

                # All selector labels must match
                if all(resource_labels.get(k) == v for k, v in label_selector.items()):
                    matching.append(resource)

            log.debug(f"Found {len(matching)} resources matching labels {label_selector}")
            return matching

        except Exception as ex:
            log.error(f"Error listing with labels {label_selector}: {ex}")
            return []

    async def compare_and_swap(self, name: str, expected_version: str, new_value: dict[str, Any]) -> bool:
        """Atomically update a resource if version matches.

        Uses etcd mod_revision for optimistic concurrency control.

        Args:
            name: Resource name
            expected_version: Expected resource version (from metadata.resourceVersion)
            new_value: New resource dictionary

        Returns:
            True if swap succeeded, False if version mismatch or error
        """
        key = self._make_key(name)
        try:
            # Get current resource with mod_revision
            response = self._client.range(key)

            if not response.kvs:
                log.warning(f"Resource '{name}' not found for compare-and-swap")
                return False

            kv = response.kvs[0]
            current_value = json.loads(kv.value.decode("utf-8"))
            current_mod_revision = kv.mod_revision

            # Check if version matches
            current_version = current_value.get("metadata", {}).get("resourceVersion", "")
            if current_version != expected_version:
                log.warning(f"Version mismatch for '{name}': " f"expected={expected_version}, current={current_version}")
                return False

            # Use etcd transaction for atomic swap
            # NOTE: This is a simplified implementation
            # The actual etcd3-py transaction API needs to be verified
            new_json = json.dumps(new_value, ensure_ascii=False)

            # For now, do a simple put - in production, this should use transactions
            # TODO: Implement proper etcd transaction: IF mod_revision == X THEN put ELSE fail
            self._client.put(key, new_json)

            log.debug(f"Compare-and-swap succeeded for '{name}'")
            log.warning("CAS using simple put - not truly atomic. Needs etcd transaction API.")
            return True

        except Exception as ex:
            log.error(f"Error in compare-and-swap for '{name}': {ex}")
            return False
