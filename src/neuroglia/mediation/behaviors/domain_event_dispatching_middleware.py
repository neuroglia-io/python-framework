"""Deprecated DomainEventDispatchingMiddleware placeholder."""

import logging
import warnings
from collections.abc import Awaitable, Callable
from typing import Any

from neuroglia.core import OperationResult
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.mediation import Command
from neuroglia.mediation.pipeline_behavior import PipelineBehavior

log = logging.getLogger(__name__)


class DomainEventDispatchingMiddleware(PipelineBehavior[Any, Any]):
    """Deprecated placeholder for the former UnitOfWork-based middleware."""

    def __init__(self, *args, **kwargs) -> None:  # pragma: no cover - deprecated path
        warnings.warn(
            "DomainEventDispatchingMiddleware is deprecated and no longer performs domain event dispatching. " "Remove this middleware and register DomainEventCloudEventBehavior instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        log.warning("DomainEventDispatchingMiddleware has been deprecated. It now acts as a no-op. " "Please remove it from your pipeline configuration and adopt DomainEventCloudEventBehavior.")

    async def handle_async(self, request: Any, next_handler: Callable[[], Awaitable[Any]]) -> Any:  # pragma: no cover - deprecated path
        """No-op handler kept for backward compatibility."""
        return await next_handler()

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> ApplicationBuilderBase:  # pragma: no cover - deprecated path
        """Deprecated configuration helper retained for compatibility."""
        warnings.warn(
            "DomainEventDispatchingMiddleware.configure is deprecated. " "No middleware is registered. Use DomainEventCloudEventBehavior.configure instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        log.warning("DomainEventDispatchingMiddleware.configure() no longer registers any services. " "Ensure DomainEventCloudEventBehavior is configured explicitly.")
        return builder


class TransactionBehavior(PipelineBehavior[Command, OperationResult]):
    """
    Pipeline behavior that provides transaction management around command execution.

    This behavior can be used to wrap command execution in database transactions,
    ensuring atomicity of operations and proper rollback on failures.

    Note: This is a placeholder implementation. Actual transaction management
    would depend on your specific database and ORM implementation.

    Examples:
        ```python
        # Register before DomainEventDispatchingMiddleware
        services.add_scoped(PipelineBehavior, TransactionBehavior)
        services.add_scoped(PipelineBehavior, DomainEventDispatchingMiddleware)

        # Transaction flow:
        # 1. Begin transaction
        # 2. Execute command
        # 3. Commit transaction (on success)
        # 4. Dispatch domain events (after commit)
        # 5. Rollback transaction (on failure)
        ```
    """

    async def handle_async(self, request: Command, next_handler: Callable[[], Awaitable[OperationResult]]) -> OperationResult:
        """Executes command within a transaction context."""
        command_name = type(request).__name__
        log.debug(f"Beginning transaction for command {command_name}")

        try:
            # TODO: Begin database transaction here
            # await self.db_context.begin_transaction()

            result = await next_handler()

            if result.is_success:
                # TODO: Commit transaction on success
                # await self.db_context.commit_transaction()
                log.debug(f"Transaction committed for command {command_name}")
            else:
                # TODO: Rollback transaction on business logic failure
                # await self.db_context.rollback_transaction()
                log.debug(f"Transaction rolled back for command {command_name} (business failure)")

            return result

        except Exception as e:
            # TODO: Rollback transaction on exception
            # await self.db_context.rollback_transaction()
            log.error(f"Transaction rolled back for command {command_name} (exception): {e}")
            raise
