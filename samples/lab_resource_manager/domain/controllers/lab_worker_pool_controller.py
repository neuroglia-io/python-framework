"""LabWorkerPool Resource Controller.

This module implements the resource controller for LabWorkerPool resources,
handling auto-scaling, capacity planning, and worker lifecycle management.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from domain.resources.lab_worker import LabWorker, LabWorkerPhase, LabWorkerSpec
from domain.resources.lab_worker_pool import (
    LabWorkerPool,
    LabWorkerPoolPhase,
    LabWorkerPoolSpec,
    LabWorkerPoolStatus,
    PoolCapacitySummary,
    ScalingEvent,
    WorkerInfo,
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


class LabWorkerPoolController(ResourceControllerBase[LabWorkerPoolSpec, LabWorkerPoolStatus]):
    """Controller for reconciling LabWorkerPool resources."""

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        event_publisher: Optional[CloudEventPublisher] = None,
    ):
        super().__init__(service_provider, event_publisher)
        self.finalizer_name = "lab-worker-pool-controller.neuroglia.io"

    async def _do_reconcile(self, resource: LabWorkerPool) -> ReconciliationResult:
        """Implement the actual reconciliation logic for LabWorkerPools."""
        current_phase = resource.status.phase
        resource_name = f"{resource.metadata.namespace}/{resource.metadata.name}"

        log.debug(f"Reconciling LabWorkerPool {resource_name} in phase {current_phase}")

        try:
            # Update timestamp
            resource.status.last_reconciled = datetime.now()

            # Handle different phases
            if current_phase == LabWorkerPoolPhase.PENDING:
                return await self._reconcile_pending_phase(resource)

            elif current_phase == LabWorkerPoolPhase.INITIALIZING:
                return await self._reconcile_initializing_phase(resource)

            elif current_phase == LabWorkerPoolPhase.READY:
                return await self._reconcile_ready_phase(resource)

            elif current_phase == LabWorkerPoolPhase.SCALING_UP:
                return await self._reconcile_scaling_up_phase(resource)

            elif current_phase == LabWorkerPoolPhase.SCALING_DOWN:
                return await self._reconcile_scaling_down_phase(resource)

            elif current_phase == LabWorkerPoolPhase.DRAINING:
                return await self._reconcile_draining_phase(resource)

            elif current_phase == LabWorkerPoolPhase.TERMINATING:
                return await self._reconcile_terminating_phase(resource)

            elif current_phase in [LabWorkerPoolPhase.TERMINATED, LabWorkerPoolPhase.FAILED]:
                # Terminal states
                return ReconciliationResult.success("Pool is in terminal state")

            else:
                return ReconciliationResult.failed(ValueError(f"Unknown phase: {current_phase}"), f"Unknown phase {current_phase}")

        except Exception as e:
            log.error(f"Reconciliation failed for {resource_name}: {e}", exc_info=True)
            resource.status.error_message = str(e)
            resource.status.error_count += 1
            return ReconciliationResult.failed(e, f"Reconciliation error: {str(e)}")

    async def finalize(self, resource: LabWorkerPool) -> bool:
        """Clean up resources before deletion."""
        log.info(f"Finalizing LabWorkerPool {resource.metadata.name}")

        try:
            # Get all workers in the pool
            workers = await self._list_workers_for_pool(resource)

            # Delete all workers
            for worker in workers:
                log.info(f"Deleting worker {worker.metadata.name}")
                await self._delete_worker(worker)

            log.info(f"Finalization complete for {resource.metadata.name}")
            return True

        except Exception as e:
            log.error(f"Finalization failed for {resource.metadata.name}: {e}")
            return False

    # Phase-specific reconciliation methods

    async def _reconcile_pending_phase(self, resource: LabWorkerPool) -> ReconciliationResult:
        """Reconcile a pool in PENDING phase."""
        log.info(f"Initializing pool {resource.metadata.name}")

        # Validate specification
        validation_errors = resource.spec.validate()
        if validation_errors:
            error_msg = f"Invalid specification: {'; '.join(validation_errors)}"
            resource.status.phase = LabWorkerPoolPhase.FAILED
            resource.status.error_message = error_msg
            return ReconciliationResult.failed(ValueError(error_msg), error_msg)

        # Transition to initializing
        resource.status.phase = LabWorkerPoolPhase.INITIALIZING
        resource.status.initialized_at = datetime.now()

        return ReconciliationResult.success("Transitioned to INITIALIZING")

    async def _reconcile_initializing_phase(self, resource: LabWorkerPool) -> ReconciliationResult:
        """Reconcile a pool in INITIALIZING phase."""

        # Update worker list and capacity
        await self._update_pool_state(resource)

        # Check if we need to create initial workers
        target_count = max(resource.spec.scaling.min_workers, 1)
        current_count = resource.status.total_workers_count

        if current_count < target_count:
            log.info(f"Creating initial workers for pool {resource.metadata.name}: " f"{current_count}/{target_count}")

            # Create missing workers
            for i in range(current_count, target_count):
                worker_name = resource.generate_worker_name(i)
                await self._create_worker(resource, worker_name)

            # Requeue to check worker creation
            return ReconciliationResult.requeue_after(timedelta(seconds=30), f"Creating initial workers ({current_count}/{target_count})")

        # Check if at least one worker is ready
        if resource.status.ready_workers_count > 0:
            resource.status.phase = LabWorkerPoolPhase.READY
            resource.status.ready_condition = True
            log.info(f"Pool {resource.metadata.name} is now READY")
            return ReconciliationResult.success("Pool initialized and ready")

        # Still waiting for workers to become ready
        return ReconciliationResult.requeue_after(timedelta(seconds=30), "Waiting for workers to become ready")

    async def _reconcile_ready_phase(self, resource: LabWorkerPool) -> ReconciliationResult:
        """Reconcile a pool in READY phase."""

        # Update worker list and capacity
        await self._update_pool_state(resource)

        # Check if desired phase changed
        if resource.spec.desired_phase == LabWorkerPoolPhase.DRAINING:
            resource.status.phase = LabWorkerPoolPhase.DRAINING
            return ReconciliationResult.success("Transitioned to DRAINING")

        # Check if auto-scaling is needed
        if resource.should_scale_up():
            log.info(f"Pool {resource.metadata.name} needs to scale up")
            resource.status.phase = LabWorkerPoolPhase.SCALING_UP
            return ReconciliationResult.success("Starting scale-up")

        if resource.should_scale_down():
            log.info(f"Pool {resource.metadata.name} needs to scale down")
            resource.status.phase = LabWorkerPoolPhase.SCALING_DOWN
            return ReconciliationResult.success("Starting scale-down")

        # Regular monitoring
        return ReconciliationResult.requeue_after(timedelta(minutes=2), "Monitoring pool capacity")

    async def _reconcile_scaling_up_phase(self, resource: LabWorkerPool) -> ReconciliationResult:
        """Reconcile a pool in SCALING_UP phase."""

        # Update worker list
        await self._update_pool_state(resource)

        target_count = resource.get_target_worker_count()
        current_count = resource.status.total_workers_count

        log.info(f"Scaling up pool {resource.metadata.name}: " f"{current_count}/{target_count} workers")

        if current_count < target_count:
            # Create new worker
            worker_name = resource.generate_worker_name(current_count)
            await self._create_worker(resource, worker_name)

            # Record scaling event
            resource.status.last_scale_up = datetime.now()
            resource.status.add_scaling_event(ScalingEvent(timestamp=datetime.now(), event_type="scale_up", reason="Capacity threshold exceeded", old_worker_count=current_count, new_worker_count=current_count + 1, triggered_by="capacity"))

            # Wait for worker to be created
            return ReconciliationResult.requeue_after(timedelta(seconds=30), "Worker creation initiated")

        # Scale-up complete
        resource.status.phase = LabWorkerPoolPhase.READY
        log.info(f"Scale-up complete for pool {resource.metadata.name}")
        return ReconciliationResult.success("Scale-up complete")

    async def _reconcile_scaling_down_phase(self, resource: LabWorkerPool) -> ReconciliationResult:
        """Reconcile a pool in SCALING_DOWN phase."""

        # Update worker list
        await self._update_pool_state(resource)

        target_count = resource.get_target_worker_count()
        current_count = resource.status.total_workers_count

        log.info(f"Scaling down pool {resource.metadata.name}: " f"{current_count}/{target_count} workers")

        if current_count > target_count:
            # Find least utilized worker to remove
            worker_to_remove = resource.status.get_least_utilized_worker()

            if worker_to_remove:
                log.info(f"Removing worker {worker_to_remove.name} from pool " f"{resource.metadata.name}")

                # Get the worker resource and delete it
                worker = await self._get_worker(worker_to_remove.namespace, worker_to_remove.name)
                if worker:
                    await self._delete_worker(worker)

                # Record scaling event
                resource.status.last_scale_down = datetime.now()
                resource.status.add_scaling_event(ScalingEvent(timestamp=datetime.now(), event_type="scale_down", reason="Low capacity utilization", old_worker_count=current_count, new_worker_count=current_count - 1, triggered_by="capacity"))

                # Wait for worker to be deleted
                return ReconciliationResult.requeue_after(timedelta(seconds=30), "Worker deletion initiated")
            else:
                # No idle workers to remove - cannot scale down safely
                log.warning(f"Cannot scale down pool {resource.metadata.name}: " f"no idle workers available")
                resource.status.phase = LabWorkerPoolPhase.READY
                return ReconciliationResult.success("Scale-down cancelled: no idle workers")

        # Scale-down complete
        resource.status.phase = LabWorkerPoolPhase.READY
        log.info(f"Scale-down complete for pool {resource.metadata.name}")
        return ReconciliationResult.success("Scale-down complete")

    async def _reconcile_draining_phase(self, resource: LabWorkerPool) -> ReconciliationResult:
        """Reconcile a pool in DRAINING phase."""

        # Update worker list
        await self._update_pool_state(resource)

        # Check if all labs are finished
        if resource.status.capacity.total_labs_hosted == 0:
            log.info(f"All labs drained from pool {resource.metadata.name}")

            # Check desired next phase
            if resource.spec.desired_phase == LabWorkerPoolPhase.TERMINATED:
                resource.status.phase = LabWorkerPoolPhase.TERMINATING
                return ReconciliationResult.success("Starting termination")
            else:
                # Return to ready state
                resource.status.phase = LabWorkerPoolPhase.READY
                return ReconciliationResult.success("Returned to READY state")

        # Still draining
        log.info(f"Draining pool {resource.metadata.name}: " f"{resource.status.capacity.total_labs_hosted} labs remaining")
        return ReconciliationResult.requeue_after(timedelta(minutes=1), f"Waiting for {resource.status.capacity.total_labs_hosted} labs to finish")

    async def _reconcile_terminating_phase(self, resource: LabWorkerPool) -> ReconciliationResult:
        """Reconcile a pool in TERMINATING phase."""

        # Update worker list
        await self._update_pool_state(resource)

        # Delete all workers
        if resource.status.total_workers_count > 0:
            workers = await self._list_workers_for_pool(resource)

            for worker in workers:
                log.info(f"Deleting worker {worker.metadata.name}")
                await self._delete_worker(worker)

            # Wait for workers to be deleted
            return ReconciliationResult.requeue_after(timedelta(seconds=30), f"Deleting {len(workers)} workers")

        # All workers deleted
        resource.status.phase = LabWorkerPoolPhase.TERMINATED
        log.info(f"Pool {resource.metadata.name} terminated")
        return ReconciliationResult.success("Pool terminated")

    # Helper methods

    async def _update_pool_state(self, resource: LabWorkerPool) -> None:
        """Update pool state by querying current workers."""
        try:
            workers = await self._list_workers_for_pool(resource)

            # Build worker info list
            worker_infos: list[WorkerInfo] = []
            worker_names: list[str] = []

            for worker in workers:
                worker_names.append(worker.metadata.name)

                # Get utilization metrics
                cpu_util = 0.0
                mem_util = 0.0
                storage_util = 0.0

                if worker.status.capacity:
                    cpu_util = worker.status.capacity.cpu_utilization_percent or 0.0
                    mem_util = worker.status.capacity.memory_utilization_percent or 0.0
                    storage_util = worker.status.capacity.storage_utilization_percent or 0.0

                worker_info = WorkerInfo(name=worker.metadata.name, namespace=worker.metadata.namespace, phase=worker.status.phase, active_lab_count=worker.status.active_lab_count, cpu_utilization_percent=cpu_util, memory_utilization_percent=mem_util, storage_utilization_percent=storage_util, is_licensed=worker.status.cml_licensed, created_at=worker.metadata.created_at or datetime.now(), last_updated=datetime.now())
                worker_infos.append(worker_info)

            # Update status
            resource.status.workers = worker_infos
            resource.status.worker_names = worker_names
            resource.status.total_workers_count = len(workers)

            # Calculate capacity summary
            capacity = await self._calculate_pool_capacity(workers)
            resource.status.capacity = capacity

            # Count ready workers
            ready_count = sum(1 for w in workers if w.status.phase in [LabWorkerPhase.READY, LabWorkerPhase.ACTIVE, LabWorkerPhase.READY_UNLICENSED])
            resource.status.ready_workers_count = ready_count
            resource.status.ready_condition = ready_count > 0

        except Exception as e:
            log.error(f"Error updating pool state: {e}")
            raise

    async def _calculate_pool_capacity(self, workers: list[LabWorker]) -> PoolCapacitySummary:
        """Calculate aggregate capacity across all workers."""
        capacity = PoolCapacitySummary()

        if not workers:
            return capacity

        capacity.total_workers = len(workers)

        # Count workers by state
        for worker in workers:
            if worker.status.phase in [LabWorkerPhase.READY, LabWorkerPhase.READY_UNLICENSED]:
                capacity.ready_workers += 1
            elif worker.status.phase == LabWorkerPhase.ACTIVE:
                capacity.active_workers += 1
            elif worker.status.phase == LabWorkerPhase.DRAINING:
                capacity.draining_workers += 1
            elif worker.status.phase == LabWorkerPhase.FAILED:
                capacity.failed_workers += 1

        # Aggregate capacity and utilization
        total_cpu_util = 0.0
        total_mem_util = 0.0
        total_storage_util = 0.0
        worker_count = 0

        for worker in workers:
            if not worker.status.capacity:
                continue

            cap = worker.status.capacity

            # Total capacity
            capacity.total_cpu_cores += cap.total_cpu_cores
            capacity.total_memory_mb += cap.total_memory_mb
            capacity.total_storage_gb += cap.total_storage_gb

            # Available capacity (only from ready/active workers)
            if worker.status.phase in [LabWorkerPhase.READY, LabWorkerPhase.ACTIVE, LabWorkerPhase.READY_UNLICENSED]:
                capacity.available_cpu_cores += cap.available_cpu_cores
                capacity.available_memory_mb += cap.available_memory_mb
                capacity.available_storage_gb += cap.available_storage_gb
                capacity.max_concurrent_labs += cap.max_concurrent_labs

            # Lab count
            capacity.total_labs_hosted += worker.status.active_lab_count

            # Utilization
            if cap.cpu_utilization_percent is not None:
                total_cpu_util += cap.cpu_utilization_percent
                worker_count += 1
            if cap.memory_utilization_percent is not None:
                total_mem_util += cap.memory_utilization_percent
            if cap.storage_utilization_percent is not None:
                total_storage_util += cap.storage_utilization_percent

        # Calculate average utilization
        if worker_count > 0:
            capacity.avg_cpu_utilization_percent = total_cpu_util / worker_count
            capacity.avg_memory_utilization_percent = total_mem_util / worker_count
            capacity.avg_storage_utilization_percent = total_storage_util / worker_count

        return capacity

    async def _create_worker(self, pool: LabWorkerPool, worker_name: str) -> LabWorker:
        """Create a new LabWorker resource for the pool."""
        log.info(f"Creating worker {worker_name} for pool {pool.metadata.name}")

        # Build worker spec from template
        template = pool.spec.worker_template

        worker_spec = LabWorkerSpec(aws_config=template.aws_config, cml_config=template.cml_config, auto_license=template.auto_license, desired_phase=None)

        # Create worker resource
        worker = LabWorker(namespace=pool.metadata.namespace, name=worker_name, spec=worker_spec)

        # Add labels
        worker.metadata.labels = {"app": "lab-resource-manager", "component": "lab-worker", "pool": pool.metadata.name, "track": pool.spec.lab_track, **template.labels}

        # Add annotations
        worker.metadata.annotations = {"managed-by": "lab-worker-pool-controller", "pool-name": pool.metadata.name, "pool-namespace": pool.metadata.namespace, **template.annotations}

        # TODO: Actually create the worker resource in the cluster
        # This would use the ResourceRepository or ResourceClient
        # For now, this is a placeholder

        return worker

    async def _delete_worker(self, worker: LabWorker) -> None:
        """Delete a LabWorker resource."""
        log.info(f"Deleting worker {worker.metadata.name}")

        # TODO: Actually delete the worker resource from the cluster
        # This would use the ResourceRepository or ResourceClient
        # For now, this is a placeholder

    async def _get_worker(self, namespace: str, name: str) -> Optional[LabWorker]:
        """Get a LabWorker resource by name."""
        # TODO: Actually get the worker resource from the cluster
        # This would use the ResourceRepository or ResourceClient
        # For now, this is a placeholder
        return None

    async def _list_workers_for_pool(self, pool: LabWorkerPool) -> list[LabWorker]:
        """List all LabWorker resources belonging to this pool."""
        # TODO: Actually list workers from the cluster using label selectors
        # This would use the ResourceRepository or ResourceClient
        # selector: pool={pool.metadata.name},track={pool.spec.lab_track}
        # For now, return empty list
        return []
