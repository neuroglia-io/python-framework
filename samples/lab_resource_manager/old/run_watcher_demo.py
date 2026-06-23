#!/usr/bin/env python3
"""
Watcher and Reconciliation Loop Demonstration

This demo shows the Resource Oriented Architecture patterns in action:
- Watcher: Polls for resource changes and notifies controllers
- Controller: Responds to resource changes with business logic
- Reconciliation Loop: Ensures desired state matches actual state

Run with: python run_watcher_demo.py
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

# Configure logging to see the patterns in action
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


class ResourceState(Enum):
    """Resource states in the ROA lifecycle."""

    PENDING = "pending"
    PROVISIONING = "provisioning"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"
    DELETED = "deleted"


@dataclass
class LabInstanceResource:
    """A Kubernetes-style resource representing a lab instance."""

    api_version: str = "lab.neuroglia.com/v1"
    kind: str = "LabInstance"
    metadata: dict[str, Any] = None
    spec: dict[str, Any] = None
    status: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.spec is None:
            self.spec = {}
        if self.status is None:
            self.status = {"state": ResourceState.PENDING.value}


class InMemoryStorage:
    """Simple in-memory storage to simulate Kubernetes API."""

    def __init__(self):
        self.resources: dict[str, LabInstanceResource] = {}
        self.resource_version = 0

    def create_resource(self, resource: LabInstanceResource) -> LabInstanceResource:
        """Create a new resource."""
        resource_id = f"{resource.metadata.get('namespace', 'default')}/{resource.metadata.get('name')}"
        self.resource_version += 1
        resource.metadata["resourceVersion"] = str(self.resource_version)
        resource.metadata["creationTimestamp"] = datetime.now(timezone.utc).isoformat()

        self.resources[resource_id] = resource
        logger.info(f"📦 Created resource: {resource_id}")
        return resource

    def update_resource(self, resource_id: str, updates: dict[str, Any]) -> Optional[LabInstanceResource]:
        """Update an existing resource."""
        if resource_id not in self.resources:
            return None

        resource = self.resources[resource_id]
        self.resource_version += 1
        resource.metadata["resourceVersion"] = str(self.resource_version)

        # Apply updates
        if "status" in updates:
            resource.status.update(updates["status"])
        if "spec" in updates:
            resource.spec.update(updates["spec"])

        logger.info(f"🔄 Updated resource: {resource_id} -> {updates}")
        return resource

    def list_resources(self, since_version: int = 0) -> list[LabInstanceResource]:
        """List resources, optionally filtered by resource version."""
        return [resource for resource in self.resources.values() if int(resource.metadata.get("resourceVersion", "0")) > since_version]

    def get_resource(self, resource_id: str) -> Optional[LabInstanceResource]:
        """Get a specific resource."""
        return self.resources.get(resource_id)


class LabInstanceWatcher:
    """
    Watcher that polls for LabInstance resource changes.

    This demonstrates the WATCH pattern where the watcher:
    1. Polls the storage backend for changes
    2. Detects new/modified resources
    3. Notifies controllers of changes
    """

    def __init__(self, storage: InMemoryStorage, poll_interval: float = 2.0):
        self.storage = storage
        self.poll_interval = poll_interval
        self.last_resource_version = 0
        self.is_running = False
        self.event_handlers = []

    def add_event_handler(self, handler):
        """Add a handler for resource change events."""
        self.event_handlers.append(handler)

    async def start_watching(self):
        """Start the watch loop."""
        self.is_running = True
        logger.info("👀 LabInstance Watcher started")

        while self.is_running:
            try:
                # Poll for changes since last known version
                changes = self.storage.list_resources(since_version=self.last_resource_version)

                for resource in changes:
                    resource_version = int(resource.metadata.get("resourceVersion", "0"))
                    if resource_version > self.last_resource_version:
                        await self._handle_resource_change(resource)
                        self.last_resource_version = max(self.last_resource_version, resource_version)

                # Wait before next poll
                await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"❌ Watcher error: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _handle_resource_change(self, resource: LabInstanceResource):
        """Handle a detected resource change."""
        resource_id = f"{resource.metadata.get('namespace', 'default')}/{resource.metadata.get('name')}"
        state = resource.status.get("state", ResourceState.PENDING.value)

        logger.info(f"🔍 Watcher detected change: {resource_id} -> {state}")

        # Notify all registered handlers
        for handler in self.event_handlers:
            try:
                await handler(resource)
            except Exception as e:
                logger.error(f"❌ Handler error: {e}")

    def stop_watching(self):
        """Stop the watch loop."""
        self.is_running = False
        logger.info("⏹️ LabInstance Watcher stopped")


class LabInstanceController:
    """
    Controller that responds to LabInstance resource changes.

    This demonstrates the CONTROLLER pattern where the controller:
    1. Receives notifications from watchers
    2. Implements business logic for state transitions
    3. Updates resources based on business rules
    """

    def __init__(self, storage: InMemoryStorage):
        self.storage = storage

    async def handle_resource_event(self, resource: LabInstanceResource):
        """Handle a resource change event."""
        resource_id = f"{resource.metadata.get('namespace', 'default')}/{resource.metadata.get('name')}"
        current_state = resource.status.get("state")

        logger.info(f"🎮 Controller processing: {resource_id} (state: {current_state})")

        # Implement state machine logic
        if current_state == ResourceState.PENDING.value:
            await self._start_provisioning(resource_id, resource)
        elif current_state == ResourceState.PROVISIONING.value:
            await self._check_provisioning_status(resource_id, resource)
        elif current_state == ResourceState.READY.value:
            await self._monitor_lab_instance(resource_id, resource)

    async def _start_provisioning(self, resource_id: str, resource: LabInstanceResource):
        """Start provisioning a lab instance."""
        logger.info(f"🚀 Starting provisioning for: {resource_id}")

        # Simulate starting provisioning process
        updates = {"status": {"state": ResourceState.PROVISIONING.value, "message": "Starting lab instance provisioning", "startedAt": datetime.now(timezone.utc).isoformat()}}
        self.storage.update_resource(resource_id, updates)

    async def _check_provisioning_status(self, resource_id: str, resource: LabInstanceResource):
        """Check if provisioning is complete."""
        started_at = resource.status.get("startedAt")
        if started_at:
            # Simulate provisioning completion after some time
            start_time = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            elapsed = datetime.now(timezone.utc) - start_time

            if elapsed.total_seconds() > 5:  # Complete after 5 seconds
                logger.info(f"✅ Provisioning completed for: {resource_id}")
                updates = {"status": {"state": ResourceState.READY.value, "message": "Lab instance is ready", "readyAt": datetime.now(timezone.utc).isoformat(), "endpoint": f"https://lab-{resource.metadata.get('name')}.example.com"}}
                self.storage.update_resource(resource_id, updates)

    async def _monitor_lab_instance(self, resource_id: str, resource: LabInstanceResource):
        """Monitor a ready lab instance."""
        # In a real system, this would check health, usage, etc.
        logger.info(f"💚 Monitoring ready lab: {resource_id}")


class LabInstanceScheduler:
    """
    Scheduler that runs reconciliation loops for LabInstance resources.

    This demonstrates the RECONCILIATION pattern where the scheduler:
    1. Periodically checks all resources
    2. Ensures desired state matches actual state
    3. Takes corrective actions when needed
    """

    def __init__(self, storage: InMemoryStorage, reconcile_interval: float = 10.0):
        self.storage = storage
        self.reconcile_interval = reconcile_interval
        self.is_running = False

    async def start_reconciliation(self):
        """Start the reconciliation loop."""
        self.is_running = True
        logger.info("🔄 LabInstance Scheduler started reconciliation")

        while self.is_running:
            try:
                await self._reconcile_all_resources()
                await asyncio.sleep(self.reconcile_interval)
            except Exception as e:
                logger.error(f"❌ Reconciliation error: {e}")
                await asyncio.sleep(self.reconcile_interval)

    async def _reconcile_all_resources(self):
        """Reconcile all LabInstance resources."""
        resources = self.storage.list_resources()

        if resources:
            logger.info(f"🔄 Reconciling {len(resources)} lab instances")

            for resource in resources:
                await self._reconcile_resource(resource)

    async def _reconcile_resource(self, resource: LabInstanceResource):
        """Reconcile a single resource."""
        resource_id = f"{resource.metadata.get('namespace', 'default')}/{resource.metadata.get('name')}"
        current_state = resource.status.get("state")

        # Check for stuck states
        created_at = resource.metadata.get("creationTimestamp")
        if created_at:
            creation_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - creation_time

            # If provisioning for too long, mark as failed
            if current_state == ResourceState.PROVISIONING.value and age.total_seconds() > 30:
                logger.warning(f"⚠️ Reconciler: Lab instance stuck in provisioning: {resource_id}")
                updates = {"status": {"state": ResourceState.FAILED.value, "message": "Provisioning timeout", "failedAt": datetime.now(timezone.utc).isoformat()}}
                self.storage.update_resource(resource_id, updates)

        # Check for cleanup needs (simulate lab expiration)
        ready_at = resource.status.get("readyAt")
        if ready_at and current_state == ResourceState.READY.value:
            ready_time = datetime.fromisoformat(ready_at.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - ready_time

            # Expire labs after 20 seconds for demo
            if age.total_seconds() > 20:
                logger.info(f"⏰ Reconciler: Expiring lab instance: {resource_id}")
                updates = {"status": {"state": ResourceState.DELETING.value, "message": "Lab session expired"}}
                self.storage.update_resource(resource_id, updates)

    def stop_reconciliation(self):
        """Stop the reconciliation loop."""
        self.is_running = False
        logger.info("⏹️ LabInstance Scheduler stopped reconciliation")


async def main():
    """
    Main demonstration showing watcher and reconciliation patterns.
    """
    print("🎯 Resource Oriented Architecture: Watcher & Reconciliation Demo")
    print("=" * 60)
    print("This demo shows:")
    print("- Watcher: Detects resource changes (every 2s)")
    print("- Controller: Responds to changes with business logic")
    print("- Scheduler: Reconciles state periodically (every 10s)")
    print("=" * 60)

    # Create components
    storage = InMemoryStorage()
    watcher = LabInstanceWatcher(storage, poll_interval=2.0)
    controller = LabInstanceController(storage)
    scheduler = LabInstanceScheduler(storage, reconcile_interval=10.0)

    # Wire up event handling
    watcher.add_event_handler(controller.handle_resource_event)

    # Start background tasks
    watcher_task = asyncio.create_task(watcher.start_watching())
    scheduler_task = asyncio.create_task(scheduler.start_reconciliation())

    try:
        # Let components start up
        await asyncio.sleep(1)

        # Create some lab instances to watch
        lab1 = LabInstanceResource()
        lab1.metadata = {"name": "python-basics-lab", "namespace": "student-labs"}
        lab1.spec = {"template": "python-basics", "studentEmail": "student1@example.com", "duration": "60m"}
        storage.create_resource(lab1)

        # Wait a bit, then create another
        await asyncio.sleep(3)

        lab2 = LabInstanceResource()
        lab2.metadata = {"name": "web-dev-lab", "namespace": "student-labs"}
        lab2.spec = {"template": "web-development", "studentEmail": "student2@example.com", "duration": "90m"}
        storage.create_resource(lab2)

        # Let the demo run for a while to see all patterns
        print("\n⏱️  Demo running... Watch the logs to see the patterns in action!")
        print("   - Resource creation and state transitions")
        print("   - Watcher detecting changes")
        print("   - Controller responding with business logic")
        print("   - Scheduler reconciling state")
        print("\n📝 Press Ctrl+C to stop the demo\n")

        # Keep running until interrupted
        await asyncio.sleep(60)  # Run for 1 minute

    except KeyboardInterrupt:
        print("\n🛑 Demo stopped by user")
    finally:
        # Clean shutdown
        watcher.stop_watching()
        scheduler.stop_reconciliation()

        # Wait for tasks to complete
        watcher_task.cancel()
        scheduler_task.cancel()

        try:
            await asyncio.gather(watcher_task, scheduler_task, return_exceptions=True)
        except:
            pass

        print("✨ Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
