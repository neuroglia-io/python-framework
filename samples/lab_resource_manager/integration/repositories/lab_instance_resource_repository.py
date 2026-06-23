"""Lab Instance Resource Repository.

This repository manages lab instance resources using the Resource Oriented
Architecture patterns with multi-format serialization support.
"""

import logging

from domain.resources.lab_instance_request import (
    LabInstancePhase,
    LabInstanceRequest,
    LabInstanceRequestSpec,
    LabInstanceRequestStatus,
)

from neuroglia.data.infrastructure.resources.resource_repository import (
    ResourceRepository,
)
from neuroglia.data.resources.serializers.yaml_serializer import YamlResourceSerializer
from neuroglia.serialization.abstractions import TextSerializer

log = logging.getLogger(__name__)


class LabInstanceResourceRepository(ResourceRepository[LabInstanceRequestSpec, LabInstanceRequestStatus]):
    """Repository for managing LabInstanceRequest resources."""

    def __init__(self, storage_backend: any, serializer: TextSerializer):
        super().__init__(storage_backend=storage_backend, serializer=serializer, resource_type="LabInstanceRequest")

    async def find_by_namespace_async(self, namespace: str) -> list[LabInstanceRequest]:
        """Find all lab instances in a specific namespace."""
        try:
            resources = await self.list_async(namespace=namespace)
            return [r for r in resources if isinstance(r, LabInstanceRequest)]
        except Exception as e:
            log.error(f"Failed to find lab instances in namespace {namespace}: {e}")
            return []

    async def find_by_student_email_async(self, student_email: str) -> list[LabInstanceRequest]:
        """Find all lab instances for a specific student."""
        try:
            all_resources = await self.list_async()
            student_resources = []

            for resource in all_resources:
                if isinstance(resource, LabInstanceRequest) and resource.spec.student_email == student_email:
                    student_resources.append(resource)

            return student_resources
        except Exception as e:
            log.error(f"Failed to find lab instances for student {student_email}: {e}")
            return []

    async def find_by_phase_async(self, phase: LabInstancePhase) -> list[LabInstanceRequest]:
        """Find all lab instances in a specific phase."""
        try:
            all_resources = await self.list_async()
            phase_resources = []

            for resource in all_resources:
                if isinstance(resource, LabInstanceRequest) and resource.status.phase == phase:
                    phase_resources.append(resource)

            return phase_resources
        except Exception as e:
            log.error(f"Failed to find lab instances in phase {phase}: {e}")
            return []

    async def find_scheduled_pending_async(self) -> list[LabInstanceRequest]:
        """Find all scheduled lab instances that are still pending."""
        try:
            pending_resources = await self.find_by_phase_async(LabInstancePhase.PENDING)
            scheduled_pending = []

            for resource in pending_resources:
                if resource.is_scheduled():
                    scheduled_pending.append(resource)

            return scheduled_pending
        except Exception as e:
            log.error(f"Failed to find scheduled pending lab instances: {e}")
            return []

    async def find_running_instances_async(self) -> list[LabInstanceRequest]:
        """Find all currently running lab instances."""
        return await self.find_by_phase_async(LabInstancePhase.RUNNING)

    async def find_expired_instances_async(self) -> list[LabInstanceRequest]:
        """Find all running lab instances that have expired."""
        try:
            running_resources = await self.find_running_instances_async()
            expired_resources = []

            for resource in running_resources:
                if resource.is_expired():
                    expired_resources.append(resource)

            return expired_resources
        except Exception as e:
            log.error(f"Failed to find expired lab instances: {e}")
            return []

    async def count_by_namespace_async(self, namespace: str) -> int:
        """Count lab instances in a namespace."""
        try:
            resources = await self.find_by_namespace_async(namespace)
            return len(resources)
        except Exception as e:
            log.error(f"Failed to count lab instances in namespace {namespace}: {e}")
            return 0

    async def count_by_phase_async(self, phase: LabInstancePhase) -> int:
        """Count lab instances in a specific phase."""
        try:
            resources = await self.find_by_phase_async(phase)
            return len(resources)
        except Exception as e:
            log.error(f"Failed to count lab instances in phase {phase}: {e}")
            return 0

    @classmethod
    def create_with_yaml_serializer(cls, storage_backend: any) -> "LabInstanceResourceRepository":
        """Create repository with YAML serializer."""
        if not YamlResourceSerializer.is_available():
            raise ImportError("YAML serializer not available. Install PyYAML.")

        serializer = YamlResourceSerializer()
        return cls(storage_backend, serializer)

    @classmethod
    def create_with_json_serializer(cls, storage_backend: any) -> "LabInstanceResourceRepository":
        """Create repository with JSON serializer."""
        from neuroglia.serialization.json import JsonSerializer

        serializer = JsonSerializer()
        return cls(storage_backend, serializer)
