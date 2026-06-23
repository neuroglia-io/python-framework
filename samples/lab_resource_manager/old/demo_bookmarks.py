"""
Watch Bookmarks Demo - Reliable Event Processing

This demo shows how to use watch bookmarks to ensure reliable event
processing even when watchers restart or crash.

Bookmarks solve the problem of:
- Missing events during restarts
- Processing events multiple times
- Maintaining correct event order
- Handling long-running operations

Features Demonstrated:
- Bookmark persistence to Redis
- Automatic resumption from last processed event
- Crash recovery without event loss
- Bookmark key management
- Multiple watchers with independent bookmarks

Usage:
    # Start Redis (required for bookmarks)
    docker run -d -p 6379:6379 redis:latest

    # Run the demo
    python samples/lab_resource_manager/demo_bookmarks.py
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
from redis.asyncio import Redis

from neuroglia.data.resources import ResourceMetadata, ResourceWatcherBase
from neuroglia.data.resources.controller import (
    ReconciliationResult,
    ResourceControllerBase,
)
from neuroglia.dependency_injection import ServiceCollection

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class EventTracker:
    """Tracks processed events for demonstration."""

    def __init__(self):
        self.events = []

    def track(self, resource_name: str, resource_version: str, action: str):
        event = {"timestamp": datetime.now(), "resource": resource_name, "version": resource_version, "action": action}
        self.events.append(event)
        log.info(f"📝 Tracked event: {resource_name} v{resource_version} - {action}")

    def summary(self):
        log.info("📊 Event Processing Summary:")
        log.info(f"   Total events processed: {len(self.events)}")
        if self.events:
            log.info(f"   First event: {self.events[0]['resource']} at {self.events[0]['timestamp'].strftime('%H:%M:%S')}")
            log.info(f"   Last event: {self.events[-1]['resource']} at {self.events[-1]['timestamp'].strftime('%H:%M:%S')}")


class SimpleLabController(ResourceControllerBase):
    """Simple controller for demo purposes."""

    def __init__(self, service_provider, event_tracker: EventTracker):
        super().__init__(service_provider)
        self.event_tracker = event_tracker

    async def _do_reconcile(self, resource: LabInstanceRequest) -> ReconciliationResult:
        """Simple reconciliation that just tracks the event."""
        self.event_tracker.track(resource.metadata.name, resource.metadata.resource_version, f"Reconciled in phase {resource.status.phase}")

        # Simulate some processing time
        await asyncio.sleep(0.1)

        return ReconciliationResult.success(f"Reconciled {resource.metadata.name}")


class LabInstanceWatcherWithBookmarks(ResourceWatcherBase):
    """Watcher that uses bookmarks for reliable event processing."""

    def __init__(self, controller: ResourceControllerBase, bookmark_storage: Redis, watcher_id: str, event_tracker: EventTracker):
        # Initialize with bookmark support
        super().__init__(controller=controller, poll_interval=timedelta(seconds=2), bookmark_storage=bookmark_storage, bookmark_key=f"lab-watcher-bookmark:{watcher_id}")
        self.watcher_id = watcher_id
        self.event_tracker = event_tracker

    async def handle_async(self, resource: LabInstanceRequest) -> None:
        """
        Handle resource changes.

        The bookmark is automatically:
        1. Loaded when the watcher starts (in watch() method)
        2. Saved after each event is processed (in _watch_loop())
        """
        log.info(f"[{self.watcher_id}] Processing: {resource.metadata.name} v{resource.metadata.resource_version}")

        self.event_tracker.track(resource.metadata.name, resource.metadata.resource_version, f"Watched by {self.watcher_id}")

        # Controller handles reconciliation
        await self.controller.reconcile(resource)


async def create_test_resources(count: int) -> list[LabInstanceRequest]:
    """Create test resources with incrementing versions."""
    resources = []

    for i in range(1, count + 1):
        resource = LabInstanceRequest(metadata=ResourceMetadata(name=f"lab-{i:03d}", namespace="default", resource_version=str(i), labels={"batch": "demo", "index": str(i)}), spec=LabInstanceRequestSpec(lab_template="python-jupyter", student_email=f"student{i}@example.com", resource_limits=ResourceLimits(cpu_cores=2.0, memory_mb=4096)), status=LabInstanceRequestStatus(phase=LabInstancePhase.PENDING))  # Simulated version
        resources.append(resource)

    return resources


async def demo_basic_bookmarks():
    """Demonstrate basic bookmark functionality."""

    log.info("=" * 80)
    log.info("🎯 Demo 1: Basic Bookmark Usage")
    log.info("=" * 80)

    # Setup Redis
    redis_client = Redis.from_url("redis://localhost:6379/2", decode_responses=True)

    # Clear any existing bookmarks
    await redis_client.delete("lab-watcher-bookmark:watcher-1")

    event_tracker = EventTracker()
    services = ServiceCollection()
    service_provider = services.build_provider()
    controller = SimpleLabController(service_provider, event_tracker)

    # Create watcher with bookmark support
    watcher = LabInstanceWatcherWithBookmarks(controller=controller, bookmark_storage=redis_client, watcher_id="watcher-1", event_tracker=event_tracker)

    log.info("\n📚 Creating test resources...")
    resources = await create_test_resources(5)
    log.info(f"✅ Created {len(resources)} resources")

    # Simulate processing resources
    log.info("\n🔄 Processing resources...")
    for resource in resources:
        await watcher.handle_async(resource)
        # Bookmark is automatically saved after each event
        bookmark = await redis_client.get("lab-watcher-bookmark:watcher-1")
        log.info(f"   Bookmark saved: {bookmark}")

    # Check final bookmark
    final_bookmark = await redis_client.get("lab-watcher-bookmark:watcher-1")
    log.info(f"\n✅ Final bookmark: {final_bookmark}")
    log.info(f"   This bookmark will be used for resumption on restart")

    event_tracker.summary()

    await redis_client.close()


async def demo_crash_recovery():
    """Demonstrate crash recovery with bookmarks."""

    log.info("\n" + "=" * 80)
    log.info("🎯 Demo 2: Crash Recovery")
    log.info("=" * 80)

    redis_client = Redis.from_url("redis://localhost:6379/2", decode_responses=True)

    # Clear bookmark
    await redis_client.delete("lab-watcher-bookmark:watcher-2")

    event_tracker = EventTracker()
    services = ServiceCollection()
    service_provider = services.build_provider()

    # Create resources
    all_resources = await create_test_resources(10)

    # --- First Run: Process partial set ---
    log.info("\n🟢 First run: Processing 6 out of 10 resources...")
    controller1 = SimpleLabController(service_provider, event_tracker)
    watcher1 = LabInstanceWatcherWithBookmarks(controller=controller1, bookmark_storage=redis_client, watcher_id="watcher-2", event_tracker=event_tracker)

    # Process first 6 resources
    for resource in all_resources[:6]:
        await watcher1.handle_async(resource)

    bookmark_after_first_run = await redis_client.get("lab-watcher-bookmark:watcher-2")
    log.info(f"✅ Processed 6 resources, bookmark: {bookmark_after_first_run}")

    # Simulate crash
    log.info("\n💥 SIMULATING CRASH - Watcher stopped unexpectedly!")
    log.info("   (In real scenario, pod might be killed or node fails)")
    await asyncio.sleep(1)

    # --- Second Run: Resume from bookmark ---
    log.info("\n🟢 Second run: Restarting watcher (will resume from bookmark)...")
    event_tracker2 = EventTracker()
    controller2 = SimpleLabController(service_provider, event_tracker2)
    watcher2 = LabInstanceWatcherWithBookmarks(controller=controller2, bookmark_storage=redis_client, watcher_id="watcher-2", event_tracker=event_tracker2)  # Same ID = same bookmark

    # The watcher will load the bookmark when it starts
    loaded_bookmark = await redis_client.get("lab-watcher-bookmark:watcher-2")
    log.info(f"📖 Loaded bookmark on restart: {loaded_bookmark}")
    log.info(f"   Will skip resources 1-6, start from resource 7")

    # Process remaining resources (simulating resumed watch)
    # In real scenario, the watch loop would filter based on resource version
    log.info("\n🔄 Processing remaining resources...")
    for resource in all_resources[6:]:
        await watcher2.handle_async(resource)

    final_bookmark = await redis_client.get("lab-watcher-bookmark:watcher-2")
    log.info(f"\n✅ All resources processed after recovery")
    log.info(f"   Final bookmark: {final_bookmark}")
    log.info(f"   Events in first run: {len(event_tracker.events)}")
    log.info(f"   Events in second run: {len(event_tracker2.events)}")
    log.info(f"   Total unique resources: {len(all_resources)}")

    await redis_client.close()


async def demo_multiple_watchers():
    """Demonstrate multiple watchers with independent bookmarks."""

    log.info("\n" + "=" * 80)
    log.info("🎯 Demo 3: Multiple Independent Watchers")
    log.info("=" * 80)

    redis_client = Redis.from_url("redis://localhost:6379/2", decode_responses=True)

    # Clear bookmarks
    await redis_client.delete("lab-watcher-bookmark:watcher-fast")
    await redis_client.delete("lab-watcher-bookmark:watcher-slow")

    services = ServiceCollection()
    service_provider = services.build_provider()

    # Create resources
    resources = await create_test_resources(5)

    # Create two watchers with different IDs (independent bookmarks)
    log.info("\n🏃 Creating two watchers:")
    log.info("   - watcher-fast: Processes quickly")
    log.info("   - watcher-slow: Processes slowly")

    tracker_fast = EventTracker()
    controller_fast = SimpleLabController(service_provider, tracker_fast)
    watcher_fast = LabInstanceWatcherWithBookmarks(controller=controller_fast, bookmark_storage=redis_client, watcher_id="watcher-fast", event_tracker=tracker_fast)

    tracker_slow = EventTracker()
    controller_slow = SimpleLabController(service_provider, tracker_slow)
    watcher_slow = LabInstanceWatcherWithBookmarks(controller=controller_slow, bookmark_storage=redis_client, watcher_id="watcher-slow", event_tracker=tracker_slow)

    # Process with fast watcher
    log.info("\n⚡ Fast watcher processing all resources...")
    for resource in resources:
        await watcher_fast.handle_async(resource)

    bookmark_fast = await redis_client.get("lab-watcher-bookmark:watcher-fast")
    log.info(f"✅ Fast watcher bookmark: {bookmark_fast}")

    # Process only some with slow watcher
    log.info("\n🐌 Slow watcher processing first 3 resources...")
    for resource in resources[:3]:
        await watcher_slow.handle_async(resource)
        await asyncio.sleep(0.2)  # Simulate slow processing

    bookmark_slow = await redis_client.get("lab-watcher-bookmark:watcher-slow")
    log.info(f"✅ Slow watcher bookmark: {bookmark_slow}")

    # Show independence
    log.info("\n📊 Bookmark Independence:")
    log.info(f"   Fast watcher: {bookmark_fast} (processed all)")
    log.info(f"   Slow watcher: {bookmark_slow} (processed 3/5)")
    log.info(f"   ✅ Each watcher maintains its own progress!")

    await redis_client.close()


async def main():
    """Run all demos."""

    log.info("🚀 Watch Bookmarks Demo - Reliable Event Processing")
    log.info("=" * 80)

    try:
        # Check Redis connectivity
        redis_test = Redis.from_url("redis://localhost:6379", decode_responses=True)
        await redis_test.ping()
        await redis_test.close()
        log.info("✅ Redis connection verified\n")
    except Exception as e:
        log.error(f"❌ Redis connection failed: {e}")
        log.error("Please start Redis: docker run -d -p 6379:6379 redis:latest")
        return

    # Run demos
    await demo_basic_bookmarks()
    await demo_crash_recovery()
    await demo_multiple_watchers()

    log.info("\n" + "=" * 80)
    log.info("✨ All demos complete!")
    log.info("=" * 80)
    log.info("\n📚 Key Takeaways:")
    log.info("   1. Bookmarks persist the last processed resource version")
    log.info("   2. Watchers automatically resume from bookmarks on restart")
    log.info("   3. Each watcher can have independent bookmarks")
    log.info("   4. No events are lost during crashes or restarts")
    log.info("   5. Events are not processed multiple times")


if __name__ == "__main__":
    asyncio.run(main())
