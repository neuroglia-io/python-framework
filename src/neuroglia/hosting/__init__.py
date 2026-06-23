"""
Comprehensive hosting infrastructure for building and managing Neuroglia applications.

This module provides enterprise-grade application hosting capabilities including web
application builders, hosted services, application lifecycle management, configuration
management, and multi-application support with advanced controller and middleware
management for production-ready microservices.

Key Components:
    - WebApplicationBuilder: Unified builder supporting both simple and advanced scenarios
    - ApplicationBuilderBase: Base abstraction for custom application builders
    - HostedService: Background services and application lifecycle management
    - ExceptionHandlingMiddleware: Global error handling and response formatting
    - EnhancedWebHost: Advanced host with multi-app support and lifecycle management

Architecture:
    The hosting system has been unified around WebApplicationBuilder, which automatically
    detects and enables advanced features based on configuration:

    - Simple Mode: WebApplicationBuilder() - Basic FastAPI hosting
    - Advanced Mode: WebApplicationBuilder(app_settings) - Multi-app, observability, etc.

Features:
    - Dependency injection container integration
    - Configuration management with environment support
    - Middleware pipeline configuration
    - Controller auto-discovery and registration
    - Background service lifecycle management
    - Multi-application hosting on single process
    - Health checks and monitoring endpoints
    - Graceful shutdown and startup handling
    - OpenTelemetry observability integration
    - Controller deduplication across apps

Examples:
    ```python
    from neuroglia.hosting import WebApplicationBuilder, HostedService
    from neuroglia.hosting.abstractions import ApplicationSettings

    # Simple Mode - Basic web application
    builder = WebApplicationBuilder()
    builder.services.add_scoped(UserService)
    builder.services.add_controllers(['api.controllers'])

    app = builder.build()
    app.run(host="0.0.0.0", port=8000)

    # Advanced Mode - Multi-app with observability
    app_settings = ApplicationSettings()
    builder = WebApplicationBuilder(app_settings)

    # Configure services
    builder.services.add_scoped(UserService)
    builder.services.add_singleton(DatabaseConnection)

    # Add controllers to specific apps
    builder.add_controllers(['api.controllers'], prefix="/api")
    builder.add_controllers(['admin.controllers'], prefix="/admin")

    # Add hosted services
    builder.services.add_hosted_service(BackgroundTaskService)

    # Build with integrated lifecycle management
    app = builder.build_app_with_lifespan(
        title="My Microservice",
        version="1.0.0"
    )

    # Controllers are automatically mounted
    app.run(host="0.0.0.0", port=8000)
    ```

Migration from EnhancedWebApplicationBuilder:
    ```python
    # Old (deprecated but still works via alias)
    from neuroglia.hosting import EnhancedWebApplicationBuilder
    builder = EnhancedWebApplicationBuilder(app_settings)

    # New (recommended)
    from neuroglia.hosting import WebApplicationBuilder
    builder = WebApplicationBuilder(app_settings)
    ```

See Also:
    - Application Hosting Guide: https://bvandewe.github.io/pyneuro/features/
    - Configuration Management: https://bvandewe.github.io/pyneuro/guides/
    - Getting Started: https://bvandewe.github.io/pyneuro/getting-started/
"""

from .abstractions import ApplicationBuilderBase, HostedService
from .web import (
    EnhancedWebHost,
    ExceptionHandlingMiddleware,
    SubAppConfig,
    WebApplicationBuilder,
)

# Backward compatibility alias (deprecated)
EnhancedWebApplicationBuilder = WebApplicationBuilder

__all__ = [
    "WebApplicationBuilder",
    "ApplicationBuilderBase",
    "HostedService",
    "EnhancedWebApplicationBuilder",  # Deprecated alias
    "ExceptionHandlingMiddleware",
    "EnhancedWebHost",
    "SubAppConfig",  # Sub-application configuration
]
