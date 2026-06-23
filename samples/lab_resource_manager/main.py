#!/usr/bin/env python3
"""Lab Resource Manager Sample Application.

This sample demonstrates Resource Oriented Architecture (ROA) patterns
using the Neuroglia framework to manage lab instance resources with
declarative specifications, state machines, and concurrent execution.
"""

import logging
import sys
from pathlib import Path

# Add the project root to Python path so we can import neuroglia
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Third-party imports
import etcd3
from application.services.logger import configure_logging

# Application imports
from application.settings import app_settings
from integration.repositories.etcd_lab_worker_repository import (
    EtcdLabWorkerResourceRepository,
)

# Framework imports (must be after path manipulation)
from neuroglia.data.resources.serializers.yaml_serializer import YamlResourceSerializer
from neuroglia.eventing.cloud_events.infrastructure import (
    CloudEventMiddleware,
    CloudEventPublisher,
)
from neuroglia.hosting.web import SubAppConfig, WebApplicationBuilder
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.serialization.json import JsonSerializer

configure_logging(log_level=app_settings.log_level.upper())
log = logging.getLogger(__name__)
log.info("🧪 Lab Resource Manager starting up...")


def create_lab_resource_manager_app():
    """Create and configure the Lab Resource Manager application."""
    log.info("Bootstrapping Lab Resource Manager...")

    builder = WebApplicationBuilder(app_settings)

    # Configure Core services
    Mediator.configure(builder, ["application.commands", "application.queries", "application.events"])
    Mapper.configure(builder, ["application", "integration.models"])
    JsonSerializer.configure(builder, ["domain"])
    CloudEventPublisher.configure(builder)

    # Configure resource serialization
    if YamlResourceSerializer.is_available():
        builder.services.add_singleton(YamlResourceSerializer)
        log.info("YAML serialization enabled")
    else:
        log.warning("YAML serialization not available - install PyYAML")

    # Register etcd client as singleton for resource persistence
    # Using sync Client - storage operations are wrapped in async by repository layer
    # etcd provides native watchable API, strong consistency, and atomic operations
    etcd_client = etcd3.Client(host=app_settings.etcd_host, port=app_settings.etcd_port, timeout=app_settings.etcd_timeout)
    builder.services.try_add_singleton(etcd3.Client, singleton=etcd_client)
    log.info(f"etcd client registered as singleton: {app_settings.etcd_host}:{app_settings.etcd_port}")

    # Register EtcdLabWorkerResourceRepository as scoped service (one per request)
    # Scoped lifetime ensures proper async context and integration with UnitOfWork
    def create_lab_worker_repository(sp):
        """Factory function for EtcdLabWorkerResourceRepository with DI."""
        return EtcdLabWorkerResourceRepository.create_with_json_serializer(
            etcd_client=sp.get_required_service(etcd3.Client),
            prefix=f"{app_settings.etcd_prefix}/lab-workers/",
        )

    builder.services.add_scoped(EtcdLabWorkerResourceRepository, implementation_factory=create_lab_worker_repository)
    log.info("EtcdLabWorkerResourceRepository registered as scoped service")

    # Register application services
    # builder.services.add_singleton(ContainerService)
    # builder.services.add_singleton(ResourceAllocator)
    # builder.services.add_scoped(LabInstanceRequestController)
    # builder.services.add_scoped(LabInstanceSchedulerService)

    # Configure sub-applications declaratively
    # API sub-app: REST API with OAuth2/JWT authentication
    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            title="Lab Resource Manager API",
            description="Lab instance and worker resource management API with OAuth2/JWT authentication",
            version="1.0.0",
            controllers=["api.controllers"],
            docs_url="/docs",
        )
    )

    # Build the complete application with all sub-apps mounted and configured
    # This automatically:
    # - Creates the main FastAPI app with Host lifespan
    # - Creates and configures the API sub-app
    # - Mounts sub-app to main app
    # - Adds exception handling
    # - Injects service provider to all apps
    app = builder.build_app_with_lifespan(
        title="Lab Resource Manager",
        description="Lab instance and worker resource management system with OAuth2 auth",
        version="1.0.0",
        debug=app_settings.debug,
    )
    app.add_middleware(CloudEventMiddleware, service_provider=app.state.services)

    log.info("Lab Resource Manager is ready!")
    return app


def main():
    """Main entry point when running as a script."""
    import uvicorn

    # Parse command line arguments
    port = 8000
    host = "0.0.0.0"

    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv[1:], 1):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
            elif arg == "--host" and i + 1 < len(sys.argv):
                host = sys.argv[i + 1]

    print(f"🧪 Starting Lab Resource Manager on http://{host}:{port}")
    print(f"📖 API Documentation available at http://{host}:{port}/api/docs")
    print(f"🗄️  etcd v3 for resource persistence ({app_settings.etcd_host}:{app_settings.etcd_port})")
    print("🔍 OpenTelemetry tracing enabled")
    print("👁️  Native watchable API for real-time resource updates")

    # Run with module:app string so uvicorn can properly detect lifespan
    uvicorn.run("main:app", host=host, port=port, reload=True, log_level="info")


# Create app instance for uvicorn direct usage
app = create_lab_resource_manager_app()

if __name__ == "__main__":
    main()
