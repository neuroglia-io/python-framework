#!/usr/bin/env python3
"""
Mario's Pizzeria - Main Application Entry Point

This is the complete sample application demonstrating all major Neuroglia framework features.

"""

import logging
import sys
from pathlib import Path
from typing import Optional

from starlette.middleware.sessions import SessionMiddleware

# Add the project root to Python path so we can import neuroglia
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Framework imports (must be after path manipulation)
from api.services.auth import DualAuthService
from api.services.openapi import set_oas_description
from application.services import AuthService, configure_logging
from application.settings import app_settings
from domain.entities import Customer, Kitchen, Order, Pizza
from domain.repositories import (
    ICustomerRepository,
    IKitchenRepository,
    IOrderRepository,
    IPizzaRepository,
)
from integration.repositories import (
    MongoCustomerRepository,
    MongoKitchenRepository,
    MongoOrderRepository,
    MongoPizzaRepository,
)

from neuroglia.data.infrastructure.mongo import MotorRepository
from neuroglia.eventing.cloud_events.infrastructure import (
    CloudEventIngestor,
    CloudEventMiddleware,
    CloudEventPublisher,
)
from neuroglia.hosting.web import SubAppConfig, WebApplicationBuilder
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.observability import Observability
from neuroglia.serialization.json import JsonSerializer

configure_logging(log_level=app_settings.log_level.upper())
log = logging.getLogger(__name__)
log.info("🍕 Mario's Pizzeria starting up...")


def create_pizzeria_app(data_dir: Optional[str] = None, port: int = 8080):
    """
    Create Mario's Pizzeria application with multi-app architecture.

    Creates separate apps for:
    - API backend (/api prefix)
    - UI frontend with Keycloak auth (/ prefix)

    Args:
        data_dir: Directory for data storage (defaults to ./data)
        port: Port to run the application on

    Returns:
        Configured FastAPI application with multiple mounted apps
    """

    # Create web application builder with app_settings (enables advanced features)
    builder = WebApplicationBuilder(app_settings)

    # Configure Core services
    Mediator.configure(builder, ["application.commands", "application.queries", "application.events"])
    Mapper.configure(builder, ["application.mapping", "api.dtos", "domain.entities"])
    JsonSerializer.configure(builder, ["domain.entities.enums", "domain.entities"])

    # Optional: configure CloudEvent emission and consumption
    CloudEventPublisher.configure(builder)
    CloudEventIngestor.configure(builder, ["application.events.integration"])

    # Optional: configure Observability
    Observability.configure(builder)

    # Configure authentication with session store (Redis or in-memory fallback)
    DualAuthService.configure(builder)

    # Optional: configure persistence settings
    MotorRepository.configure(
        builder,
        entity_type=Customer,
        key_type=str,
        database_name="mario_pizzeria",
        collection_name="customers",
        domain_repository_type=ICustomerRepository,
        implementation_type=MongoCustomerRepository,
    )
    MotorRepository.configure(
        builder,
        entity_type=Order,
        key_type=str,
        database_name="mario_pizzeria",
        collection_name="orders",
        domain_repository_type=IOrderRepository,
        implementation_type=MongoOrderRepository,
    )
    MotorRepository.configure(
        builder,
        entity_type=Pizza,
        key_type=str,
        database_name="mario_pizzeria",
        collection_name="pizzas",
        domain_repository_type=IPizzaRepository,
        implementation_type=MongoPizzaRepository,
    )
    MotorRepository.configure(
        builder,
        entity_type=Kitchen,
        key_type=str,
        database_name="mario_pizzeria",
        collection_name="kitchen",
        domain_repository_type=IKitchenRepository,
        implementation_type=MongoKitchenRepository,
    )

    # Register application services
    builder.services.add_scoped(AuthService)

    # Configure sub-applications declaratively
    # API sub-app: REST API with OAuth2/JWT authentication
    builder.add_sub_app(
        SubAppConfig(
            path="/api",
            name="api",
            title="Mario's Pizzeria API",
            description="Pizza ordering and management API with OAuth2/JWT authentication",
            version="1.0.0",
            controllers=["api.controllers"],
            custom_setup=lambda app, settings: set_oas_description(app, settings),
            docs_url="/docs",
        )
    )

    # UI sub-app: Web interface with Keycloak SSO
    builder.add_sub_app(
        SubAppConfig(
            path="/",
            name="ui",
            title="Mario's Pizzeria UI",
            description="Pizza ordering web interface with Keycloak SSO",
            version="1.0.0",
            controllers=["ui.controllers"],
            middleware=[(SessionMiddleware, {"secret_key": app_settings.session_secret_key, "session_cookie": "mario_session", "max_age": 3600, "same_site": "lax", "https_only": not app_settings.local_dev})],
            static_files={"/static": "static"},
            templates_dir="ui/templates",
            docs_url="/docs",
        )
    )  # Disable docs for UI

    # Build the complete application with all sub-apps mounted and configured
    # This automatically:
    # - Creates the main FastAPI app with Host lifespan
    # - Creates and configures both sub-apps
    # - Mounts sub-apps to main app
    # - Adds exception handling
    # - Injects service provider to all apps
    app = builder.build_app_with_lifespan(title="Mario's Pizzeria", description="Complete pizza ordering and management system with Keycloak auth", version="1.0.0", debug=True)

    # Configure middleware
    DualAuthService.configure_middleware(app)  # Inject DualAuthService into request state
    app.add_middleware(CloudEventMiddleware, service_provider=app.state.services)

    log.info("App is ready to rock.")
    return app


def main():
    """Main entry point when running as a script"""
    import uvicorn

    # Parse command line arguments
    port = 8080
    host = "0.0.0.0"

    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv[1:], 1):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
            elif arg == "--host" and i + 1 < len(sys.argv):
                host = sys.argv[i + 1]

    # Don't call create_pizzeria_app() here - it would build twice
    # Instead, let uvicorn import and call it via the module:app pattern

    print(f"🍕 Starting Mario's Pizzeria on http://{host}:{port}")
    print(f"📖 API Documentation available at http://{host}:{port}/api/docs")
    print(f"🌐 UI available at http://{host}:{port}/")
    print(f"🔐 Keycloak SSO Login at http://{host}:{port}/auth/login")
    print("💾 MongoDB (Motor async) for all data: customers, orders, pizzas, kitchen")

    # Run with module:app string so uvicorn can properly detect lifespan
    # The --reload flag in uvicorn will work correctly this way
    uvicorn.run("main:app", host=host, port=port, reload=True, log_level="info")  # Module path to app instance


# Create app instance for uvicorn direct usage
# This is called when uvicorn imports this module
app = create_pizzeria_app()

if __name__ == "__main__":
    main()
