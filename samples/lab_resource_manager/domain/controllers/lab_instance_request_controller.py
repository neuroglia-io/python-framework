"""Lab Instance Resource Controller.

This module implements the resource controller for LabInstanceRequest resources,
handling reconciliation logic and state transitions.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from domain.resources.lab_instance_request import (
    LabInstanceCondition,
    LabInstancePhase,
    LabInstanceRequest,
    LabInstanceRequestSpec,
    LabInstanceRequestStatus,
)
from integration.services.container_service import ContainerService
from integration.services.resource_allocator import ResourceAllocator

from neuroglia.data.resources.controller import (
    ReconciliationResult,
    ResourceControllerBase,
)
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublisher,
)

log = logging.getLogger(__name__)


class LabInstanceRequestController(ResourceControllerBase[LabInstanceRequestSpec, LabInstanceRequestStatus]):
    """Controller for reconciling LabInstanceRequest resources to their desired state."""

    def __init__(self, service_provider: ServiceProviderBase, container_service: ContainerService, resource_allocator: ResourceAllocator, event_publisher: Optional[CloudEventPublisher] = None):
        super().__init__(service_provider, event_publisher)
        self.container_service = container_service
        self.resource_allocator = resource_allocator

    async def _do_reconcile(self, resource: LabInstanceRequest) -> ReconciliationResult:
        """Implement the actual reconciliation logic for lab instances."""

        current_phase = resource.status.phase
        resource_name = f"{resource.metadata.namespace}/{resource.metadata.name}"

        log.debug(f"Reconciling lab instance {resource_name} in phase {current_phase}")

        try:
            # Handle different phases
            if current_phase == LabInstancePhase.PENDING:
                return await self._reconcile_pending_phase(resource)

            elif current_phase == LabInstancePhase.PROVISIONING:
                return await self._reconcile_provisioning_phase(resource)

            elif current_phase == LabInstancePhase.RUNNING:
                return await self._reconcile_running_phase(resource)

            elif current_phase == LabInstancePhase.STOPPING:
                return await self._reconcile_stopping_phase(resource)

            elif current_phase in [LabInstancePhase.COMPLETED, LabInstancePhase.FAILED, LabInstancePhase.EXPIRED]:
                # Terminal states - no reconciliation needed
                return ReconciliationResult.success("Resource is in terminal state")

            else:
                return ReconciliationResult.failed(ValueError(f"Unknown phase: {current_phase}"), f"Unknown phase {current_phase}")

        except Exception as e:
            log.error(f"Reconciliation failed for {resource_name}: {e}")
            return ReconciliationResult.failed(e, f"Reconciliation error: {str(e)}")

    async def _reconcile_pending_phase(self, resource: LabInstanceRequest) -> ReconciliationResult:
        """Reconcile a lab instance in PENDING phase."""

        # Check if this is a scheduled lab that should start now
        if resource.is_scheduled() and not resource.should_start_now():
            scheduled_start = resource.spec.scheduled_start.isoformat()
            return ReconciliationResult.requeue_after(timedelta(minutes=1), f"Waiting for scheduled start time: {scheduled_start}")

        # Check resource availability
        resources_available = await self._check_resource_availability(resource)
        if not resources_available:
            return ReconciliationResult.requeue_after(timedelta(minutes=2), "Waiting for resources to become available")

        # Transition to provisioning phase
        await self._transition_to_provisioning(resource)
        return ReconciliationResult.success("Transitioned to provisioning phase")

    async def _reconcile_provisioning_phase(self, resource: LabInstanceRequest) -> ReconciliationResult:
        """Reconcile a lab instance in PROVISIONING phase."""

        # Check if container is ready
        container_ready = await self._check_container_readiness(resource)
        if not container_ready:
            # Check if provisioning is taking too long (timeout after 10 minutes)
            provisioning_start = resource.status.last_updated
            if datetime.now() - provisioning_start > timedelta(minutes=10):
                await self._transition_to_failed(resource, "Provisioning timeout")
                return ReconciliationResult.failed(TimeoutError("Provisioning timeout"), "Container provisioning timed out")

            return ReconciliationResult.requeue_after(timedelta(seconds=30), "Waiting for container to be ready")

        # Transition to running phase
        await self._transition_to_running(resource)
        return ReconciliationResult.success("Transitioned to running phase")

    async def _reconcile_running_phase(self, resource: LabInstanceRequest) -> ReconciliationResult:
        """Reconcile a lab instance in RUNNING phase."""

        # Check if lab instance has expired
        if resource.is_expired():
            await self._transition_to_stopping(resource, "Lab instance expired")
            return ReconciliationResult.success("Lab instance expired, initiating shutdown")

        # Check container health
        container_healthy = await self._check_container_health(resource)
        if not container_healthy:
            await self._transition_to_failed(resource, "Container health check failed")
            return ReconciliationResult.failed(RuntimeError("Container unhealthy"), "Container health check failed")

        # Schedule next health check
        return ReconciliationResult.requeue_after(timedelta(minutes=2), "Scheduled health check")

    async def _reconcile_stopping_phase(self, resource: LabInstanceRequest) -> ReconciliationResult:
        """Reconcile a lab instance in STOPPING phase."""

        # Check if cleanup is complete
        cleanup_complete = await self._check_cleanup_completion(resource)
        if cleanup_complete:
            await self._transition_to_completed(resource)
            return ReconciliationResult.success("Lab instance cleanup completed")

        # Check for cleanup timeout (5 minutes)
        stopping_start = resource.status.last_updated
        if datetime.now() - stopping_start > timedelta(minutes=5):
            await self._transition_to_failed(resource, "Cleanup timeout")
            return ReconciliationResult.failed(TimeoutError("Cleanup timeout"), "Container cleanup timed out")

        return ReconciliationResult.requeue_after(timedelta(seconds=15), "Waiting for cleanup completion")

    # State transition methods
    async def _transition_to_provisioning(self, resource: LabInstanceRequest) -> None:
        """Transition lab instance to PROVISIONING phase."""

        try:
            # Allocate resources
            allocation = await self.resource_allocator.allocate_resources(resource.spec.resource_limits)

            # Start container
            container_info = await self.container_service.create_container(template=resource.spec.lab_template, resources=allocation, environment=resource.spec.environment_variables, student_email=resource.spec.student_email)

            # Update resource status
            resource.transition_to_phase(LabInstancePhase.PROVISIONING, "ResourcesAllocated")
            resource.status.container_id = container_info.container_id
            resource.status.resource_allocation = allocation

            # Add condition
            condition = LabInstanceCondition(type="ResourcesAllocated", status=True, last_transition=datetime.now(), reason="AllocationSuccessful", message=f"Allocated resources: {allocation}")
            resource.status.add_condition(condition)

            log.info(f"Started provisioning for {resource.metadata.name}")

        except Exception as e:
            await self._transition_to_failed(resource, f"Provisioning failed: {str(e)}")
            raise

    async def _transition_to_running(self, resource: LabInstanceRequest) -> None:
        """Transition lab instance to RUNNING phase."""

        try:
            # Get container access URL
            access_url = await self.container_service.get_access_url(resource.status.container_id)

            # Update resource status
            resource.transition_to_phase(LabInstancePhase.RUNNING, "ContainerReady")
            resource.status.start_time = datetime.now()
            resource.status.access_url = access_url

            # Add condition
            condition = LabInstanceCondition(type="ContainerReady", status=True, last_transition=datetime.now(), reason="ContainerStarted", message=f"Container accessible at: {access_url}")
            resource.status.add_condition(condition)

            log.info(f"Lab instance {resource.metadata.name} is now running at {access_url}")

        except Exception as e:
            await self._transition_to_failed(resource, f"Failed to start container: {str(e)}")
            raise

    async def _transition_to_stopping(self, resource: LabInstanceRequest, reason: str) -> None:
        """Transition lab instance to STOPPING phase."""

        try:
            # Initiate graceful shutdown
            await self.container_service.stop_container(resource.status.container_id, graceful=True)

            # Update resource status
            resource.transition_to_phase(LabInstancePhase.STOPPING, reason)

            # Add condition
            condition = LabInstanceCondition(type="StoppingInitiated", status=True, last_transition=datetime.now(), reason="GracefulShutdown", message=f"Graceful shutdown initiated: {reason}")
            resource.status.add_condition(condition)

            log.info(f"Initiated shutdown for {resource.metadata.name}: {reason}")

        except Exception as e:
            await self._transition_to_failed(resource, f"Failed to stop container: {str(e)}")
            raise

    async def _transition_to_completed(self, resource: LabInstanceRequest) -> None:
        """Transition lab instance to COMPLETED phase."""

        # Release resources
        if resource.status.resource_allocation:
            await self.resource_allocator.release_resources(resource.status.resource_allocation)

        # Update resource status
        resource.transition_to_phase(LabInstancePhase.COMPLETED, "CleanupCompleted")
        resource.status.completion_time = datetime.now()

        # Add condition
        condition = LabInstanceCondition(type="CleanupCompleted", status=True, last_transition=datetime.now(), reason="SuccessfulCompletion", message="Lab instance completed successfully")
        resource.status.add_condition(condition)

        log.info(f"Lab instance {resource.metadata.name} completed successfully")

    async def _transition_to_failed(self, resource: LabInstanceRequest, error_message: str) -> None:
        """Transition lab instance to FAILED phase."""

        try:
            # Cleanup resources
            if resource.status.container_id:
                await self.container_service.stop_container(resource.status.container_id, graceful=False)

            if resource.status.resource_allocation:
                await self.resource_allocator.release_resources(resource.status.resource_allocation)

        except Exception as cleanup_error:
            log.error(f"Cleanup failed during failure handling: {cleanup_error}")

        # Update resource status
        resource.transition_to_phase(LabInstancePhase.FAILED, "ErrorOccurred")
        resource.status.error_message = error_message
        resource.status.completion_time = datetime.now()

        # Add condition
        condition = LabInstanceCondition(type="Failed", status=True, last_transition=datetime.now(), reason="ErrorOccurred", message=error_message)
        resource.status.add_condition(condition)

        log.error(f"Lab instance {resource.metadata.name} failed: {error_message}")

    # Helper methods for checking conditions
    async def _check_resource_availability(self, resource: LabInstanceRequest) -> bool:
        """Check if required resources are available."""
        return await self.resource_allocator.check_availability(resource.spec.resource_limits)

    async def _check_container_readiness(self, resource: LabInstanceRequest) -> bool:
        """Check if container is ready."""
        if not resource.status.container_id:
            return False

        return await self.container_service.is_container_ready(resource.status.container_id)

    async def _check_container_health(self, resource: LabInstanceRequest) -> bool:
        """Check if container is healthy."""
        if not resource.status.container_id:
            return False

        return await self.container_service.is_container_healthy(resource.status.container_id)

    async def _check_cleanup_completion(self, resource: LabInstanceRequest) -> bool:
        """Check if cleanup is complete."""
        if not resource.status.container_id:
            return True

        return await self.container_service.is_container_stopped(resource.status.container_id)
