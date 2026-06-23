"""Simple UI application entry point."""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI

# Add parent directories to Python path for framework imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging using framework's standard configuration
from application.settings import configure_logging
from domain.repositories.task_repository import TaskRepository
from integration.repositories.in_memory_task_repository import InMemoryTaskRepository

from neuroglia.eventing.cloud_events.infrastructure import CloudEventPublisher
from neuroglia.hosting.web import SubAppConfig, WebApplicationBuilder
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.serialization.json import JsonSerializer

# Note: Observability not used in this simple sample
# from neuroglia.observability import Observability


configure_logging(log_level="INFO")
log = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create Simple UI application with multi-app architecture.

    Creates separate apps for:
    - API backend (/api prefix) - REST API for task management
    - UI frontend (/ prefix) - Web interface

    Returns:
        Configured FastAPI application with multiple mounted apps
    """

    log.info("🚀 Creating Simple UI application...")

    # Create application builder
    builder = WebApplicationBuilder()

    # Configure services
    services = builder.services

    # Register repositories
    services.add_singleton(TaskRepository, InMemoryTaskRepository)

    # Configure Core services using native .configure() methods
    # This enables automatic discovery and registration of handlers, mappers, etc.
    Mediator.configure(builder, ["application.commands", "application.queries"])
    Mapper.configure(builder, ["application.commands", "domain.entities"])
    JsonSerializer.configure(builder, ["domain.entities"])

    # Optional: Configure CloudEvent emission and consumption
    CloudEventPublisher.configure(builder)
    # CloudEventIngestor.configure(builder)  # No integration events for this simple sample

    # Optional: Configure Observability (OpenTelemetry)
    # Note: Commented out because this sample doesn't have observability settings configured
    # Observability.configure(builder)

    # Configure sub-applications declaratively
    # API sub-app: REST API with JWT authentication
    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            title="Simple UI API",
            description="Task management REST API with JWT authentication",
            version="1.0.0",
            controllers=["api.controllers"],
            docs_url="/docs",
        )
    )

    # UI sub-app: Web interface (JWT-only auth, no session middleware needed)
    # Get absolute path to static directory
    static_dir = Path(__file__).parent / "static"
    templates_dir = Path(__file__).parent / "ui" / "templates"

    builder.add_sub_app(
        SubAppConfig(
            path="/",
            name="ui",
            title="Simple UI",
            description="Task management web interface",
            version="1.0.0",
            controllers=["ui.controllers"],
            static_files={"/static": str(static_dir)},
            templates_dir=str(templates_dir),
            docs_url=None,  # Disable docs for UI
            # Removed SessionMiddleware - using JWT-only authentication
        )
    )

    # Build the complete application with all sub-apps mounted and configured
    app = builder.build_app_with_lifespan(
        title="Simple UI",
        description="Task management application with multi-app architecture",
        version="1.0.0",
        debug=True,
    )

    log.info("✅ Application created successfully!")
    log.info("📊 Access points:")
    log.info("   - UI: http://localhost:8082/")
    log.info("   - API Docs: http://localhost:8082/api/docs")
    log.info("   - Auth: POST /api/auth/login")
    log.info("   - Tasks: GET /api/tasks/")
    log.info("   - Tasks: POST /api/tasks/")

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()

    log.info("🌐 Starting server on http://localhost:8000")
    log.info("👤 Demo users:")
    log.info("   - admin / admin123 (can see all tasks, can create)")
    log.info("   - manager / manager123 (can see non-admin tasks)")
    log.info("   - john.doe / user123 (can see own tasks)")
    log.info("   - jane.smith / user123 (can see own tasks)")

    uvicorn.run(app, host="0.0.0.0", port=8000)
