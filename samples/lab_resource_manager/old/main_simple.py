"""Lab Resource Manager Sample Application - Simplified Version.

This version demonstrates the Resource Oriented Architecture (ROA) patterns
with the components we've created, using in-memory storage for simplicity.
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

from application.commands.create_lab_instance_command import (
    CreateLabInstanceCommandHandler,
)
from application.queries.get_lab_instance_query_handler import (
    GetLabInstanceQueryHandler,
)
from application.queries.list_lab_instances_query_handler import (
    ListLabInstancesQueryHandler,
)
from application.services.lab_instance_scheduler_service import (
    LabInstanceSchedulerService,
)

# Application imports
from integration.repositories.lab_instance_resource_repository import (
    LabInstanceResourceRepository,
)
from integration.services.container_service import ContainerService

from neuroglia.data.infrastructure.resources.in_memory_storage_backend import (
    InMemoryStorageBackend,
)
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.serialization.json import JsonSerializer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

log = logging.getLogger(__name__)


def create_simple_app():
    """Create a simplified version of the application for demonstration."""
    builder = WebApplicationBuilder()

    # Get service collection
    services = builder.services

    # Add framework services
    services.add_mediator()
    services.add_controllers(["api.controllers"])

    # Add infrastructure services
    services.add_singleton(InMemoryStorageBackend)
    services.add_singleton(JsonSerializer)

    # Add repository with factory method
    def create_repository(service_provider):
        storage = service_provider.get_service(InMemoryStorageBackend)
        return LabInstanceResourceRepository.create_with_json_serializer(storage)

    services.add_scoped(LabInstanceResourceRepository, create_repository)

    # Add integration services
    services.add_scoped(ContainerService)

    # Add background services
    services.add_hosted_service(LabInstanceSchedulerService)

    # Add command and query handlers
    services.add_scoped(CreateLabInstanceCommandHandler)
    services.add_scoped(GetLabInstanceQueryHandler)
    services.add_scoped(ListLabInstancesQueryHandler)

    # Build the application
    app = builder.build()

    # Configure middleware and routes
    app.use_controllers()

    return app


async def create_sample_data(app):
    """Create some sample lab instances for testing."""
    try:
        from application.commands.create_lab_instance_command import (
            CreateLabInstanceCommand,
        )

        from neuroglia.mediation.abstractions import Mediator

        # Get services
        service_provider = app.service_provider
        mediator = service_provider.get_service(Mediator)

        log.info("Creating sample lab instances...")

        # Create sample lab instances
        sample_commands = [
            CreateLabInstanceCommand(namespace="default", name="python-basics-lab-001", lab_template="python:3.9-alpine", student_email="student1@university.edu", duration_minutes=60, scheduled_start_time=datetime.utcnow() + timedelta(minutes=5), environment={"LAB_TYPE": "python-basics"}),
            CreateLabInstanceCommand(namespace="advanced", name="docker-workshop-lab-001", lab_template="docker:dind", student_email="student2@university.edu", duration_minutes=120, scheduled_start_time=datetime.utcnow() + timedelta(minutes=10), environment={"LAB_TYPE": "docker-workshop", "DOCKER_TLS_CERTDIR": ""}),
            CreateLabInstanceCommand(namespace="default", name="web-dev-lab-001", lab_template="node:16-alpine", student_email="student3@university.edu", duration_minutes=90, scheduled_start_time=datetime.utcnow() + timedelta(hours=1), environment={"LAB_TYPE": "web-development", "NODE_ENV": "development"}),
        ]

        for command in sample_commands:
            try:
                result = await mediator.execute_async(command)
                if result.is_success:
                    log.info(f"✓ Created sample lab instance: {command.name}")
                else:
                    log.warning(f"✗ Failed to create sample lab instance {command.name}: {result.error_message}")
            except Exception as e:
                log.error(f"✗ Error creating sample lab instance {command.name}: {e}")

        log.info("Sample data creation completed")

    except Exception as e:
        log.error(f"Error creating sample data: {e}")


def main():
    """Main application entry point."""
    log.info("🚀 Starting Lab Resource Manager")

    app = create_simple_app()

    # Schedule sample data creation
    asyncio.create_task(create_sample_data(app))

    log.info("🌐 Lab Resource Manager started successfully")
    log.info("📋 API available at: http://localhost:8000")
    log.info("📖 Swagger UI at: http://localhost:8000/docs")
    log.info("❤️  Health check at: http://localhost:8000/api/status/health")
    log.info("📊 System status at: http://localhost:8000/api/status/status")
    log.info("🧪 Lab instances at: http://localhost:8000/api/lab-instances/")

    # Run the application
    app.run(host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
