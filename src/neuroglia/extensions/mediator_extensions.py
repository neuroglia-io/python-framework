"""
Extensions for registering Mediator services with automatic handler discovery.

This module provides convenient extension methods for configuring the mediator
with automatic handler discovery and proper dependency injection.
"""

from neuroglia.dependency_injection import ServiceCollection
from neuroglia.mediation.mediator import Mediator


def add_mediator(services: ServiceCollection) -> ServiceCollection:
    """
    Registers the Mediator service with proper dependency injection support.

    NOTE: This is a low-level extension method. For most use cases, prefer using
    `Mediator.configure(builder, packages)` which combines service registration
    with automatic handler discovery.

    This method configures the dependency injection container with the Mediator
    service, enabling CQRS pattern support.

    Services Registered:
        - Mediator -> Mediator (Singleton): Central request dispatcher

    Args:
        services: The service collection to configure

    Returns:
        The configured service collection for fluent chaining

    Recommended Usage (Mediator.configure):
        ```python
        from neuroglia.hosting.web import WebApplicationBuilder
        from neuroglia.mediation import Mediator

        builder = WebApplicationBuilder()

        # Preferred: One-line configuration with automatic handler discovery
        Mediator.configure(builder, [
            "application.commands",
            "application.queries"
        ])

        app = builder.build()
        app.run()
        ```

    Legacy Usage (Direct Service Registration):
        ```python
        # Still supported, but requires manual handler registration
        services = ServiceCollection()
        services.add_mediator()

        # Must manually register handlers
        services.add_scoped(CreateUserHandler)
        services.add_scoped(GetUserHandler)

        provider = services.build()
        ```

    See Also:
        - Mediator.configure(): Recommended high-level API
        - CQRS Pattern: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Mediator Pattern: https://bvandewe.github.io/pyneuro/patterns/cqrs/
    """
    services.add_singleton(Mediator, Mediator)
    return services


# Extend ServiceCollection with extension method using setattr to avoid linting issues
setattr(ServiceCollection, "add_mediator", add_mediator)
