#!/usr/bin/env python3
"""
Demonstration of LabInstanceController with ResourceAllocator integration.

This demo shows how the controller checks resource availability before
allocating resources for lab instances.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to Python path so we can import neuroglia
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))  # For neuroglia imports
sys.path.insert(0, str(Path(__file__).parent))  # For local imports from lab_resource_manager

from integration.services.resource_allocator import ResourceAllocator

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


class MockLabInstanceRequest:
    """Mock lab instance request for demonstration."""

    def __init__(self, name: str, resource_limits: dict):
        self.metadata = type("obj", (object,), {"name": name, "namespace": "demo"})()
        self.spec = type("obj", (object,), {"resource_limits": resource_limits})()
        self.status = type("obj", (object,), {})()


class SimplifiedLabInstanceController:
    """Simplified controller showing ResourceAllocator integration."""

    def __init__(self, resource_allocator: ResourceAllocator):
        self.resource_allocator = resource_allocator

    async def _check_resource_availability(self, resource: MockLabInstanceRequest) -> bool:
        """Check if required resources are available."""
        # This is the exact line from the real controller (line 318)
        return await self.resource_allocator.check_availability(resource.spec.resource_limits)

    async def process_lab_request(self, resource: MockLabInstanceRequest) -> bool:
        """Process a lab instance request (simplified workflow)."""

        resource_name = f"{resource.metadata.namespace}/{resource.metadata.name}"
        log.info(f"🔍 Processing lab request: {resource_name}")
        log.info(f"   Resource requirements: {resource.spec.resource_limits}")

        # Step 1: Check resource availability (this is the key integration point)
        resources_available = await self._check_resource_availability(resource)

        if not resources_available:
            log.warning(f"❌ Insufficient resources for {resource_name}")
            return False

        log.info(f"✅ Resources available for {resource_name}")

        # Step 2: Allocate resources (would happen in _transition_to_provisioning)
        try:
            allocation = await self.resource_allocator.allocate_resources(resource.spec.resource_limits)
            resource.status.resource_allocation = allocation
            log.info(f"🎯 Resources allocated: {allocation['allocation_id']}")

            # Simulate lab running for a bit
            await asyncio.sleep(1)

            # Step 3: Release resources when done (would happen in _transition_to_completed)
            await self.resource_allocator.release_resources(allocation)
            log.info(f"🧹 Resources released for {resource_name}")

            return True

        except Exception as e:
            log.error(f"💥 Failed to allocate resources for {resource_name}: {e}")
            return False


async def demo_controller_with_resource_allocator():
    """Demonstrate the controller working with the ResourceAllocator."""

    print("🎯 Lab Instance Controller + ResourceAllocator Demo")
    print("=" * 60)

    # Create resource allocator with limited capacity
    allocator = ResourceAllocator(total_cpu=6.0, total_memory_gb=12)

    # Create controller
    controller = SimplifiedLabInstanceController(allocator)

    # Create various lab requests
    lab_requests = [
        MockLabInstanceRequest("python-intro", {"cpu": "1", "memory": "2Gi"}),
        MockLabInstanceRequest("data-analysis", {"cpu": "2", "memory": "4Gi"}),
        MockLabInstanceRequest("web-dev", {"cpu": "1.5", "memory": "3Gi"}),
        MockLabInstanceRequest("ml-training", {"cpu": "4", "memory": "8Gi"}),  # This should fail
        MockLabInstanceRequest("javascript-basics", {"cpu": "1", "memory": "1Gi"}),
    ]

    successful_requests = 0
    failed_requests = 0

    print(f"\n📊 Starting with {allocator.total_cpu} CPU cores and {allocator.total_memory_mb/1024}GB memory")

    # Process each request
    for i, request in enumerate(lab_requests, 1):
        print(f"\n{i}️⃣ Processing request #{i}")

        # Show current resource usage before processing
        usage = allocator.get_resource_usage()
        print(f"   📈 Current usage: {usage['cpu_utilization']:.1f}% CPU, {usage['memory_utilization']:.1f}% Memory")

        # Process the request
        success = await controller.process_lab_request(request)

        if success:
            successful_requests += 1
        else:
            failed_requests += 1

        # Show resource status after processing
        usage = allocator.get_resource_usage()
        print(f"   📊 Final usage: {usage['cpu_utilization']:.1f}% CPU, {usage['memory_utilization']:.1f}% Memory")
        print(f"   🏃 Active allocations: {usage['active_allocations']}")

    # Summary
    print(f"\n📋 Processing Summary")
    print(f"   ✅ Successful requests: {successful_requests}")
    print(f"   ❌ Failed requests: {failed_requests}")
    print(f"   📊 Final resource utilization: {usage['cpu_utilization']:.1f}% CPU, {usage['memory_utilization']:.1f}% Memory")

    # Show what the check_availability method specifically does
    print(f"\n🔍 Demonstrating the check_availability method")
    print("   This is the exact method called from LabInstanceController line 318:")
    print("   return await self.resource_allocator.check_availability(resource.spec.resource_limits)")

    test_requests = [
        {"cpu": "1", "memory": "1Gi"},
        {"cpu": "3", "memory": "6Gi"},
        {"cpu": "10", "memory": "20Gi"},  # Should be false
    ]

    for req in test_requests:
        available = await allocator.check_availability(req)
        usage = allocator.get_resource_usage()
        print(f"   Request {req}: {'✅ Available' if available else '❌ Not available'} " f"(Available: {usage['available_cpu']} CPU, {usage['available_memory_mb']}MB)")


async def main():
    """Main demo function."""
    try:
        await demo_controller_with_resource_allocator()
        print("\n🚀 ResourceAllocator integration demo completed successfully!")
        print("\nThe LabInstanceController can now:")
        print("  ✅ Check resource availability before allocation")
        print("  ✅ Allocate resources for lab instances")
        print("  ✅ Release resources when labs complete")
        print("  ✅ Handle resource limits in various formats")
        print("  ✅ Prevent over-allocation with proper error handling")

    except Exception as e:
        print(f"\n💥 Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
