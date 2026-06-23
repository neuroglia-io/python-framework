"""Container service for managing lab instance containers.

This service provides container lifecycle management for lab instances,
including creation, health monitoring, and cleanup operations.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

log = logging.getLogger(__name__)


@dataclass
class ContainerInfo:
    """Information about a created container."""

    container_id: str
    access_url: str
    internal_ip: str
    status: str


class ContainerService:
    """Service for managing lab instance containers."""

    def __init__(self):
        # In a real implementation, this would connect to Docker, Kubernetes, etc.
        self._containers: dict[str, ContainerInfo] = {}
        self._next_container_id = 1
        self._base_port = 8080
        self._container_status_overrides: dict[str, str] = {}  # For demo purposes

    async def create_container(self, template: str, resources: dict[str, str], environment: dict[str, str], student_email: str) -> ContainerInfo:
        """Create a new container for a lab instance."""

        try:
            # Generate unique container ID
            container_id = f"lab-{uuid4().hex[:8]}"

            # Simulate container creation
            log.info(f"Creating container {container_id} with template {template}")

            # In real implementation, this would:
            # 1. Pull the lab template image
            # 2. Create container with resource limits
            # 3. Set environment variables
            # 4. Expose ports for access
            # 5. Start the container

            # Simulate port allocation
            port = self._next_port
            self._next_port += 1

            access_url = f"http://localhost:{port}"
            internal_ip = f"10.0.0.{port - self._base_port + 10}"

            container_info = ContainerInfo(container_id=container_id, access_url=access_url, internal_ip=internal_ip, status="creating")

            self._containers[container_id] = container_info

            # Simulate container startup time
            await asyncio.sleep(2)

            # Update status to running
            container_info.status = "running"

            log.info(f"Container {container_id} created successfully at {access_url}")
            return container_info

        except Exception as e:
            log.error(f"Failed to create container: {e}")
            raise

    async def get_access_url(self, container_id: str) -> Optional[str]:
        """Get the access URL for a container."""
        container = self._containers.get(container_id)
        return container.access_url if container else None

    async def is_container_ready(self, container_id: str) -> bool:
        """Check if container is ready to accept connections."""
        container = self._containers.get(container_id)
        if not container:
            return False

        # In real implementation, this would:
        # 1. Check container status
        # 2. Perform health check on exposed ports
        # 3. Verify application is responding

        return container.status in ["running", "healthy"]

    async def is_container_healthy(self, container_id: str) -> bool:
        """Check if container is healthy."""
        container = self._containers.get(container_id)
        if not container:
            return False

        # In real implementation, this would:
        # 1. Execute health check commands
        # 2. Check resource usage
        # 3. Verify application responsiveness

        return container.status == "running"

    async def stop_container(self, container_id: str, graceful: bool = True) -> None:
        """Stop a container."""
        container = self._containers.get(container_id)
        if not container:
            log.warning(f"Container {container_id} not found")
            return

        try:
            log.info(f"Stopping container {container_id} (graceful={graceful})")

            if graceful:
                # In real implementation:
                # 1. Send SIGTERM to allow graceful shutdown
                # 2. Wait for specified timeout
                # 3. Send SIGKILL if still running

                container.status = "stopping"
                await asyncio.sleep(1)  # Simulate graceful shutdown time

            container.status = "stopped"

            log.info(f"Container {container_id} stopped")

        except Exception as e:
            log.error(f"Failed to stop container {container_id}: {e}")
            raise

    async def is_container_stopped(self, container_id: str) -> bool:
        """Check if container is completely stopped."""
        container = self._containers.get(container_id)
        if not container:
            return True  # Consider non-existent containers as stopped

        return container.status in ["stopped", "removed"]

    async def remove_container(self, container_id: str) -> None:
        """Remove a container and clean up resources."""
        try:
            container = self._containers.get(container_id)
            if container:
                # Ensure container is stopped first
                if container.status not in ["stopped", "removed"]:
                    await self.stop_container(container_id, graceful=False)

                # In real implementation:
                # 1. Remove container from Docker/Kubernetes
                # 2. Clean up volumes and networks
                # 3. Release allocated ports

                container.status = "removed"
                del self._containers[container_id]

                log.info(f"Container {container_id} removed")

        except Exception as e:
            log.error(f"Failed to remove container {container_id}: {e}")
            raise

    async def get_container_info(self, container_id: str) -> Optional[ContainerInfo]:
        """Get information about a container."""
        return self._containers.get(container_id)

    async def list_containers(self) -> dict[str, ContainerInfo]:
        """List all managed containers."""
        return self._containers.copy()

    async def get_container_logs(self, container_id: str, tail_lines: int = 100) -> str:
        """Get container logs."""
        container = self._containers.get(container_id)
        if not container:
            return ""

        # In real implementation, this would fetch actual container logs
        return f"Simulated logs for container {container_id}\nStatus: {container.status}\nURL: {container.access_url}"

    async def set_container_status_async(self, container_id: str, status: str):
        """Set container status override for demo purposes."""
        self._container_status_overrides[container_id] = status

    async def get_container_status_async(self, container_id: str) -> str:
        """Get container status (with override support for demo)."""
        # Check for override first
        if container_id in self._container_status_overrides:
            return self._container_status_overrides[container_id]

        container = self._containers.get(container_id)
        return container.status if container else "not_found"
