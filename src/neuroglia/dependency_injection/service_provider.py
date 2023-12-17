from abc import ABC, abstractclassmethod
from contextlib import contextmanager
from enum import Enum
import inspect
from typing import Callable, ForwardRef, List, Optional, Type, Dict

class ServiceLifetime(Enum):
    '''Enumerates all supported service lifetimes.'''

    TRANSIENT = 'transient'
    '''Transient services are created each time they are requested.'''

    SCOPED = 'scoped'
    '''Scoped services are created once per request within a scope (e.g., a web request).'''

    SINGLETON = 'singleton'
    '''Singleton services are created only once and reused for the entire application lifetime.'''


ServiceDescriptor = ForwardRef("ServiceDescriptor")

ServiceProvider = ForwardRef("ServiceProvider")

IServiceScope = ForwardRef("IServiceScope")


class IServiceProvider(ABC):
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
    
    def create_scope(self) -> IServiceScope:
        ''' Creates a new service scope '''
        raise NotImplementedError()


class IServiceScope(ABC):
    ''' Defines the fundamentals of a a limited context within which services are resolved and managed by a service provider, allowing for scoped instances and controlled lifetimes of dependencies. '''

    @abstractclassmethod
    def get_service_provider(self) -> IServiceProvider:
        ''' Gets the scoped service provider '''
        raise NotImplementedError()

    @abstractclassmethod
    def dispose(self):
        ''' Disposes of the service scope '''
        raise NotImplementedError()


class ServiceScope(IServiceScope, IServiceProvider):
    ''' Represents the default implementation of the IServiceScope class '''

    def __init__(self, root_service_provider: IServiceProvider, scoped_service_descriptors: List[ServiceDescriptor]):
        self._root_service_provider = root_service_provider
        self._scoped_service_descriptors = scoped_service_descriptors

    _root_service_provider: IServiceProvider
    ''' Gets the IServiceProvider that has created the service scope '''
    
    _scoped_service_descriptors: List[ServiceDescriptor]
    ''' Gets a list containing the configurations of all scoped dependencies '''
    
    _realized_scoped_services: Dict[Type, List]= dict[Type, List]()
    ''' Gets a type/list mapping containing all scoped services that have already been built/resolved '''
    
    def get_service_provider(self) -> IServiceProvider: return self

    def get_service(self, type: Type) -> Optional[any]:
        realized_services = self._realized_scoped_services.get(type)
        realized_service = self._root_service_provider.get_service(type) if realized_services is None else realized_services[0]
        if realized_service is not None: return realized_service
        descriptor = next(descriptor for descriptor in self._scoped_service_descriptors if descriptor.service_type == type)
        if descriptor is None: return None;
        return self._build_service(descriptor)
    
    def get_required_service(self, type: Type) -> any:
        service = self.get_service(type)
        if service is None: raise Exception(f"Failed to resolve service of type '{type.__name__}'")
        return service
    
    def get_services(self, type: Type) -> List:
        service_descriptors = [descriptor for descriptor in self._scoped_service_descriptors if descriptor.service_type == type]
        realized_services = self._realized_scoped_services.get(type)
        if realized_services is None: realized_services = List()
        for descriptor in service_descriptors:
            if any(type(service) == descriptor.service_type for service in realized_services): continue
            realized_services.append(self._build_service(descriptor))
        return realized_services + self._root_service_provider.get_services(type)
        
    def _build_service(self, service_descriptor: ServiceDescriptor) -> any:
        ''' Builds a new service provider based on the configured dependencies '''
        if service_descriptor.lifetime == ServiceLifetime.SCOPED: raise Exception(f"Failed to resolve scoped service of type '{service_descriptor.implementation_type}' from root service provider")
        if service_descriptor.singleton is not None: service = service_descriptor.singleton
        elif service_descriptor.implementation_factory is not None: service = service_descriptor.implementation_factory(self)
        else:
            init_args = [param for param in inspect.signature(service_descriptor.implementation_type.__init__).parameters.values() if param.name not in ['self', 'args', 'kwargs']]
            args = dict[Type, any]()
            for init_arg in init_args:
                dependency = self.get_service(init_arg.annotation)
                if dependency is None and init_arg.default == init_arg.empty and init_arg.name != 'self': raise Exception(f"Failed to build service of type '{service_descriptor.service_type.__name__}' because the service provider failed to resolve service '{init_arg.annotation}'")
                args[init_arg.name] = dependency
            service = service_descriptor.implementation_type(**args)
        if service_descriptor.lifetime != ServiceLifetime.TRANSIENT:
            realized_services = self._realized_scoped_services.get(service_descriptor.service_type)
            if realized_services is None: self._realized_scoped_services[service_descriptor.service_type] = { service }
            else: realized_services.append(service)
        return service

    def create_scope(self) -> IServiceScope: return self

    def dispose(self):
        for service in self._realized_scoped_services: service.__exit__()
        self._realized_scoped_services = dict[Type, List]()


class ServiceProvider(IServiceProvider):
    ''' Represents the default implementation of the IServiceProvider class '''
    
    def __init__(self, service_descriptors: List[ServiceDescriptor]):
        ''' Initializes a new service provider using the specified service dependency configuration '''
        self._service_descriptors = service_descriptors

    _service_descriptors: List[ServiceDescriptor]
    ''' Gets a list containing the configuration of all registered dependencies '''
    
    _realized_services : Dict[Type, List] = dict[Type, List]()
    ''' Gets a type/list mapping containing all services that have already been built/resolved '''
    
    def get_service(self, type: Type) -> Optional[any]:
        realized_services = self._realized_services.get(type)
        if realized_services is not None: return realized_services[0]
        descriptor = next(descriptor for descriptor in self._service_descriptors if descriptor.service_type == type)
        if descriptor is None: return None;
        return self._build_service(descriptor)
    
    def get_required_service(self, type: Type) -> any:
        service = self.get_service(type)
        if service is None: raise Exception(f"Failed to resolve service of type '{type.__name__}'")
        return service
    
    def get_services(self, type: Type) -> List:
        service_descriptors = [descriptor for descriptor in self._service_descriptors if descriptor.service_type == type]
        realized_services = self._realized_services.get(type)
        if realized_services is None: realized_services = List()
        for descriptor in service_descriptors:
            if any(type(service) == descriptor.service_type for service in realized_services): continue
            realized_services.append(self._build_service(descriptor))
        return realized_services
        
    def _build_service(self, service_descriptor: ServiceDescriptor) -> any:
        ''' Builds a new service provider based on the configured dependencies '''
        if service_descriptor.lifetime == ServiceLifetime.SCOPED: raise Exception(f"Failed to resolve scoped service of type '{service_descriptor.implementation_type}' from root service provider")
        if service_descriptor.singleton is not None: service = service_descriptor.singleton
        elif service_descriptor.implementation_factory is not None: service = service_descriptor.implementation_factory(self)
        else:
            init_args = [param for param in inspect.signature(service_descriptor.implementation_type.__init__).parameters.values() if param.name not in ['self', 'args', 'kwargs']]
            args = dict[Type, any]()
            for init_arg in init_args:
                dependency = self.get_service(init_arg.annotation)
                if dependency is None and init_arg.default == init_arg.empty and init_arg.name != 'self': raise Exception(f"Failed to build service of type '{service_descriptor.service_type.__name__}' because the service provider failed to resolve service '{init_arg.annotation}'")
                args[init_arg.name] = dependency
            service = service_descriptor.implementation_type(**args)
        if service_descriptor.lifetime != ServiceLifetime.TRANSIENT:
            realized_services = self._realized_services.get(service_descriptor.service_type)
            if realized_services is None: self._realized_services[service_descriptor.service_type] = { service }
            else: realized_services.append(service)
        return service
    
    @contextmanager
    def create_scope(self) -> IServiceScope:
        service_scope = ServiceScope(self, [descriptor for descriptor in self._service_descriptors if descriptor.lifetime == ServiceLifetime.SCOPED])
        try: yield service_scope
        finally: service_scope.dispose()

    def dispose(self):
        for service in self._realized_services: service.__exit__()
        self._realized_services = dict[Type, List]()


class ServiceDescriptor:
    ''' Represents an object used to describe and configure a service dependency '''
    
    def __init__(self, service_type: Type, implementation_type: Optional[Type] = None, singleton: any = None, implementation_factory: Callable[[ServiceProvider], any] = None, lifetime: ServiceLifetime = ServiceLifetime.SINGLETON):
        ''' Initializes a new service descriptor '''
        if singleton is not None and lifetime != ServiceLifetime.SINGLETON: raise Exception("A singleton service dependency must have lifetime set to 'SINGLETON'")
        self.service_type = service_type
        self.implementation_type = implementation_type
        self.singleton = singleton
        self.implementation_factory = implementation_factory
        self.lifetime = lifetime

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


ServiceCollection = ForwardRef("ServiceCollection")


class ServiceCollection(List[ServiceDescriptor]):
    ''' Represents a collection of service descriptors used to configure a service provider '''
    
    def add_singleton(self, service_type : Type, implementation_type: Optional[Type] = None, singleton: any = None, implementation_factory: Callable[[ServiceProvider], any] = None) -> ServiceCollection:
        ''' Registers a new singleton service dependency '''
        self.append(ServiceDescriptor(service_type, implementation_type, singleton, implementation_factory, ServiceLifetime.SINGLETON))
        return self
    
    def try_add_singleton(self, service_type : Type, implementation_type: Optional[Type] = None, singleton: any = None, implementation_factory: Callable[[ServiceProvider], any] = None) -> ServiceCollection:
        ''' Attempts to register a new singleton service dependency, if one has not already been registered'''
        if any(descriptor.service_type == service_type for descriptor in self): return self
        return self.add_singleton(service_type, implementation_type, singleton, implementation_factory)
    
    def add_transient(self, service_type : Type, implementation_type: Optional[Type] = None, implementation_factory: Callable[[ServiceProvider], any] = None) -> ServiceCollection:
        ''' Registers a new transient service dependency '''
        self.append(ServiceDescriptor(service_type, implementation_type, None, implementation_factory, ServiceLifetime.SINGLETON))
        return self
    
    def try_add_transient(self, service_type : Type, implementation_type: Optional[Type] = None, implementation_factory: Callable[[ServiceProvider], any] = None) -> ServiceCollection:
        ''' Attempts to register a new transient service dependency, if one has not already been registered'''
        if any(descriptor.service_type == service_type for descriptor in self): return self
        return self.add_transient(service_type, implementation_type, implementation_factory)

    def add_scoped(self, service_type : Type, implementation_type: Optional[Type] = None, implementation_factory: Callable[[ServiceProvider], any] = None) -> ServiceCollection:
        ''' Registers a new scoped service dependency '''
        self.append(ServiceDescriptor(service_type, implementation_type, None, implementation_factory, ServiceLifetime.SINGLETON))
        return self
    
    def try_add_scoped(self, service_type : Type, implementation_type: Optional[Type] = None, implementation_factory: Callable[[ServiceProvider], any] = None) -> ServiceCollection:
        ''' Attempts to register a new scoped service dependency, if one has not already been registered'''
        if any(descriptor.service_type == service_type for descriptor in self): return self
        return self.add_scoped(service_type, implementation_type, implementation_factory)

    def build(self) -> IServiceProvider:
        return ServiceProvider(self)
