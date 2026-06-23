"""Demonstration of Watcher and Reconciliation Loop Patterns.

This script demonstrates how the Resource Watcher and Reconciliation Loop
patterns work together to provide declarative resource management.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to Python path so we can import neuroglia
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))  # For neuroglia imports
sys.path.insert(0, str(Path(__file__).parent))  # For local imports from lab_resource_manager

from application.services.lab_instance_scheduler_service import (
    LabInstanceSchedulerService,
)
from application.watchers.lab_instance_watcher import LabInstanceWatcher
from domain.controllers.lab_instance_request_controller import (
    LabInstanceRequestController,
)

# Sample application imports
from domain.resources.lab_instance_request import (
    LabInstancePhase,
    LabInstanceRequest,
    LabInstanceRequestSpec,
    LabInstanceRequestStatus,
)
from integration.repositories.lab_instance_resource_repository import (
    LabInstanceResourceRepository,
)
from integration.services.container_service import ContainerService

from neuroglia.data.infrastructure.resources.in_memory_storage_backend import (
    InMemoryStorageBackend,
)
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublisher,
)
from neuroglia.serialization.json import JsonSerializer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

log = logging.getLogger(__name__)


class DemoEventPublisher(CloudEventPublisher):
    """Simple event publisher for demonstration."""

    def __init__(self):
        self.published_events = []

    async def publish_async(self, event):
        """Store events for demonstration."""
        self.published_events.append(
            {
                "timestamp": datetime.now(),
                "source": event.source,
                "type": event.type,
                "subject": event.subject,
                "data": event.data,
            }
        )
        log.info(f"📤 EVENT: {event.type} - {event.subject}")


class WatcherReconciliationDemo:
    """Demonstrates watcher and reconciliation patterns."""

    def __init__(self):
        # Infrastructure
        self.storage = InMemoryStorageBackend()
        self.serializer = JsonSerializer()
        self.event_publisher = DemoEventPublisher()

        # Repository
        self.repository = LabInstanceResourceRepository(self.storage, self.serializer)

        # Services
        self.container_service = ContainerService()

        # Controller
        self.controller = LabInstanceRequestController(service_provider=None, event_publisher=self.event_publisher)  # Not needed for demo

        # Watcher
        self.watcher = LabInstanceWatcher(
            repository=self.repository,
            controller=self.controller,
            event_publisher=self.event_publisher,
            watch_interval=2.0,  # Fast polling for demo
        )

        # Scheduler (background reconciliation loop)
        self.scheduler = LabInstanceSchedulerService(
            service_provider=None,  # Not needed for demo
            repository=self.repository,
            container_service=self.container_service,
            event_bus=None,  # Not needed for demo
        )
        self.scheduler._scheduler_interval = 3  # Fast loop for demo

        self.demo_running = False

    async def create_sample_resource(self, name: str, start_delay_minutes: int = 0) -> LabInstanceRequest:
        """Create a sample lab instance resource."""
        spec = LabInstanceRequestSpec(
            lab_template="python:3.9-alpine",
            student_email=f"student-{name}@university.edu",
            duration_minutes=30,
            scheduled_start_time=datetime.utcnow() + timedelta(minutes=start_delay_minutes),
            environment={"LAB_TYPE": "demo"},
        )

        status = LabInstanceRequestStatus(phase=LabInstancePhase.PENDING)

        resource = LabInstanceRequest(spec=spec, status=status, namespace="demo", name=name)

        log.info(f"💾 Creating resource: {resource.metadata.namespace}/{resource.metadata.name}")
        await self.repository.save_async(resource)
        return resource

    async def update_resource_spec(self, resource: LabInstanceRequest, new_duration: int):
        """Update a resource's spec to trigger reconciliation."""
        log.info(f"📝 Updating resource spec: {resource.metadata.name} duration to {new_duration} minutes")
        resource.spec.duration_minutes = new_duration
        resource.metadata.generation += 1  # Increment generation for spec change
        await self.repository.save_async(resource)

    async def simulate_container_completion(self, resource: LabInstanceRequest):
        """Simulate a container completing."""
        if resource.status.container_id:
            log.info(f"🏁 Simulating container completion for: {resource.metadata.name}")
            # Mock container service will return "stopped" for this container
            await self.container_service.set_container_status_async(resource.status.container_id, "stopped")

    async def print_status_summary(self):
        """Print current status of all resources and services."""
        print("\n" + "=" * 80)
        print("📊 SYSTEM STATUS SUMMARY")
        print("=" * 80)

        # Repository status
        all_resources = await self.repository.list_async()
        print(f"📦 Total Resources: {len(all_resources)}")

        # Phase distribution
        phase_counts = {}
        for resource in all_resources:
            phase = resource.status.phase.value if resource.status else "UNKNOWN"
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        print("📈 Phase Distribution:")
        for phase, count in phase_counts.items():
            print(f"   {phase}: {count}")

        # Watcher status
        watcher_status = await self.watcher.get_watcher_status()
        print(f"👁️  Watcher: {'🟢 Active' if watcher_status['is_watching'] else '🔴 Inactive'}")
        print(f"   Cached Resources: {watcher_status['cached_resource_count']}")
        print(f"   Watch Interval: {watcher_status['watch_interval_seconds']}s")

        # Scheduler status
        scheduler_stats = await self.scheduler.get_service_statistics_async()
        print(f"⚙️  Scheduler: {'🟢 Running' if scheduler_stats.get('running', False) else '🔴 Stopped'}")

        # Recent events
        recent_events = self.event_publisher.published_events[-5:]  # Last 5 events
        print("📤 Recent Events:")
        for event in recent_events:
            print(f"   {event['timestamp'].strftime('%H:%M:%S')} - {event['type']} - {event['subject']}")

        print("=" * 80 + "\n")

    async def demonstrate_patterns(self):
        """Run the complete demonstration."""
        log.info("🚀 Starting Watcher and Reconciliation Loop Demonstration")

        try:
            self.demo_running = True

            # Step 1: Start background processes
            log.info("\n📋 Step 1: Starting Watcher and Scheduler")
            watcher_task = asyncio.create_task(self.watcher.watch(namespace="demo"))
            scheduler_task = asyncio.create_task(self.scheduler.start_async())

            await asyncio.sleep(1)  # Let them initialize

            # Step 2: Create initial resources
            log.info("\n📋 Step 2: Creating Initial Resources")
            resource1 = await self.create_sample_resource("lab-001", start_delay_minutes=0)  # Should start now
            resource2 = await self.create_sample_resource("lab-002", start_delay_minutes=2)  # Start in 2 min

            await asyncio.sleep(3)  # Let watcher detect and reconcile
            await self.print_status_summary()

            # Step 3: Update a resource spec
            log.info("\n📋 Step 3: Updating Resource Specification")
            await self.update_resource_spec(resource1, 45)  # Change duration

            await asyncio.sleep(3)  # Let watcher detect update
            await self.print_status_summary()

            # Step 4: Wait for scheduled resource to start
            log.info("\n📋 Step 4: Waiting for Scheduled Resource to Start")
            await asyncio.sleep(5)  # Let scheduler process
            await self.print_status_summary()

            # Step 5: Simulate container completion
            log.info("\n📋 Step 5: Simulating Container Completion")
            await self.simulate_container_completion(resource1)

            await asyncio.sleep(4)  # Let scheduler detect completion
            await self.print_status_summary()

            # Step 6: Create resource with immediate start
            log.info("\n📋 Step 6: Creating Resource with Immediate Start")
            resource3 = await self.create_sample_resource("lab-003", start_delay_minutes=0)

            await asyncio.sleep(4)  # Let system process
            await self.print_status_summary()

            # Step 7: Final status and cleanup
            log.info("\n📋 Step 7: Final Status and Cleanup")
            await asyncio.sleep(2)
            await self.print_status_summary()

            log.info("🎯 Demonstration completed successfully!")

        except Exception as e:
            log.error(f"❌ Demonstration failed: {e}")
            raise
        finally:
            # Cleanup
            self.demo_running = False
            await self.watcher.stop_watching()
            await self.scheduler.stop_async()

            if "watcher_task" in locals():
                watcher_task.cancel()
            if "scheduler_task" in locals():
                scheduler_task.cancel()

    async def demonstrate_event_flow(self):
        """Demonstrate the event flow in detail."""
        log.info("🔄 Demonstrating Event Flow Patterns")

        print("\n" + "=" * 80)
        print("🔄 EVENT FLOW DEMONSTRATION")
        print("=" * 80)

        # Start watcher only (no scheduler)
        watcher_task = asyncio.create_task(self.watcher.watch(namespace="demo"))
        await asyncio.sleep(1)

        print("1️⃣ Creating resource (triggers CREATED event)")
        resource = await self.create_sample_resource("event-demo", 0)
        await asyncio.sleep(2)  # Let watcher detect

        print("2️⃣ Updating resource spec (triggers UPDATED event)")
        await self.update_resource_spec(resource, 60)
        await asyncio.sleep(2)  # Let watcher detect

        print("3️⃣ Manually updating status (triggers STATUS_UPDATED event)")
        resource.status.phase = LabInstancePhase.PROVISIONING
        resource.status.last_updated = datetime.now(timezone.utc)
        await self.repository.save_async(resource)
        await asyncio.sleep(2)  # Let watcher detect

        print("4️⃣ Deleting resource (triggers DELETED event)")
        await self.repository.delete_async(resource.id)
        await asyncio.sleep(2)  # Let watcher detect

        # Show all events
        print("\n📤 All Events Published:")
        for i, event in enumerate(self.event_publisher.published_events, 1):
            print(f"   {i}. {event['timestamp'].strftime('%H:%M:%S')} - {event['type']}")
            print(f"      Subject: {event['subject']}")
            print(f"      Source: {event['source']}")
            if "changeType" in event["data"]:
                print(f"      Change: {event['data']['changeType']}")
            print()

        # Cleanup
        watcher_task.cancel()
        await self.watcher.stop_watching()


async def main():
    """Main demonstration function."""
    demo = WatcherReconciliationDemo()

    print("🎭 WATCHER AND RECONCILIATION LOOP DEMONSTRATION")
    print("=" * 60)
    print()
    print("This demo shows how:")
    print("• Resource Watcher detects changes and emits events")
    print("• Reconciliation Loop ensures desired state")
    print("• Controllers respond to changes")
    print("• Background services monitor resources")
    print()

    # Run main demonstration
    await demo.demonstrate_patterns()

    print("\n" + "=" * 60)
    input("Press Enter to see detailed event flow demonstration...")

    # Reset for event flow demo
    demo = WatcherReconciliationDemo()
    await demo.demonstrate_event_flow()

    print("\n🎉 All demonstrations completed!")


if __name__ == "__main__":
    asyncio.run(main())
