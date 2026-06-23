"""
High Availability Deployment Demo

This demo shows how to run multiple instances of the Lab Resource Manager
with leader election to ensure only one controller is actively reconciling
resources at a time.

Features Demonstrated:
- Leader election for multi-instance deployments
- Automatic failover when leader goes down
- Graceful handoff during rolling updates
- Resource finalizers for cleanup
- Watch bookmarks for resumption

Usage:
    # Terminal 1 - Start first instance (becomes leader)
    python samples/lab_resource_manager/demo_ha_deployment.py --instance-id instance-1 --port 8001

    # Terminal 2 - Start second instance (becomes standby)
    python samples/lab_resource_manager/demo_ha_deployment.py --instance-id instance-2 --port 8002

    # Terminal 3 - Start third instance (becomes standby)
    python samples/lab_resource_manager/demo_ha_deployment.py --instance-id instance-2 --port 8002
"""

import argparse
import asyncio
import logging
import sys
from datetime import timedelta
from pathlib import Path

# Add the project root to Python path so we can import neuroglia
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))  # For neuroglia imports
sys.path.insert(0, str(Path(__file__).parent))  # For local imports from lab_resource_manager

from domain.controllers.lab_instance_request_controller import (
    LabInstanceRequestController,
)
from domain.resources.lab_instance_request import (
    LabInstanceRequest,
    LabInstanceRequestSpec,
    LabInstanceRequestStatus,
)
from integration.services.container_service import ContainerService
from integration.services.resource_allocator import ResourceAllocator
from redis.asyncio import Redis

from neuroglia.coordination import (
    LeaderElection,
    LeaderElectionConfig,
    RedisCoordinationBackend,
)
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepository
from neuroglia.data.resources import ResourceWatcherBase
from neuroglia.data.resources.serializers.yaml_serializer import YamlResourceSerializer
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublisher,
)
from neuroglia.hosting.configuration.data_access_layer import DataAccessLayer
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.logging.logger import configure_logging
from neuroglia.mapping.mapper import Mapper
from neuroglia.mediation.mediator import Mediator
from neuroglia.serialization.json import JsonSerializer

configure_logging(level=logging.INFO)
log = logging.getLogger(__name__)


class HALabInstanceWatcher(ResourceWatcherBase[LabInstanceRequestSpec, LabInstanceRequestStatus]):
    """Watcher with bookmark support for reliable event resumption."""

    def __init__(self, controller: LabInstanceRequestController, bookmark_storage: Redis, instance_id: str):
        # Pass bookmark storage for resumption support
        super().__init__(controller=controller, poll_interval=timedelta(seconds=5), bookmark_storage=bookmark_storage, bookmark_key=f"lab-watcher-bookmark:{instance_id}")
        self.instance_id = instance_id

    async def handle_async(self, resource: LabInstanceRequest) -> None:
        """Handle resource changes - bookmarks are automatically saved."""
        resource_name = f"{resource.metadata.namespace}/{resource.metadata.name}"
        log.info(f"[{self.instance_id}] Processing resource change: {resource_name}")

        # Controller handles the reconciliation
        # The bookmark is automatically saved after this completes
        await self.controller.reconcile(resource)


async def setup_leader_election(redis_client: Redis, instance_id: str, controller: LabInstanceRequestController) -> LeaderElection:
    """Set up leader election for the controller."""

    # Create coordination backend
    backend = RedisCoordinationBackend(redis_client)

    # Configure leader election
    config = LeaderElectionConfig(lock_name="lab-instance-controller-leader", identity=instance_id, lease_duration=timedelta(seconds=15), renew_deadline=timedelta(seconds=10), retry_period=timedelta(seconds=2))  # How long before lease expires  # How often to renew  # How often to retry acquiring

    # Create leader election instance
    election = LeaderElection(config=config, backend=backend, on_start_leading=lambda: log.info(f"🎉 [{instance_id}] Became LEADER - starting reconciliation"), on_stop_leading=lambda: log.warning(f"🔄 [{instance_id}] Lost leadership - stopping reconciliation"))

    return election


async def create_ha_application(instance_id: str, port: int) -> tuple:
    """Create HA-enabled application with leader election."""

    log.info(f"🚀 Starting Lab Resource Manager instance: {instance_id} on port {port}")

    # Create Redis clients for coordination and bookmarks
    redis_coordination = Redis.from_url("redis://localhost:6379/0", decode_responses=False)
    redis_bookmarks = Redis.from_url("redis://localhost:6379/1", decode_responses=True)

    database_name = "lab_manager_ha"
    application_module = "application"

    builder = WebApplicationBuilder()

    # Configure core services
    Mapper.configure(builder, [application_module])
    Mediator.configure(builder, [application_module])
    JsonSerializer.configure(builder)
    CloudEventPublisher.configure(builder)

    # Configure resource serialization
    if YamlResourceSerializer.is_available():
        builder.services.add_singleton(YamlResourceSerializer)

    # Configure data access
    DataAccessLayer.ReadModel.configure(builder, ["integration.models"], lambda b, entity_type, key_type: MongoRepository.configure(b, entity_type, key_type, database_name))

    # Register application services
    builder.services.add_singleton(ContainerService)
    builder.services.add_singleton(ResourceAllocator)

    # Register controllers WITHOUT hosted services (we'll manage lifecycle manually)
    builder.add_controllers(["api.controllers"])

    app = builder.build()
    app.use_controllers()

    # Create controller manually with finalizer support
    service_provider = app.services
    container_service = service_provider.get_service(ContainerService)
    resource_allocator = service_provider.get_service(ResourceAllocator)
    event_publisher = service_provider.get_service(CloudEventPublisher)

    controller = LabInstanceRequestController(service_provider=service_provider, container_service=container_service, resource_allocator=resource_allocator, event_publisher=event_publisher)

    # Add finalizer for cleanup
    controller.finalizer_name = f"lab-instance-controller.neuroglia.io/{instance_id}"

    # Set up leader election
    leader_election = await setup_leader_election(redis_coordination, instance_id, controller)

    # Create watcher with bookmark support
    watcher = HALabInstanceWatcher(controller=controller, bookmark_storage=redis_bookmarks, instance_id=instance_id)

    # Attach leader election to controller
    controller.leader_election = leader_election

    log.info(f"✅ [{instance_id}] Instance configured with:")
    log.info(f"   - Leader Election: Enabled")
    log.info(f"   - Finalizer: {controller.finalizer_name}")
    log.info(f"   - Bookmark Key: lab-watcher-bookmark:{instance_id}")
    log.info(f"   - API Port: {port}")

    return app, controller, watcher, leader_election


async def run_ha_instance(instance_id: str, port: int):
    """Run a single HA instance."""

    app, controller, watcher, leader_election = await create_ha_application(instance_id, port)

    # Start leader election
    election_task = asyncio.create_task(leader_election.run())

    # Wait a bit for election to settle
    await asyncio.sleep(2)

    # Start watcher (only processes when leader)
    watcher_task = asyncio.create_task(watcher.watch())

    log.info(f"🎯 [{instance_id}] All services started")
    log.info(f"   Leadership status: {'LEADER' if leader_election.is_leader() else 'STANDBY'}")

    try:
        # Keep running
        await asyncio.gather(election_task, watcher_task)
    except KeyboardInterrupt:
        log.info(f"🛑 [{instance_id}] Shutting down gracefully...")

        # Stop watcher first
        watcher.stop()
        await watcher_task

        # Release leadership
        await leader_election.release()
        election_task.cancel()

        log.info(f"✅ [{instance_id}] Shutdown complete")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run HA Lab Resource Manager instance")
    parser.add_argument("--instance-id", required=True, help="Unique instance identifier")
    parser.add_argument("--port", type=int, required=True, help="API port")
    parser.add_argument("--log-level", default="INFO", help="Log level")

    args = parser.parse_args()

    # Configure logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Run instance
    asyncio.run(run_ha_instance(args.instance_id, args.port))


if __name__ == "__main__":
    main()
