from enum import Enum
import inspect
from typing import Callable, ForwardRef, List, Optional, Type, Dict

class ServiceScope(Enum):
    '''Enumeration representing different service scopes.'''

    TRANSIENT = 'transient'
    '''Transient services are created each time they are requested.'''

    SCOPED = 'scoped'
    '''Scoped services are created once per request within a scope (e.g., a web request).'''

    SINGLETON = 'singleton'
    '''Singleton services are created only once and reused for the entire application lifetime.'''

ServiceDescriptor = ForwardRef("ServiceDescriptor")

class ServiceProvider:
    
    def __init__(self, service_descriptors: List[ServiceDescriptor]):
        self.service_descriptors = service_descriptors

    service_descriptors: List[ServiceDescriptor]
    
    service_realized_services : Dict[Type, object] = dict[Type, object]()
    
    def get_service(self, type: Type) -> Optional[object]:
        realized_service = self.service_realized_services.get(type)
        if realized_service is not None: 
            return realized_service
        descriptor = next(descriptor for descriptor in self.service_descriptors if descriptor.service_type == type)
        if descriptor is None: 
            return None;
        return self.build_service(descriptor)
        
    def build_service(self, service_descriptor: ServiceDescriptor) -> object:
        if service_descriptor.implementation_factory is not None: return service_descriptor.implementation_factory(self)
        init_args = [param for param in inspect.signature(service_descriptor.implementation_type.__init__).parameters.values() if param.name not in ['self', 'args', 'kwargs']]
        required_args = [param for param in init_args if param.default == param.empty and param.name != 'self']
        args = dict[Type, object]()
        for init_arg in init_args:
            dependency = self.get_service(init_arg.annotation)
            if dependency is None and init_arg.default == init_arg.empty and init_arg.name != 'self': raise Exception(f"Failed to build service of type '{service_descriptor.service_type.__name__}' because the service provider failed to resolve service '{init_arg.annotation}'")
            args[init_arg.name] = dependency
        service = service_descriptor.implementation_type(**args)
        return service

class ServiceDescriptor:
    
    def __init__(self, service_type: Type, implementation_type: Optional[Type] = None, implementation_factory: Callable[[ServiceProvider], object] = None, service_scope: ServiceScope = ServiceScope.SINGLETON):
        self.service_type = service_type
        self.implementation_type = implementation_type
        self.implementation_factory = implementation_factory
        self.service_scope = service_scope

    service_type: Type
    
    implementation_type: Optional[Type]
    
    implementation_factory: Callable[[ServiceProvider], object]
    
    service_scope: ServiceScope = ServiceScope.SINGLETON

class ServiceCollection(List[ServiceDescriptor]):
    
    def build(self) -> ServiceProvider:
        return ServiceProvider(self)
