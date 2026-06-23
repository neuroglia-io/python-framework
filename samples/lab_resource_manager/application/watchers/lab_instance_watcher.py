"""Lab Instance Resource Watcher Implementation.

This watcher monitors lab instance resources and triggers reconciliation
when changes are detected.
"""

import logging
from typing import Optional

from domain.controllers.lab_instance_request_controller import (
    LabInstanceRequestController,
)
from domain.resources.lab_instance_request import (
    LabInstanceRequest,
    LabInstanceRequestSpec,
    LabInstanceRequestStatus,
)
from integration.repositories.lab_instance_resource_repository import (
    LabInstanceResourceRepository,
)

from neuroglia.data.resources.watcher import ResourceWatcherBase
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublisher,
)

log = logging.getLogger(__name__)


class LabInstanceWatcher(ResourceWatcherBase[LabInstanceRequestSpec, LabInstanceRequestStatus]):
    """Watcher for lab instance resources."""

    def __init__(self, repository: LabInstanceResourceRepository, controller: LabInstanceRequestController, event_publisher: Optional[CloudEventPublisher] = None, watch_interval: float = 10.0):
        super().__init__(event_publisher, watch_interval)
        self.repository = repository
        self.controller = controller

        # Register controller as change handler
        self.add_change_handler(self._handle_resource_change)

        log.info(f"Lab Instance Watcher initialized with {watch_interval}s interval")

    async def _list_resources(self, namespace: Optional[str] = None, label_selector: Optional[dict[str, str]] = None) -> list[LabInstanceRequest]:
        """List all lab instance resources matching the criteria."""
        try:
            if namespace:
                resources = await self.repository.find_by_namespace_async(namespace)
            else:
                resources = await self.repository.list_async()

            # Apply label selector if provided
            if label_selector:
                filtered_resources = []
                for resource in resources:
                    if self._matches_label_selector(resource, label_selector):
                        filtered_resources.append(resource)
                return filtered_resources

            return resources

        except Exception as e:
            log.error(f"Failed to list lab instance resources: {e}")
            return []

    def _matches_label_selector(self, resource: LabInstanceRequest, label_selector: dict[str, str]) -> bool:
        """Check if resource matches the label selector."""
        if not resource.metadata.labels:
            return not label_selector  # Empty selector matches resources without labels

        for key, value in label_selector.items():
            if resource.metadata.labels.get(key) != value:
                return False

        return True

    async def _handle_resource_change(self, change):
        """Handle detected resource changes by triggering controller actions."""
        try:
            resource = change.resource
            change_type = change.change_type

            log.info(f"Handling {change_type.value} for lab instance {resource.metadata.namespace}/{resource.metadata.name}")

            if change_type.value in ["Created", "Updated"]:
                # Trigger reconciliation for created or updated resources
                log.debug(f"Triggering reconciliation for {resource.metadata.name}")
                await self.controller.reconcile(resource)

            elif change_type.value == "Deleted":
                # Trigger finalization for deleted resources
                log.debug(f"Triggering finalization for {resource.metadata.name}")
                await self.controller.finalize(resource)

            elif change_type.value == "StatusUpdated":
                # For status updates, check if reconciliation is needed
                if resource.needs_reconciliation():
                    log.debug(f"Status update requires reconciliation for {resource.metadata.name}")
                    await self.controller.reconcile(resource)
                else:
                    log.debug(f"Status update does not require reconciliation for {resource.metadata.name}")

        except Exception as e:
            log.error(f"Error handling resource change: {e}")

    def _has_status_changed(self, current: LabInstanceRequest, cached: LabInstanceRequest) -> bool:
        """Check if the lab instance status has changed."""
        # Call parent implementation first
        if super()._has_status_changed(current, cached):
            return True

        # Lab instance specific status change detection
        if current.status is None and cached.status is None:
            return False
        if current.status is None or cached.status is None:
            return True

        # Check phase changes
        if current.status.phase != cached.status.phase:
            return True

        # Check container ID changes
        if current.status.container_id != cached.status.container_id:
            return True

        # Check timing changes
        if current.status.started_at != cached.status.started_at:
            return True

        if current.status.completed_at != cached.status.completed_at:
            return True

        # Check error message changes
        if current.status.error_message != cached.status.error_message:
            return True

        return False

    async def get_watcher_status(self) -> dict[str, any]:
        """Get current watcher status and statistics."""
        cached_resources = self.get_cached_resources()

        # Count resources by phase
        phase_counts = {}
        for resource in cached_resources:
            if resource.status and resource.status.phase:
                phase = resource.status.phase.value
                phase_counts[phase] = phase_counts.get(phase, 0) + 1

        return {"is_watching": self.is_watching(), "watch_interval_seconds": self.watch_interval, "cached_resource_count": self.get_cached_resource_count(), "change_handlers": len(self._change_handlers), "phase_distribution": phase_counts, "last_check": "N/A"}  # Could track last successful check time

    async def watch_namespace(self, namespace: str):
        """Convenience method to watch a specific namespace."""
        log.info(f"Starting to watch lab instances in namespace: {namespace}")
        await self.watch(namespace=namespace)

    async def watch_with_labels(self, label_selector: dict[str, str]):
        """Convenience method to watch resources matching label selector."""
        log.info(f"Starting to watch lab instances with labels: {label_selector}")
        await self.watch(label_selector=label_selector)
