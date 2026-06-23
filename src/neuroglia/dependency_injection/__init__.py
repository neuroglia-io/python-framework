"""
Dependency injection abstractions and container implementation for the Neuroglia framework.

This module provides a comprehensive dependency injection system with support for multiple
service lifetimes, automatic dependency resolution, service scoping, and fluent configuration.
It enables loose coupling, testability, and modular architecture patterns.

Key Components:
    - ServiceCollection: Fluent service registration builder
    - ServiceProvider: Main dependency injection container
    - ServiceScope: Request/operation-scoped service management
    - ServiceDescriptor: Service registration metadata
    - ServiceLifetime: Service instance lifecycle management

Examples:
    ```python
    from neuroglia.dependency_injection import ServiceCollection, ServiceLifetime

    # Configure services
    services = ServiceCollection()
    services.add_singleton(AppConfiguration) \\
            .add_scoped(IUserRepository, SqlUserRepository) \\
            .add_transient(EmailService)

    # Build and use container
    provider = services.build_provider()

    # Resolve services
    config = provider.get_required_service(AppConfiguration)
    email_service = provider.get_service(EmailService)

    # Create scoped context
    with provider.create_scope() as scope:
        user_repo = scope.get_service(IUserRepository)
        # Scoped services are automatically disposed
    ```

See Also:
    - Dependency Injection Guide: https://bvandewe.github.io/pyneuro/patterns/dependency-injection/
    - Configurable Type Discovery: https://bvandewe.github.io/pyneuro/features/configurable-type-discovery/
    - Getting Started: https://bvandewe.github.io/pyneuro/getting-started/
"""

from .service_provider import *

__all__ = [
    "ServiceCollection",
    "ServiceProvider",
    "ServiceProviderBase",
    "ServiceScope",
    "ServiceScopeBase",
    "ServiceDescriptor",
    "ServiceLifetime",
]
