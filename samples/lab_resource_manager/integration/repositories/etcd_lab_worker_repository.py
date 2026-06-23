"""etcd-based LabWorker Resource Repository.

This module provides an etcd-backed repository for LabWorker resources,
leveraging etcd's native watch API for real-time updates.
"""

import json
import logging
from typing import Optional

import etcd3
from domain.resources.lab_worker import LabWorker, LabWorkerPhase
from integration.repositories.etcd_storage_backend import EtcdStorageBackend

from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.data.infrastructure.tracing_mixin import TracedRepositoryMixin
from neuroglia.serialization.json import JsonSerializer

log = logging.getLogger(__name__)


class EtcdLabWorkerResourceRepository(TracedRepositoryMixin, Repository[LabWorker, str]):
    """etcd-based repository for LabWorker resources with automatic tracing.

    This repository uses etcd as the persistence layer, providing:
    - Strong consistency via Raft consensus
    - Native watchable API for real-time updates
    - Atomic operations for safe concurrent access
    - High availability through clustering
    - Automatic OpenTelemetry tracing for all operations (via TracedRepositoryMixin)

    The repository stores LabWorker resources in etcd with JSON serialization
    and supports custom queries for finding workers by phase, lab track, etc.
    """

    def __init__(
        self,
        etcd_client: etcd3.Client,
        serializer: JsonSerializer,
        prefix: str = "/lab-workers/",
    ):
        """Initialize etcd-based LabWorker repository.

        Args:
            etcd_client: Configured etcd3 sync client
            serializer: JSON serializer for resource serialization
            prefix: etcd key prefix for lab worker resources
        """
        super().__init__()

        # Create etcd storage backend
        self.storage_backend = EtcdStorageBackend(etcd_client, prefix)
        self.serializer = serializer
        self._etcd_client = etcd_client
        self._prefix = prefix
        log.info(f"EtcdLabWorkerResourceRepository initialized with prefix: {prefix}")

    async def contains_async(self, id: str) -> bool:
        """Check if a worker exists."""
        return await self.storage_backend.exists(id)

    async def get_async(self, id: str) -> Optional[LabWorker]:
        """Get a worker by ID."""
        resource_dict = await self.storage_backend.get(id)
        if not resource_dict:
            return None
        return self._dict_to_resource(resource_dict)

    async def _do_add_async(self, entity: LabWorker) -> LabWorker:
        """Add a new worker.

        Uses Resource.to_dict() to exclude non-serializable fields (like state_machine)
        and DateTimeEncoder to handle datetime, enum, and dataclass serialization.

        Note: Cannot use JsonSerializer.serialize_to_text(entity) directly because
        the state_machine contains dict[Enum, list[Enum]] which isn't JSON serializable.
        The to_dict() method only includes metadata/spec/status, which is the data we want to persist.
        """
        from integration.repositories.etcd_storage_backend import DateTimeEncoder

        # Convert to dict (excludes state_machine, only keeps metadata/spec/status)
        resource_dict = entity.to_dict()

        # Serialize with DateTimeEncoder to handle datetime, enum, dataclass
        json_str = json.dumps(resource_dict, cls=DateTimeEncoder)

        # Parse back to plain dict (all special types converted to JSON-safe values)
        resource_dict = json.loads(json_str)

        await self.storage_backend.set(entity.metadata.name, resource_dict)
        return entity

    async def _do_update_async(self, entity: LabWorker) -> LabWorker:
        """Update an existing worker.

        Uses the same approach as add: to_dict() + DateTimeEncoder.
        """
        from integration.repositories.etcd_storage_backend import DateTimeEncoder

        resource_dict = entity.to_dict()
        json_str = json.dumps(resource_dict, cls=DateTimeEncoder)
        resource_dict = json.loads(json_str)

        await self.storage_backend.set(entity.metadata.name, resource_dict)
        return entity

    async def _do_remove_async(self, id: str) -> None:
        """Remove a worker."""
        await self.storage_backend.delete(id)

    async def list_async(self, namespace: Optional[str] = None, label_selector: Optional[dict[str, str]] = None) -> list[LabWorker]:
        """List all workers matching the criteria."""
        # Get all worker names
        names = await self.storage_backend.keys()

        workers = []
        for name in names:
            resource_dict = await self.storage_backend.get(name)
            if not resource_dict:
                continue

            worker = self._dict_to_resource(resource_dict)

            # Apply filters
            if namespace and worker.metadata.namespace != namespace:
                continue

            if label_selector:
                match = all(worker.metadata.labels.get(k) == v for k, v in label_selector.items())
                if not match:
                    continue

            workers.append(worker)

        return workers

    def _dict_to_resource(self, resource_dict: dict) -> LabWorker:
        """Convert dictionary to LabWorker resource.

        Manual reconstruction is necessary because:
        1. ResourceMetadata structure needs explicit construction
        2. JsonSerializer is used for spec/status to handle enums and dataclasses
        3. State machine is reconstructed by LabWorker constructor

        This hybrid approach:
        - Manually builds metadata from dict keys
        - Uses framework JsonSerializer for spec/status (handles enum conversion, dataclasses)
        - Lets LabWorker.__init__ create the state machine
        """
        from domain.resources.lab_worker import LabWorkerSpec, LabWorkerStatus

        from neuroglia.data.resources.abstractions import ResourceMetadata

        # Extract nested dicts
        metadata_dict = resource_dict.get("metadata", {})
        spec_dict = resource_dict.get("spec", {})
        status_dict = resource_dict.get("status", {})

        # Manually reconstruct metadata (no complex types here)
        metadata = ResourceMetadata(
            name=metadata_dict.get("name"),
            namespace=metadata_dict.get("namespace"),
            labels=metadata_dict.get("labels", {}),
            annotations=metadata_dict.get("annotations", {}),
            uid=metadata_dict.get("uid"),
            resource_version=metadata_dict.get("resource_version"),
            generation=metadata_dict.get("generation"),
            creation_timestamp=metadata_dict.get("creation_timestamp"),
            deletion_timestamp=metadata_dict.get("deletion_timestamp"),
        )

        # Use framework's JsonSerializer for spec/status
        # This handles enum string-to-enum conversion, datetime parsing, and dataclass reconstruction
        spec_json = json.dumps(spec_dict)
        spec = self.serializer.deserialize_from_text(spec_json, LabWorkerSpec)

        status_json = json.dumps(status_dict)
        status = self.serializer.deserialize_from_text(status_json, LabWorkerStatus)

        # LabWorker constructor will create the state_machine
        return LabWorker(metadata=metadata, spec=spec, status=status)

    @classmethod
    def create_with_json_serializer(
        cls,
        etcd_client: etcd3.Client,
        prefix: str = "/lab-workers/",
    ) -> "EtcdLabWorkerResourceRepository":
        """Factory method to create repository with framework's JsonSerializer.

        Registers domain type modules for automatic enum and dataclass discovery.
        This enables the JsonSerializer to properly serialize/deserialize:
        - LabWorker, LabWorkerSpec, LabWorkerStatus classes
        - LabWorkerPhase enum
        - AwsEc2Config, CmlConfig dataclasses
        - DateTime, nested objects, etc.

        Args:
            etcd_client: Configured etcd3 client
            prefix: etcd key prefix for lab worker resources

        Returns:
            Configured EtcdLabWorkerResourceRepository instance with JsonSerializer
        """
        # Register domain type modules for complete type discovery
        # This allows JsonSerializer to find and convert enums, dataclasses, etc.
        JsonSerializer.register_type_modules(
            [
                "domain.resources",  # LabWorker and all resource classes
                "domain.value_objects",  # AwsEc2Config, CmlConfig
            ]
        )

        serializer = JsonSerializer()
        return cls(etcd_client, serializer, prefix)

    # Custom query methods for LabWorker-specific operations

    async def find_by_lab_track_async(self, lab_track: str) -> list[LabWorker]:
        """Find all workers assigned to a specific lab track.

        Args:
            lab_track: Lab track identifier

        Returns:
            List of LabWorker resources assigned to the lab track
        """
        try:
            # Use label selector to find workers with matching lab track
            resources = await self.storage_backend.list_with_labels({"lab-track": lab_track})
            workers = [self._dict_to_resource(r) for r in resources]
            log.debug(f"Found {len(workers)} workers for lab track: {lab_track}")
            return workers
        except Exception as ex:
            log.error(f"Error finding workers by lab track '{lab_track}': {ex}")
            return []

    async def find_by_phase_async(self, phase: LabWorkerPhase) -> list[LabWorker]:
        """Find all workers in a specific lifecycle phase.

        Args:
            phase: Worker lifecycle phase (Pending, Ready, Draining, Terminated)

        Returns:
            List of LabWorker resources in the specified phase
        """
        try:
            all_workers = await self.list_async()
            matching_workers = [w for w in all_workers if w.status and w.status.phase == phase]
            log.debug(f"Found {len(matching_workers)} workers in phase: {phase}")
            return matching_workers
        except Exception as ex:
            log.error(f"Error finding workers by phase '{phase}': {ex}")
            return []

    async def find_active_workers_async(self) -> list[LabWorker]:
        """Find all active workers (Ready or Draining phases).

        Returns:
            List of active LabWorker resources
        """
        try:
            all_workers = await self.list_async()
            active_workers = [w for w in all_workers if w.status and w.status.phase in [LabWorkerPhase.READY, LabWorkerPhase.DRAINING]]
            log.debug(f"Found {len(active_workers)} active workers")
            return active_workers
        except Exception as ex:
            log.error(f"Error finding active workers: {ex}")
            return []

    async def find_ready_workers_async(self) -> list[LabWorker]:
        """Find all workers available for assignment (Ready phase).

        Returns:
            List of ready LabWorker resources
        """
        return await self.find_by_phase_async(LabWorkerPhase.READY)

    async def find_draining_workers_async(self) -> list[LabWorker]:
        """Find all workers being decommissioned (Draining phase).

        Returns:
            List of draining LabWorker resources
        """
        return await self.find_by_phase_async(LabWorkerPhase.DRAINING)

    async def count_by_phase_async(self, phase: LabWorkerPhase) -> int:
        """Count workers in a specific phase.

        Args:
            phase: Worker lifecycle phase

        Returns:
            Number of workers in the phase
        """
        workers = await self.find_by_phase_async(phase)
        return len(workers)

    async def count_by_lab_track_async(self, lab_track: str) -> int:
        """Count workers assigned to a lab track.

        Args:
            lab_track: Lab track identifier

        Returns:
            Number of workers assigned to the lab track
        """
        workers = await self.find_by_lab_track_async(lab_track)
        return len(workers)

    def watch_workers(self, callback):
        """Watch for changes to lab worker resources in real-time.

        Uses etcd's native watch API to get notifications when workers are
        created, updated, or deleted.

        Args:
            callback: Function to call on worker changes (event -> None)

        Returns:
            Watch object that can be cancelled

        Example:
            def on_worker_change(event):
                if event.type == etcd3.events.PutEvent:
                    print(f"Worker added/updated: {event.key}")
                elif event.type == etcd3.events.DeleteEvent:
                    print(f"Worker deleted: {event.key}")

            watch_id = repository.watch_workers(on_worker_change)
            # Later: watch_id.cancel()
        """
        log.info("Starting watch on lab worker resources")
        return self.storage_backend.watch(callback)

    def _deserialize_resource(self, resource_dict: dict) -> LabWorker:
        """Deserialize resource dictionary to LabWorker object.

        Args:
            resource_dict: Resource dictionary from storage

        Returns:
            LabWorker resource object
        """
        # Use serializer to deserialize from dict to LabWorker
        json_str = self.serializer.serialize(resource_dict)
        return self.serializer.deserialize(json_str, LabWorker)
