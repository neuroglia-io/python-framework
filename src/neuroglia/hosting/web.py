from abc import abstractmethod
import importlib
import inspect
from types import ModuleType
from typing import List
from fastapi import FastAPI
from neuroglia.core.type_finder import TypeFinder
from neuroglia.dependency_injection.service_provider import ServiceCollection, ServiceProviderBase
from neuroglia.hosting.abstractions import ApplicationBuilderBase, Host, HostBase
from neuroglia.mvc.controller_base import ControllerBase


class WebHostBase(HostBase, FastAPI):
    ''' Defines the fundamentals of a web application's abstraction '''
    
    def __init__(self):
        FastAPI.__init__(self)
        
    def use_controllers(self):
        ''' Configures FastAPI routes for registered controller services '''
        controller : ControllerBase
        for controller in self.services.get_services(ControllerBase):
            self.include_router(controller.router)
        

class WebHost(WebHostBase, Host):
    ''' Represents the default implementation of the HostBase class '''
    
    def __init__(self, services : ServiceProviderBase):
        WebHostBase.__init__(self)
        Host.__init__(self, services)
         

class WebApplicationBuilderBase(ApplicationBuilderBase):
    ''' Defines the fundamentals of a service used to build applications '''
   
    def __init__(self):
        super().__init__()

    def add_controllers(self, modules : List[str]) -> ServiceCollection:
        ''' Registers all API controller types, which enables automatic configuration and implicit Dependency Injection of the application's controllers (specialized router class in FastAPI) '''
        controller_types = []
        for module in [importlib.import_module(module_name) for module_name in modules]:
            controller_types.extend(TypeFinder.get_types(module, lambda t: inspect.isclass(t) and issubclass(t, ControllerBase) and t != ControllerBase, include_sub_packages=True))
        for controller_type in set(controller_types):
            self.services.add_singleton(ControllerBase, controller_type)
        return self.services
    
    @abstractmethod
    def build(self) -> WebHostBase: 
        ''' Builds the application's host  '''
        raise NotImplementedError()
    

class WebApplicationBuilder(WebApplicationBuilderBase):
    ''' Represents the default implementation of the ApplicationBuilderBase class '''
    
    def __init__(self):
        super().__init__()
    
    def build(self) -> WebHostBase: 
        return WebHost(self.services.build())