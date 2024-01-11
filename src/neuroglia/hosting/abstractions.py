import asyncio
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Dict, cast
from neuroglia.dependency_injection.service_provider import ServiceCollection, ServiceProviderBase, ServiceScopeBase
from pydantic_settings import BaseSettings

class HostBase(ABC):
    ''' Defines the fundamentals of an program's abstraction '''

    services : ServiceProviderBase

    @abstractmethod
    async def start_async(self):
        ''' Starts the program '''
        raise NotImplementedError()
    
    @abstractmethod
    async def stop_async(self):
        ''' Attempts to gracefully stop the program '''
        raise NotImplementedError()
    
    def run(self):
        ''' Runs the program '''
        asyncio.ensure_future(self.start_async())

    @abstractmethod
    def dispose(self):
        ''' Disposes of the program's resources '''
        raise NotImplementedError()
 
class HostedServiceBase:
    ''' Defines the fundamentals of a service managed by the host '''
    
    async def start_async(self):
        ''' Starts the service '''
        pass
    
    async def stop_async(self):
        ''' Attempts to gracefully stop the service '''
        pass


class Host(HostBase):
    ''' Represents the default implementation of the HostBase class '''
    
    def __init__(self, services : ServiceProviderBase):
        self.services = services

    async def start_async(self):
        hosted_services = [cast(HostedServiceBase, service) for service in self.services.get_services(HostedServiceBase)]
        start_tasks = [hosted_service.start_async() for hosted_service in hosted_services]
        await asyncio.gather(*start_tasks)
        
    async def stop_async(self):
        hosted_services = [cast(HostedServiceBase, service) for service in self.services.get_services(HostedServiceBase)]
        stop_tasks = [hosted_service.stop_async() for hosted_service in hosted_services]
        await asyncio.gather(*stop_tasks)
        
    def dispose(self):
        if isinstance(self.services, ServiceScopeBase): self.services.dispose()
   
        
class ApplicationSettings(BaseSettings):
    
    connection_strings : dict[str, str] = dict[str, str]()
    

class ApplicationBuilderBase:
    ''' Defines the fundamentals of a service used to build applications '''
   
    settings : ApplicationSettings = ApplicationSettings()

    services : ServiceCollection = ServiceCollection()
    
    @abstractmethod
    def build(self) -> HostBase: 
        ''' Builds the application's host  '''
        raise NotImplementedError()
    

class ApplicationBuilder(ApplicationBuilderBase):
    ''' Represents the default implementation of the ApplicationBuilderBase class '''
    
    @contextmanager
    def build(self) -> HostBase: 
        try:
            service_provider = self.services.build()
            host = Host(service_provider)
            yield host
        finally:
            host.dispose()