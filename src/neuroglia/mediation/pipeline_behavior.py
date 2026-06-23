from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar

from neuroglia.core import OperationResult

TRequest = TypeVar("TRequest")
TResult = TypeVar("TResult")


class PipelineBehavior(Generic[TRequest, TResult], ABC):
    """
    Represents the abstraction for pipeline behaviors in the mediation pipeline.

    Pipeline behaviors provide a way to implement cross-cutting concerns such as:
    - Validation
    - Logging
    - Caching
    - Transaction management
    - Domain event dispatching
    - Performance monitoring
    - Authorization

    Behaviors execute in the order they are registered and form a chain of responsibility
    around the actual command/query handler execution.

    Type Parameters:
        TRequest: The type of request this behavior can handle
        TResult: The type of result this behavior returns

    Examples:
        ```python
        class ValidationBehavior(PipelineBehavior[Command, OperationResult]):
            async def handle_async(self, request: Command, next_handler: Callable):
                # Pre-processing: validation
                if not self._is_valid(request):
                    return OperationResult.validation_error("Invalid request")

                # Continue pipeline
                result = await next_handler()

                # Post-processing: logging
                self._log_result(request, result)
                return result

        class CachingBehavior(PipelineBehavior[Query, OperationResult]):
            async def handle_async(self, request: Query, next_handler: Callable):
                # Check cache first
                cached = await self._cache.get(request)
                if cached:
                    return cached

                # Execute query
                result = await next_handler()

                # Cache result
                await self._cache.set(request, result)
                return result
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Pipeline Pattern: https://bvandewe.github.io/pyneuro/patterns/pipeline/
        - Domain Event Dispatching: https://bvandewe.github.io/pyneuro/patterns/domain-events/
    """

    @abstractmethod
    async def handle_async(self, request: TRequest, next_handler: Callable[[], Awaitable[TResult]]) -> TResult:
        """
        Handles the request and delegates to the next behavior or handler in the pipeline.

        This method implements the chain of responsibility pattern, where each behavior
        can perform pre-processing, call the next handler, and perform post-processing.

        Args:
            request: The request being processed through the pipeline
            next_handler: Async callable to invoke the next behavior/handler in the chain

        Returns:
            The result after processing by this behavior and the rest of the pipeline

        Examples:
            ```python
            async def handle_async(self, request: CreateUserCommand, next_handler):
                # Pre-processing
                await self._validate_request(request)

                # Continue pipeline execution
                result = await next_handler()

                # Post-processing
                await self._audit_result(request, result)

                return result
            ```
        """
        raise NotImplementedError()


class BasePipelineBehavior(PipelineBehavior[Any, Any]):
    """
    Base implementation of PipelineBehavior that provides common functionality.

    This class can be used as a base for simple behaviors that don't need
    generic type constraints and want default implementations for common patterns.
    """

    async def handle_async(self, request: Any, next_handler: Callable[[], Awaitable[Any]]) -> Any:
        """Default implementation that simply calls the next handler."""
        return await next_handler()


# Type aliases for common pipeline behavior patterns
ValidationBehavior = PipelineBehavior[Any, OperationResult]
"""Type alias for validation behaviors that return OperationResult"""

LoggingBehavior = PipelineBehavior[Any, Any]
"""Type alias for logging behaviors that can handle any request/result type"""

CachingBehavior = PipelineBehavior[Any, OperationResult]
"""Type alias for caching behaviors that return OperationResult"""

TransactionBehavior = PipelineBehavior[Any, OperationResult]
"""Type alias for transaction behaviors that return OperationResult"""
