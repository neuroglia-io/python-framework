import asyncio
import inspect
import logging

from abc import ABC, abstractmethod
from types import UnionType
from typing import Any, Generic, List, Optional, TypeVar
from neuroglia.core import ModuleLoader, OperationResult, TypeFinder, TypeExtensions
from neuroglia.data.abstractions import DomainEvent
from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.integration.models import IntegrationEvent

log = logging.getLogger(__name__)


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
    async def handle_async(self, request: TRequest) -> TResult:
        ''' Handles the specified request '''
        raise NotImplementedError()

    def ok(self, data: Optional[Any] = None) -> TResult:
        result: OperationResult = OperationResult("OK", 200)
        result.data = data
        return result

    def created(self, data: Optional[Any] = None) -> TResult:
        result: OperationResult = OperationResult("Created", 201)
        result.data = data
        return result

    def bad_request(self, detail: str) -> TResult:
        ''' Creates a new OperationResult to describe the fact that the request is invalid '''
        return OperationResult("Bad Request", 400, detail, "https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Bad%20Request")

    def not_found(self, entity_type, entity_key, key_name: str = "id") -> TResult:
        ''' Creates a new OperationResult to describe the fact that an entity of the specified type and key could not be found or does not exist '''
        return OperationResult("Not Found", 404, f"Failed to find an entity of type '{entity_type.__name__}' with the specified {key_name} '{entity_key}'", "https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Not%20found%20404")


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
    async def handle_async(self, notification: TNotification) -> None:
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

    _service_provider: ServiceProviderBase

    def __init__(self, service_provider: ServiceProviderBase):
        self._service_provider = service_provider

    async def execute_async(self, request: Request) -> OperationResult:
        ''' Executes the specified request '''
        handlers: List[RequestHandler] = [candidate for candidate in self._service_provider.get_services(RequestHandler) if self._request_handler_matches(candidate, request)]
        if handlers is None or len(handlers) < 1:
            raise Exception(f"Failed to find a handler for request of type '{type(request).__name__}'")
        elif len(handlers) > 1:
            raise Exception(f"There must be exactly one handler defined for the command of type '{type(request).__name__}'")
        log.info(f"Executing request type {type(request).__name__}")
        handler = handlers[0]
        return await handler.handle_async(request)

    async def publish_async(self, notification: object):
        ''' Publishes the specified notification '''
        handlers: List[NotificationHandler] = [candidate for candidate in self._service_provider.get_services(NotificationHandler) if self._notification_handler_matches(candidate, type(notification))]
        if handlers is None or len(handlers) < 1:
            return
        await asyncio.gather(*(handler.handle_async(notification) for handler in handlers))

    def _request_handler_matches(self, candidate, request_type) -> bool:
        expected_request_type = request_type.__orig_class__ if hasattr(request_type, "__orig_class__") else request_type
        handler_type = TypeExtensions.get_generic_implementation(candidate, RequestHandler)
        handled_request_type = handler_type.__args__[0]
        if type(handled_request_type) == type(expected_request_type):
            matches = handled_request_type == expected_request_type
            return matches
        else:
            return handled_request_type == type(expected_request_type)

    def _notification_handler_matches(self, candidate, request_type) -> bool:
        candidate_type = type(candidate)
        handler_type = next(base for base in candidate_type.__orig_bases__ if (issubclass(base.__origin__, NotificationHandler) if hasattr(base, '__origin__') else issubclass(base, NotificationHandler)))
        handled_notification_type = handler_type.__args__[0]
        if isinstance(handled_notification_type, UnionType):
            return any(issubclass(t, request_type) for t in handled_notification_type.__args__)
        else:
            return issubclass(handled_notification_type.__origin__, request_type) if hasattr(handled_notification_type, '__origin__') else issubclass(handled_notification_type, request_type)

    def configure(app: ApplicationBuilderBase, modules: List[str] = list[str]()) -> ApplicationBuilderBase:
        ''' Registers and configures mediation-related services (command/query/notification handlers) to the specified service collection.

            Args:
                services (ServiceCollection): the service collection to configure
                modules (List[str]): a list containing the names of the modules to scan for mediation services to register
        '''
        for module in [ModuleLoader.load(module_name) for module_name in modules]:
            for command_handler_type in TypeFinder.get_types(module, lambda cls: inspect.isclass(cls) and (not hasattr(cls, "__parameters__") or len(cls.__parameters__) < 1) and issubclass(cls, CommandHandler) and cls != CommandHandler, include_sub_modules=True):
                app.services.add_transient(RequestHandler, command_handler_type)
            for queryhandler_type in TypeFinder.get_types(module, lambda cls: inspect.isclass(cls) and not hasattr(cls, "__parameters__") and issubclass(cls, QueryHandler) and cls != QueryHandler, include_sub_modules=True):
                app.services.add_transient(RequestHandler, queryhandler_type)
            for domain_event_handler_type in TypeFinder.get_types(module, lambda cls: inspect.isclass(cls) and issubclass(cls, DomainEventHandler) and cls != DomainEventHandler, include_sub_modules=True):
                app.services.add_transient(NotificationHandler, domain_event_handler_type)
            for integration_event_handler_type in TypeFinder.get_types(module, lambda cls: inspect.isclass(cls) and issubclass(cls, IntegrationEventHandler) and cls != IntegrationEventHandler, include_sub_packages=True):
                app.services.add_transient(NotificationHandler, integration_event_handler_type)
        app.services.add_singleton(Mediator)
        return app
