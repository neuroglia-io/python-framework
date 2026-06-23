"""
Finalizers Demo - Resource Cleanup Pattern

This demo shows how to use finalizers to ensure proper cleanup of
external resources before a resource is deleted from the system.

Finalizers are Kubernetes-inspired hooks that:
1. Block deletion until cleanup is complete
2. Allow controllers to perform graceful cleanup
3. Support multiple finalizers on a single resource
4. Prevent orphaned external resources

Features Demonstrated:
- Adding finalizers to resources
- Controller-based finalizer processing
- Automatic cleanup on deletion
- Graceful failure handling
- Multi-finalizer coordination

Usage:
    python samples/lab_resource_manager/demo_finalizers.py
"""

import asyncio
import logging
from datetime import datetime, timedelta

from domain.resources.lab_instance_request import (
    LabInstancePhase,
    LabInstanceRequest,
    LabInstanceRequestSpec,
    LabInstanceRequestStatus,
    ResourceLimits,
)

from neuroglia.data.resources import ResourceMetadata
from neuroglia.data.resources.controller import (
    ReconciliationResult,
    ResourceControllerBase,
)
from neuroglia.dependency_injection import ServiceCollection, ServiceProviderBase

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class CleanupTracker:
    """Tracks cleanup operations for demonstration."""

    def __init__(self):
        self.container_cleanups = []
        self.resource_releases = []
        self.network_cleanups = []

    def track_container_cleanup(self, container_id: str):
        self.container_cleanups.append({"container_id": container_id, "timestamp": datetime.now()})
        log.info(f"🐳 Cleaned up container: {container_id}")

    def track_resource_release(self, allocation: dict):
        self.resource_releases.append({"allocation": allocation, "timestamp": datetime.now()})
        log.info(f"💾 Released resources: {allocation}")

    def track_network_cleanup(self, network_id: str):
        self.network_cleanups.append({"network_id": network_id, "timestamp": datetime.now()})
        log.info(f"🌐 Cleaned up network: {network_id}")

    def summary(self):
        log.info("📊 Cleanup Summary:")
        log.info(f"   Containers cleaned: {len(self.container_cleanups)}")
        log.info(f"   Resources released: {len(self.resource_releases)}")
        log.info(f"   Networks cleaned: {len(self.network_cleanups)}")


class LabInstanceControllerWithFinalizers(ResourceControllerBase):
    """Enhanced controller with comprehensive finalizer support."""

    # Finalizer constants
    CONTAINER_FINALIZER = "container-cleanup.lab-instance.neuroglia.io"
    RESOURCE_FINALIZER = "resource-allocation.lab-instance.neuroglia.io"
    NETWORK_FINALIZER = "network-cleanup.lab-instance.neuroglia.io"

    def __init__(self, service_provider: ServiceProviderBase, cleanup_tracker: CleanupTracker):
        super().__init__(service_provider)
        self.cleanup_tracker = cleanup_tracker

        # Set the finalizer name for automatic processing
        # The controller will add this finalizer to all resources it manages
        self.finalizer_name = self.CONTAINER_FINALIZER

    async def _do_reconcile(self, resource: LabInstanceRequest) -> ReconciliationResult:
        """Normal reconciliation logic."""
        log.info(f"🔄 Reconciling resource: {resource.metadata.name}")

        # Ensure all finalizers are present
        if not resource.metadata.has_finalizer(self.CONTAINER_FINALIZER):
            resource.metadata.add_finalizer(self.CONTAINER_FINALIZER)
            log.info(f"✅ Added container finalizer to {resource.metadata.name}")

        if not resource.metadata.has_finalizer(self.RESOURCE_FINALIZER):
            resource.metadata.add_finalizer(self.RESOURCE_FINALIZER)
            log.info(f"✅ Added resource finalizer to {resource.metadata.name}")

        if not resource.metadata.has_finalizer(self.NETWORK_FINALIZER):
            resource.metadata.add_finalizer(self.NETWORK_FINALIZER)
            log.info(f"✅ Added network finalizer to {resource.metadata.name}")

        return ReconciliationResult.success("Resource reconciled")

    async def finalize(self, resource: LabInstanceRequest) -> bool:
        """
        Clean up external resources before deletion.

        This method is automatically called by the base controller when:
        1. The resource is marked for deletion (deletion_timestamp is set)
        2. The resource has the controller's finalizer

        Returns:
            bool: True if cleanup successful, False to retry later
        """
        log.info(f"🧹 Starting finalizer processing for {resource.metadata.name}")
        log.info(f"   Finalizers remaining: {resource.metadata.finalizers}")

        # Process each finalizer
        all_successful = True

        # 1. Container cleanup
        if resource.metadata.has_finalizer(self.CONTAINER_FINALIZER):
            try:
                await self._cleanup_container(resource)
                resource.metadata.remove_finalizer(self.CONTAINER_FINALIZER)
                log.info(f"✅ Container finalizer completed for {resource.metadata.name}")
            except Exception as e:
                log.error(f"❌ Container cleanup failed: {e}")
                all_successful = False

        # 2. Resource allocation cleanup
        if resource.metadata.has_finalizer(self.RESOURCE_FINALIZER):
            try:
                await self._release_resources(resource)
                resource.metadata.remove_finalizer(self.RESOURCE_FINALIZER)
                log.info(f"✅ Resource finalizer completed for {resource.metadata.name}")
            except Exception as e:
                log.error(f"❌ Resource release failed: {e}")
                all_successful = False

        # 3. Network cleanup
        if resource.metadata.has_finalizer(self.NETWORK_FINALIZER):
            try:
                await self._cleanup_network(resource)
                resource.metadata.remove_finalizer(self.NETWORK_FINALIZER)
                log.info(f"✅ Network finalizer completed for {resource.metadata.name}")
            except Exception as e:
                log.error(f"❌ Network cleanup failed: {e}")
                all_successful = False

        if all_successful:
            log.info(f"🎉 All finalizers completed for {resource.metadata.name}")
        else:
            log.warning(f"⚠️ Some finalizers failed for {resource.metadata.name}, will retry")

        return all_successful

    async def _cleanup_container(self, resource: LabInstanceRequest):
        """Clean up container resources."""
        log.info(f"🐳 Cleaning up container for {resource.metadata.name}")
        await asyncio.sleep(0.5)  # Simulate async cleanup

        container_id = resource.status.container_id if resource.status else "simulated-container-123"
        self.cleanup_tracker.track_container_cleanup(container_id)

    async def _release_resources(self, resource: LabInstanceRequest):
        """Release allocated resources."""
        log.info(f"💾 Releasing resources for {resource.metadata.name}")
        await asyncio.sleep(0.3)  # Simulate async cleanup

        allocation = resource.status.resource_allocation if resource.status else {"cpu": 2.0, "memory_mb": 4096}
        self.cleanup_tracker.track_resource_release(allocation)

    async def _cleanup_network(self, resource: LabInstanceRequest):
        """Clean up network resources."""
        log.info(f"🌐 Cleaning up network for {resource.metadata.name}")
        await asyncio.sleep(0.2)  # Simulate async cleanup

        network_id = f"network-{resource.metadata.name}"
        self.cleanup_tracker.track_network_cleanup(network_id)


async def demo_finalizers():
    """Demonstrate finalizer functionality."""

    log.info("=" * 80)
    log.info("🎯 Finalizers Demo - Resource Cleanup Pattern")
    log.info("=" * 80)

    # Setup
    cleanup_tracker = CleanupTracker()
    services = ServiceCollection()
    service_provider = services.build_provider()
    controller = LabInstanceControllerWithFinalizers(service_provider, cleanup_tracker)

    # Create a lab instance
    log.info("\n📝 Creating lab instance resource...")
    lab_instance = LabInstanceRequest(
        metadata=ResourceMetadata(name="demo-lab-001", namespace="default", labels={"environment": "demo", "type": "python"}, annotations={"created-by": "finalizers-demo"}),
        spec=LabInstanceRequestSpec(lab_template="python-jupyter", student_email="student@example.com", duration=timedelta(hours=2), resource_limits=ResourceLimits(cpu_cores=2.0, memory_mb=4096)),
        status=LabInstanceRequestStatus(phase=LabInstancePhase.PENDING, container_id="container-12345", resource_allocation={"cpu": 2.0, "memory_mb": 4096}),
    )

    log.info(f"✅ Created resource: {lab_instance.metadata.name}")
    log.info(f"   Finalizers: {lab_instance.metadata.finalizers}")

    # Reconcile to add finalizers
    log.info("\n🔄 Reconciling resource (adds finalizers)...")
    await controller.reconcile(lab_instance)
    log.info(f"   Finalizers after reconciliation: {lab_instance.metadata.finalizers}")

    # Simulate deletion request
    log.info("\n🗑️  Simulating deletion request...")
    lab_instance.metadata.mark_for_deletion()
    log.info(f"   Deletion timestamp: {lab_instance.metadata.deletion_timestamp}")
    log.info(f"   Is being deleted: {lab_instance.metadata.is_being_deleted()}")
    log.info(f"   Has finalizers: {lab_instance.metadata.has_finalizers()}")

    # Reconcile will now process finalizers
    log.info("\n🧹 Reconciling for finalizer processing...")
    await controller.reconcile(lab_instance)

    # Check results
    log.info("\n✅ Finalizer processing complete!")
    log.info(f"   Remaining finalizers: {lab_instance.metadata.finalizers}")
    log.info(f"   Can be deleted: {not lab_instance.metadata.has_finalizers()}")

    # Show cleanup summary
    log.info("\n" + "=" * 80)
    cleanup_tracker.summary()
    log.info("=" * 80)

    # Demonstrate edge cases
    log.info("\n📚 Additional Scenarios:")

    # Scenario 1: Resource without finalizers
    log.info("\n1️⃣ Resource without finalizers (immediate deletion)")
    simple_resource = LabInstanceRequest(metadata=ResourceMetadata(name="no-finalizers", namespace="default"), spec=LabInstanceRequestSpec(lab_template="basic", student_email="test@example.com", resource_limits=ResourceLimits(cpu_cores=1.0, memory_mb=2048)))
    simple_resource.metadata.mark_for_deletion()
    log.info(f"   Has finalizers: {simple_resource.metadata.has_finalizers()}")
    log.info(f"   Ready for deletion: {simple_resource.metadata.is_being_deleted() and not simple_resource.metadata.has_finalizers()}")

    # Scenario 2: Multiple finalizers
    log.info("\n2️⃣ Resource with multiple custom finalizers")
    multi_finalizer_resource = LabInstanceRequest(metadata=ResourceMetadata(name="multi-finalizers", namespace="default"), spec=LabInstanceRequestSpec(lab_template="advanced", student_email="advanced@example.com", resource_limits=ResourceLimits(cpu_cores=4.0, memory_mb=8192)))
    multi_finalizer_resource.metadata.add_finalizer("storage.neuroglia.io/cleanup")
    multi_finalizer_resource.metadata.add_finalizer("monitoring.neuroglia.io/cleanup")
    multi_finalizer_resource.metadata.add_finalizer("logging.neuroglia.io/cleanup")
    log.info(f"   Finalizers: {multi_finalizer_resource.metadata.finalizers}")
    log.info(f"   Count: {len(multi_finalizer_resource.metadata.finalizers)}")

    # Scenario 3: Checking specific finalizers
    log.info("\n3️⃣ Checking for specific finalizers")
    log.info(f"   Has storage finalizer: {multi_finalizer_resource.metadata.has_finalizer('storage.neuroglia.io/cleanup')}")
    log.info(f"   Has network finalizer: {multi_finalizer_resource.metadata.has_finalizer('network.neuroglia.io/cleanup')}")

    log.info("\n✨ Demo complete!")


if __name__ == "__main__":
    asyncio.run(demo_finalizers())
