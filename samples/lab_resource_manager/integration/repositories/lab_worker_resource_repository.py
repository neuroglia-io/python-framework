"""Lab Worker Resource Repository.

MongoDB-based repository for managing LabWorker resources using Motor async driver.
"""

import logging
from typing import Optional

from domain.resources.lab_worker import (
    LabWorker,
    LabWorkerPhase,
    LabWorkerSpec,
    LabWorkerStatus,
)
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from neuroglia.data.infrastructure.resources import ResourceRepository
from neuroglia.serialization.abstractions import TextSerializer

log = logging.getLogger(__name__)


class MongoStorageBackend:
    """MongoDB storage backend for ResourceRepository using Motor."""

    def __init__(self, collection: AsyncIOMotorCollection):
        self._collection = collection

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the collection."""
        count = await self._collection.count_documents({"_id": key}, limit=1)
        return count > 0

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        doc = await self._collection.find_one({"_id": key})
        return doc.get("data") if doc else None

    async def set(self, key: str, value: str) -> None:
        """Set value by key."""
        await self._collection.replace_one({"_id": key}, {"_id": key, "data": value}, upsert=True)

    async def delete(self, key: str) -> None:
        """Delete value by key."""
        await self._collection.delete_one({"_id": key})

    async def keys(self, pattern: str) -> list[str]:
        """Get all keys matching pattern (supports * wildcard)."""
        # Convert Redis-style pattern to MongoDB regex
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            cursor = self._collection.find({"_id": {"$regex": f"^{prefix}"}})
        else:
            cursor = self._collection.find({"_id": pattern})

        keys = []
        async for doc in cursor:
            keys.append(doc["_id"])
        return keys


class LabWorkerResourceRepository(ResourceRepository[LabWorkerSpec, LabWorkerStatus]):
    """Repository for managing LabWorker resources with MongoDB storage."""

    def __init__(self, motor_client: AsyncIOMotorClient, database_name: str, collection_name: str, serializer: TextSerializer):
        """
        Initialize the LabWorker resource repository.

        Args:
            motor_client: Motor async MongoDB client
            database_name: Name of the MongoDB database
            collection_name: Name of the collection for lab workers
            serializer: Text serializer for resource serialization
        """
        # Create MongoDB storage backend
        db = motor_client[database_name]
        collection = db[collection_name]
        storage_backend = MongoStorageBackend(collection)

        # Initialize base ResourceRepository
        super().__init__(storage_backend=storage_backend, serializer=serializer, resource_type="LabWorker")

        self._motor_client = motor_client
        self._database_name = database_name
        self._collection_name = collection_name

    async def find_by_lab_track_async(self, lab_track: str) -> list[LabWorker]:
        """Find all lab workers for a specific lab track."""
        try:
            all_workers = await self.list_async(label_selector={"lab-track": lab_track})
            return [w for w in all_workers if isinstance(w, LabWorker)]
        except Exception as e:
            log.error(f"Failed to find lab workers for lab track {lab_track}: {e}")
            return []

    async def find_by_phase_async(self, phase: LabWorkerPhase) -> list[LabWorker]:
        """Find all lab workers in a specific phase."""
        try:
            all_workers = await self.list_async()
            phase_workers = []

            for worker in all_workers:
                if isinstance(worker, LabWorker) and worker.status and worker.status.phase == phase:
                    phase_workers.append(worker)

            return phase_workers
        except Exception as e:
            log.error(f"Failed to find lab workers in phase {phase}: {e}")
            return []

    async def find_active_workers_async(self) -> list[LabWorker]:
        """Find all active lab workers."""
        return await self.find_by_phase_async(LabWorkerPhase.ACTIVE)

    async def find_ready_workers_async(self) -> list[LabWorker]:
        """Find all ready lab workers (available for lab assignments)."""
        return await self.find_by_phase_async(LabWorkerPhase.READY)

    async def find_draining_workers_async(self) -> list[LabWorker]:
        """Find all workers that are currently draining."""
        try:
            all_workers = await self.list_async()
            draining_workers = []

            for worker in all_workers:
                if isinstance(worker, LabWorker) and worker.status and worker.status.is_draining:
                    draining_workers.append(worker)

            return draining_workers
        except Exception as e:
            log.error(f"Failed to find draining lab workers: {e}")
            return []

    async def count_by_phase_async(self, phase: LabWorkerPhase) -> int:
        """Count lab workers in a specific phase."""
        try:
            workers = await self.find_by_phase_async(phase)
            return len(workers)
        except Exception as e:
            log.error(f"Failed to count lab workers in phase {phase}: {e}")
            return 0

    async def count_by_lab_track_async(self, lab_track: str) -> int:
        """Count lab workers for a specific lab track."""
        try:
            workers = await self.find_by_lab_track_async(lab_track)
            return len(workers)
        except Exception as e:
            log.error(f"Failed to count lab workers for lab track {lab_track}: {e}")
            return 0

    @classmethod
    def create_with_json_serializer(cls, motor_client: AsyncIOMotorClient, database_name: str, collection_name: str) -> "LabWorkerResourceRepository":
        """Create repository with JSON serializer."""
        from neuroglia.serialization.json import JsonSerializer

        serializer = JsonSerializer()
        return cls(motor_client, database_name, collection_name, serializer)

    @classmethod
    def create_with_yaml_serializer(cls, motor_client: AsyncIOMotorClient, database_name: str, collection_name: str) -> "LabWorkerResourceRepository":
        """Create repository with YAML serializer."""
        from neuroglia.data.resources.serializers.yaml_serializer import (
            YamlResourceSerializer,
        )

        if not YamlResourceSerializer.is_available():
            raise ImportError("YAML serializer not available. Install PyYAML.")

        serializer = YamlResourceSerializer()
        return cls(motor_client, database_name, collection_name, serializer)
