from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import Any, List, Optional, Type, get_args, get_origin, get_type_hints

from neuroglia.core.type_extensions import TypeExtensions


class ServiceLifetime(Enum):
    """
    Defines the abstraction for service instance lifecycle management in the dependency injection container.

    This enumeration controls how and when service instances are created, cached, and disposed of
    throughout the application lifecycle, enabling proper resource management and performance optimization.

    Lifetime Patterns:
        - TRANSIENT: New instance every time (stateless services)
        - SCOPED: One instance per scope/request (request-specific state)
        - SINGLETON: One instance for entire application (shared state)

    Examples:
        ```python
        # Transient: New instance each time (e.g., calculators, validators)
        services.add_transient(EmailValidator)
        services.add_transient(PriceCalculator)

        # Scoped: One per HTTP request (e.g., repositories, unit of work)
        services.add_scoped(UserRepository)
        services.add_scoped(OrderRepository)

        # Singleton: One for entire app (e.g., configuration, cache)
        services.add_singleton(AppConfiguration)
        services.add_singleton(MemoryCache)
        ```

    See Also:
        - Dependency Injection Guide: https://bvandewe.github.io/pyneuro/patterns/dependency-injection/
        - Service Registration: https://bvandewe.github.io/pyneuro/features/
    """

    TRANSIENT = "transient"
    """Transient services are created each time they are requested - ideal for lightweight, stateless services."""

    SCOPED = "scoped"
    """Scoped services are created once per scope (e.g., HTTP request) - perfect for request-specific state."""

    SINGLETON = "singleton"
    """Singleton services are created once and reused for the entire application lifetime - best for shared state."""


# Forward references - these will be defined later in this file


class ServiceProviderBase(ABC):
    """
    Represents the abstraction for dependency injection containers that manage and provide service instances.

    This abstraction defines the core contract for dependency injection systems, enabling loose coupling,
    testability, and modular architecture by managing object creation and dependency resolution throughout
    the application lifecycle.

    Key Responsibilities:
        - Service instance creation and management
        - Dependency graph resolution and injection
        - Lifetime management (singleton, scoped, transient)
        - Service scope creation and disposal
        - Circular dependency detection and handling

    Examples:
        ```python
        # Service resolution
        provider = services.build_provider()

        # Get optional service
        email_service = provider.get_service(EmailService)
        if email_service:
            await email_service.send_email("test@example.com", "Hello")

        # Get required service (throws if not found)
        user_repository = provider.get_required_service(UserRepository)
        users = await user_repository.get_all_async()

        # Get all implementations of an interface
        validators = provider.get_services(IValidator)
        for validator in validators:
            validator.validate(data)

        # Create scoped context
        with provider.create_scope() as scope:
            scoped_service = scope.get_service(RequestScopedService)
            # Scoped services disposed automatically
        ```

    Architecture:
        ```
        Application -> ServiceProvider -> ServiceDescriptor -> Service Instance
                   ^                  ^                     ^
                   |                  |                     |
              Resolution           Configuration        Implementation
        ```

    See Also:
        - Dependency Injection Guide: https://bvandewe.github.io/pyneuro/patterns/dependency-injection/
        - Service Registration: https://bvandewe.github.io/pyneuro/features/configurable-type-discovery/
        - Getting Started: https://bvandewe.github.io/pyneuro/getting-started/
    """

    def get_service(self, type: type) -> Optional[any]:
        """Gets the service with the specified type, if any has been registered"""
        raise NotImplementedError()

    def get_required_service(self, type: type) -> any:
        """Gets the required service with the specified type"""
        raise NotImplementedError()

    def get_services(self, type: type) -> list:
        """Gets all services of the specified type"""
        raise NotImplementedError()

    def create_scope(self) -> "ServiceScopeBase":
        """Creates a new service scope"""
        raise NotImplementedError()

    def create_async_scope(self):
        """
        Creates an asynchronous service scope for resolving scoped services.

        This method provides an async context manager that creates a service scope,
        allowing scoped services to be properly resolved and automatically disposed
        when the scope exits. This is essential for event-driven architectures where
        handlers need access to scoped dependencies like repositories.

        Returns:
            An async context manager that yields a ServiceScope

        Examples:
            ```python
            # Event processing with scoped services
            async with service_provider.create_async_scope() as scope:
                handler = scope.get_service(EventHandler)
                await handler.handle_async(event)
            # Scope automatically disposed here

            # Multiple services in same scope
            async with service_provider.create_async_scope() as scope:
                repository = scope.get_service(Repository)
                unit_of_work = scope.get_service(UnitOfWork)
                await process_with_shared_context(repository, unit_of_work)
            ```

        See Also:
            - Scoped Service Resolution: https://bvandewe.github.io/pyneuro/patterns/dependency-injection
            - Event-Driven Architecture: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        """
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _scope_context():
            scope = self.create_scope()
            try:
                yield scope
            finally:
                # Dispose scope asynchronously if supported, otherwise synchronous
                if hasattr(scope, "dispose_async"):
                    await scope.dispose_async()
                elif hasattr(scope, "dispose"):
                    scope.dispose()

        # Return the context manager itself (already callable)
        return _scope_context()


class ServiceScopeBase(ABC):
    """
    Represents the abstraction for service scopes that provide controlled dependency lifetimes and isolation.

    Service scopes create isolated contexts where scoped services are instantiated once per scope
    and automatically disposed when the scope ends. This is crucial for managing per-request state,
    database connections, and other resources that need controlled lifecycles.

    Key Features:
        - Isolated service instances per scope
        - Automatic resource cleanup on disposal
        - Prevents service leakage between requests
        - Enables proper unit of work patterns
        - Supports nested scopes for complex scenarios

    Examples:
        ```python
        # HTTP request scope pattern
        @app.middleware("http")
        async def scoped_middleware(request: Request, call_next):
            with service_provider.create_scope() as scope:
                # Scoped services are unique to this request
                request.state.scope = scope

                # All scoped services share the same instances within this request
                user_repository = scope.get_service(UserRepository)
                order_repository = scope.get_service(OrderRepository)

                response = await call_next(request)
                # Automatic cleanup happens here
                return response

        # Unit of work pattern
        async def process_order(order_data: dict):
            with service_provider.create_scope() as scope:
                unit_of_work = scope.get_service(UnitOfWork)
                order_service = scope.get_service(OrderService)

                try:
                    order = await order_service.create_order(order_data)
                    await unit_of_work.commit_async()
                    return order
                except Exception:
                    await unit_of_work.rollback_async()
                    raise
                # Automatic resource disposal

        # Testing with isolated scopes
        def test_user_service():
            with test_provider.create_scope() as scope:
                user_service = scope.get_service(UserService)
                # Each test gets fresh scoped services
                assert user_service.user_count == 0
        ```

    See Also:
        - Service Scopes Guide: https://bvandewe.github.io/pyneuro/patterns/dependency-injection
        - Request Lifecycle Management: https://bvandewe.github.io/pyneuro/features/
    """

    @abstractmethod
    def get_service_provider(self) -> ServiceProviderBase:
        """Gets the scoped service provider"""
        raise NotImplementedError()

    @abstractmethod
    def dispose(self):
        """Disposes of the service scope"""
        raise NotImplementedError()


class ServiceScope(ServiceScopeBase, ServiceProviderBase):
    """Represents the default implementation of the IServiceScope class"""

    def __init__(
        self,
        root_service_provider: ServiceProviderBase,
        scoped_service_descriptors: list[ServiceDescriptor],
        all_service_descriptors: list[ServiceDescriptor],
    ):
        self._root_service_provider = root_service_provider
        self._scoped_service_descriptors = scoped_service_descriptors
        self._all_service_descriptors = all_service_descriptors
        self._realized_scoped_services = dict[Type, List]()  # Instance-level cache

    _root_service_provider: ServiceProviderBase
    """ Gets the IServiceProvider that has created the service scope """

    _scoped_service_descriptors: list[ServiceDescriptor]
    """ Gets a list containing the configurations of all scoped dependencies """

    def get_service_provider(self) -> ServiceProviderBase:
        return self

    def get_service(self, type: type) -> Optional[any]:
        if type == ServiceProviderBase:
            return self

        # First check if we have a scoped service descriptor
        scoped_descriptor = next(
            (descriptor for descriptor in self._scoped_service_descriptors if descriptor.service_type == type),
            None,
        )
        if scoped_descriptor is not None:
            # Check if we already have a cached scoped instance
            realized_services = self._realized_scoped_services.get(type)
            if realized_services is not None and len(realized_services) > 0:
                return realized_services[0]
            else:
                # Build new scoped service
                return self._build_service(scoped_descriptor)

        # For non-scoped services, we need to check if it's a transient that might have scoped dependencies
        # Try to find the descriptor in the root provider and handle it accordingly
        root_descriptor = next(
            (descriptor for descriptor in self._all_service_descriptors if descriptor.service_type == type),
            None,
        )
        if root_descriptor is not None:
            # If it's a transient service, build it in the scope context so dependencies resolve correctly
            if root_descriptor.lifetime == ServiceLifetime.TRANSIENT:
                return self._build_service(root_descriptor)
            # For singleton services, delegate to root provider
            elif root_descriptor.lifetime == ServiceLifetime.SINGLETON:
                return self._root_service_provider.get_service(type)
            # Scoped services should have been handled above, but just in case
            elif root_descriptor.lifetime == ServiceLifetime.SCOPED:
                return self._build_service(root_descriptor)

        # Fall back to root service provider for anything else
        return self._root_service_provider.get_service(type)

    def get_required_service(self, type: type) -> any:
        service = self.get_service(type)
        if service is None:
            raise Exception(f"Failed to resolve service of type '{type.__name__}'")
        return service

    def get_services(self, type: type) -> list:
        if type == ServiceProviderBase:
            return [self]
        service_descriptors = [descriptor for descriptor in self._scoped_service_descriptors if descriptor.service_type == type]
        realized_services = self._realized_scoped_services.get(type)
        if realized_services is None:
            realized_services = list()
        for descriptor in service_descriptors:
            # Avoid instantiation issues with abstract base classes
            # Check if service is already in realized_services by identity/type matching
            already_exists = False
            for service in realized_services:
                try:
                    if type(service) == descriptor.service_type:
                        already_exists = True
                        break
                    if isinstance(service, descriptor.service_type):
                        already_exists = True
                        break
                except (TypeError, AttributeError):
                    # Handle cases where type comparison fails (e.g., with ABCs)
                    continue

            if already_exists:
                continue

            realized_services.append(self._build_service(descriptor))

        # Get singleton services from root provider
        # IMPORTANT: Transient services must be built in THIS scope (not root)
        # to allow them to resolve scoped dependencies correctly
        root_singleton_descriptors = [descriptor for descriptor in self._all_service_descriptors if descriptor.service_type == type and descriptor.lifetime == ServiceLifetime.SINGLETON]

        # Build transient services in THIS scope so they can access scoped dependencies
        transient_descriptors = [descriptor for descriptor in self._all_service_descriptors if descriptor.service_type == type and descriptor.lifetime == ServiceLifetime.TRANSIENT]

        # Get realized singletons - build each descriptor separately to get distinct instances
        # This is critical when multiple services are registered with the same base type
        # (e.g., NotificationHandler) - we need ALL distinct instances, not just the first one
        root_services = []
        for descriptor in root_singleton_descriptors:
            try:
                # For singletons, use the singleton instance directly from the descriptor
                # or build it if needed. Do NOT use get_service(descriptor.service_type)
                # as that returns only the first registered service for that type
                if descriptor.singleton is not None:
                    root_services.append(descriptor.singleton)
                elif descriptor.implementation_factory is not None:
                    service = descriptor.implementation_factory(self._root_service_provider)
                    root_services.append(service)
                else:
                    # For non-singleton, non-factory services, we need to build them
                    # Cast to access _build_service (it exists but typing doesn't know)
                    service = self._root_service_provider._build_service(descriptor)  # type: ignore
                    root_services.append(service)
            except Exception:
                pass

        # Build transient services in this scope
        transient_services = []
        for descriptor in transient_descriptors:
            try:
                service = self._build_service(descriptor)
                transient_services.append(service)
            except Exception:
                # If building fails, skip this service
                pass

        return realized_services + root_services + transient_services

    def _build_service(self, service_descriptor: ServiceDescriptor) -> any:
        """Builds a new scoped service"""
        if service_descriptor.singleton is not None:
            service = service_descriptor.singleton
        elif service_descriptor.implementation_factory is not None:
            service = service_descriptor.implementation_factory(self)
        else:
            is_service_generic = not inspect.isclass(service_descriptor.implementation_type)
            service_generic_type = service_descriptor.implementation_type.__origin__ if is_service_generic else None
            service_type = service_descriptor.implementation_type if service_generic_type is None else service_generic_type

            # Resolve string annotations (forward references) to actual types
            try:
                type_hints = get_type_hints(service_type.__init__)
            except Exception:
                # If get_type_hints fails, fall back to inspecting annotations directly
                type_hints = {}

            service_init_args = [param for param in inspect.signature(service_type.__init__).parameters.values() if param.name not in ["self", "args", "kwargs"]]
            service_generic_args = TypeExtensions.get_generic_arguments(service_descriptor.implementation_type)
            service_args = dict[Type, any]()
            for init_arg in service_init_args:
                # Get the resolved type hint (handles string annotations)
                resolved_annotation = type_hints.get(init_arg.name, init_arg.annotation)

                # Use typing.get_origin() and get_args() for robust generic type handling
                origin = get_origin(resolved_annotation)
                args = get_args(resolved_annotation)

                # Determine the dependency type to resolve
                if origin is not None and args:
                    # It's a parameterized generic type (e.g., Repository[User, int])
                    # Check if it contains type variables that need substitution
                    # (e.g., CacheRepositoryOptions[TEntity, TKey] -> CacheRepositoryOptions[MozartSession, str])
                    dependency_type = TypeExtensions._substitute_generic_arguments(resolved_annotation, service_generic_args)
                else:
                    # Simple non-generic type (use resolved annotation, not raw annotation)
                    dependency_type = resolved_annotation

                dependency = self.get_service(dependency_type)
                if dependency is None and init_arg.default == init_arg.empty and init_arg.name != "self":
                    # Safe error message generation - handle all annotation types:
                    # 1. String annotations (forward references): "ClassName"
                    # 2. Types without __name__: typing constructs like Union, Optional
                    # 3. Regular types with __name__: normal classes
                    def _get_type_name(t) -> str:
                        if isinstance(t, str):
                            return t  # Already a string (forward reference)
                        return getattr(t, "__name__", str(t))

                    service_type_name = _get_type_name(service_descriptor.service_type)
                    dependency_type_name = _get_type_name(dependency_type)
                    raise Exception(f"Failed to build service of type '{service_type_name}' because the service provider failed to resolve service '{dependency_type_name}'")
                service_args[init_arg.name] = dependency
            service = service_descriptor.implementation_type(**service_args)

        # Cache the scoped service
        realized_services = self._realized_scoped_services.get(service_descriptor.service_type)
        if realized_services is None:
            self._realized_scoped_services[service_descriptor.service_type] = [service]
        else:
            realized_services.append(service)
        return service

    def dispose(self):
        for services in self._realized_scoped_services.values():
            for service in services:
                try:
                    if hasattr(service, "__exit__"):
                        service.__exit__(None, None, None)
                except:
                    pass
        self._realized_scoped_services = dict[Type, List]()

    async def dispose_async(self):
        """Asynchronously dispose of scoped services"""
        for services in self._realized_scoped_services.values():
            for service in services:
                try:
                    # Try async context manager exit first
                    if hasattr(service, "__aexit__"):
                        await service.__aexit__(None, None, None)
                    # Fall back to sync context manager exit
                    elif hasattr(service, "__exit__"):
                        service.__exit__(None, None, None)

                    # Also call dispose() method if it exists (for explicit resource cleanup)
                    if hasattr(service, "dispose"):
                        result = service.dispose()
                        # If dispose() returns a coroutine, await it
                        if hasattr(result, "__await__"):
                            await result
                except:
                    pass
        self._realized_scoped_services = dict[Type, List]()

    def create_scope(self) -> ServiceScopeBase:
        return self


class ServiceProvider(ServiceProviderBase):
    """Represents the default implementation of the IServiceProvider class"""

    def __init__(self, service_descriptors: list[ServiceDescriptor]):
        """Initializes a new service provider using the specified service dependency configuration"""
        self._service_descriptors = service_descriptors
        self._realized_services = dict[Type, List]()  # Instance-level cache

    _service_descriptors: list[ServiceDescriptor]
    """ Gets a list containing the configuration of all registered dependencies """

    def get_service(self, type: type) -> Optional[any]:
        if type == ServiceProviderBase:
            return self

        descriptor = next(
            (descriptor for descriptor in self._service_descriptors if descriptor.service_type == type),
            None,
        )
        if descriptor is None:
            return None

        # For transient services, always create new instances
        if descriptor.lifetime == ServiceLifetime.TRANSIENT:
            return self._build_service(descriptor)

        # For non-transient services, check cache first
        realized_services = self._realized_services.get(type)
        if realized_services is not None:
            return realized_services[0]

        return self._build_service(descriptor)

    def get_required_service(self, type: type) -> any:
        service = self.get_service(type)
        if service is None:
            raise Exception(f"Failed to resolve service of type '{type.__name__}'")
        return service

    def get_services(self, type: type) -> list:
        if type == ServiceProviderBase:
            return [self]
        service_descriptors = [descriptor for descriptor in self._service_descriptors if descriptor.service_type == type]
        realized_services = self._realized_services.get(type)
        if realized_services is None:
            realized_services = list()
        for descriptor in service_descriptors:
            implementation_type = descriptor.get_implementation_type()
            realized_service = next(
                (service for service in realized_services if self._is_service_instance_of(service, implementation_type)),
                None,
            )
            if realized_service is None:
                realized_services.append(self._build_service(descriptor))
        return realized_services

    def _get_non_scoped_services(self, type: type) -> list:
        """
        Gets all singleton and transient services of the specified type,
        excluding scoped services (which should only be resolved from a ServiceScope).

        This is used by ServiceScope.get_services() to avoid trying to resolve
        scoped services from the root provider.
        """
        if type == ServiceProviderBase:
            return [self]

        # Only include singleton and transient descriptors (skip scoped)
        service_descriptors = [descriptor for descriptor in self._service_descriptors if descriptor.service_type == type and descriptor.lifetime != ServiceLifetime.SCOPED]

        realized_services = self._realized_services.get(type)
        if realized_services is None:
            realized_services = list()

        # Build services for non-scoped descriptors
        result_services = []
        for descriptor in service_descriptors:
            implementation_type = descriptor.get_implementation_type()
            realized_service = next(
                (service for service in realized_services if self._is_service_instance_of(service, implementation_type)),
                None,
            )
            if realized_service is None:
                service = self._build_service(descriptor)
                result_services.append(service)
            else:
                result_services.append(realized_service)

        return result_services

    def _is_service_instance_of(self, service: Any, type_: type) -> bool:
        # Handle None or invalid types (e.g., inspect._empty from untyped factories)
        if type_ is None or not isinstance(type_, type) and not hasattr(type_, "__origin__"):
            # Cannot determine type - fall back to checking if service exists
            return service is not None
        if hasattr(type_, "__origin__"):
            service_type = service.__orig_class__ if hasattr(service, "__orig_class__") else type(service)
            service_generic_arguments = TypeExtensions.get_generic_arguments(service_type)
            implementation_generic_arguments = TypeExtensions.get_generic_arguments(type_)
            for i in range(len(implementation_generic_arguments)):
                generic_argument_name = list(implementation_generic_arguments.keys())[i]
                service_generic_argument = service_generic_arguments.get(generic_argument_name, None)
                if service_generic_argument is None or service_generic_argument != implementation_generic_arguments[generic_argument_name]:
                    return False
            return isinstance(service, type_.__origin__)
        else:
            return isinstance(service, type_)

    def _build_service(self, service_descriptor: ServiceDescriptor) -> any:
        """Builds a new service provider based on the configured dependencies"""
        if service_descriptor.lifetime == ServiceLifetime.SCOPED:
            raise Exception(f"Failed to resolve scoped service of type '{service_descriptor.implementation_type}' from root service provider")
        if service_descriptor.singleton is not None:
            service = service_descriptor.singleton
        elif service_descriptor.implementation_factory is not None:
            service = service_descriptor.implementation_factory(self)
        else:
            # Check if implementation_type is a class or a generic type
            # Added defensive check: ensure __origin__ exists before accessing it
            is_service_generic = not inspect.isclass(service_descriptor.implementation_type) and hasattr(service_descriptor.implementation_type, "__origin__")
            service_generic_type = service_descriptor.implementation_type.__origin__ if is_service_generic else None  # retrieve the generic type, used to determine the __init__ args
            service_type = service_descriptor.implementation_type if service_generic_type is None else service_generic_type  # get the type used to determine the __init__ args: the implementation type as is or its generic type definition

            # Resolve string annotations (forward references) to actual types
            try:
                type_hints = get_type_hints(service_type.__init__)
            except Exception:
                # If get_type_hints fails, fall back to inspecting annotations directly
                type_hints = {}

            service_init_args = [param for param in inspect.signature(service_type.__init__).parameters.values() if param.name not in ["self", "args", "kwargs"]]  # gets the __init__ args and leave out self, args and kwargs
            service_generic_args = TypeExtensions.get_generic_arguments(service_descriptor.implementation_type)  # gets the generic args: we will need them to substitute the type args of potential generic dependencies
            service_args = dict[Type, any]()
            for init_arg in service_init_args:
                # Get the resolved type hint (handles string annotations)
                resolved_annotation = type_hints.get(init_arg.name, init_arg.annotation)

                # Use typing.get_origin() and get_args() for robust generic type handling
                origin = get_origin(resolved_annotation)
                args = get_args(resolved_annotation)

                # Determine the dependency type to resolve
                if origin is not None and args:
                    # It's a parameterized generic type (e.g., Repository[User, int])
                    # Check if it contains type variables that need substitution
                    # (e.g., CacheRepositoryOptions[TEntity, TKey] -> CacheRepositoryOptions[MozartSession, str])
                    dependency_type = TypeExtensions._substitute_generic_arguments(resolved_annotation, service_generic_args)
                else:
                    # Simple non-generic type (use resolved annotation, not raw annotation)
                    dependency_type = resolved_annotation

                dependency = self.get_service(dependency_type)
                if dependency is None and init_arg.default == init_arg.empty and init_arg.name != "self":
                    # Safe error message generation - handle all annotation types:
                    # 1. String annotations (forward references): "ClassName"
                    # 2. Types without __name__: typing constructs like Union, Optional
                    # 3. Regular types with __name__: normal classes
                    def _get_type_name(t) -> str:
                        if isinstance(t, str):
                            return t  # Already a string (forward reference)
                        return getattr(t, "__name__", str(t))

                    service_type_name = _get_type_name(service_descriptor.service_type)
                    dependency_type_name = _get_type_name(dependency_type)
                    raise Exception(f"Failed to build service of type '{service_type_name}' because the service provider failed to resolve service '{dependency_type_name}'")
                service_args[init_arg.name] = dependency
            service = service_descriptor.implementation_type(**service_args)
        if service_descriptor.lifetime != ServiceLifetime.TRANSIENT:
            realized_services = self._realized_services.get(service_descriptor.service_type)
            if realized_services is None:
                self._realized_services[service_descriptor.service_type] = [service]
            else:
                realized_services.append(service)
        return service

    def create_scope(self) -> ServiceScopeBase:
        return ServiceScope(
            self,
            [descriptor for descriptor in self._service_descriptors if descriptor.lifetime == ServiceLifetime.SCOPED],
            self._service_descriptors,
        )

    def dispose(self):
        for service in self._realized_services:
            try:
                service.__exit__()
            except:
                pass
        self._realized_services = dict[Type, List]()


class ServiceDescriptor:
    """
    Represents the configuration metadata for service registration in the dependency injection container.

    Service descriptors encapsulate all information needed to create and manage service instances,
    including the service type, implementation strategy, lifetime management, and creation logic.

    Configuration Options:
        - Service Type: The interface or abstract class being registered
        - Implementation Type: The concrete class to instantiate
        - Singleton: Pre-created instance to reuse
        - Implementation Factory: Custom creation logic
        - Lifetime: How instances are managed (singleton, scoped, transient)

    Examples:
        ```python
        # Interface to implementation mapping
        descriptor = ServiceDescriptor(
            service_type=IUserRepository,
            implementation_type=SqlUserRepository,
            lifetime=ServiceLifetime.SCOPED
        )

        # Singleton instance
        config = AppConfiguration()
        descriptor = ServiceDescriptor(
            service_type=AppConfiguration,
            singleton=config,
            lifetime=ServiceLifetime.SINGLETON
        )

        # Factory-based creation
        def create_email_service(provider: ServiceProvider) -> EmailService:
            config = provider.get_service(EmailConfiguration)
            return SmtpEmailService(config.smtp_server, config.port)

        descriptor = ServiceDescriptor(
            service_type=EmailService,
            implementation_factory=create_email_service,
            lifetime=ServiceLifetime.TRANSIENT
        )
        ```

    See Also:
        - Service Registration: https://bvandewe.github.io/pyneuro/features/
        - Dependency Injection Guide: https://bvandewe.github.io/pyneuro/patterns/
    """

    def __init__(
        self,
        service_type: type,
        implementation_type: Optional[type] = None,
        singleton: any = None,
        implementation_factory: Callable[[ServiceProvider], any] = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
    ):
        """Initializes a new service descriptor"""
        if singleton is not None and lifetime != ServiceLifetime.SINGLETON:
            raise Exception("A singleton service dependency must have lifetime set to 'SINGLETON'")
        self.service_type = service_type
        self.implementation_type = implementation_type
        self.singleton = singleton
        self.implementation_factory = implementation_factory
        self.lifetime = lifetime
        if self.singleton is None and self.implementation_factory is None and self.implementation_type is None:
            self.implementation_type = self.service_type

    service_type: type
    """ Gets the type of the service dependency """

    implementation_type: Optional[type]
    """ Gets the service dependency's implementation/concretion type, if any, to be instanciated on demand by a service provider. If set, 'singleton' and 'implementation-factory' are ignored. """

    singleton: any
    """ Gets the service instance singleton, if any. If set, 'implementation_type' and 'implementation-factory' are ignored. """

    implementation_factory: Callable[[ServiceProvider], any]
    """ Gets a function, if any, use to create a new instance of the service dependency. If set, 'implementation_type' and 'singleton' are ignored. """

    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    """ Gets the service's lifetime. Defaults to 'SINGLETON' """

    def get_implementation_type(self) -> type | None:
        """Gets the service's implementation type.

        Returns:
            The implementation type, or None if it cannot be determined
            (e.g., untyped lambda factories).
        """
        if self.implementation_type is not None:
            return self.implementation_type
        if self.singleton is not None:
            return type(self.singleton)
        if self.implementation_factory is not None:
            return_annotation = inspect.signature(self.implementation_factory).return_annotation
            # Handle missing annotations (inspect._empty) or string annotations
            if return_annotation is not inspect.Parameter.empty and isinstance(return_annotation, type):
                return return_annotation
            # For string annotations or forward references, return None
            # The caller should handle this gracefully
        return None


# ServiceCollection will be defined at the end of this file


class ServiceCollection(List[ServiceDescriptor]):
    """
    Represents a fluent configuration builder for dependency injection container services.

    The ServiceCollection provides a chainable API for registering services with different
    lifetimes and configuration options, making it easy to set up complex dependency graphs
    with minimal boilerplate code.

    Key Features:
        - Fluent registration API with method chaining
        - Support for all service lifetimes (singleton, scoped, transient)
        - Interface-to-implementation mappings
        - Factory-based service creation
        - Conditional registration with try_add methods
        - Automatic service provider building

    Examples:
        ```python
        # Basic service registration
        services = ServiceCollection()

        # Singleton services (shared across application)
        services.add_singleton(AppConfiguration) \\
                .add_singleton(ICache, MemoryCache) \\
                .add_singleton(ILogger, FileLogger)

        # Scoped services (one per request/scope)
        services.add_scoped(IUserRepository, SqlUserRepository) \\
                .add_scoped(IOrderRepository, SqlOrderRepository) \\
                .add_scoped(UnitOfWork)

        # Transient services (new instance each time)
        services.add_transient(IValidator, EmailValidator) \\
                .add_transient(IValidator, PasswordValidator) \\
                .add_transient(OrderService)

        # Factory-based registration
        services.add_singleton(
            IEmailService,
            implementation_factory=lambda p: SmtpEmailService(
                p.get_service(EmailConfiguration)
            )
        )

        # Conditional registration (only if not already registered)
        services.try_add_scoped(IUserRepository, InMemoryUserRepository)

        # Build the container
        provider = services.build_provider()
        ```

    Registration Patterns:
        ```python
        # Self-registration (concrete class as interface)
        services.add_scoped(UserService)

        # Interface mapping
        services.add_scoped(IUserService, UserService)

        # Multiple implementations
        services.add_transient(INotificationSender, EmailSender) \\
                .add_transient(INotificationSender, SmsSender)

        # Configuration-based factories
        services.add_singleton(
            DatabaseContext,
            implementation_factory=lambda p: DatabaseContext(
                p.get_service(DatabaseConfiguration).connection_string
            )
        )
        ```

    See Also:
        - Dependency Injection Guide: https://bvandewe.github.io/pyneuro/patterns/
        - Service Registration: https://bvandewe.github.io/pyneuro/features/
        - Getting Started: https://bvandewe.github.io/pyneuro/getting-started/
    """

    def add_singleton(
        self,
        service_type: type,
        implementation_type: Optional[type] = None,
        singleton: any = None,
        implementation_factory: Callable[[ServiceProvider], any] = None,
    ) -> ServiceCollection:
        """Registers a new singleton service dependency"""
        self.append(
            ServiceDescriptor(
                service_type,
                implementation_type,
                singleton,
                implementation_factory,
                ServiceLifetime.SINGLETON,
            )
        )
        return self

    def try_add_singleton(
        self,
        service_type: type,
        implementation_type: Optional[type] = None,
        singleton: any = None,
        implementation_factory: Callable[[ServiceProvider], any] = None,
    ) -> ServiceCollection:
        """Attempts to register a new singleton service dependency, if one has not already been registered"""
        if any(descriptor.service_type == service_type for descriptor in self):
            return self
        return self.add_singleton(service_type, implementation_type, singleton, implementation_factory)

    def add_transient(
        self,
        service_type: type,
        implementation_type: Optional[type] = None,
        implementation_factory: Callable[[ServiceProvider], any] = None,
    ) -> ServiceCollection:
        """Registers a new transient service dependency"""
        self.append(
            ServiceDescriptor(
                service_type,
                implementation_type,
                None,
                implementation_factory,
                ServiceLifetime.TRANSIENT,
            )
        )
        return self

    def try_add_transient(
        self,
        service_type: type,
        implementation_type: Optional[type] = None,
        implementation_factory: Callable[[ServiceProvider], any] = None,
    ) -> ServiceCollection:
        """Attempts to register a new transient service dependency, if one has not already been registered"""
        if any(descriptor.service_type == service_type for descriptor in self):
            return self
        return self.add_transient(service_type, implementation_type, implementation_factory)

    def add_scoped(
        self,
        service_type: type,
        implementation_type: Optional[type] = None,
        singleton: any = None,
        implementation_factory: Callable[[ServiceProvider], any] = None,
    ) -> ServiceCollection:
        """Registers a new scoped service dependency"""
        self.append(
            ServiceDescriptor(
                service_type,
                implementation_type,
                singleton,
                implementation_factory,
                ServiceLifetime.SCOPED,
            )
        )
        return self

    def try_add_scoped(
        self,
        service_type: type,
        implementation_type: Optional[type] = None,
        singleton: any = None,
        implementation_factory: Callable[[ServiceProvider], any] = None,
    ) -> ServiceCollection:
        """Attempts to register a new scoped service dependency, if one has not already been registered"""
        if any(descriptor.service_type == service_type for descriptor in self):
            return self
        return self.add_scoped(service_type, implementation_type, singleton, implementation_factory)

    def build(self) -> ServiceProviderBase:
        return ServiceProvider(self)
