#!/usr/bin/env python3
"""
Simple test for the ResourceAllocator service.

This test demonstrates the ResourceAllocator functionality and verifies
that the LabInstanceController can properly check resource availability.
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


async def test_resource_allocator():
    """Test the ResourceAllocator functionality."""

    print("🧪 Testing ResourceAllocator Service")
    print("=" * 50)

    # Create allocator with limited resources for testing
    allocator = ResourceAllocator(total_cpu=4.0, total_memory_gb=8)

    # Test 1: Check initial availability
    print("\n1️⃣ Testing initial resource availability")

    small_request = {"cpu": "1", "memory": "2Gi"}
    large_request = {"cpu": "8", "memory": "16Gi"}  # Larger than available

    small_available = await allocator.check_availability(small_request)
    large_available = await allocator.check_availability(large_request)

    print(f"   Small request {small_request}: {'✅ Available' if small_available else '❌ Not available'}")
    print(f"   Large request {large_request}: {'✅ Available' if large_available else '❌ Not available'}")

    assert small_available, "Small request should be available"
    assert not large_available, "Large request should not be available"

    # Test 2: Allocate resources
    print("\n2️⃣ Testing resource allocation")

    try:
        allocation1 = await allocator.allocate_resources(small_request)
        print(f"   ✅ Allocated resources: {allocation1}")

        # Check usage
        usage = allocator.get_resource_usage()
        print(f"   📊 CPU usage: {usage['allocated_cpu']}/{usage['total_cpu']} ({usage['cpu_utilization']:.1f}%)")
        print(f"   📊 Memory usage: {usage['allocated_memory_mb']}/{usage['total_memory_mb']}MB ({usage['memory_utilization']:.1f}%)")

    except Exception as e:
        print(f"   ❌ Allocation failed: {e}")
        raise

    # Test 3: Check availability after allocation
    print("\n3️⃣ Testing availability after allocation")

    another_request = {"cpu": "2", "memory": "3Gi"}
    still_available = await allocator.check_availability(another_request)
    print(f"   Request {another_request}: {'✅ Available' if still_available else '❌ Not available'}")

    # Test 4: Allocate more resources
    print("\n4️⃣ Testing second allocation")

    if still_available:
        try:
            allocation2 = await allocator.allocate_resources(another_request)
            print(f"   ✅ Second allocation: {allocation2}")

            # Check usage again
            usage = allocator.get_resource_usage()
            print(f"   📊 CPU usage: {usage['allocated_cpu']}/{usage['total_cpu']} ({usage['cpu_utilization']:.1f}%)")
            print(f"   📊 Memory usage: {usage['allocated_memory_mb']}/{usage['total_memory_mb']}MB ({usage['memory_utilization']:.1f}%)")

        except Exception as e:
            print(f"   ❌ Second allocation failed: {e}")
            allocation2 = None
    else:
        print("   ⏭️ Skipping second allocation (not enough resources)")
        allocation2 = None

    # Test 5: Try to over-allocate
    print("\n5️⃣ Testing over-allocation protection")

    big_request = {"cpu": "4", "memory": "8Gi"}  # Should exceed remaining capacity
    try:
        await allocator.allocate_resources(big_request)
        print("   ❌ Over-allocation should have failed!")
        assert False, "Over-allocation should have been prevented"
    except ValueError as e:
        print(f"   ✅ Over-allocation correctly prevented: {e}")

    # Test 6: Release resources
    print("\n6️⃣ Testing resource release")

    await allocator.release_resources(allocation1)
    print(f"   ✅ Released first allocation")

    if allocation2:
        await allocator.release_resources(allocation2)
        print(f"   ✅ Released second allocation")

    # Check final usage
    usage = allocator.get_resource_usage()
    print(f"   📊 Final CPU usage: {usage['allocated_cpu']}/{usage['total_cpu']} ({usage['cpu_utilization']:.1f}%)")
    print(f"   📊 Final memory usage: {usage['allocated_memory_mb']}/{usage['total_memory_mb']}MB ({usage['memory_utilization']:.1f}%)")

    # Test 7: Test various resource limit formats
    print("\n7️⃣ Testing different resource limit formats")

    formats_to_test = [
        {"cpu": "0.5", "memory": "512Mi"},
        {"cpu": "1.5", "memory": "1.5Gi"},
        {"cpu": "2", "memory": "1024Mi"},
        {"cpu": "1", "memory": "2G"},  # Alternative format
    ]

    for i, format_test in enumerate(formats_to_test, 1):
        try:
            available = await allocator.check_availability(format_test)
            print(f"   ✅ Format {i} {format_test}: {'Available' if available else 'Not available'}")
        except Exception as e:
            print(f"   ❌ Format {i} {format_test}: Error - {e}")

    print("\n🎉 All ResourceAllocator tests completed successfully!")


async def test_controller_integration():
    """Test that simulates how the LabInstanceController would use ResourceAllocator."""

    print("\n🎮 Testing Controller Integration")
    print("=" * 50)

    # Create allocator
    allocator = ResourceAllocator(total_cpu=8.0, total_memory_gb=16)

    # Simulate typical lab instance resource requirements
    lab_templates = [
        {"name": "python-basics", "cpu": "1", "memory": "2Gi"},
        {"name": "data-science", "cpu": "2", "memory": "4Gi"},
        {"name": "web-development", "cpu": "1.5", "memory": "3Gi"},
        {"name": "machine-learning", "cpu": "4", "memory": "8Gi"},
    ]

    allocations = []

    # Try to allocate resources for multiple lab instances
    for i, template in enumerate(lab_templates, 1):
        resource_limits = {"cpu": template["cpu"], "memory": template["memory"]}

        print(f"\n{i}️⃣ Checking availability for {template['name']} lab")
        print(f"   Resource requirements: {resource_limits}")

        # This is the key method that LabInstanceController calls
        available = await allocator.check_availability(resource_limits)

        if available:
            print(f"   ✅ Resources available, allocating...")
            try:
                allocation = await allocator.allocate_resources(resource_limits)
                allocations.append(allocation)
                print(f"   ✅ Allocation successful: {allocation['allocation_id']}")

                # Show current usage
                usage = allocator.get_resource_usage()
                print(f"   📊 Total usage: {usage['cpu_utilization']:.1f}% CPU, {usage['memory_utilization']:.1f}% Memory")

            except Exception as e:
                print(f"   ❌ Allocation failed: {e}")
        else:
            print(f"   ❌ Insufficient resources for {template['name']} lab")
            # Show what's available
            usage = allocator.get_resource_usage()
            print(f"   📊 Available: {usage['available_cpu']} CPU, {usage['available_memory_mb']}MB Memory")

    # Show all active allocations
    print(f"\n📋 Active allocations: {len(allocations)}")
    active = allocator.get_active_allocations()
    for alloc_id, alloc_info in active.items():
        print(f"   {alloc_id}: {alloc_info['cpu']} CPU, {alloc_info['memory']} Memory")

    # Simulate lab completion and resource release
    print(f"\n🧹 Cleaning up allocations...")
    for allocation in allocations:
        await allocator.release_resources(allocation)
        print(f"   ✅ Released {allocation['allocation_id']}")

    # Final check
    usage = allocator.get_resource_usage()
    print(f"\n🎉 Cleanup complete. Usage: {usage['cpu_utilization']:.1f}% CPU, {usage['memory_utilization']:.1f}% Memory")


async def main():
    """Main test function."""
    try:
        await test_resource_allocator()
        await test_controller_integration()
        print("\n🚀 All tests passed! ResourceAllocator is ready for use.")

    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
