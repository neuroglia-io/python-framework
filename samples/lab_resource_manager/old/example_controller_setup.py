"""
Example showing how to set up the LabInstanceController with ResourceAllocator.

This demonstrates the dependency injection and service setup for the controller.
"""

from integration.services.container_service import ContainerService
from integration.services.resource_allocator import ResourceAllocator

# For demonstration - normally these would come from the framework's DI container


class ExampleControllerSetup:
    """Example showing how to wire up the controller with its dependencies."""

    @staticmethod
    def create_resource_allocator() -> ResourceAllocator:
        """Create and configure a ResourceAllocator instance."""

        # Configure based on your environment
        # For a development environment:
        if True:  # development mode
            return ResourceAllocator(total_cpu=8.0, total_memory_gb=16)  # 8 CPU cores available  # 16 GB RAM available

        # For production, you might read from config:
        # return ResourceAllocator(
        #     total_cpu=float(os.getenv("TOTAL_CPU_CORES", "32")),
        #     total_memory_gb=int(os.getenv("TOTAL_MEMORY_GB", "128"))
        # )

    @staticmethod
    def create_lab_instance_controller():
        """Create a LabInstanceController with all its dependencies."""

        # Create services
        resource_allocator = ExampleControllerSetup.create_resource_allocator()
        container_service = ContainerService()  # Assuming this exists

        # Note: In a real setup, you would import and instantiate:
        # from domain.controllers.lab_instance_controller import LabInstanceController
        #
        # controller = LabInstanceController(
        #     service_provider=service_provider,  # From DI container
        #     container_service=container_service,
        #     resource_allocator=resource_allocator,
        #     event_publisher=event_publisher     # Optional
        # )

        print("✅ LabInstanceController configured with:")
        print(f"   📊 ResourceAllocator: {resource_allocator.total_cpu} CPU, {resource_allocator.total_memory_mb/1024}GB RAM")
        print(f"   🐳 ContainerService: {type(container_service).__name__}")

        return {"resource_allocator": resource_allocator, "container_service": container_service}


# Example usage
if __name__ == "__main__":
    print("🔧 Example LabInstanceController Setup")
    print("=" * 50)

    # This shows how you would set up the controller
    services = ExampleControllerSetup.create_lab_instance_controller()

    print(f"\n📋 ResourceAllocator capabilities:")
    allocator = services["resource_allocator"]
    usage = allocator.get_resource_usage()
    print(f"   💻 Total CPU cores: {usage['total_cpu']}")
    print(f"   🧠 Total memory: {usage['total_memory_mb']/1024:.1f}GB")
    print(f"   📈 Current utilization: {usage['cpu_utilization']:.1f}% CPU, {usage['memory_utilization']:.1f}% Memory")

    print(f"\n🎯 The controller is now ready to:")
    print(f"   ✅ Check resource availability with: await resource_allocator.check_availability(resource.spec.resource_limits)")
    print(f"   ✅ Allocate resources with: await resource_allocator.allocate_resources(resource.spec.resource_limits)")
    print(f"   ✅ Release resources with: await resource_allocator.release_resources(allocation)")

    print(f"\n🚀 Ready to handle lab instance requests!")
