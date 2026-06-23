"""Simple Watcher and Reconciliation Demo.

A standalone demonstration of the watcher and reconciliation patterns
that doesn't rely on complex import paths.
"""

import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

# Add the project root to Python path so we can import neuroglia
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))  # For neuroglia imports
sys.path.insert(0, str(Path(__file__).parent))  # For local imports from lab_resource_manager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


# Simple mock implementations for demonstration
class LabInstancePhase(Enum):
    """Lab instance phases."""

    PENDING = "Pending"
    PROVISIONING = "Provisioning"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    TIMEOUT = "Timeout"


@dataclass
class SimpleResource:
    """Simple resource for demonstration."""

    id: str
    name: str
    namespace: str
    phase: LabInstancePhase
    generation: int = 1
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class SimpleWatcher:
    """Simple watcher implementation for demonstration."""

    def __init__(self, storage: dict[str, SimpleResource], watch_interval: float = 2.0):
        self.storage = storage
        self.watch_interval = watch_interval
        self.cache: dict[str, SimpleResource] = {}
        self.watching = False
        self.change_handlers = []

    def add_change_handler(self, handler):
        """Add a change handler."""
        self.change_handlers.append(handler)

    async def watch(self):
        """Start watching for changes."""
        self.watching = True
        log.info("🔍 Starting resource watcher")

        while self.watching:
            try:
                # Get current resources
                current_resources = dict(self.storage)

                # Detect changes
                changes = self._detect_changes(current_resources)

                # Process changes
                for change in changes:
                    log.info(f"📝 Detected {change['type']}: {change['resource'].name}")

                    # Call change handlers
                    for handler in self.change_handlers:
                        try:
                            await handler(change)
                        except Exception as e:
                            log.error(f"Change handler error: {e}")

                # Update cache
                self.cache = current_resources

                # Wait before next poll
                await asyncio.sleep(self.watch_interval)

            except Exception as e:
                log.error(f"Watch loop error: {e}")
                await asyncio.sleep(self.watch_interval)

    def _detect_changes(self, current_resources):
        """Detect changes between current and cached resources."""
        changes = []
        current_ids = set(current_resources.keys())
        cached_ids = set(self.cache.keys())

        # New resources
        for resource_id in current_ids - cached_ids:
            changes.append({"type": "CREATED", "resource": current_resources[resource_id]})

        # Deleted resources
        for resource_id in cached_ids - current_ids:
            changes.append({"type": "DELETED", "resource": self.cache[resource_id]})

        # Updated resources
        for resource_id in current_ids & cached_ids:
            current = current_resources[resource_id]
            cached = self.cache[resource_id]

            if current.generation > cached.generation:
                changes.append({"type": "UPDATED", "resource": current, "old_resource": cached})
            elif current.phase != cached.phase:
                changes.append({"type": "STATUS_UPDATED", "resource": current, "old_resource": cached})

        return changes

    def stop(self):
        """Stop watching."""
        self.watching = False


class SimpleController:
    """Simple controller for demonstration."""

    def __init__(self, storage: dict[str, SimpleResource]):
        self.storage = storage

    async def handle_change(self, change):
        """Handle a resource change."""
        resource = change["resource"]
        change_type = change["type"]

        log.info(f"🎯 Controller handling {change_type} for {resource.name}")

        if change_type == "CREATED":
            await self._reconcile_created(resource)
        elif change_type == "UPDATED":
            await self._reconcile_updated(resource)
        elif change_type == "STATUS_UPDATED":
            await self._reconcile_status_updated(resource)

    async def _reconcile_created(self, resource):
        """Reconcile a newly created resource."""
        if resource.phase == LabInstancePhase.PENDING:
            log.info(f"  💭 New resource {resource.name} is pending, no action needed yet")

    async def _reconcile_updated(self, resource):
        """Reconcile an updated resource."""
        log.info(f"  🔄 Resource {resource.name} was updated, checking for actions")

        if resource.phase == LabInstancePhase.PENDING:
            # Simulate scheduling logic
            log.info(f"  ⏰ Checking if {resource.name} should be started...")
            # Could check scheduling time here

    async def _reconcile_status_updated(self, resource):
        """Reconcile a status update."""
        log.info(f"  📊 Resource {resource.name} status updated to {resource.phase.value}")


class SimpleScheduler:
    """Simple scheduler for demonstration."""

    def __init__(self, storage: dict[str, SimpleResource], interval: float = 3.0):
        self.storage = storage
        self.interval = interval
        self.running = False

    async def start(self):
        """Start the scheduler loop."""
        self.running = True
        log.info("⚙️ Starting background scheduler")

        while self.running:
            try:
                await self._reconcile_all()
                await asyncio.sleep(self.interval)
            except Exception as e:
                log.error(f"Scheduler error: {e}")
                await asyncio.sleep(self.interval)

    async def _reconcile_all(self):
        """Reconcile all resources."""
        resources = list(self.storage.values())

        # Simulate processing pending resources
        pending_resources = [r for r in resources if r.phase == LabInstancePhase.PENDING]
        if pending_resources:
            log.info(f"🔄 Scheduler processing {len(pending_resources)} pending resources")

            for resource in pending_resources:
                # Simulate starting a resource after some time
                age = datetime.now(timezone.utc) - resource.created_at
                if age.total_seconds() > 5:  # Start after 5 seconds
                    log.info(f"  🚀 Starting resource {resource.name}")
                    resource.phase = LabInstancePhase.RUNNING

        # Simulate completing running resources
        running_resources = [r for r in resources if r.phase == LabInstancePhase.RUNNING]
        for resource in running_resources:
            age = datetime.now(timezone.utc) - resource.created_at
            if age.total_seconds() > 15:  # Complete after 15 seconds
                log.info(f"  ✅ Completing resource {resource.name}")
                resource.phase = LabInstancePhase.COMPLETED

    def stop(self):
        """Stop the scheduler."""
        self.running = False


async def demonstrate_patterns():
    """Demonstrate the watcher and reconciliation patterns."""
    print("\n🎭 WATCHER AND RECONCILIATION DEMONSTRATION")
    print("=" * 60)
    print("This demo shows simplified versions of:")
    print("• Resource Watcher detecting changes")
    print("• Controller responding to changes")
    print("• Background Scheduler reconciling state")
    print("=" * 60)

    # Shared storage
    storage: dict[str, SimpleResource] = {}

    # Create components
    watcher = SimpleWatcher(storage, watch_interval=2.0)
    controller = SimpleController(storage)
    scheduler = SimpleScheduler(storage, interval=3.0)

    # Connect watcher to controller
    watcher.add_change_handler(controller.handle_change)

    # Start background processes
    log.info("\n📋 Step 1: Starting Watcher and Scheduler")
    watcher_task = asyncio.create_task(watcher.watch())
    scheduler_task = asyncio.create_task(scheduler.start())

    await asyncio.sleep(1)  # Let them start

    # Create resources
    log.info("\n📋 Step 2: Creating Resources")

    resource1 = SimpleResource(id="lab-001", name="python-lab-001", namespace="default", phase=LabInstancePhase.PENDING)
    storage[resource1.id] = resource1
    log.info(f"💾 Created resource: {resource1.name}")

    await asyncio.sleep(3)  # Let watcher detect

    resource2 = SimpleResource(id="lab-002", name="docker-lab-002", namespace="advanced", phase=LabInstancePhase.PENDING)
    storage[resource2.id] = resource2
    log.info(f"💾 Created resource: {resource2.name}")

    await asyncio.sleep(4)  # Let system process

    # Update a resource
    log.info("\n📋 Step 3: Updating Resource")
    resource1.generation += 1  # Increment generation
    log.info(f"📝 Updated resource: {resource1.name} (generation {resource1.generation})")

    await asyncio.sleep(4)  # Let system process

    # Show current state
    log.info("\n📋 Step 4: Current State")
    for resource in storage.values():
        log.info(f"  📦 {resource.name}: {resource.phase.value}")

    # Wait for scheduler to process
    log.info("\n📋 Step 5: Waiting for Scheduler Processing")
    await asyncio.sleep(8)

    # Show final state
    log.info("\n📋 Step 6: Final State")
    for resource in storage.values():
        log.info(f"  📦 {resource.name}: {resource.phase.value}")

    # Cleanup
    log.info("\n📋 Step 7: Cleanup")
    watcher.stop()
    scheduler.stop()

    # Cancel tasks
    watcher_task.cancel()
    scheduler_task.cancel()

    try:
        await watcher_task
    except asyncio.CancelledError:
        pass

    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass

    print("\n🎉 Demonstration completed!")
    print("\nKey Takeaways:")
    print("• Watcher polls storage and detects changes")
    print("• Controller responds to changes with reconciliation logic")
    print("• Scheduler runs independently to enforce policies")
    print("• All components work together for declarative management")


if __name__ == "__main__":
    try:
        asyncio.run(demonstrate_patterns())
    except KeyboardInterrupt:
        print("\n\n⚡ Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()
