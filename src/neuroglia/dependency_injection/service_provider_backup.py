from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum
import inspect
from typing import Any, Callable, List, Optional, Type, Dict, TypeVar

from ..core.type_extensions import TypeExtensions


class ServiceLifetime(Enum):
    '''Enumerates all supported service lifetimes.'''

    TRANSIENT = 'transient'
    '''Transient services are created each time they are requested.'''

    SCOPED = 'scoped'
    '''Scoped services are created once per request within a scope (e.g., a web request).'''

    SINGLETON = 'singleton'
    '''Singleton services are created only once and reused for the entire application lifetime.'''


class ServiceProviderBase(ABC):
    ''' Defines the fundamentals of a container used to manage and provide instances of dependencies, enabling dependency injection to promote modularity and maintainability. '''

    @abstractmethod
    def get_service(self, type: Type) -> Optional[Any]:
        ''' Gets the service with the specified type, if any has been registered '''
        pass

    @abstractmethod
    def get_required_service(self, type: Type) -> Any:
        ''' Gets the required service with the specified type '''
        pass

    @abstractmethod
    def get_services(self, type: Type) -> List[Any]:
        ''' Gets all services of the specified type '''
        pass

    @abstractmethod
    def create_scope(self) -> "ServiceScopeBase":
        ''' Creates a new service scope '''
        pass


class ServiceScopeBase(ABC):
    ''' Defines the fundamentals of a a limited context within which services are resolved and managed by a service provider, allowing for scoped instances and controlled lifetimes of dependencies. '''

    @abstractmethod
    def get_service_provider(self) -> ServiceProviderBase:
        ''' Gets the scoped service provider '''
        pass

    @abstractmethod
    def dispose(self):
        ''' Disposes of the service scope '''
        pass


class ServiceDescriptor:
    ''' Describes a service with the required information to create instances of it '''

    def __init__(self, service_type: Type, implementation_type: Optional[Type] = None, singleton: Any = None, implementation_factory: Optional[Callable[[ServiceProviderBase], Any]] = None, lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT):
        ''' Initializes a new ServiceDescriptor '''
        self.service_type = service_type
        self.implementation_type = implementation_type if implementation_type is not None else service_type
        self.singleton = singleton
        self.implementation_factory = implementation_factory
        self.lifetime = lifetime

    service_type: Type
    ''' Gets the type of the service '''

    implementation_type: Type
    ''' Gets the type of the service implementation '''

    singleton: Any
    ''' Gets the service singleton instance, if any '''

    implementation_factory: Optional[Callable[[ServiceProviderBase], Any]]
    ''' Gets the factory, if any, used to create the service instance '''

    lifetime: ServiceLifetime
    ''' Gets the service lifetime '''

    @property
    def is_key_service(self) -> bool:
        ''' Gets a boolean indicating whether or not the descriptor defines a key service '''
        return_type = inspect.signature(self.implementation_factory).return_annotation if self.implementation_factory is not None else None
        if return_type is None and self.implementation_factory is not None:
            return_type = type(self.implementation_factory(None))
        return return_type is not type(None) and return_type != self.service_type


class ServiceProvider(ServiceProviderBase):
    ''' Represents the default implementation of the IServiceProvider interface '''

    def __init__(self, service_descriptors: List[ServiceDescriptor]):
        self._service_descriptors = service_descriptors
        self._realized_singleton_services: Dict[Type, List[Any]] = {}

    _service_descriptors: List[ServiceDescriptor]
    ''' Gets a list of the service descriptors that define the services exposed by the service provider '''

    _realized_singleton_services: Dict[Type, List[Any]]
    ''' Gets a list of the cached service instances '''

    def get_service(self, type: Type) -> Optional[Any]:
        ''' Gets the service with the specified type, if any has been registered '''
        service_descriptor = next((descriptor for descriptor in self._service_descriptors if descriptor.service_type == type), None)
        if service_descriptor is None:
            return None
        
        realized_services = self._realized_singleton_services.get(service_descriptor.service_type)
        if service_descriptor.lifetime == ServiceLifetime.SINGLETON and realized_services is not None and len(realized_services) > 0:
            return realized_services[-1]
        else:
            return self._build_service(service_descriptor)

    def get_required_service(self, type: Type) -> Any:
        ''' Gets the required service with the specified type '''
        service = self.get_service(type)
        if service is None:
            raise Exception(f'Failed to retrieve required service of type {type}')
        return service

    def get_services(self, type: Type) -> List[Any]:
        ''' Gets all services of the specified type '''
        services = []
        service_descriptors = [descriptor for descriptor in self._service_descriptors if descriptor.service_type == type]
        for service_descriptor in service_descriptors:
            services.append(self._build_service(service_descriptor))
        return services

    def create_scope(self) -> ServiceScopeBase:
        ''' Creates a new service scope '''
        return ServiceScope(self, [descriptor for descriptor in self._service_descriptors if descriptor.lifetime == ServiceLifetime.SCOPED])

    def _build_service(self, service_descriptor: ServiceDescriptor) -> Any:
        ''' Builds a new service based on the service descriptor '''
        # Root ServiceProvider cannot build scoped services
        if service_descriptor.lifetime == ServiceLifetime.SCOPED:
            raise Exception(f"Failed to resolve scoped service of type '{service_descriptor.implementation_type}' from root service provider")
            
        if service_descriptor.singleton is not None:
            service = service_descriptor.singleton
        elif service_descriptor.implementation_factory is not None:
            service = service_descriptor.implementation_factory(self)
        else:
            init_args = [param for param in inspect.signature(service_descriptor.implementation_type.__init__).parameters.values() if param.name not in ['self', 'args', 'kwargs']]
            args: Dict[str, Any] = {}
            for init_arg in init_args:
                dependency = self.get_service(init_arg.annotation)
                if dependency is None and init_arg.default == init_arg.empty and init_arg.name != 'self':
                    raise Exception(f"Failed to build service of type '{service_descriptor.service_type.__name__}' because the service provider failed to resolve service '{init_arg.annotation}'")
                args[init_arg.name] = dependency
            service = service_descriptor.implementation_type(**args)
        
        # Cache singleton services
        if service_descriptor.lifetime == ServiceLifetime.SINGLETON:
            realized_services = self._realized_singleton_services.get(service_descriptor.service_type)
            if realized_services is None:
                self._realized_singleton_services[service_descriptor.service_type] = [service]
            else:
                realized_services.append(service)
        return service


class ServiceScope(ServiceProviderBase, ServiceScopeBase):
    ''' Represents the default implementation of the IServiceScope class '''

    def __init__(self, root_service_provider: ServiceProviderBase, scoped_service_descriptors: List[ServiceDescriptor]):
        self._root_service_provider = root_service_provider
        self._scoped_service_descriptors = scoped_service_descriptors
        self._realized_scoped_services: Dict[Type, List[Any]] = {}

    _root_service_provider: ServiceProviderBase
    ''' Gets the IServiceProvider that has created the service scope '''

    _scoped_service_descriptors: List[ServiceDescriptor]
    ''' Gets a list of the scoped service descriptors '''

    _realized_scoped_services: Dict[Type, List[Any]]
    ''' Gets the collection of realized scoped services '''

    def get_service_provider(self) -> ServiceProviderBase:
        ''' Gets the scoped service provider '''
        return self

    def get_service(self, type: Type) -> Optional[Any]:
        ''' Gets the service with the specified type, if any has been registered '''
        # First try to get from scoped services
        scoped_descriptor = next((descriptor for descriptor in self._scoped_service_descriptors if descriptor.service_type == type), None)
        if scoped_descriptor is not None:
            # Check if we already have a cached scoped instance
            realized_services = self._realized_scoped_services.get(scoped_descriptor.service_type)
            if realized_services is not None and len(realized_services) > 0:
                return realized_services[-1]
            else:
                # Build new scoped service
                return self._build_service(scoped_descriptor)
        
        # Fall back to root service provider for singleton/transient services
        return self._root_service_provider.get_service(type)

    def get_required_service(self, type: Type) -> Any:
        ''' Gets the required service with the specified type '''
        service = self.get_service(type)
        if service is None:
            raise Exception(f'Failed to retrieve required service of type {type}')
        return service

    def get_services(self, type: Type) -> List[Any]:
        ''' Gets all services of the specified type '''
        services = []
        # Get scoped services
        scoped_descriptors = [descriptor for descriptor in self._scoped_service_descriptors if descriptor.service_type == type]
        for service_descriptor in scoped_descriptors:
            services.append(self._build_service(service_descriptor))
        
        # Get root services (singleton/transient)
        root_services = self._root_service_provider.get_services(type)
        services.extend(root_services)
        return services

    def create_scope(self) -> ServiceScopeBase: 
        return self

    def dispose(self):
        ''' Disposes of the service scope '''
        # Dispose of scoped services that implement disposal
        for services_list in self._realized_scoped_services.values():
            for service in services_list:
                if hasattr(service, 'dispose'):
                    service.dispose()
        self._realized_scoped_services.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()

    def _build_service(self, service_descriptor: ServiceDescriptor) -> Any:
        ''' Builds a new service based on the service descriptor '''
        if service_descriptor.singleton is not None:
            service = service_descriptor.singleton
        elif service_descriptor.implementation_factory is not None:
            service = service_descriptor.implementation_factory(self)
        else:
            init_args = [param for param in inspect.signature(service_descriptor.implementation_type.__init__).parameters.values() if param.name not in ['self', 'args', 'kwargs']]
            args: Dict[str, Any] = {}
            for init_arg in init_args:
                dependency = self.get_service(init_arg.annotation)
                if dependency is None and init_arg.default == init_arg.empty and init_arg.name != 'self':
                    raise Exception(f"Failed to build service of type '{service_descriptor.service_type.__name__}' because the service provider failed to resolve service '{init_arg.annotation}'")
                args[init_arg.name] = dependency
            service = service_descriptor.implementation_type(**args)
        
        # Cache scoped services (but not transient)
        if service_descriptor.lifetime == ServiceLifetime.SCOPED:
            realized_services = self._realized_scoped_services.get(service_descriptor.service_type)
            if realized_services is None:
                self._realized_scoped_services[service_descriptor.service_type] = [service]
            else:
                realized_services.append(service)
        return service


class ServiceCollection(List[ServiceDescriptor]):
    ''' Represents a collection of service descriptors used to configure a service provider '''

    def add_singleton(self, service_type: Type, implementation_type: Optional[Type] = None, singleton: Any = None, implementation_factory: Optional[Callable[[ServiceProviderBase], Any]] = None) -> "ServiceCollection":
        ''' Registers a new singleton service dependency '''
        self.append(ServiceDescriptor(service_type, implementation_type, singleton, implementation_factory, ServiceLifetime.SINGLETON))
        return self

    def try_add_singleton(self, service_type: Type, implementation_type: Optional[Type] = None, singleton: Any = None, implementation_factory: Optional[Callable[[ServiceProviderBase], Any]] = None) -> "ServiceCollection":
        ''' Attempts to register a new singleton service dependency, if one has not already been registered'''
        if any(descriptor.service_type == service_type for descriptor in self):
            return self
        return self.add_singleton(service_type, implementation_type, singleton, implementation_factory)

    def add_transient(self, service_type: Type, implementation_type: Optional[Type] = None, implementation_factory: Optional[Callable[[ServiceProviderBase], Any]] = None) -> "ServiceCollection":
        ''' Registers a new transient service dependency '''
        self.append(ServiceDescriptor(service_type, implementation_type, None, implementation_factory, ServiceLifetime.TRANSIENT))
        return self

    def try_add_transient(self, service_type: Type, implementation_type: Optional[Type] = None, implementation_factory: Optional[Callable[[ServiceProviderBase], Any]] = None) -> "ServiceCollection":
        ''' Attempts to register a new transient service dependency, if one has not already been registered'''
        if any(descriptor.service_type == service_type for descriptor in self):
            return self
        return self.add_transient(service_type, implementation_type, implementation_factory)

    def add_scoped(self, service_type: Type, implementation_type: Optional[Type] = None, implementation_factory: Optional[Callable[[ServiceProviderBase], Any]] = None) -> "ServiceCollection":
        ''' Registers a new scoped service dependency '''
        self.append(ServiceDescriptor(service_type, implementation_type, None, implementation_factory, ServiceLifetime.SCOPED))
        return self

    def try_add_scoped(self, service_type: Type, implementation_type: Optional[Type] = None, implementation_factory: Optional[Callable[[ServiceProviderBase], Any]] = None) -> "ServiceCollection":
        ''' Attempts to register a new scoped service dependency, if one has not already been registered'''
        if any(descriptor.service_type == service_type for descriptor in self):
            return self
        return self.add_scoped(service_type, implementation_type, implementation_factory)

    def build(self) -> ServiceProviderBase:
        ''' Builds a service provider from the registered service descriptors '''
        return ServiceProvider(list(self))

    TRANSIENT = 'transient'
    '''Transient services are created each time they are requested.'''

    SCOPED = 'scoped'
    '''Scoped services are created once per request within a scope (e.g., a web request).'''

    SINGLETON = 'singleton'
    '''Singleton services are created only once and reused for the entire application lifetime.'''


class ServiceProviderBase(ABC):
    ''' Defines the fundamentals of a container used to manage and provide instances of dependencies, enabling dependency injection to promote modularity and maintainability. '''

    def get_service(self, type: Type) -> Optional[any]:
        ''' Gets the service with the specified type, if any has been registered '''
        raise NotImplementedError()

    def get_required_service(self, type: Type) -> any:
        ''' Gets the required service with the specified type '''
        raise NotImplementedError()

    def get_services(self, type: Type) -> List:
        ''' Gets all services of the specified type '''
        raise NotImplementedError()

    def create_scope(self) -> "ServiceScopeBase":
        ''' Creates a new service scope '''
        raise NotImplementedError()


class ServiceScopeBase(ABC):
    ''' Defines the fundamentals of a a limited context within which services are resolved and managed by a service provider, allowing for scoped instances and controlled lifetimes of dependencies. '''

    @abstractmethod
    def get_service_provider(self) -> ServiceProviderBase:
        ''' Gets the scoped service provider '''
        raise NotImplementedError()

    @abstractmethod
    def dispose(self):
        ''' Disposes of the service scope '''
        raise NotImplementedError()


# ServiceDescriptor needs to be declared before ServiceScope uses it
class ServiceDescriptor:
    ''' Describes a service with the required information to create instances of it '''

    def __init__(self, service_type: Type, implementation_type: Optional[Type] = None, singleton: any = None, implementation_factory: Callable[[ServiceProviderBase], any] = None, lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT):
        ''' Initializes a new ServiceDescriptor '''
        self.service_type = service_type
        self.implementation_type = implementation_type if implementation_type is not None else service_type
        self.singleton = singleton
        self.implementation_factory = implementation_factory
        self.lifetime = lifetime

    service_type: Type
    ''' Gets the type of the service '''

    implementation_type: Type
    ''' Gets the type of the service implementation '''

    singleton: any
    ''' Gets the service singleton instance, if any '''

    implementation_factory: Callable[[ServiceProviderBase], any]
    ''' Gets the factory, if any, used to create the service instance '''

    lifetime: ServiceLifetime
    ''' Gets the service lifetime '''

    @property
    def is_key_service(self) -> bool:
        ''' Gets a boolean indicating whether or not the descriptor defines a key service '''
        return_type = inspect.signature(self.implementation_factory).return_annotation if self.implementation_factory is not None else None
        if return_type is None and self.implementation_factory is not None:
            return_type = type(self.implementation_factory(None))
        return return_type != type(None) and return_type != self.service_type


class ServiceProvider(ServiceProviderBase):
    ''' Represents the default implementation of the IServiceProvider interface '''

    def __init__(self, service_descriptors: List[ServiceDescriptor]):
        self._service_descriptors = service_descriptors
        self._realized_singleton_services = dict[Type, List[any]]()

    _service_descriptors: List[ServiceDescriptor]
    ''' Gets a list of the service descriptors that define the services exposed by the service provider '''

    _realized_singleton_services: Dict[Type, List[any]]
    ''' Gets a list of the cached service instances '''

    def get_service(self, type: Type) -> Optional[any]:
        ''' Gets the service with the specified type, if any has been registered '''
        service_descriptor = [descriptor for descriptor in self._service_descriptors if descriptor.service_type == type]
        if service_descriptor is None or len(service_descriptor) == 0:
            return None
        service_descriptor = service_descriptor[0]
        realized_services = self._realized_singleton_services.get(service_descriptor.service_type)
        if service_descriptor.lifetime == ServiceLifetime.SINGLETON and realized_services is not None and len(realized_services) > 0:
            return realized_services[-1]
        else:
            return self._build_service(service_descriptor)

    def get_required_service(self, type: Type) -> any:
        ''' Gets the required service with the specified type '''
        service = self.get_service(type)
        if service is None:
            raise Exception(f'Failed to retrieve required service of type {type}')
        return service

    def get_services(self, type: Type) -> List:
        ''' Gets all services of the specified type '''
        services = []
        service_descriptors = [descriptor for descriptor in self._service_descriptors if descriptor.service_type == type]
        for service_descriptor in service_descriptors:
            services.append(self._build_service(service_descriptor))
        return services

    def create_scope(self) -> ServiceScopeBase:
        ''' Creates a new service scope '''
        return ServiceScope(self, [descriptor for descriptor in self._service_descriptors if descriptor.lifetime == ServiceLifetime.SCOPED])

    def _build_service(self, service_descriptor: ServiceDescriptor) -> any:
        ''' Builds a new service based on the service descriptor '''
        if service_descriptor.singleton is not None:
            service = service_descriptor.singleton
        elif service_descriptor.implementation_factory is not None:
            service = service_descriptor.implementation_factory(self)
        else:
            init_args = [param for param in inspect.signature(service_descriptor.implementation_type.__init__).parameters.values() if param.name not in ['self', 'args', 'kwargs']]
            args = dict[Type, any]()
            for init_arg in init_args:
                dependency = self.get_service(init_arg.annotation)
                if dependency is None and init_arg.default == init_arg.empty and init_arg.name != 'self':
                    raise Exception(f"Failed to build service of type '{service_descriptor.service_type.__name__}' because the service provider failed to resolve service '{init_arg.annotation}'")
                args[init_arg.name] = dependency
            service = service_descriptor.implementation_type(**args)
        
        # Cache singleton services
        if service_descriptor.lifetime == ServiceLifetime.SINGLETON:
            realized_services = self._realized_singleton_services.get(service_descriptor.service_type)
            if realized_services is None:
                self._realized_singleton_services[service_descriptor.service_type] = [service]
            else:
                realized_services.append(service)
        return service


class ServiceScope(ServiceProviderBase):
    ''' Represents the default implementation of the IServiceScope class '''

    def __init__(self, root_service_provider: ServiceProviderBase, scoped_service_descriptors: List[ServiceDescriptor]):
        self._root_service_provider = root_service_provider
        self._scoped_service_descriptors = scoped_service_descriptors
        self._realized_scoped_services = dict[Type, List[any]]()

    _root_service_provider: ServiceProviderBase
    ''' Gets the IServiceProvider that has created the service scope '''

    _scoped_service_descriptors: List[ServiceDescriptor]
    ''' Gets a list of the scoped service descriptors '''

    _realized_scoped_services: Dict[Type, List[any]]
    ''' Gets the collection of realized scoped services '''

    def get_service_provider(self) -> ServiceProviderBase:
        ''' Gets the scoped service provider '''
        return self

    def get_service(self, type: Type) -> Optional[any]:
        ''' Gets the service with the specified type, if any has been registered '''
        # First try to get from scoped services
        scoped_descriptor = next((descriptor for descriptor in self._scoped_service_descriptors if descriptor.service_type == type), None)
        if scoped_descriptor is not None:
            # Check if we already have a cached scoped instance
            realized_services = self._realized_scoped_services.get(scoped_descriptor.service_type)
            if realized_services is not None and len(realized_services) > 0:
                return realized_services[-1]
            else:
                # Build new scoped service
                return self._build_service(scoped_descriptor)
        
        # Fall back to root service provider for singleton/transient services
        return self._root_service_provider.get_service(type)

    def get_required_service(self, type: Type) -> any:
        ''' Gets the required service with the specified type '''
        service = self.get_service(type)
        if service is None:
            raise Exception(f'Failed to retrieve required service of type {type}')
        return service

    def get_services(self, type: Type) -> List:
        ''' Gets all services of the specified type '''
        services = []
        # Get scoped services
        scoped_descriptors = [descriptor for descriptor in self._scoped_service_descriptors if descriptor.service_type == type]
        for service_descriptor in scoped_descriptors:
            services.append(self._build_service(service_descriptor))
        
        # Get root services (singleton/transient)
        root_services = self._root_service_provider.get_services(type)
        services.extend(root_services)
        return services

    def create_scope(self) -> ServiceScopeBase: 
        return self

    def dispose(self):
        ''' Disposes of the service scope '''
        # Dispose of scoped services that implement disposal
        for services_list in self._realized_scoped_services.values():
            for service in services_list:
                if hasattr(service, 'dispose'):
                    service.dispose()
        self._realized_scoped_services.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()

    def _build_service(self, service_descriptor: ServiceDescriptor) -> any:
        ''' Builds a new service based on the service descriptor '''
        # ServiceScope can build scoped services - this is its purpose
        if service_descriptor.singleton is not None:
            service = service_descriptor.singleton
        elif service_descriptor.implementation_factory is not None:
            service = service_descriptor.implementation_factory(self)
        else:
            init_args = [param for param in inspect.signature(service_descriptor.implementation_type.__init__).parameters.values() if param.name not in ['self', 'args', 'kwargs']]
            args = dict[Type, any]()
            for init_arg in init_args:
                dependency = self.get_service(init_arg.annotation)
                if dependency is None and init_arg.default == init_arg.empty and init_arg.name != 'self':
                    raise Exception(f"Failed to build service of type '{service_descriptor.service_type.__name__}' because the service provider failed to resolve service '{init_arg.annotation}'")
                args[init_arg.name] = dependency
            service = service_descriptor.implementation_type(**args)
        
        # Cache non-transient services
        if service_descriptor.lifetime != ServiceLifetime.TRANSIENT:
            realized_services = self._realized_scoped_services.get(service_descriptor.service_type)
            if realized_services is None:
                self._realized_scoped_services[service_descriptor.service_type] = [service]
            else:
                realized_services.append(service)
        return service

    _root_service_provider: ServiceProviderBase
    ''' Gets the IServiceProvider that has created the service scope '''

    _scoped_service_descriptors: List[ServiceDescriptor]
    ''' Gets a list containing the configurations of all scoped dependencies '''

    _realized_scoped_services: Dict[Type, List] = dict[Type, List]()
    ''' Gets a type/list mapping containing all scoped services that have already been built/resolved '''

    def get_service_provider(self) -> ServiceProviderBase: return self

    def get_service(self, type: Type) -> Optional[any]:
        if type == ServiceProviderBase:
            return self
        
        # Check if we have a scoped service already realized
        realized_services = self._realized_scoped_services.get(type)
        if realized_services is not None and len(realized_services) > 0:
            return realized_services[0]
        
        # Look for scoped service descriptor
        descriptor = next((descriptor for descriptor in self._scoped_service_descriptors if descriptor.service_type == type), None)
        if descriptor is not None:
            return self._build_service(descriptor)
        
        # Fall back to root service provider for non-scoped services
        return self._root_service_provider.get_service(type)

    def get_required_service(self, type: Type) -> any:
        service = self.get_service(type)
        if service is None:
            raise Exception(f"Failed to resolve service of type '{type.__name__}'")
        return service

    def get_services(self, type: Type) -> List:
        if type == ServiceProviderBase:
            return [self]
        
        # Collect scoped services
        service_descriptors = [descriptor for descriptor in self._scoped_service_descriptors if descriptor.service_type == type]
        realized_services = self._realized_scoped_services.get(type, [])
        
        # Build missing scoped services
        for descriptor in service_descriptors:
            implementation_type = descriptor.get_implementation_type()
            if not any(isinstance(service, implementation_type) for service in realized_services):
                realized_services.append(self._build_service(descriptor))
        
        # Combine with root provider services (non-scoped)
        root_services = self._root_service_provider.get_services(type)
        return realized_services + root_services

    def _build_service(self, service_descriptor: ServiceDescriptor) -> any:
        ''' Builds a new service based on the service descriptor '''
        # ServiceScope can build scoped services - this is its purpose
        if service_descriptor.singleton is not None:
            service = service_descriptor.singleton
        elif service_descriptor.implementation_factory is not None:
            service = service_descriptor.implementation_factory(self)
        else:
            init_args = [param for param in inspect.signature(service_descriptor.implementation_type.__init__).parameters.values() if param.name not in ['self', 'args', 'kwargs']]
            args = dict[Type, any]()
            for init_arg in init_args:
                dependency = self.get_service(init_arg.annotation)
                if dependency is None and init_arg.default == init_arg.empty and init_arg.name != 'self':
                    raise Exception(f"Failed to build service of type '{service_descriptor.service_type.__name__}' because the service provider failed to resolve service '{init_arg.annotation}'")
                args[init_arg.name] = dependency
            service = service_descriptor.implementation_type(**args)
        
        # Cache non-transient services
        if service_descriptor.lifetime != ServiceLifetime.TRANSIENT:
            realized_services = self._realized_scoped_services.get(service_descriptor.service_type)
            if realized_services is None:
                self._realized_scoped_services[service_descriptor.service_type] = [service]
            else:
                realized_services.append(service)
        return service

    def create_scope(self) -> ServiceScopeBase: return self

    def dispose(self):
        # Properly dispose of all realized scoped services
        for service_type, services in self._realized_scoped_services.items():
            for service in services:
                if hasattr(service, '__exit__'):
                    try:
                        service.__exit__(None, None, None)
                    except Exception:
                        pass  # Ignore disposal exceptions
                elif hasattr(service, 'dispose'):
                    try:
                        service.dispose()
                    except Exception:
                        pass  # Ignore disposal exceptions
        self._realized_scoped_services.clear()


class ServiceProvider(ServiceProviderBase):
    ''' Represents the default implementation of the IServiceProvider class '''

    def __init__(self, service_descriptors: List[ServiceDescriptor]):
        ''' Initializes a new service provider using the specified service dependency configuration '''
        self._service_descriptors = service_descriptors

    _service_descriptors: List[ServiceDescriptor]
    ''' Gets a list containing the configuration of all registered dependencies '''

    _realized_services: Dict[Type, List] = dict[Type, List]()
    ''' Gets a type/list mapping containing all services that have already been built/resolved '''

    def get_service(self, type: Type) -> Optional[any]:
        if type == ServiceProviderBase:
            return self
        realized_services = self._realized_services.get(type)
        if realized_services is not None:
            return realized_services[0]
        if len(self._service_descriptors) < 1:
            return None
        descriptor = next((descriptor for descriptor in self._service_descriptors if descriptor.service_type == type), None)
        if descriptor is None:
            return None
        return self._build_service(descriptor)

    def get_required_service(self, type: Type) -> any:
        service = self.get_service(type)
        if service is None:
            raise Exception(f"Failed to resolve service of type '{type.__name__}'")
        return service

    def get_services(self, type: Type) -> List:
        if type == ServiceProviderBase:
            return [self]
        service_descriptors = [descriptor for descriptor in self._service_descriptors if descriptor.service_type == type]
        realized_services = self._realized_services.get(type)
        if realized_services is None:
            realized_services = list()
        for descriptor in service_descriptors:
            implementation_type = descriptor.get_implementation_type()
            realized_service = next((service for service in realized_services if self._is_service_instance_of(service, implementation_type)), None)
            if realized_service is None:
                realized_services.append(self._build_service(descriptor))
        return realized_services

    def _is_service_instance_of(self, service: Any, type_: Type) -> bool:
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
        ''' Builds a new service provider based on the configured dependencies '''
        if service_descriptor.lifetime == ServiceLifetime.SCOPED:
            raise Exception(f"Failed to resolve scoped service of type '{service_descriptor.implementation_type}' from root service provider")
        if service_descriptor.singleton is not None:
            service = service_descriptor.singleton
        elif service_descriptor.implementation_factory is not None:
            service = service_descriptor.implementation_factory(self)
        else:
            is_service_generic = not inspect.isclass(service_descriptor.implementation_type)  # if implementation_type is not a class, then it must be a generic type
            service_generic_type = service_descriptor.implementation_type.__origin__ if is_service_generic else None  # retrieve the generic type, used to determine the __init__ args
            service_type = service_descriptor.implementation_type if service_generic_type is None else service_generic_type  # get the type used to determine the __init__ args: the implementation type as is or its generic type definition
            service_init_args = [param for param in inspect.signature(service_type.__init__).parameters.values() if param.name not in ['self', 'args', 'kwargs']]  # gets the __init__ args and leave out self, args and kwargs
            service_generic_args = TypeExtensions.get_generic_arguments(service_descriptor.implementation_type)  # gets the generic args: we will need them to substitute the type args of potential generic dependencies
            service_args = dict[Type, any]()
            for init_arg in service_init_args:
                is_dependency_generic = not inspect.isclass(init_arg.annotation)
                dependency_generic_type = init_arg.annotation.__origin__ if is_dependency_generic else None
                dependency_generic_args = None if dependency_generic_type is None else init_arg.annotation.__args__
                if dependency_generic_args is not None:
                    dependency_generic_args = [service_generic_args[arg.__name__] if type(arg) == TypeVar else arg for arg in dependency_generic_args]  # replace TypeVar generic arguments by the service's matching generic argument
                dependency_type = init_arg.annotation.__origin__[*dependency_generic_args] if is_dependency_generic else init_arg.annotation
                dependency = self.get_service(dependency_type)
                if dependency is None and init_arg.default == init_arg.empty and init_arg.name != 'self':
                    raise Exception(f"Failed to build service of type '{service_descriptor.service_type.__name__}' because the service provider failed to resolve service '{dependency_type.__name__}'")
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
        """Creates a new service scope with scoped services"""
        return ServiceScope(self, [descriptor for descriptor in self._service_descriptors if descriptor.lifetime == ServiceLifetime.SCOPED])

    def dispose(self):
        for service in self._realized_services:
            try:
                service.__exit__()
            except:
                pass
        self._realized_services = dict[Type, List]()


class ServiceDescriptor:
    ''' Represents an object used to describe and configure a service dependency '''

    def __init__(self, service_type: Type, implementation_type: Optional[Type] = None, singleton: any = None, implementation_factory: Callable[[ServiceProvider], any] = None, lifetime: ServiceLifetime = ServiceLifetime.SINGLETON):
        ''' Initializes a new service descriptor '''
        if singleton is not None and lifetime != ServiceLifetime.SINGLETON:
            raise Exception("A singleton service dependency must have lifetime set to 'SINGLETON'")
        self.service_type = service_type
        self.implementation_type = implementation_type
        self.singleton = singleton
        self.implementation_factory = implementation_factory
        self.lifetime = lifetime
        if self.singleton is None and self.implementation_factory is None and self.implementation_type is None:
            self.implementation_type = self.service_type

    service_type: Type
    ''' Gets the type of the service dependency '''

    implementation_type: Optional[Type]
    ''' Gets the service dependency's implementation/concretion type, if any, to be instanciated on demand by a service provider. If set, 'singleton' and 'implementation-factory' are ignored. '''

    singleton: any
    ''' Gets the service instance singleton, if any. If set, 'implementation_type' and 'implementation-factory' are ignored. '''

    implementation_factory: Callable[[ServiceProvider], any]
    ''' Gets a function, if any, use to create a new instance of the service dependency. If set, 'implementation_type' and 'singleton' are ignored. '''

    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    ''' Gets the service's lifetime. Defaults to 'SINGLETON' '''

    def get_implementation_type(self) -> Type:
        ''' Gets the service's implementation type '''
        if self.implementation_type is not None:
            return self.implementation_type
        return_type = inspect.signature(self.implementation_factory).return_annotation if self.implementation_factory != None else None
        if return_type is None and self.implementation_factory != None:
            if self.implementation_type is None:
                raise Exception(f"Failed to determine the return type of the implementation factory configured for service of type '{self.service_type.__name__}'. Either specify the implementation type, or use a function instead of a lambda as factory callable.")
            else:
                return_type = self.implementation_type
        return type(self.singleton) if self.singleton is not None else inspect.signature(self.implementation_factory).return_annotation


# ServiceCollection will be defined at the end of this file


class ServiceCollection(List[ServiceDescriptor]):
    ''' Represents a collection of service descriptors used to configure a service provider '''

    def add_singleton(self, service_type: Type, implementation_type: Optional[Type] = None, singleton: any = None, implementation_factory: Callable[[ServiceProvider], any] = None) -> ServiceCollection:
        ''' Registers a new singleton service dependency '''
        self.append(ServiceDescriptor(service_type, implementation_type, singleton, implementation_factory, ServiceLifetime.SINGLETON))
        return self

    def try_add_singleton(self, service_type: Type, implementation_type: Optional[Type] = None, singleton: any = None, implementation_factory: Callable[[ServiceProvider], any] = None) -> ServiceCollection:
        ''' Attempts to register a new singleton service dependency, if one has not already been registered'''
        if any(descriptor.service_type == service_type for descriptor in self):
            return self
        return self.add_singleton(service_type, implementation_type, singleton, implementation_factory)

    def add_transient(self, service_type: Type, implementation_type: Optional[Type] = None, implementation_factory: Callable[[ServiceProvider], any] = None) -> ServiceCollection:
        ''' Registers a new transient service dependency '''
        self.append(ServiceDescriptor(service_type, implementation_type, None, implementation_factory, ServiceLifetime.TRANSIENT))
        return self

    def try_add_transient(self, service_type: Type, implementation_type: Optional[Type] = None, implementation_factory: Callable[[ServiceProvider], any] = None) -> ServiceCollection:
        ''' Attempts to register a new transient service dependency, if one has not already been registered'''
        if any(descriptor.service_type == service_type for descriptor in self):
            return self
        return self.add_transient(service_type, implementation_type, implementation_factory)

    def add_scoped(self, service_type: Type, implementation_type: Optional[Type] = None, implementation_factory: Callable[[ServiceProvider], any] = None) -> ServiceCollection:
        ''' Registers a new scoped service dependency '''
        self.append(ServiceDescriptor(service_type, implementation_type, None, implementation_factory, ServiceLifetime.SCOPED))
        return self

    def try_add_scoped(self, service_type: Type, implementation_type: Optional[Type] = None, implementation_factory: Callable[[ServiceProvider], any] = None) -> ServiceCollection:
        ''' Attempts to register a new scoped service dependency, if one has not already been registered'''
        if any(descriptor.service_type == service_type for descriptor in self):
            return self
        return self.add_scoped(service_type, implementation_type, implementation_factory)

    def build(self) -> ServiceProviderBase:
        return ServiceProvider(self)
