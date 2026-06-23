"""Resource watcher implementation for change detection and event emission.

This module provides resource watching capabilities to detect changes
and emit events for resource modifications.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Generic, Optional

from neuroglia.eventing.cloud_events.cloud_event import CloudEvent
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublisher,
)

from .abstractions import Resource, ResourceWatcher, TResourceSpec, TResourceStatus

log = logging.getLogger(__name__)


class ResourceChangeType(Enum):
    """Types of resource changes that can be detected."""

    CREATED = "Created"
    UPDATED = "Updated"
    DELETED = "Deleted"
    STATUS_UPDATED = "StatusUpdated"


@dataclass
class ResourceChangeEvent(Generic[TResourceSpec, TResourceStatus]):
    """Event representing a change to a resource."""

    change_type: ResourceChangeType
    resource: Resource[TResourceSpec, TResourceStatus]
    old_resource: Optional[Resource[TResourceSpec, TResourceStatus]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ResourceWatcherBase(Generic[TResourceSpec, TResourceStatus], ResourceWatcher[TResourceSpec, TResourceStatus], ABC):
    """Base implementation for resource watchers with event emission."""

    def __init__(self, event_publisher: Optional[CloudEventPublisher] = None, watch_interval: float = 5.0, bookmark_storage=None, bookmark_key: Optional[str] = None):
        self.event_publisher = event_publisher
        self.watch_interval = watch_interval
        self._watching = False
        self._watch_task: Optional[asyncio.Task] = None
        self._change_handlers: list[callable] = []

        # Cache for tracking resource states
        self._resource_cache: dict[str, Resource[TResourceSpec, TResourceStatus]] = {}

        # Bookmark support for resumption
        self.bookmark_storage = bookmark_storage
        self.bookmark_key = bookmark_key or f"watcher_bookmark_{self.__class__.__name__}"
        self._last_resource_version: Optional[str] = None

    async def watch(self, namespace: Optional[str] = None, label_selector: Optional[dict[str, str]] = None) -> None:
        """Start watching for resource changes."""

        if self._watching:
            log.warning("Watcher is already running")
            return

        # Load last known position for resumption
        self._last_resource_version = await self._load_bookmark()
        if self._last_resource_version:
            log.info(f"Starting watcher from resource version: {self._last_resource_version}")
        else:
            log.info("Starting watcher from beginning (no bookmark found)")

        self._watching = True
        log.info(f"Starting resource watcher for namespace={namespace}, labels={label_selector}")

        # Start the watch loop
        self._watch_task = asyncio.create_task(self._watch_loop(namespace, label_selector))

        try:
            await self._watch_task
        except asyncio.CancelledError:
            log.info("Resource watcher was cancelled")
        except Exception as e:
            log.error(f"Resource watcher failed: {e}")
            raise
        finally:
            self._watching = False

    async def stop_watching(self) -> None:
        """Stop watching for resource changes."""

        if not self._watching:
            return

        log.info("Stopping resource watcher")
        self._watching = False

        if self._watch_task and not self._watch_task.done():
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass

        self._resource_cache.clear()

    def add_change_handler(self, handler: callable) -> None:
        """Add a handler to be called when resource changes are detected."""
        self._change_handlers.append(handler)

    def remove_change_handler(self, handler: callable) -> None:
        """Remove a change handler."""
        if handler in self._change_handlers:
            self._change_handlers.remove(handler)

    @abstractmethod
    async def _list_resources(self, namespace: Optional[str] = None, label_selector: Optional[dict[str, str]] = None) -> list[Resource[TResourceSpec, TResourceStatus]]:
        """List all resources matching the criteria. Implement in subclass."""
        raise NotImplementedError()

    async def _watch_loop(self, namespace: Optional[str] = None, label_selector: Optional[dict[str, str]] = None) -> None:
        """Main watch loop that detects and processes resource changes."""

        while self._watching:
            try:
                # Get current resources
                current_resources = await self._list_resources(namespace, label_selector)
                current_resource_map = {r.id: r for r in current_resources}

                # Detect changes
                changes = self._detect_changes(current_resource_map)

                # Process each change
                for change in changes:
                    await self._process_change(change)

                # Update cache
                self._resource_cache = current_resource_map

                # Save bookmark with latest resource version
                if current_resources:
                    latest_rv = max((r.metadata.resource_version for r in current_resources), default=None)
                    if latest_rv:
                        await self._save_bookmark(latest_rv)
                        self._last_resource_version = latest_rv

                # Wait before next poll
                await asyncio.sleep(self.watch_interval)

            except Exception as e:
                log.error(f"Error in watch loop: {e}")
                await asyncio.sleep(self.watch_interval)

    async def _load_bookmark(self) -> Optional[str]:
        """Load last known resource version from storage for resumption."""
        if not self.bookmark_storage:
            return None

        try:
            bookmark = await self.bookmark_storage.get(self.bookmark_key)
            if bookmark:
                log.info(f"Loaded bookmark: {bookmark}")
            return bookmark
        except Exception as e:
            log.warning(f"Failed to load bookmark: {e}")
            return None

    async def _save_bookmark(self, resource_version: str) -> None:
        """Save current resource version as bookmark."""
        if not self.bookmark_storage:
            return

        try:
            await self.bookmark_storage.set(self.bookmark_key, resource_version)
            log.debug(f"Saved bookmark at resource version: {resource_version}")
        except Exception as e:
            log.error(f"Failed to save bookmark: {e}")

    def _detect_changes(self, current_resources: dict[str, Resource[TResourceSpec, TResourceStatus]]) -> list[ResourceChangeEvent[TResourceSpec, TResourceStatus]]:
        """Detect changes between current resources and cached resources."""

        changes = []
        current_ids = set(current_resources.keys())
        cached_ids = set(self._resource_cache.keys())

        # Detect new resources (CREATED)
        for resource_id in current_ids - cached_ids:
            resource = current_resources[resource_id]
            changes.append(ResourceChangeEvent(change_type=ResourceChangeType.CREATED, resource=resource))
            log.debug(f"Detected CREATED: {resource.metadata.namespace}/{resource.metadata.name}")

        # Detect deleted resources (DELETED)
        for resource_id in cached_ids - current_ids:
            old_resource = self._resource_cache[resource_id]
            # Create a copy for the event since the resource is being deleted
            changes.append(
                ResourceChangeEvent(
                    change_type=ResourceChangeType.DELETED,
                    resource=old_resource,
                    old_resource=old_resource,
                )
            )
            log.debug(f"Detected DELETED: {old_resource.metadata.namespace}/{old_resource.metadata.name}")

        # Detect updated resources (UPDATED/STATUS_UPDATED)
        for resource_id in current_ids & cached_ids:
            current_resource = current_resources[resource_id]
            cached_resource = self._resource_cache[resource_id]

            # Check if spec changed (generation increment)
            if current_resource.metadata.generation > cached_resource.metadata.generation:
                changes.append(
                    ResourceChangeEvent(
                        change_type=ResourceChangeType.UPDATED,
                        resource=current_resource,
                        old_resource=cached_resource,
                    )
                )
                log.debug(f"Detected UPDATED: {current_resource.metadata.namespace}/{current_resource.metadata.name}")

            # Check if status changed (observed generation or other status fields)
            elif self._has_status_changed(current_resource, cached_resource):
                changes.append(
                    ResourceChangeEvent(
                        change_type=ResourceChangeType.STATUS_UPDATED,
                        resource=current_resource,
                        old_resource=cached_resource,
                    )
                )
                log.debug(f"Detected STATUS_UPDATED: {current_resource.metadata.namespace}/{current_resource.metadata.name}")

        return changes

    def _has_status_changed(
        self,
        current: Resource[TResourceSpec, TResourceStatus],
        cached: Resource[TResourceSpec, TResourceStatus],
    ) -> bool:
        """Check if the resource status has changed."""

        # If either resource has no status, consider it changed if they differ
        if current.status is None and cached.status is None:
            return False
        if current.status is None or cached.status is None:
            return True

        # Compare observed generation
        if current.status.observed_generation != cached.status.observed_generation:
            return True

        # Compare last updated time
        if current.status.last_updated != cached.status.last_updated:
            return True

        # Subclasses can override this for more specific status comparison
        return False

    async def _process_change(self, change: ResourceChangeEvent[TResourceSpec, TResourceStatus]) -> None:
        """Process a detected resource change."""

        try:
            # Call registered change handlers
            for handler in self._change_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(change)
                    else:
                        handler(change)
                except Exception as e:
                    log.error(f"Change handler failed: {e}")

            # Publish cloud event
            await self._publish_change_event(change)

        except Exception as e:
            log.error(f"Failed to process change for resource {change.resource.id}: {e}")

    async def _publish_change_event(self, change: ResourceChangeEvent[TResourceSpec, TResourceStatus]) -> None:
        """Publish a cloud event for the resource change."""

        if not self.event_publisher:
            return

        resource = change.resource
        event_type = f"{resource.kind.lower()}.{change.change_type.value.lower()}"

        event_data = {
            "resourceUid": resource.id,
            "apiVersion": resource.api_version,
            "kind": resource.kind,
            "namespace": resource.metadata.namespace,
            "name": resource.metadata.name,
            "generation": resource.metadata.generation,
            "changeType": change.change_type.value,
            "timestamp": change.timestamp.isoformat(),
        }

        # Add status information if available
        if resource.status:
            event_data["observedGeneration"] = resource.status.observed_generation

        # Add old resource information for updates/deletes
        if change.old_resource:
            event_data["oldGeneration"] = change.old_resource.metadata.generation
            if change.old_resource.status:
                event_data["oldObservedGeneration"] = change.old_resource.status.observed_generation

        event = CloudEvent(
            source=f"watcher/{resource.kind.lower()}",
            type=event_type,
            subject=f"{resource.metadata.namespace}/{resource.metadata.name}",
            data=event_data,
        )

        try:
            await self.event_publisher.publish_async(event)
            log.debug(f"Published change event: {event_type} for {resource.metadata.namespace}/{resource.metadata.name}")
        except Exception as e:
            log.error(f"Failed to publish change event: {e}")

    def is_watching(self) -> bool:
        """Check if the watcher is currently active."""
        return self._watching

    def get_cached_resource_count(self) -> int:
        """Get the number of resources currently in the cache."""
        return len(self._resource_cache)

    def get_cached_resources(self) -> list[Resource[TResourceSpec, TResourceStatus]]:
        """Get a copy of all cached resources."""
        return list(self._resource_cache.values())
