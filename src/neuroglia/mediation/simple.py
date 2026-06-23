"""
Simplified CQRS patterns for basic applications.

This module provides simplified base classes and helper methods for applications
that need basic CQRS functionality without complex event sourcing or cloud events.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, Optional, TypeVar

from neuroglia.core.operation_result import OperationResult
from neuroglia.dependency_injection.service_provider import ServiceCollection

if TYPE_CHECKING:
    pass


TResult = TypeVar("TResult")
TCommand = TypeVar("TCommand")
TQuery = TypeVar("TQuery")


class SimpleCommandHandler(Generic[TCommand, TResult], ABC):
    """
    Simplified command handler abstraction for basic CQRS scenarios without complex infrastructure.

    This abstraction provides sensible defaults and convenience methods for building
    command handlers without requiring extensive dependency injection setup, making it
    ideal for smaller applications or rapid prototyping.

    Type Parameters:
        TCommand: The command type this handler processes
        TResult: The result type returned (typically OperationResult)

    Features:
        - Built-in response helper methods (ok, created, bad_request, etc.)
        - Simplified error handling patterns
        - Minimal boilerplate for common scenarios

    Examples:
        ```python
        @dataclass
        class CreateUserCommand:
            name: str
            email: str

        class CreateUserHandler(SimpleCommandHandler[CreateUserCommand, OperationResult[UserDto]]):
            def __init__(self, user_repository: UserRepository):
                self.user_repository = user_repository

            async def handle_async(self, command: CreateUserCommand) -> OperationResult[UserDto]:
                # Validate
                if not command.email:
                    return self.bad_request("Email is required")

                if await self.user_repository.exists_by_email(command.email):
                    return self.conflict("User with this email already exists")

                # Business logic
                user = User.create(command.name, command.email)
                await self.user_repository.save_async(user)

                # Return success
                user_dto = UserDto.from_entity(user)
                return self.created(user_dto)
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Getting Started: https://bvandewe.github.io/pyneuro/getting-started/
    """

    @abstractmethod
    async def handle_async(self, command: TCommand) -> TResult:
        """Handle the command and return the result."""
        raise NotImplementedError()

    # Success response methods (2xx)

    def ok(self, data=None) -> "OperationResult":
        """Create a successful operation result (HTTP 200 OK)."""
        result: OperationResult = OperationResult("OK", 200)
        result.data = data
        return result

    def created(self, data=None) -> "OperationResult":
        """Create a successful creation result (HTTP 201 Created)."""
        result: OperationResult = OperationResult("Created", 201)
        result.data = data
        return result

    def accepted(self, data=None) -> "OperationResult":
        """Create an accepted result for async operations (HTTP 202 Accepted)."""
        result: OperationResult = OperationResult("Accepted", 202)
        result.data = data
        return result

    def no_content(self) -> "OperationResult":
        """Create a successful no content result (HTTP 204 No Content)."""
        result: OperationResult = OperationResult("No Content", 204)
        result.data = None
        return result

    # Client error response methods (4xx)

    def bad_request(self, message: str) -> "OperationResult":
        """Create a bad request error result (HTTP 400 Bad Request)."""
        result: OperationResult = OperationResult(
            "Bad Request",
            400,
            message,
            "https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Bad%20Request",
        )
        result.data = None
        return result

    def unauthorized(self, message: str = "Authentication required") -> "OperationResult":
        """Create an unauthorized error result (HTTP 401 Unauthorized)."""
        result: OperationResult = OperationResult(
            "Unauthorized",
            401,
            message,
            "https://www.w3.org/Protocols/HTTP/HTRESP.html",
        )
        result.data = None
        return result

    def forbidden(self, message: str = "Access denied") -> "OperationResult":
        """Create a forbidden error result (HTTP 403 Forbidden)."""
        result: OperationResult = OperationResult(
            "Forbidden",
            403,
            message,
            "https://www.w3.org/Protocols/HTTP/HTRESP.html",
        )
        result.data = None
        return result

    def not_found(self, message: str = "Resource not found") -> "OperationResult":
        """Create a not found error result (HTTP 404 Not Found)."""
        result: OperationResult = OperationResult(
            "Not Found",
            404,
            message,
            "https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Not%20found%20404",
        )
        result.data = None
        return result

    def conflict(self, message: str) -> "OperationResult":
        """Create a conflict error result (HTTP 409 Conflict)."""
        result: OperationResult = OperationResult("Conflict", 409, message, "https://www.w3.org/Protocols/HTTP/HTRESP.html")
        result.data = None
        return result

    def unprocessable_entity(self, message: str) -> "OperationResult":
        """Create an unprocessable entity error result (HTTP 422 Unprocessable Entity)."""
        result: OperationResult = OperationResult(
            "Unprocessable Entity",
            422,
            message,
            "https://www.w3.org/Protocols/HTTP/HTRESP.html",
        )
        result.data = None
        return result

    # Server error response methods (5xx)

    def internal_error(self, message: str) -> "OperationResult":
        """Create an internal server error result (HTTP 500 Internal Server Error)."""
        result: OperationResult = OperationResult(
            "Internal Server Error",
            500,
            message,
            "https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Internal%20Server%20Error",
        )
        result.data = None
        return result

    def service_unavailable(self, message: str = "Service temporarily unavailable") -> "OperationResult":
        """Create a service unavailable error result (HTTP 503 Service Unavailable)."""
        result: OperationResult = OperationResult(
            "Service Unavailable",
            503,
            message,
            "https://www.w3.org/Protocols/HTTP/HTRESP.html",
        )
        result.data = None
        return result


class SimpleQueryHandler(Generic[TQuery, TResult], ABC):
    """
    Simplified query handler abstraction for basic CQRS read operations.

    This abstraction provides streamlined patterns for read operations without requiring
    complex infrastructure setup, perfect for applications that need clean separation
    of read and write operations without event sourcing complexity.

    Type Parameters:
        TQuery: The query type this handler processes
        TResult: The data type returned by the query

    Features:
        - Minimal boilerplate for query operations
        - Direct data return without OperationResult wrapping
        - Simple error handling patterns
        - Easy integration with repositories

    Examples:
        ```python
        @dataclass
        class GetUserByIdQuery:
            user_id: str

        class GetUserByIdHandler(SimpleQueryHandler[GetUserByIdQuery, Optional[UserDto]]):
            def __init__(self, user_repository: UserRepository):
                self.user_repository = user_repository

            async def handle_async(self, query: GetUserByIdQuery) -> Optional[UserDto]:
                user = await self.user_repository.get_by_id_async(query.user_id)
                if not user:
                    return None

                return UserDto(
                    id=user.id,
                    name=user.name,
                    email=user.email,
                    created_at=user.created_at
                )

        @dataclass
        class SearchUsersQuery:
            search_term: str
            limit: int = 20

        class SearchUsersHandler(SimpleQueryHandler[SearchUsersQuery, List[UserDto]]):
            async def handle_async(self, query: SearchUsersQuery) -> List[UserDto]:
                users = await self.user_repository.search_async(
                    query.search_term,
                    limit=query.limit
                )
                return [UserDto.from_entity(u) for u in users]
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Getting Started: https://bvandewe.github.io/pyneuro/getting-started/
    """

    @abstractmethod
    async def handle_async(self, query: TQuery) -> TResult:
        """Handle the query and return the result."""
        raise NotImplementedError()


# Helper functions for simple service registration


def add_simple_mediator(services: ServiceCollection) -> ServiceCollection:
    """
    Add basic mediator setup without complex cloud events infrastructure.

    This is a simplified version that just registers the core mediator
    without event sourcing or cloud events dependencies.

    Usage:
        services = ServiceCollection()
        add_simple_mediator(services)

        # Register your handlers
        register_simple_handler(services, CreateUserHandler)
        register_simple_handler(services, GetUserByIdHandler)

        provider = services.build()
    """
    from neuroglia.mediation.mediator import Mediator

    # Register core mediator the same way tests do it
    services.add_singleton(Mediator, Mediator)
    return services


def register_simple_handler(services: ServiceCollection, handler_class):
    """
    Convenience method to register command or query handlers.

    Usage:
        register_simple_handler(services, CreateUserHandler)
        register_simple_handler(services, GetUserByIdHandler)
    """
    # Import locally to avoid circular dependencies
    from neuroglia.mediation.mediator import RequestHandler

    services.add_scoped(RequestHandler, handler_class)
    return services


def register_simple_handlers(services: ServiceCollection, *handler_classes):
    """
    Convenience method to register multiple handlers at once.

    Usage:
        register_simple_handlers(services, CreateUserHandler, UpdateUserHandler, GetUserByIdHandler)
    """
    for handler_class in handler_classes:
        register_simple_handler(services, handler_class)
    return services


def create_simple_app(*handler_classes, repositories=None):
    """
    One-line app creation for simple CQRS applications.

    Usage:
        # Basic usage
        provider = create_simple_app(CreateTaskHandler, GetTaskHandler)

        # With repositories
        provider = create_simple_app(
            CreateTaskHandler, GetTaskHandler,
            repositories=[InMemoryRepository[Task]]
        )
    """
    services = ServiceCollection()

    # Add mediator
    add_simple_mediator(services)

    # Register repositories if provided
    if repositories:
        for repo_class in repositories:
            services.add_singleton(repo_class)

    # Register handlers
    register_simple_handlers(services, *handler_classes)

    return services.build()


# Common patterns for simple applications


class InMemoryRepository(Generic[TResult], ABC):
    """
    Simple in-memory repository for testing and prototyping.

    This provides a basic storage implementation without requiring database setup.
    """

    def __init__(self):
        self._storage = {}

    async def save_async(self, entity) -> None:
        """Save an entity to memory storage."""
        self._storage[entity.id] = entity

    async def get_by_id_async(self, entity_id: str) -> Optional[TResult]:
        """Get an entity by ID from memory storage."""
        return self._storage.get(entity_id)

    async def get_all_async(self) -> list[TResult]:
        """Get all entities from memory storage."""
        return list(self._storage.values())

    async def delete_async(self, entity_id: str) -> bool:
        """Delete an entity from memory storage."""
        if entity_id in self._storage:
            del self._storage[entity_id]
            return True
        return False


@dataclass
class SimpleApplicationSettings:
    """
    Minimal settings class for simple applications that don't need cloud events.

    This can be used instead of the full ApplicationSettings when you only need
    basic configuration without event sourcing complexity.
    """

    app_name: str = "MyApp"
    debug: bool = False
    log_level: str = "INFO"

    # Database settings (optional)
    database_url: Optional[str] = None
    database_name: str = "myapp"

    # API settings
    api_title: str = "My Application API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api"


# Example usage documentation

USAGE_DOCS = """
SIMPLE CQRS EXAMPLE:

```python
from dataclasses import dataclass
from typing import Optional
import uuid
from neuroglia.mediation.simple import (
    SimpleCommandHandler,
    SimpleQueryHandler,
    add_simple_mediator,
    register_simple_handler,
    InMemoryRepository
)
from neuroglia.mediation.mediator import Command, Query, Mediator
from neuroglia.core.operation_result import OperationResult
from neuroglia.dependency_injection.service_provider import ServiceCollection

# Define your data models
@dataclass
class User:
    id: str
    name: str
    email: str

@dataclass
class UserDto:
    id: str
    name: str
    email: str

# Define commands and queries
@dataclass
class CreateUserCommand(Command[OperationResult[UserDto]]):
    name: str
    email: str

@dataclass
class GetUserByIdQuery(Query[Optional[UserDto]]):
    user_id: str

# Create simple handlers that inherit from framework handlers
from neuroglia.mediation.mediator import CommandHandler, QueryHandler

class CreateUserHandler(CommandHandler[CreateUserCommand, OperationResult[UserDto]]):
    def __init__(self, user_repository: InMemoryRepository[User]):
        self.user_repository = user_repository

    async def handle_async(self, command: CreateUserCommand) -> OperationResult[UserDto]:
        if not command.email:
            return OperationResult.error("Bad Request", 400, "Email is required")

        user = User(str(uuid.uuid4()), command.name, command.email)
        await self.user_repository.save_async(user)

        user_dto = UserDto(user.id, user.name, user.email)
        return OperationResult.success(user_dto)

class GetUserByIdHandler(QueryHandler[GetUserByIdQuery, Optional[UserDto]]):
    def __init__(self, user_repository: InMemoryRepository[User]):
        self.user_repository = user_repository

    async def handle_async(self, query: GetUserByIdQuery) -> Optional[UserDto]:
        user = await self.user_repository.get_by_id_async(query.user_id)
        if not user:
            return None

        return UserDto(user.id, user.name, user.email)

# Setup your application
def create_app():
    # Create service collection
    services = ServiceCollection()

    # Add simple mediator (no cloud events)
    add_simple_mediator(services)

    # Register repository
    services.add_singleton(InMemoryRepository[User])

    # Register handlers
    register_simple_handler(services, CreateUserHandler)
    register_simple_handler(services, GetUserByIdHandler)

    # Build provider
    provider = services.build()

    return provider

# Use in your application
async def main():
    provider = create_app()
    mediator = provider.get_service(Mediator)

    # Create a user
    create_command = CreateUserCommand("John Doe", "john@example.com")
    result = await mediator.execute_async(create_command)

    if result.is_success:
        print(f"Created user: {result.data.name}")

        # Get the user
        get_query = GetUserByIdQuery(result.data.id)
        user = await mediator.execute_async(get_query)
        print(f"Retrieved user: {user.name if user else 'Not found'}")
```

This approach gives you:
1. Simple CQRS patterns without complex infrastructure
2. Easy testing with in-memory repositories
3. Clear separation of concerns
4. Minimal configuration overhead
5. Easy to understand and extend
"""
