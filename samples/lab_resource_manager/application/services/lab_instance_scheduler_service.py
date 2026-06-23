"""Lab Instance Scheduler Service.

This service handles background scheduling and lifecycle management of lab instances.
It monitors for scheduled lab instances and transitions them through their lifecycle.
"""

import asyncio
import logging
from typing import Optional

from domain.resources.lab_instance_request import LabInstancePhase, LabInstanceRequest
from integration.repositories.lab_instance_resource_repository import (
    LabInstanceResourceRepository,
)
from integration.services.container_service import ContainerService

from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.hosting.abstractions import HostedService

log = logging.getLogger(__name__)


class LabInstanceSchedulerService(HostedService):
    """Background service for scheduling and managing lab instance lifecycle."""

    def __init__(self, service_provider: ServiceProviderBase, repository: LabInstanceResourceRepository, container_service: ContainerService, event_bus: CloudEventBus):
        self._service_provider = service_provider
        self._repository = repository
        self._container_service = container_service
        self._event_bus = event_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._scheduler_interval = 30  # seconds
        self._cleanup_interval = 300  # 5 minutes

    async def start_async(self):
        """Start the scheduler service."""
        if self._running:
            return

        log.info("Starting Lab Instance Scheduler Service")
        self._running = True
        self._task = asyncio.create_task(self._run_scheduler_loop())

    async def stop_async(self):
        """Stop the scheduler service."""
        if not self._running:
            return

        log.info("Stopping Lab Instance Scheduler Service")
        self._running = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_scheduler_loop(self):
        """Main scheduler loop."""
        cleanup_counter = 0

        while self._running:
            try:
                # Process scheduled instances
                await self._process_scheduled_instances()

                # Process running instances
                await self._process_running_instances()

                # Periodic cleanup
                cleanup_counter += self._scheduler_interval
                if cleanup_counter >= self._cleanup_interval:
                    await self._cleanup_expired_instances()
                    cleanup_counter = 0

                # Wait before next iteration
                await asyncio.sleep(self._scheduler_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self._scheduler_interval)

    async def _process_scheduled_instances(self):
        """Process lab instances that are scheduled to start."""
        try:
            pending_instances = await self._repository.find_scheduled_pending_async()

            for instance in pending_instances:
                if instance.should_start_now():
                    await self._start_lab_instance(instance)

        except Exception as e:
            log.error(f"Error processing scheduled instances: {e}")

    async def _process_running_instances(self):
        """Monitor running instances for completion or errors."""
        try:
            running_instances = await self._repository.find_running_instances_async()

            for instance in running_instances:
                # Check if container is still running
                container_status = await self._container_service.get_container_status_async(instance.status.container_id)

                if container_status == "stopped":
                    await self._complete_lab_instance(instance)
                elif container_status == "error":
                    await self._fail_lab_instance(instance, "Container error")
                elif instance.is_expired():
                    await self._timeout_lab_instance(instance)

        except Exception as e:
            log.error(f"Error processing running instances: {e}")

    async def _cleanup_expired_instances(self):
        """Clean up expired instances."""
        try:
            expired_instances = await self._repository.find_expired_instances_async()

            for instance in expired_instances:
                if instance.status.phase == LabInstancePhase.RUNNING:
                    await self._timeout_lab_instance(instance)
                elif instance.status.phase in [LabInstancePhase.COMPLETED, LabInstancePhase.FAILED]:
                    # Clean up container if still exists
                    if instance.status.container_id:
                        await self._container_service.cleanup_container_async(instance.status.container_id)

        except Exception as e:
            log.error(f"Error during cleanup: {e}")

    async def _start_lab_instance(self, instance: LabInstanceRequest):
        """Start a lab instance."""
        try:
            log.info(f"Starting lab instance {instance.metadata.name}")

            # Transition to provisioning
            instance.transition_to_provisioning()
            await self._repository.save_async(instance)

            # Create container
            container_id = await self._container_service.create_lab_container_async(image=instance.spec.lab_template, duration_minutes=instance.spec.duration_minutes, environment=instance.spec.environment or {})

            if container_id:
                # Start container
                success = await self._container_service.start_container_async(container_id)

                if success:
                    # Transition to running
                    instance.transition_to_running(container_id)
                    await self._repository.save_async(instance)
                    log.info(f"Lab instance {instance.metadata.name} started with container {container_id}")
                else:
                    await self._fail_lab_instance(instance, "Failed to start container")
            else:
                await self._fail_lab_instance(instance, "Failed to create container")

        except Exception as e:
            log.error(f"Error starting lab instance {instance.metadata.name}: {e}")
            await self._fail_lab_instance(instance, f"Startup error: {str(e)}")

    async def _complete_lab_instance(self, instance: LabInstanceRequest):
        """Mark a lab instance as completed."""
        try:
            log.info(f"Completing lab instance {instance.metadata.name}")

            instance.transition_to_completed()
            await self._repository.save_async(instance)

            # Cleanup container
            if instance.status.container_id:
                await self._container_service.cleanup_container_async(instance.status.container_id)

        except Exception as e:
            log.error(f"Error completing lab instance {instance.metadata.name}: {e}")

    async def _fail_lab_instance(self, instance: LabInstanceRequest, error_message: str):
        """Mark a lab instance as failed."""
        try:
            log.warning(f"Failing lab instance {instance.metadata.name}: {error_message}")

            instance.transition_to_failed(error_message)
            await self._repository.save_async(instance)

            # Cleanup container if exists
            if instance.status.container_id:
                await self._container_service.cleanup_container_async(instance.status.container_id)

        except Exception as e:
            log.error(f"Error failing lab instance {instance.metadata.name}: {e}")

    async def _timeout_lab_instance(self, instance: LabInstanceRequest):
        """Handle lab instance timeout."""
        try:
            log.warning(f"Lab instance {instance.metadata.name} timed out")

            instance.transition_to_timeout()
            await self._repository.save_async(instance)

            # Force cleanup container
            if instance.status.container_id:
                await self._container_service.stop_container_async(instance.status.container_id)
                await self._container_service.cleanup_container_async(instance.status.container_id)

        except Exception as e:
            log.error(f"Error timing out lab instance {instance.metadata.name}: {e}")

    async def get_service_statistics_async(self) -> dict[str, any]:
        """Get scheduler service statistics."""
        try:
            stats = {"running": self._running, "scheduler_interval": self._scheduler_interval, "cleanup_interval": self._cleanup_interval}

            # Add phase counts
            for phase in LabInstancePhase:
                count = await self._repository.count_by_phase_async(phase)
                stats[f"instances_{phase.value.lower()}"] = count

            return stats

        except Exception as e:
            log.error(f"Error getting service statistics: {e}")
            return {"error": str(e)}
