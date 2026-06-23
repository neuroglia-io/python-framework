"""LabWorker Resource Controller.

This module implements the resource controller for LabWorker resources,
handling the complete lifecycle from EC2 provisioning through CML licensing
to lab hosting and eventual termination.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from domain.resources.lab_worker import (
    LabWorker,
    LabWorkerCondition,
    LabWorkerConditionType,
    LabWorkerPhase,
    LabWorkerSpec,
    LabWorkerStatus,
    ResourceCapacity,
)
from integration.services import CloudProviderSPI, InstanceOperationError
from integration.services.providers.cml_client_service import (
    CmlAuthenticationError,
    CmlClientService,
    CmlLicensingError,
)

from neuroglia.data.resources.controller import (
    ReconciliationResult,
    ResourceControllerBase,
)
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublisher,
)

log = logging.getLogger(__name__)


class LabWorkerController(ResourceControllerBase[LabWorkerSpec, LabWorkerStatus]):
    """Controller for reconciling LabWorker resources to their desired state."""

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        cloud_provider: CloudProviderSPI,
        cml_client: CmlClientService,
        event_publisher: Optional[CloudEventPublisher] = None,
    ):
        super().__init__(service_provider, event_publisher)
        self.cloud_provider = cloud_provider
        self.cml_client = cml_client

        # Set finalizer for cleanup
        self.finalizer_name = "lab-worker-controller.neuroglia.io"

    async def _do_reconcile(self, resource: LabWorker) -> ReconciliationResult:
        """Implement the actual reconciliation logic for LabWorkers."""
        current_phase = resource.status.phase
        resource_name = f"{resource.metadata.namespace}/{resource.metadata.name}"

        log.debug(f"Reconciling LabWorker {resource_name} in phase {current_phase}")

        try:
            # Handle different phases
            if current_phase == LabWorkerPhase.PENDING:
                return await self._reconcile_pending_phase(resource)

            elif current_phase == LabWorkerPhase.PROVISIONING_EC2:
                return await self._reconcile_provisioning_ec2_phase(resource)

            elif current_phase == LabWorkerPhase.EC2_READY:
                return await self._reconcile_ec2_ready_phase(resource)

            elif current_phase == LabWorkerPhase.STARTING:
                return await self._reconcile_starting_phase(resource)

            elif current_phase == LabWorkerPhase.READY_UNLICENSED:
                return await self._reconcile_ready_unlicensed_phase(resource)

            elif current_phase == LabWorkerPhase.LICENSING:
                return await self._reconcile_licensing_phase(resource)

            elif current_phase == LabWorkerPhase.READY:
                return await self._reconcile_ready_phase(resource)

            elif current_phase == LabWorkerPhase.ACTIVE:
                return await self._reconcile_active_phase(resource)

            elif current_phase == LabWorkerPhase.DRAINING:
                return await self._reconcile_draining_phase(resource)

            elif current_phase == LabWorkerPhase.UNLICENSING:
                return await self._reconcile_unlicensing_phase(resource)

            elif current_phase == LabWorkerPhase.STOPPING:
                return await self._reconcile_stopping_phase(resource)

            elif current_phase == LabWorkerPhase.TERMINATING_EC2:
                return await self._reconcile_terminating_ec2_phase(resource)

            elif current_phase in [LabWorkerPhase.TERMINATED, LabWorkerPhase.FAILED]:
                # Terminal states - no reconciliation needed
                return ReconciliationResult.success("Resource is in terminal state")

            else:
                return ReconciliationResult.failed(ValueError(f"Unknown phase: {current_phase}"), f"Unknown phase {current_phase}")

        except Exception as e:
            log.error(f"Reconciliation failed for {resource_name}: {e}", exc_info=True)
            resource.status.error_message = str(e)
            resource.status.error_count += 1
            return ReconciliationResult.failed(e, f"Reconciliation error: {str(e)}")

    async def finalize(self, resource: LabWorker) -> bool:
        """
        Clean up resources before deletion.

        Ensures EC2 instance is terminated and CML resources are cleaned up.
        """
        log.info(f"Finalizing LabWorker {resource.metadata.name}")

        try:
            # If EC2 instance exists, terminate it
            if resource.status.ec2_instance_id:
                log.info(f"Terminating EC2 instance {resource.status.ec2_instance_id}")
                try:
                    await self.cloud_provider.terminate_instance(resource.status.ec2_instance_id)
                    await self.cloud_provider.wait_for_instance_terminated(resource.status.ec2_instance_id, timeout_seconds=300)
                except InstanceOperationError as e:
                    log.warning(f"Error during EC2 termination: {e}")

            log.info(f"Finalization complete for {resource.metadata.name}")
            return True

        except Exception as e:
            log.error(f"Finalization failed for {resource.metadata.name}: {e}")
            return False

    # Phase-specific reconciliation methods

    async def _reconcile_pending_phase(self, resource: LabWorker) -> ReconciliationResult:
        """Reconcile a LabWorker in PENDING phase."""
        log.info(f"Starting EC2 provisioning for {resource.metadata.name}")

        # Validate specification
        validation_errors = resource.spec.validate()
        if validation_errors:
            error_msg = f"Invalid specification: {'; '.join(validation_errors)}"
            await self._transition_to_failed(resource, error_msg)
            return ReconciliationResult.failed(ValueError(error_msg), error_msg)

        # Transition to provisioning
        if resource.transition_to_phase(LabWorkerPhase.PROVISIONING_EC2, "StartingProvisioning"):
            resource.status.provisioning_started = datetime.now()
            return ReconciliationResult.success("Transitioned to provisioning phase")

        return ReconciliationResult.failed(ValueError("Failed to transition to PROVISIONING_EC2"), "State machine rejected transition")

    async def _reconcile_provisioning_ec2_phase(self, resource: LabWorker) -> ReconciliationResult:
        """Reconcile a LabWorker in PROVISIONING_EC2 phase."""

        # If instance already exists, check its status
        if resource.status.ec2_instance_id:
            try:
                instance_info = await self.cloud_provider.get_instance_info(resource.status.ec2_instance_id)

                if instance_info.state == "running":
                    # Update status
                    resource.status.ec2_state = "running"
                    resource.status.ec2_public_ip = instance_info.public_ip
                    resource.status.ec2_private_ip = instance_info.private_ip
                    resource.status.provisioning_completed = datetime.now()

                    # Add condition
                    resource.status.add_condition(LabWorkerCondition(type=LabWorkerConditionType.EC2_PROVISIONED, status=True, last_transition=datetime.now(), reason="InstanceRunning", message=f"EC2 instance {instance_info.instance_id} is running"))

                    # Transition to EC2_READY
                    resource.transition_to_phase(LabWorkerPhase.EC2_READY, "EC2InstanceReady")
                    return ReconciliationResult.success("EC2 instance is ready")

                elif instance_info.state == "pending":
                    # Still starting up
                    resource.status.ec2_state = "pending"
                    return ReconciliationResult.requeue_after(timedelta(seconds=30), "Waiting for EC2 instance to start")

                else:
                    # Unexpected state
                    error_msg = f"EC2 instance in unexpected state: {instance_info.state}"
                    await self._transition_to_failed(resource, error_msg)
                    return ReconciliationResult.failed(ValueError(error_msg), error_msg)

            except InstanceOperationError as e:
                error_msg = f"Error checking EC2 instance: {str(e)}"
                log.error(error_msg)
                await self._transition_to_failed(resource, error_msg)
                return ReconciliationResult.failed(e, error_msg)

        # No instance yet - provision it
        try:
            instance_info = await self.cloud_provider.provision_instance(config=resource.spec.aws_config, worker_name=resource.metadata.name, worker_namespace=resource.metadata.namespace)

            # Update status
            resource.status.ec2_instance_id = instance_info.instance_id
            resource.status.ec2_state = instance_info.state
            resource.status.ec2_private_ip = instance_info.private_ip
            resource.status.ec2_public_ip = instance_info.public_ip

            log.info(f"EC2 instance {instance_info.instance_id} provisioned for {resource.metadata.name}")

            # Wait for it to be running
            return ReconciliationResult.requeue_after(timedelta(seconds=30), "EC2 instance provisioning initiated")

        except InstanceOperationError as e:
            error_msg = f"Failed to provision EC2 instance: {str(e)}"
            log.error(error_msg)
            await self._transition_to_failed(resource, error_msg)
            return ReconciliationResult.failed(e, error_msg)

    async def _reconcile_ec2_ready_phase(self, resource: LabWorker) -> ReconciliationResult:
        """Reconcile a LabWorker in EC2_READY phase."""
        log.info(f"EC2 instance ready for {resource.metadata.name}, waiting for CML to start")

        # Build CML API URL
        if not resource.status.ec2_public_ip:
            return ReconciliationResult.requeue_after(timedelta(seconds=30), "Waiting for public IP assignment")

        resource.status.cml_api_url = f"http://{resource.status.ec2_public_ip}/api/v0"

        # Transition to STARTING phase
        if resource.transition_to_phase(LabWorkerPhase.STARTING, "StartingCML"):
            # Give CML some time to boot
            return ReconciliationResult.requeue_after(timedelta(minutes=3), "CML services are starting up")

        return ReconciliationResult.failed(ValueError("Failed to transition to STARTING"), "State machine rejected transition")

    async def _reconcile_starting_phase(self, resource: LabWorker) -> ReconciliationResult:
        """Reconcile a LabWorker in STARTING phase."""

        if not resource.status.cml_api_url:
            error_msg = "CML API URL not set"
            await self._transition_to_failed(resource, error_msg)
            return ReconciliationResult.failed(ValueError(error_msg), error_msg)

        # Try to authenticate to CML
        try:
            auth_token = await self.cml_client.authenticate(base_url=resource.status.cml_api_url, username=resource.spec.cml_config.admin_username, password=resource.spec.cml_config.admin_password or "admin")

            # Check if system is ready
            system_ready = await self.cml_client.check_system_ready(base_url=resource.status.cml_api_url, token=auth_token.token)

            if system_ready:
                # Get system information
                system_info = await self.cml_client.get_system_information(base_url=resource.status.cml_api_url, token=auth_token.token)

                resource.status.cml_version = system_info.get("version")
                resource.status.cml_ready = True

                # Add condition
                resource.status.add_condition(LabWorkerCondition(type=LabWorkerConditionType.CML_READY, status=True, last_transition=datetime.now(), reason="CMLSystemReady", message=f"CML version {resource.status.cml_version} is ready"))

                # Get initial capacity information
                await self._update_capacity_info(resource, auth_token.token)

                # Check if we should auto-license
                if resource.spec.auto_license and resource.spec.cml_config.license_token:
                    # Transition to LICENSING
                    resource.transition_to_phase(LabWorkerPhase.LICENSING, "AutoLicensingEnabled")
                    return ReconciliationResult.success("CML ready, starting auto-licensing")
                else:
                    # Transition to READY_UNLICENSED
                    resource.transition_to_phase(LabWorkerPhase.READY_UNLICENSED, "CMLReadyUnlicensed")
                    return ReconciliationResult.success("CML ready in unlicensed mode")

            else:
                # System not ready yet
                return ReconciliationResult.requeue_after(timedelta(seconds=30), "CML system not ready yet")

        except CmlAuthenticationError as e:
            # CML might still be booting
            log.warning(f"Authentication failed (CML may still be starting): {e}")
            return ReconciliationResult.requeue_after(timedelta(seconds=30), "Waiting for CML authentication to be available")
        except Exception as e:
            # Check for timeout - if we've been trying too long, fail
            if resource.status.provisioning_started:
                elapsed = datetime.now() - resource.status.provisioning_started
                if elapsed > timedelta(minutes=15):
                    error_msg = f"CML startup timeout after {elapsed.total_seconds():.0f}s: {str(e)}"
                    await self._transition_to_failed(resource, error_msg)
                    return ReconciliationResult.failed(TimeoutError(error_msg), error_msg)

            log.warning(f"Error during CML startup check: {e}")
            return ReconciliationResult.requeue_after(timedelta(seconds=30), "Retrying CML startup check")

    async def _reconcile_ready_unlicensed_phase(self, resource: LabWorker) -> ReconciliationResult:
        """Reconcile a LabWorker in READY_UNLICENSED phase."""

        # Perform health check
        await self._perform_health_check(resource)

        # Update capacity and utilization
        await self._update_capacity_and_utilization(resource)

        # Check if we should license
        if resource.spec.auto_license and resource.spec.cml_config.license_token and resource.spec.desired_phase == LabWorkerPhase.READY:
            # Transition to LICENSING
            resource.transition_to_phase(LabWorkerPhase.LICENSING, "LicensingRequested")
            return ReconciliationResult.success("Starting licensing process")

        # Check if any labs were added (transition to ACTIVE)
        if resource.status.active_lab_count > 0:
            resource.transition_to_phase(LabWorkerPhase.ACTIVE, "LabsHosted")
            return ReconciliationResult.success("Transitioned to ACTIVE (hosting labs)")

        # Regular monitoring
        return ReconciliationResult.requeue_after(timedelta(minutes=2), "Monitoring worker in unlicensed mode")

    async def _reconcile_licensing_phase(self, resource: LabWorker) -> ReconciliationResult:
        """Reconcile a LabWorker in LICENSING phase."""

        if not resource.spec.cml_config.license_token:
            error_msg = "No license token configured"
            await self._transition_to_failed(resource, error_msg)
            return ReconciliationResult.failed(ValueError(error_msg), error_msg)

        try:
            # Authenticate
            auth_token = await self.cml_client.authenticate(base_url=resource.status.cml_api_url, username=resource.spec.cml_config.admin_username, password=resource.spec.cml_config.admin_password or "admin")

            # Apply license
            success = await self.cml_client.set_license(base_url=resource.status.cml_api_url, token=auth_token.token, license_token=resource.spec.cml_config.license_token)

            if success:
                # Verify license was applied
                license_info = await self.cml_client.get_license_status(base_url=resource.status.cml_api_url, token=auth_token.token)

                if license_info.is_licensed:
                    resource.status.cml_licensed = True

                    # Add condition
                    resource.status.add_condition(LabWorkerCondition(type=LabWorkerConditionType.LICENSED, status=True, last_transition=datetime.now(), reason="LicenseApplied", message=f"Licensed for {license_info.max_nodes} nodes"))

                    # Update capacity with licensed limits
                    await self._update_capacity_info(resource, auth_token.token)

                    # Transition to READY
                    resource.transition_to_phase(LabWorkerPhase.READY, "LicensingComplete")
                    return ReconciliationResult.success("Licensing completed successfully")

                else:
                    error_msg = "License applied but not showing as licensed"
                    log.error(error_msg)
                    return ReconciliationResult.requeue_after(timedelta(seconds=30), "Waiting for license activation")

            else:
                error_msg = "Failed to apply license"
                log.error(error_msg)
                await self._transition_to_failed(resource, error_msg)
                return ReconciliationResult.failed(CmlLicensingError(error_msg), error_msg)

        except Exception as e:
            error_msg = f"Error during licensing: {str(e)}"
            log.error(error_msg)
            await self._transition_to_failed(resource, error_msg)
            return ReconciliationResult.failed(e, error_msg)

    async def _reconcile_ready_phase(self, resource: LabWorker) -> ReconciliationResult:
        """Reconcile a LabWorker in READY phase."""

        # Perform health check
        await self._perform_health_check(resource)

        # Update capacity and utilization
        await self._update_capacity_and_utilization(resource)

        # Check if any labs were added (transition to ACTIVE)
        if resource.status.active_lab_count > 0:
            resource.transition_to_phase(LabWorkerPhase.ACTIVE, "LabsHosted")
            return ReconciliationResult.success("Transitioned to ACTIVE (hosting labs)")

        # Check if draining was requested
        if resource.spec.desired_phase == LabWorkerPhase.DRAINING:
            resource.transition_to_phase(LabWorkerPhase.DRAINING, "DrainingRequested")
            return ReconciliationResult.success("Transitioned to DRAINING")

        # Regular monitoring
        return ReconciliationResult.requeue_after(timedelta(minutes=2), "Monitoring ready worker")

    async def _reconcile_active_phase(self, resource: LabWorker) -> ReconciliationResult:
        """Reconcile a LabWorker in ACTIVE phase."""

        # Perform health check
        health_ok = await self._perform_health_check(resource)
        if not health_ok:
            error_msg = "Health check failed for active worker"
            log.error(error_msg)
            await self._transition_to_failed(resource, error_msg)
            return ReconciliationResult.failed(RuntimeError(error_msg), error_msg)

        # Update capacity and utilization
        await self._update_capacity_and_utilization(resource)

        # Check if all labs were removed (transition back to READY)
        if resource.status.active_lab_count == 0:
            if resource.status.cml_licensed:
                resource.transition_to_phase(LabWorkerPhase.READY, "NoLabsHosted")
            else:
                resource.transition_to_phase(LabWorkerPhase.READY_UNLICENSED, "NoLabsHosted")
            return ReconciliationResult.success("Transitioned back to READY (no labs)")

        # Check if draining was requested
        if resource.spec.desired_phase == LabWorkerPhase.DRAINING:
            resource.transition_to_phase(LabWorkerPhase.DRAINING, "DrainingRequested")
            return ReconciliationResult.success("Transitioned to DRAINING")

        # Regular monitoring
        return ReconciliationResult.requeue_after(timedelta(minutes=1), "Monitoring active worker")

    async def _reconcile_draining_phase(self, resource: LabWorker) -> ReconciliationResult:
        """Reconcile a LabWorker in DRAINING phase."""

        # Update capacity and utilization
        await self._update_capacity_and_utilization(resource)

        # Check if all labs are finished
        if resource.status.active_lab_count == 0:
            log.info(f"All labs drained from {resource.metadata.name}")

            # Check desired next phase
            if resource.spec.desired_phase in [LabWorkerPhase.STOPPING, LabWorkerPhase.TERMINATED]:
                # Start shutdown process
                if resource.status.cml_licensed:
                    resource.transition_to_phase(LabWorkerPhase.UNLICENSING, "DrainingComplete")
                    return ReconciliationResult.success("Starting unlicensing process")
                else:
                    resource.transition_to_phase(LabWorkerPhase.STOPPING, "DrainingComplete")
                    return ReconciliationResult.success("Starting shutdown process")
            else:
                # Return to ready state
                if resource.status.cml_licensed:
                    resource.transition_to_phase(LabWorkerPhase.READY, "DrainingComplete")
                else:
                    resource.transition_to_phase(LabWorkerPhase.READY_UNLICENSED, "DrainingComplete")
                return ReconciliationResult.success("Returned to READY state")

        # Still draining
        log.info(f"Draining worker {resource.metadata.name}: {resource.status.active_lab_count} labs remaining")
        return ReconciliationResult.requeue_after(timedelta(minutes=1), f"Waiting for {resource.status.active_lab_count} labs to finish")

    async def _reconcile_unlicensing_phase(self, resource: LabWorker) -> ReconciliationResult:
        """Reconcile a LabWorker in UNLICENSING phase."""

        try:
            # Authenticate
            auth_token = await self.cml_client.authenticate(base_url=resource.status.cml_api_url, username=resource.spec.cml_config.admin_username, password=resource.spec.cml_config.admin_password or "admin")

            # Remove license
            success = await self.cml_client.remove_license(base_url=resource.status.cml_api_url, token=auth_token.token)

            if success:
                resource.status.cml_licensed = False

                # Remove licensed condition
                resource.status.conditions = [c for c in resource.status.conditions if c.type != LabWorkerConditionType.LICENSED]

                log.info(f"License removed from {resource.metadata.name}")

                # Check next phase
                if resource.spec.desired_phase in [LabWorkerPhase.STOPPING, LabWorkerPhase.TERMINATED]:
                    resource.transition_to_phase(LabWorkerPhase.STOPPING, "UnlicensingComplete")
                    return ReconciliationResult.success("Starting shutdown")
                else:
                    resource.transition_to_phase(LabWorkerPhase.READY_UNLICENSED, "UnlicensingComplete")
                    return ReconciliationResult.success("Returned to unlicensed mode")

            else:
                log.warning(f"Failed to remove license from {resource.metadata.name}")
                # Continue anyway
                resource.transition_to_phase(LabWorkerPhase.STOPPING, "UnlicensingFailed")
                return ReconciliationResult.success("Continuing to shutdown despite unlicensing failure")

        except Exception as e:
            log.error(f"Error during unlicensing: {e}")
            # Continue to shutdown anyway
            resource.transition_to_phase(LabWorkerPhase.STOPPING, "UnlicensingError")
            return ReconciliationResult.success("Continuing to shutdown despite error")

    async def _reconcile_stopping_phase(self, resource: LabWorker) -> ReconciliationResult:
        """Reconcile a LabWorker in STOPPING phase."""

        log.info(f"Stopping CML services for {resource.metadata.name}")

        # In CML, there's no explicit "stop" API - we just move to terminating EC2
        resource.status.cml_ready = False

        # Transition to terminating EC2
        resource.transition_to_phase(LabWorkerPhase.TERMINATING_EC2, "CMLStopped")
        return ReconciliationResult.success("CML stopped, terminating EC2 instance")

    async def _reconcile_terminating_ec2_phase(self, resource: LabWorker) -> ReconciliationResult:
        """Reconcile a LabWorker in TERMINATING_EC2 phase."""

        if not resource.status.ec2_instance_id:
            # No instance to terminate
            resource.transition_to_phase(LabWorkerPhase.TERMINATED, "NoEC2Instance")
            return ReconciliationResult.success("No EC2 instance to terminate")

        try:
            # Check current instance state
            instance_info = await self.cloud_provider.get_instance_info(resource.status.ec2_instance_id)

            if instance_info.state == "terminated":
                # Already terminated
                resource.status.ec2_state = "terminated"
                resource.transition_to_phase(LabWorkerPhase.TERMINATED, "EC2Terminated")
                return ReconciliationResult.success("EC2 instance terminated")

            elif instance_info.state in ["stopping", "shutting-down"]:
                # Still terminating
                return ReconciliationResult.requeue_after(timedelta(seconds=30), "Waiting for EC2 instance to terminate")

            else:
                # Initiate termination
                await self.cloud_provider.terminate_instance(resource.status.ec2_instance_id)
                resource.status.ec2_state = "terminating"
                log.info(f"Initiated termination of EC2 instance {resource.status.ec2_instance_id}")

                return ReconciliationResult.requeue_after(timedelta(seconds=30), "EC2 termination initiated")

        except InstanceOperationError as e:
            # Instance might already be gone
            log.warning(f"Error terminating EC2 instance: {e}")
            resource.transition_to_phase(LabWorkerPhase.TERMINATED, "EC2TerminationError")
            return ReconciliationResult.success("Marked as terminated despite error")

    # Helper methods

    async def _transition_to_failed(self, resource: LabWorker, error_message: str) -> None:
        """Transition a worker to FAILED state with error message."""
        resource.status.error_message = error_message
        resource.status.error_count += 1
        resource.transition_to_phase(LabWorkerPhase.FAILED, "Error")
        log.error(f"Worker {resource.metadata.name} transitioned to FAILED: {error_message}")

    async def _perform_health_check(self, resource: LabWorker) -> bool:
        """Perform health check on the CML worker."""
        if not resource.status.cml_api_url:
            return False

        try:
            auth_token = await self.cml_client.authenticate(base_url=resource.status.cml_api_url, username=resource.spec.cml_config.admin_username, password=resource.spec.cml_config.admin_password or "admin")

            is_healthy = await self.cml_client.health_check(base_url=resource.status.cml_api_url, token=auth_token.token)

            resource.status.last_health_check = datetime.now()

            # Update health condition
            resource.status.add_condition(LabWorkerCondition(type=LabWorkerConditionType.HEALTH_CHECK_PASSED, status=is_healthy, last_transition=datetime.now(), reason="HealthCheckComplete", message="Health check passed" if is_healthy else "Health check failed"))

            return is_healthy

        except Exception as e:
            log.warning(f"Health check failed for {resource.metadata.name}: {e}")
            resource.status.add_condition(LabWorkerCondition(type=LabWorkerConditionType.HEALTH_CHECK_PASSED, status=False, last_transition=datetime.now(), reason="HealthCheckError", message=str(e)))
            return False

    async def _update_capacity_info(self, resource: LabWorker, auth_token: str) -> None:
        """Update resource capacity information from CML."""
        try:
            stats = await self.cml_client.get_system_stats(base_url=resource.status.cml_api_url, token=auth_token)

            # Get license info to determine max nodes
            license_info = await self.cml_client.get_license_status(base_url=resource.status.cml_api_url, token=auth_token)

            # Update or create capacity
            if not resource.status.capacity:
                resource.status.capacity = ResourceCapacity(total_cpu_cores=stats.cpu_usage_percent / 100.0 * 48.0, total_memory_mb=stats.memory_total_mb, total_storage_gb=stats.disk_total_gb, max_concurrent_labs=20)  # Estimate based on m5zn.metal
            else:
                resource.status.capacity.total_memory_mb = stats.memory_total_mb
                resource.status.capacity.total_storage_gb = stats.disk_total_gb

        except Exception as e:
            log.warning(f"Error updating capacity info: {e}")

    async def _update_capacity_and_utilization(self, resource: LabWorker) -> None:
        """Update capacity and current utilization from CML."""
        try:
            auth_token = await self.cml_client.authenticate(base_url=resource.status.cml_api_url, username=resource.spec.cml_config.admin_username, password=resource.spec.cml_config.admin_password or "admin")

            stats = await self.cml_client.get_system_stats(base_url=resource.status.cml_api_url, token=auth_token)

            if resource.status.capacity:
                # Update utilization
                resource.status.capacity.allocated_memory_mb = stats.memory_used_mb
                resource.status.capacity.allocated_storage_gb = stats.disk_used_gb

            # Update lab count from CML
            resource.status.active_lab_count = stats.lab_count

        except Exception as e:
            log.warning(f"Error updating utilization: {e}")
