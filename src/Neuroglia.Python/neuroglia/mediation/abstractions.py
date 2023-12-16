from abc import ABC
from typing import Generic, TypeVar

from neuroglia.core.operation_result import OperationResult

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
    ''' Represents a service used to handle CQRS requests '''
    
    def handle(request : TRequest) -> TResult:
        ''' Handles the specified request '''
        pass

TCommand = TypeVar('TCommand', bound=Command)
''' Represents the type of CQRS command to handle '''

class CommandHandler(Generic[TCommand, TResult], RequestHandler[TCommand, TResult], ABC):
    ''' Represents a service used to handle commands '''
    
    pass
    
TQuery = TypeVar('TQuery', bound=Query)

class QueryHandler(Generic[TQuery, TResult], RequestHandler[TQuery, TResult], ABC):
    ''' Represents a service used to handle queries '''
    
    pass

class Mediator:
    ''' Represents a service used to mediate calls '''
    
    def execute(request: Request) -> OperationResult:
        ''' Executes the specified request '''
        pass
    
    def publish(notification : object):
        ''' Publishes the specified notification '''
        pass