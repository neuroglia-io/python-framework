"""Resource Allocator Service.

This module provides resource allocation and availability checking for lab instances.
It manages CPU, memory, and other resource limits for containers.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

log = logging.getLogger(__name__)


@dataclass
class ResourceAllocation:
    """Represents an allocated set of resources."""

    allocation_id: str
    cpu: float
    memory_mb: int
    allocated_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, str]:
        """Convert allocation to dictionary format for storage."""
        return {"allocation_id": self.allocation_id, "cpu": str(self.cpu), "memory": f"{self.memory_mb}Mi", "allocated_at": self.allocated_at.isoformat(), **self.metadata}

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "ResourceAllocation":
        """Create allocation from dictionary format."""
        return cls(allocation_id=data["allocation_id"], cpu=float(data["cpu"]), memory_mb=int(data["memory"].replace("Mi", "").replace("Gi", "")) * (1024 if "Gi" in data["memory"] else 1), allocated_at=datetime.fromisoformat(data["allocated_at"]), metadata={k: v for k, v in data.items() if k not in ["allocation_id", "cpu", "memory", "allocated_at"]})


class ResourceAllocator:
    """Service for managing resource allocation and availability for lab instances."""

    def __init__(self, total_cpu: float = 32.0, total_memory_gb: int = 128):
        """Initialize resource allocator with total available resources.

        Args:
            total_cpu: Total CPU cores available for allocation
            total_memory_gb: Total memory in GB available for allocation
        """
        self.total_cpu = total_cpu
        self.total_memory_mb = total_memory_gb * 1024

        # Track active allocations
        self._allocations: dict[str, ResourceAllocation] = {}
        self._allocation_counter = 0

        log.info(f"ResourceAllocator initialized with {total_cpu} CPU cores and {total_memory_gb}GB memory")

    async def check_availability(self, resource_limits: dict[str, str]) -> bool:
        """Check if the requested resources are available for allocation.

        Args:
            resource_limits: Dictionary with resource requirements (e.g., {"cpu": "2", "memory": "4Gi"})

        Returns:
            True if resources are available, False otherwise
        """
        try:
            required_cpu, required_memory_mb = self._parse_resource_limits(resource_limits)

            # Calculate currently allocated resources
            allocated_cpu = sum(alloc.cpu for alloc in self._allocations.values())
            allocated_memory_mb = sum(alloc.memory_mb for alloc in self._allocations.values())

            # Check availability
            cpu_available = (self.total_cpu - allocated_cpu) >= required_cpu
            memory_available = (self.total_memory_mb - allocated_memory_mb) >= required_memory_mb

            available = cpu_available and memory_available

            log.debug(f"Resource availability check: CPU {required_cpu}/{self.total_cpu - allocated_cpu} " f"Memory {required_memory_mb}MB/{self.total_memory_mb - allocated_memory_mb}MB - {'✓' if available else '✗'}")

            return available

        except Exception as e:
            log.error(f"Error checking resource availability: {e}")
            return False

    async def allocate_resources(self, resource_limits: dict[str, str]) -> dict[str, str]:
        """Allocate resources for a lab instance.

        Args:
            resource_limits: Dictionary with resource requirements

        Returns:
            Allocation dictionary that can be stored in resource status

        Raises:
            ValueError: If resources are not available or limits are invalid
        """
        try:
            required_cpu, required_memory_mb = self._parse_resource_limits(resource_limits)

            # Check availability first
            if not await self.check_availability(resource_limits):
                # Calculate what's available for better error message
                allocated_cpu = sum(alloc.cpu for alloc in self._allocations.values())
                allocated_memory_mb = sum(alloc.memory_mb for alloc in self._allocations.values())
                available_cpu = self.total_cpu - allocated_cpu
                available_memory_mb = self.total_memory_mb - allocated_memory_mb

                raise ValueError(f"Insufficient resources available. " f"Requested: {required_cpu} CPU, {required_memory_mb}MB memory. " f"Available: {available_cpu} CPU, {available_memory_mb}MB memory.")

            # Create allocation
            self._allocation_counter += 1
            allocation_id = f"alloc-{self._allocation_counter:06d}"

            allocation = ResourceAllocation(allocation_id=allocation_id, cpu=required_cpu, memory_mb=required_memory_mb, allocated_at=datetime.now(timezone.utc), metadata={"original_limits": str(resource_limits)})

            # Store allocation
            self._allocations[allocation_id] = allocation

            log.info(f"Allocated resources {allocation_id}: {required_cpu} CPU, {required_memory_mb}MB memory")

            return allocation.to_dict()

        except Exception as e:
            log.error(f"Error allocating resources: {e}")
            raise

    async def release_resources(self, allocation_data: dict[str, str]) -> None:
        """Release previously allocated resources.

        Args:
            allocation_data: Allocation dictionary returned by allocate_resources
        """
        try:
            if not allocation_data or "allocation_id" not in allocation_data:
                log.warning("Invalid allocation data provided for release")
                return

            allocation_id = allocation_data["allocation_id"]

            if allocation_id in self._allocations:
                allocation = self._allocations.pop(allocation_id)
                log.info(f"Released resources {allocation_id}: {allocation.cpu} CPU, {allocation.memory_mb}MB memory")
            else:
                log.warning(f"Allocation {allocation_id} not found for release")

        except Exception as e:
            log.error(f"Error releasing resources: {e}")

    def _parse_resource_limits(self, resource_limits: dict[str, str]) -> tuple[float, int]:
        """Parse resource limits into CPU cores and memory MB.

        Args:
            resource_limits: Dictionary with resource requirements

        Returns:
            Tuple of (cpu_cores, memory_mb)

        Raises:
            ValueError: If resource limits are invalid
        """
        if not resource_limits:
            raise ValueError("Resource limits cannot be empty")

        # Parse CPU
        cpu_str = resource_limits.get("cpu", "1")
        try:
            cpu = float(cpu_str)
            if cpu <= 0:
                raise ValueError(f"CPU must be positive, got: {cpu}")
            if cpu > self.total_cpu:
                raise ValueError(f"CPU request {cpu} exceeds maximum {self.total_cpu}")
        except ValueError as e:
            if "float" in str(e):
                raise ValueError(f"Invalid CPU format: {cpu_str}")
            raise

        # Parse memory
        memory_str = resource_limits.get("memory", "1Gi")
        try:
            if memory_str.endswith("Gi"):
                memory_gb = float(memory_str[:-2])
                memory_mb = int(memory_gb * 1024)
            elif memory_str.endswith("Mi"):
                memory_mb = int(memory_str[:-2])
            elif memory_str.endswith("G"):
                memory_gb = float(memory_str[:-1])
                memory_mb = int(memory_gb * 1024)
            elif memory_str.endswith("M"):
                memory_mb = int(memory_str[:-1])
            else:
                # Assume MB if no unit
                memory_mb = int(memory_str)

            if memory_mb <= 0:
                raise ValueError(f"Memory must be positive, got: {memory_mb}MB")
            if memory_mb > self.total_memory_mb:
                raise ValueError(f"Memory request {memory_mb}MB exceeds maximum {self.total_memory_mb}MB")

        except ValueError as e:
            if "invalid literal" in str(e) or "float" in str(e):
                raise ValueError(f"Invalid memory format: {memory_str}")
            raise

        return cpu, memory_mb

    # Utility methods for monitoring and debugging

    def get_resource_usage(self) -> dict[str, float]:
        """Get current resource usage statistics.

        Returns:
            Dictionary with usage information
        """
        allocated_cpu = sum(alloc.cpu for alloc in self._allocations.values())
        allocated_memory_mb = sum(alloc.memory_mb for alloc in self._allocations.values())

        return {"total_cpu": self.total_cpu, "allocated_cpu": allocated_cpu, "available_cpu": self.total_cpu - allocated_cpu, "cpu_utilization": (allocated_cpu / self.total_cpu) * 100, "total_memory_mb": self.total_memory_mb, "allocated_memory_mb": allocated_memory_mb, "available_memory_mb": self.total_memory_mb - allocated_memory_mb, "memory_utilization": (allocated_memory_mb / self.total_memory_mb) * 100, "active_allocations": len(self._allocations)}

    def get_active_allocations(self) -> dict[str, dict[str, str]]:
        """Get information about all active allocations.

        Returns:
            Dictionary mapping allocation IDs to allocation info
        """
        return {alloc_id: alloc.to_dict() for alloc_id, alloc in self._allocations.items()}

    async def cleanup_expired_allocations(self, max_age_hours: int = 24) -> int:
        """Clean up allocations older than the specified age.

        Args:
            max_age_hours: Maximum age in hours before allocation is considered expired

        Returns:
            Number of allocations cleaned up
        """
        from datetime import timedelta

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        expired_allocations = [alloc_id for alloc_id, alloc in self._allocations.items() if alloc.allocated_at < cutoff_time]

        cleaned_up = 0
        for alloc_id in expired_allocations:
            allocation = self._allocations.pop(alloc_id)
            log.warning(f"Cleaned up expired allocation {alloc_id} " f"(allocated at {allocation.allocated_at}, age: {datetime.now(timezone.utc) - allocation.allocated_at})")
            cleaned_up += 1

        if cleaned_up > 0:
            log.info(f"Cleaned up {cleaned_up} expired allocations")

        return cleaned_up
