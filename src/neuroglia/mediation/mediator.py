import asyncio

from abc import ABC, abstractmethod
from typing import Generic, List, TypeVar
from neuroglia.core.operation_result import OperationResult
from neuroglia.data.abstractions import DomainEvent
from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.integration.models import IntegrationEvent


TResult = TypeVar('TResult', bound=OperationResult)
''' Represents the expected type of result returned by the operation, in case of success '''


class Request(Generic[TResult], ABC):
    ''' Represents a CQRS request '''
    pass


class Command(Generic[TResult], Request[TResult], ABC):
    ''' Represents a CQRS command '''
    pass


class Query(Generic[TResult], Request[TResult], ABC):
    ''' Represents a CQRS query '''
    pass


TRequest = TypeVar('TRequest', bound=Request)
''' Represents the type of CQRS request to handle '''


class RequestHandler(Generic[TRequest, TResult], ABC):
    ''' Represents a service used to handle a specific type of CQRS request '''
    
    @abstractmethod
    async def handle_async(self, request : TRequest) -> TResult:
        ''' Handles the specified request '''
        raise NotImplementedError()


TCommand = TypeVar('TCommand', bound=Command)
''' Represents the type of CQRS command to handle '''


class CommandHandler(Generic[TCommand, TResult], RequestHandler[TCommand, TResult], ABC):
    ''' Represents a service used to handle a specific type of CQRS command '''
    
    pass
 

TQuery = TypeVar('TQuery', bound=Query)
''' Represents the type of CQRS query to handle '''


class QueryHandler(Generic[TQuery, TResult], RequestHandler[TQuery, TResult], ABC):
    ''' Represents a service used to handle a specific type of CQRS query '''
    
    pass


TNotification = TypeVar('TNotification', bound=object)
''' Represents the type of CQRS notification to handle '''


class NotificationHandler(Generic[TNotification], ABC):
    ''' Represents a service used to handle a specific type of CQRS notification'''
    
    @abstractmethod
    async def handle_async(self, notification : TNotification) -> None:
        ''' Handles the specified notification '''
        raise NotImplementedError() 


TDomainEvent = TypeVar('TDomainEvent', bound=DomainEvent)
''' Represents the type of domain event to handle '''


class DomainEventHandler(Generic[TDomainEvent], NotificationHandler[TDomainEvent], ABC):
    ''' Represents a service used to handle a specific domain event '''
    
    pass


TIntegrationEvent = TypeVar('TIntegrationEvent', bound=IntegrationEvent)
''' Represents the type of integration event to handle '''


class IntegrationEventHandler(Generic[TIntegrationEvent], NotificationHandler[TIntegrationEvent], ABC):
    ''' Represents a service used to handle a specific integration event '''
    
    pass


class Mediator:
    ''' Represents the default implementation of the IMediator class '''
    
    _service_provider : ServiceProviderBase

    def __init__(self, service_provider: ServiceProviderBase):
        self._service_provider = service_provider

    async def execute_async(self, request: Request) -> OperationResult:
        ''' Executes the specified request '''
        handlers : List[RequestHandler] = [candidate for candidate in self._service_provider.get_services(RequestHandler) if self._handler_matches(candidate, type(request))]
        if handlers is None or len(handlers) < 1: raise Exception(f"Failed to find a handler for request of type '{type(request).__name__}'")
        elif len(handlers) > 1: raise Exception(f"There must be exactly one handler defined for the command of type '{type(request).__name__}'")
        handler = handlers[0]
        return await handler.handle_async(request)

    async def publish_async(self, notification : object):
        ''' Publishes the specified notification '''
        handlers : List[NotificationHandler] = [candidate for candidate in self._service_provider.get_services(NotificationHandler) if candidate.__orig_bases__[0].__args__[0] == type(notification)]
        if handlers is None or len(handlers) < 1: return
        await asyncio.gather(*(handler.handle_async(notification) for handler in handlers))
        
    def _handler_matches(self, candidate, request_type):
        candidate_type = type(candidate)
        handler_type = next(base for base in candidate_type.__orig_bases__ if (issubclass(base.__origin__, RequestHandler) if hasattr(base, '__origin__') else issubclass(base, RequestHandler)))
        handled_request_type = handler_type.__args__[0]
        return issubclass(handled_request_type.__origin__, request_type) if hasattr(handled_request_type, '__origin__') else issubclass(handled_request_type, request_type)
        