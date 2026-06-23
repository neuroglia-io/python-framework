import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from pathlib import Path
from types import UnionType
from typing import Any, ClassVar, Generic, Optional, TypeVar, cast

from neuroglia.core import ModuleLoader, OperationResult, TypeExtensions, TypeFinder
from neuroglia.data.abstractions import DomainEvent
from neuroglia.dependency_injection.service_provider import ServiceProviderBase
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.integration.models import IntegrationEvent
from neuroglia.mediation.pipeline_behavior import PipelineBehavior

log = logging.getLogger(__name__)


TResult = TypeVar("TResult", bound=OperationResult)
""" Represents the expected type of result returned by the operation, in case of success """


class Request(Generic[TResult], ABC):
    """
    Represents the abstraction for all CQRS requests in the Command Query Responsibility Segregation pattern.

    This abstraction forms the foundation for both commands (write operations) and queries (read operations),
    enabling a unified approach to request handling through the mediator pattern.

    Type Parameters:
        TResult: The type of result expected from processing this request

    Examples:
        ```python
        # Custom request types inherit from this abstraction
        @dataclass
        class CustomRequest(Request[OperationResult[UserDto]]):
            user_id: str
            action_type: str

        # Processing through mediator
        request = CustomRequest(user_id="123", action_type="activate")
        result = await mediator.execute_async(request)
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Mediator Pattern: https://bvandewe.github.io/pyneuro/patterns/
    """


class Command(Generic[TResult], Request[TResult], ABC):
    """
    Represents the abstraction for CQRS commands that perform write operations and modify system state.

    Commands encapsulate business intentions and contain all necessary data to perform state-changing
    operations. Each command should have exactly one handler and represent a single business use case.

    Type Parameters:
        TResult: The type of result returned after command execution (typically OperationResult[T])

    Type Hint Patterns & Examples
    ------------------------------

    **Pattern 1: Command returning a DTO (most common)**
    ```python
    from dataclasses import dataclass
    from neuroglia.mediation import Command, CommandHandler
    from neuroglia.core import OperationResult

    @dataclass
    class CreateUserCommand(Command[OperationResult[UserDto]]):
        \"\"\"Command that returns a single user DTO.\"\"\"
        email: str
        name: str
        password: str

    class CreateUserHandler(CommandHandler[CreateUserCommand, OperationResult[UserDto]]):
        async def handle_async(self, command: CreateUserCommand) -> OperationResult[UserDto]:
            # IDE knows return type is OperationResult[UserDto]
            return self.created(user_dto)
    ```

    **Pattern 2: Command with no return data (delete, void operations)**
    ```python
    @dataclass
    class DeleteUserCommand(Command[OperationResult[None]]):
        \"\"\"Command that returns no data, only success/failure status.\"\"\"
        user_id: str

    class DeleteUserHandler(CommandHandler[DeleteUserCommand, OperationResult[None]]):
        async def handle_async(self, command: DeleteUserCommand) -> OperationResult[None]:
            await self.repository.delete_async(command.user_id)
            return self.no_content()  # 204 No Content
    ```

    **Pattern 3: Command returning a boolean**
    ```python
    @dataclass
    class ActivateUserCommand(Command[OperationResult[bool]]):
        \"\"\"Command that returns boolean success indicator.\"\"\"
        user_id: str

    class ActivateUserHandler(CommandHandler[ActivateUserCommand, OperationResult[bool]]):
        async def handle_async(self, command: ActivateUserCommand) -> OperationResult[bool]:
            success = await self.user_service.activate(command.user_id)
            return self.ok(success)
    ```

    **Pattern 4: Command returning a list of DTOs**
    ```python
    @dataclass
    class BulkCreateUsersCommand(Command[OperationResult[List[UserDto]]]):
        \"\"\"Command that creates multiple users and returns list of created DTOs.\"\"\"
        users: List[CreateUserDto]

    class BulkCreateUsersHandler(CommandHandler[BulkCreateUsersCommand, OperationResult[List[UserDto]]]):
        async def handle_async(self, command: BulkCreateUsersCommand) -> OperationResult[List[UserDto]]:
            created_users = await self.user_service.bulk_create(command.users)
            return self.created([UserDto.from_entity(u) for u in created_users])
    ```

    **Pattern 5: Command returning a primitive type (ID, count, etc.)**
    ```python
    @dataclass
    class CreateOrderCommand(Command[OperationResult[str]]):
        \"\"\"Command that returns the created order ID.\"\"\"
        customer_id: str
        items: List[OrderItemDto]

    class CreateOrderHandler(CommandHandler[CreateOrderCommand, OperationResult[str]]):
        async def handle_async(self, command: CreateOrderCommand) -> OperationResult[str]:
            order = await self.order_service.create(command)
            return self.created(order.id)  # Returns string ID
    ```

    **Pattern 6: Command with optional result (async job queued)**
    ```python
    @dataclass
    class ProcessBulkImportCommand(Command[OperationResult[Optional[str]]]):
        \"\"\"Command that queues async job and returns optional job ID.\"\"\"
        file_path: str

    class ProcessBulkImportHandler(CommandHandler[ProcessBulkImportCommand, OperationResult[Optional[str]]]):
        async def handle_async(self, command: ProcessBulkImportCommand) -> OperationResult[Optional[str]]:
            job_id = await self.task_scheduler.enqueue(self.import_job, command.file_path)
            return self.accepted(job_id)  # 202 Accepted
    ```

    **Pattern 7: Command returning complex nested types**
    ```python
    @dataclass
    class GenerateReportCommand(Command[OperationResult[Dict[str, Any]]]):
        \"\"\"Command that returns a report as dictionary.\"\"\"
        report_type: str
        start_date: datetime
        end_date: datetime

    class GenerateReportHandler(CommandHandler[GenerateReportCommand, OperationResult[Dict[str, Any]]]):
        async def handle_async(self, command: GenerateReportCommand) -> OperationResult[Dict[str, Any]]:
            report_data = await self.report_service.generate(command)
            return self.ok(report_data)
    ```

    Basic Examples:
        ```python
        @dataclass
        class CreateUserCommand(Command[OperationResult[UserDto]]):
            first_name: str
            last_name: str
            email: str

        @dataclass
        class UpdateUserCommand(Command[OperationResult[UserDto]]):
            user_id: str
            first_name: Optional[str] = None
            last_name: Optional[str] = None

        # Command execution
        command = CreateUserCommand("John", "Doe", "john@example.com")
        result = await mediator.execute_async(command)
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Command Pattern: https://bvandewe.github.io/pyneuro/patterns/
        - CommandHandler: Handler class for processing commands
    """


class Query(Generic[TResult], Request[TResult], ABC):
    """
    Represents the abstraction for CQRS queries that perform read operations without side effects.

    Queries encapsulate data retrieval intentions and should never modify system state. They can
    have multiple handlers for different projections or optimized read models of the same data.

    Type Parameters:
        TResult: The type of data returned by the query (typically OperationResult[T] or plain T)

    Type Hint Patterns & Examples
    ------------------------------

    **Pattern 1: Query returning a single optional DTO (most common for get-by-id)**
    ```python
    from dataclasses import dataclass
    from typing import Optional
    from neuroglia.mediation import Query, QueryHandler
    from neuroglia.core import OperationResult

    @dataclass
    class GetUserByIdQuery(Query[OperationResult[Optional[UserDto]]]):
        \"\"\"Query that may or may not find a user.\"\"\"
        user_id: str

    class GetUserByIdHandler(QueryHandler[GetUserByIdQuery, OperationResult[Optional[UserDto]]]):
        async def handle_async(self, query: GetUserByIdQuery) -> OperationResult[Optional[UserDto]]:
            user = await self.repository.get_by_id_async(query.user_id)
            if not user:
                return self.not_found(User, query.user_id)
            return self.ok(UserDto.from_entity(user))
    ```

    **Pattern 2: Query returning a guaranteed DTO (with error handling)**
    ```python
    @dataclass
    class GetUserByIdQuery(Query[OperationResult[UserDto]]):
        \"\"\"Query that returns user or error (no Optional).\"\"\"
        user_id: str

    class GetUserByIdHandler(QueryHandler[GetUserByIdQuery, OperationResult[UserDto]]):
        async def handle_async(self, query: GetUserByIdQuery) -> OperationResult[UserDto]:
            user = await self.repository.get_by_id_async(query.user_id)
            if not user:
                return self.not_found(User, query.user_id)  # Returns error
            return self.ok(UserDto.from_entity(user))  # Returns data
    ```

    **Pattern 3: Query returning a list of DTOs (with pagination)**
    ```python
    @dataclass
    class GetUsersQuery(Query[OperationResult[List[UserDto]]]):
        \"\"\"Query that returns paginated list of users.\"\"\"
        page: int = 1
        page_size: int = 20
        active_only: bool = True

    class GetUsersHandler(QueryHandler[GetUsersQuery, OperationResult[List[UserDto]]]):
        async def handle_async(self, query: GetUsersQuery) -> OperationResult[List[UserDto]]:
            users = await self.repository.list_async(
                skip=(query.page - 1) * query.page_size,
                limit=query.page_size
            )
            return self.ok([UserDto.from_entity(u) for u in users])
    ```

    **Pattern 4: Query returning a primitive type (count, sum, etc.)**
    ```python
    @dataclass
    class GetUserCountQuery(Query[OperationResult[int]]):
        \"\"\"Query that returns count of users.\"\"\"
        active_only: bool = True

    class GetUserCountHandler(QueryHandler[GetUserCountQuery, OperationResult[int]]):
        async def handle_async(self, query: GetUserCountQuery) -> OperationResult[int]:
            count = await self.repository.count_async(active=query.active_only)
            return self.ok(count)
    ```

    **Pattern 5: Query returning complex types (tuples, dicts)**
    ```python
    @dataclass
    class GetUserStatisticsQuery(Query[OperationResult[Dict[str, int]]]):
        \"\"\"Query that returns statistics as dictionary.\"\"\"
        start_date: datetime
        end_date: datetime

    class GetUserStatisticsHandler(QueryHandler[GetUserStatisticsQuery, OperationResult[Dict[str, int]]]):
        async def handle_async(self, query: GetUserStatisticsQuery) -> OperationResult[Dict[str, int]]:
            stats = await self.analytics_service.calculate_stats(query.start_date, query.end_date)
            return self.ok(stats)  # Returns {"total": 100, "active": 75, ...}
    ```

    **Pattern 6: Query with search/filter criteria**
    ```python
    @dataclass
    class SearchUsersQuery(Query[OperationResult[List[UserDto]]]):
        \"\"\"Query with multiple search criteria.\"\"\"
        search_term: Optional[str] = None
        role: Optional[str] = None
        min_age: Optional[int] = None
        max_age: Optional[int] = None
        page: int = 1
        page_size: int = 20

    class SearchUsersHandler(QueryHandler[SearchUsersQuery, OperationResult[List[UserDto]]]):
        async def handle_async(self, query: SearchUsersQuery) -> OperationResult[List[UserDto]]:
            users = await self.repository.search_async(
                search_term=query.search_term,
                role=query.role,
                age_range=(query.min_age, query.max_age)
            )
            return self.ok([UserDto.from_entity(u) for u in users])
    ```

    **Pattern 7: Query without OperationResult (simplified for read-only)**
    ```python
    @dataclass
    class GetUserByIdQuery(Query[Optional[UserDto]]):
        \"\"\"Simplified query returning plain optional DTO (no error handling).\"\"\"
        user_id: str

    class GetUserByIdHandler(QueryHandler[GetUserByIdQuery, Optional[UserDto]]):
        async def handle_async(self, query: GetUserByIdQuery) -> Optional[UserDto]:
            user = await self.repository.get_by_id_async(query.user_id)
            return UserDto.from_entity(user) if user else None
    ```

    **Pattern 8: Query returning paginated results with metadata**
    ```python
    @dataclass
    class PagedResult(Generic[T]):
        items: List[T]
        total_count: int
        page: int
        page_size: int

    @dataclass
    class GetUsersPagedQuery(Query[OperationResult[PagedResult[UserDto]]]):
        \"\"\"Query returning paginated results with metadata.\"\"\"
        page: int = 1
        page_size: int = 20

    class GetUsersPagedHandler(QueryHandler[GetUsersPagedQuery, OperationResult[PagedResult[UserDto]]]):
        async def handle_async(self, query: GetUsersPagedQuery) -> OperationResult[PagedResult[UserDto]]:
            users, total = await self.repository.get_paged_async(query.page, query.page_size)
            result = PagedResult(
                items=[UserDto.from_entity(u) for u in users],
                total_count=total,
                page=query.page,
                page_size=query.page_size
            )
            return self.ok(result)
    ```

    Basic Examples:
        ```python
        @dataclass
        class GetUserByIdQuery(Query[Optional[UserDto]]):
            user_id: str

        @dataclass
        class GetUsersQuery(Query[List[UserDto]]):
            page: int = 1
            page_size: int = 20
            active_only: bool = True

        @dataclass
        class GetUserCountQuery(Query[int]):
            active_only: bool = True

        # Query execution
        query = GetUserByIdQuery(user_id="123")
        user = await mediator.execute_async(query)
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Query Pattern: https://bvandewe.github.io/pyneuro/patterns/
        - QueryHandler: Handler class for processing queries
    """


TRequest = TypeVar("TRequest", bound=Request)
""" Represents the type of CQRS request to handle """


class RequestHandler(Generic[TRequest, TResult], ABC):
    """
    Represents the abstraction for services that handle specific types of CQRS requests.

    Request handlers encapsulate the business logic for processing commands and queries,
    providing separation of concerns and single responsibility. They are automatically
    discovered and registered through the dependency injection container.

    This base class provides 12 helper methods for creating standardized OperationResult
    responses with appropriate HTTP status codes. These methods should be used instead of
    manually constructing OperationResult instances.

    Type Parameters:
        TRequest: The specific type of request this handler processes
        TResult: The type of result returned after processing (typically OperationResult[T])

    ╔══════════════════════════════════════════════════════════════════════════════════╗
    ║                          AVAILABLE HELPER METHODS                                ║
    ╠══════════════════════════════════════════════════════════════════════════════════╣
    ║  SUCCESS RESPONSES (2xx)                                                         ║
    ║  ✓ ok(data)                    → 200 OK           - Standard success response   ║
    ║  ✓ created(data)               → 201 Created      - Resource created            ║
    ║  ✓ accepted(data)              → 202 Accepted     - Async operation queued      ║
    ║  ✓ no_content()                → 204 No Content   - Success, no data returned   ║
    ║                                                                                  ║
    ║  CLIENT ERRORS (4xx)                                                             ║
    ║  ✗ bad_request(detail)         → 400 Bad Request  - Validation/input error     ║
    ║  ✗ unauthorized(detail)        → 401 Unauthorized - Authentication required    ║
    ║  ✗ forbidden(detail)           → 403 Forbidden    - Access denied               ║
    ║  ✗ not_found(type, key, name)  → 404 Not Found    - Resource doesn't exist     ║
    ║  ✗ conflict(message)           → 409 Conflict     - State conflict              ║
    ║  ✗ unprocessable_entity(detail)→ 422 Unprocessable- Semantic validation error  ║
    ║                                                                                  ║
    ║  SERVER ERRORS (5xx)                                                             ║
    ║  ✗ internal_server_error(det.) → 500 Internal     - Unexpected error            ║
    ║  ✗ service_unavailable(detail) → 503 Unavailable  - Service temporarily down    ║
    ╚══════════════════════════════════════════════════════════════════════════════════╝

    Quick Start Example:
        ```python
        class CreateUserHandler(CommandHandler[CreateUserCommand, OperationResult[UserDto]]):
            async def handle_async(self, command: CreateUserCommand) -> OperationResult[UserDto]:
                # Validation errors → 400 Bad Request
                if not command.email:
                    return self.bad_request("Email is required")

                # Authorization errors → 403 Forbidden
                if not self.has_permission(command.user_context):
                    return self.forbidden("Insufficient permissions to create users")

                # Resource conflicts → 409 Conflict
                if await self.user_repository.exists_by_email(command.email):
                    return self.conflict(f"User with email {command.email} already exists")

                # Business logic
                user = User.create(command.email, command.name)
                await self.user_repository.save_async(user)

                # Success → 201 Created
                return self.created(UserDto.from_entity(user))
        ```

    Common Usage Patterns:

        **Pattern 1: Query Handler (Read Operations)**
        ```python
        class GetUserByIdHandler(QueryHandler[GetUserByIdQuery, OperationResult[UserDto]]):
            async def handle_async(self, query: GetUserByIdQuery) -> OperationResult[UserDto]:
                user = await self.user_repository.get_by_id_async(query.user_id)

                if not user:
                    return self.not_found(User, query.user_id)  # 404

                return self.ok(UserDto.from_entity(user))  # 200
        ```

        **Pattern 2: Command Handler with Validation (Write Operations)**
        ```python
        class UpdateUserHandler(CommandHandler[UpdateUserCommand, OperationResult[UserDto]]):
            async def handle_async(self, command: UpdateUserCommand) -> OperationResult[UserDto]:
                # Input validation
                if not command.user_id:
                    return self.bad_request("User ID is required")  # 400

                # Check existence
                user = await self.user_repository.get_by_id_async(command.user_id)
                if not user:
                    return self.not_found(User, command.user_id)  # 404

                # Business logic
                user.update(command.name, command.email)
                await self.user_repository.save_async(user)

                return self.ok(UserDto.from_entity(user))  # 200
        ```

        **Pattern 3: Async Operations (Long-Running Tasks)**
        ```python
        class ProcessLargeOrderHandler(CommandHandler[ProcessLargeOrderCommand, OperationResult[str]]):
            async def handle_async(self, command: ProcessLargeOrderCommand) -> OperationResult[str]:
                # Queue background job
                job_id = await self.task_scheduler.enqueue(
                    self.process_order_background,
                    command.order_id
                )

                # Return accepted with job tracking info
                return self.accepted(f"Order processing job {job_id} queued")  # 202
        ```

        **Pattern 4: Delete Operations**
        ```python
        class DeleteUserHandler(CommandHandler[DeleteUserCommand, OperationResult[None]]):
            async def handle_async(self, command: DeleteUserCommand) -> OperationResult[None]:
                user = await self.user_repository.get_by_id_async(command.user_id)
                if not user:
                    return self.not_found(User, command.user_id)  # 404

                await self.user_repository.delete_async(command.user_id)

                return self.no_content()  # 204 (no data returned)
        ```

        **Pattern 5: Exception Handling**
        ```python
        class PlaceOrderHandler(CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]):
            async def handle_async(self, command: PlaceOrderCommand) -> OperationResult[OrderDto]:
                try:
                    order = await self.create_order(command)
                    return self.created(OrderDto.from_entity(order))  # 201

                except ValidationException as e:
                    return self.bad_request(str(e))  # 400

                except InsufficientStockException as e:
                    return self.conflict(str(e))  # 409

                except Exception as e:
                    log.error(f"Unexpected error: {e}")
                    return self.internal_server_error("Failed to process order")  # 500
        ```

    Helper Method Details:

        SUCCESS METHODS (2xx):
            • ok(data: Optional[Any] = None) → OperationResult[TData]
              Returns HTTP 200 OK with optional data payload.
              Use for: Successful queries, updates, standard operations.

            • created(data: Optional[Any] = None) → OperationResult[TData]
              Returns HTTP 201 Created with optional data payload.
              Use for: Successful resource creation (POST operations).

            • accepted(data: Optional[Any] = None) → OperationResult[TData]
              Returns HTTP 202 Accepted with optional data payload.
              Use for: Async operations queued for later processing.

            • no_content() → OperationResult[None]
              Returns HTTP 204 No Content with no data payload.
              Use for: Successful deletes, operations with no return value.

        CLIENT ERROR METHODS (4xx):
            • bad_request(detail: str) → OperationResult[None]
              Returns HTTP 400 Bad Request with error message.
              Use for: Validation errors, malformed input, business rule violations.

            • unauthorized(detail: str = "Authentication required") → OperationResult[None]
              Returns HTTP 401 Unauthorized with error message.
              Use for: Missing or invalid authentication credentials.

            • forbidden(detail: str = "Access denied") → OperationResult[None]
              Returns HTTP 403 Forbidden with error message.
              Use for: Valid authentication but insufficient permissions.

            • not_found(entity_type: Type, entity_key: Any, key_name: str = "id") → OperationResult[None]
              Returns HTTP 404 Not Found with formatted error message.
              Use for: Requested resource doesn't exist.
              Example: self.not_found(User, user_id) → "Failed to find User with id 'abc123'"

            • conflict(message: str) → OperationResult[None]
              Returns HTTP 409 Conflict with error message.
              Use for: State conflicts, duplicate resources, constraint violations.

            • unprocessable_entity(detail: str) → OperationResult[None]
              Returns HTTP 422 Unprocessable Entity with error message.
              Use for: Semantic validation errors (valid format, invalid meaning).

        SERVER ERROR METHODS (5xx):
            • internal_server_error(detail: str = "An internal error occurred") → OperationResult[None]
              Returns HTTP 500 Internal Server Error with error message.
              Use for: Unexpected exceptions, infrastructure failures.

            • service_unavailable(detail: str = "Service temporarily unavailable") → OperationResult[None]
              Returns HTTP 503 Service Unavailable with error message.
              Use for: Temporary service outages, maintenance mode.

    Important Notes:

        **DO NOT construct OperationResult manually:**
        ```python
        # ❌ WRONG - Don't do this
        result = OperationResult("OK", 200)
        result.data = user

        # ✅ CORRECT - Use helper methods
        return self.ok(user)
        ```

        **Parameter Signature:**
        All handlers must implement: `async def handle_async(self, request: TRequest) -> TResult`
        Note: cancellation_token is NOT currently used in the framework.

        **Type Safety:**
        Use proper generic type hints for IDE support:
        ```python
        class MyHandler(CommandHandler[MyCommand, OperationResult[MyDto]]):
            async def handle_async(self, command: MyCommand) -> OperationResult[MyDto]:
                return self.ok(my_dto)  # Type-checked by IDE
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Handler Pattern: https://bvandewe.github.io/pyneuro/patterns/
        - OperationResult: neuroglia.core.OperationResult (DO NOT construct manually)
    """

    @abstractmethod
    async def handle_async(self, request: TRequest) -> TResult:
        """Handles the specified request"""
        raise NotImplementedError()

    # Success response methods (2xx)

    def ok(self, data: Optional[Any] = None) -> TResult:
        """Creates a successful operation result (HTTP 200 OK)"""
        result: OperationResult = OperationResult("OK", 200)
        result.data = data
        return cast(TResult, result)

    def created(self, data: Optional[Any] = None) -> TResult:
        """Creates a successful creation result (HTTP 201 Created)"""
        result: OperationResult = OperationResult("Created", 201)
        result.data = data
        return cast(TResult, result)

    def accepted(self, data: Optional[Any] = None) -> TResult:
        """Creates an accepted result for async operations (HTTP 202 Accepted)"""
        result: OperationResult = OperationResult("Accepted", 202)
        result.data = data
        return cast(TResult, result)

    def no_content(self) -> TResult:
        """Creates a successful no content result (HTTP 204 No Content)"""
        result: OperationResult = OperationResult("No Content", 204)
        result.data = None
        return cast(TResult, result)

    # Client error response methods (4xx)

    def bad_request(self, detail: str) -> TResult:
        """Creates a bad request error result (HTTP 400 Bad Request)"""
        result: OperationResult = OperationResult("Bad Request", 400, detail, "https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Bad%20Request")
        result.data = None
        return cast(TResult, result)

    def unauthorized(self, detail: str = "Authentication required") -> TResult:
        """Creates an unauthorized error result (HTTP 401 Unauthorized)"""
        result: OperationResult = OperationResult("Unauthorized", 401, detail, "https://www.w3.org/Protocols/HTTP/HTRESP.html")
        result.data = None
        return cast(TResult, result)

    def forbidden(self, detail: str = "Access denied") -> TResult:
        """Creates a forbidden error result (HTTP 403 Forbidden)"""
        result: OperationResult = OperationResult("Forbidden", 403, detail, "https://www.w3.org/Protocols/HTTP/HTRESP.html")
        result.data = None
        return cast(TResult, result)

    def not_found(self, entity_type, entity_key, key_name: str = "id") -> TResult:
        """Creates a not found error result (HTTP 404 Not Found)"""
        result: OperationResult = OperationResult("Not Found", 404, f"Failed to find an entity of type '{entity_type.__name__}' with the specified {key_name} '{entity_key}'", "https://www.w3.org/Protocols/HTTP/HTRESP.html#:~:text=Not%20found%20404")
        result.data = None
        return cast(TResult, result)

    def conflict(self, message: str) -> TResult:
        """Creates a conflict error result (HTTP 409 Conflict)"""
        result: OperationResult = OperationResult("Conflict", 409, message, "https://www.w3.org/Protocols/HTTP/HTRESP.html")
        result.data = None
        return cast(TResult, result)

    def unprocessable_entity(self, detail: str) -> TResult:
        """Creates an unprocessable entity error result (HTTP 422 Unprocessable Entity)"""
        result: OperationResult = OperationResult("Unprocessable Entity", 422, detail, "https://www.w3.org/Protocols/HTTP/HTRESP.html")
        result.data = None
        return cast(TResult, result)

    # Server error response methods (5xx)

    def internal_server_error(self, detail: str = "An internal error occurred") -> TResult:
        """Creates an internal server error result (HTTP 500 Internal Server Error)"""
        result: OperationResult = OperationResult("Internal Server Error", 500, detail, "https://www.w3.org/Protocols/HTTP/HTRESP.html")
        result.data = None
        return cast(TResult, result)

    def service_unavailable(self, detail: str = "Service temporarily unavailable") -> TResult:
        """Creates a service unavailable error result (HTTP 503 Service Unavailable)"""
        result: OperationResult = OperationResult("Service Unavailable", 503, detail, "https://www.w3.org/Protocols/HTTP/HTRESP.html")
        result.data = None
        return cast(TResult, result)


TCommand = TypeVar("TCommand", bound=Command)
""" Represents the type of CQRS command to handle """


class CommandHandler(Generic[TCommand, TResult], RequestHandler[TCommand, TResult], ABC):
    """
    Represents the abstraction for services that handle specific types of CQRS commands.

    Command handlers contain the business logic for processing write operations that modify
    system state. Each command type must have exactly one handler to maintain consistency
    and avoid ambiguity in business operation execution.

    Type Parameters:
        TCommand: The specific command type this handler processes
        TResult: The result type returned after command execution

    Examples:
        ```python
        class CreateUserCommandHandler(CommandHandler[CreateUserCommand, OperationResult[UserDto]]):
            def __init__(self, user_repository: UserRepository, email_service: EmailService):
                self.user_repository = user_repository
                self.email_service = email_service

            async def handle_async(self, command: CreateUserCommand) -> OperationResult[UserDto]:
                # Validation
                if await self.user_repository.exists_by_email(command.email):
                    return self.bad_request("User with this email already exists")

                # Business logic
                user = User.create(command.first_name, command.last_name, command.email)
                await self.user_repository.save_async(user)

                # Side effects (events will be published automatically)
                await self.email_service.send_welcome_email(user.email)

                return self.created(UserDto.from_entity(user))
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Command Pattern: https://bvandewe.github.io/pyneuro/patterns/
    """


TQuery = TypeVar("TQuery", bound=Query)
""" Represents the type of CQRS query to handle """


class QueryHandler(Generic[TQuery, TResult], RequestHandler[TQuery, TResult], ABC):
    """
    Represents the abstraction for services that handle specific types of CQRS queries.

    Query handlers contain the logic for processing read operations that retrieve data
    without side effects. Unlike commands, multiple query handlers can exist for different
    data projections, optimized views, or caching strategies of the same entity.

    Type Parameters:
        TQuery: The specific query type this handler processes
        TResult: The data type returned by the query

    Examples:
        ```python
        class GetUserByIdQueryHandler(QueryHandler[GetUserByIdQuery, Optional[UserDto]]):
            def __init__(self, user_repository: UserRepository):
                self.user_repository = user_repository

            async def handle_async(self, query: GetUserByIdQuery) -> Optional[UserDto]:
                user = await self.user_repository.get_by_id_async(query.user_id)
                return UserDto.from_entity(user) if user else None

        class GetUsersQueryHandler(QueryHandler[GetUsersQuery, List[UserDto]]):
            def __init__(self, user_repository: QueryableRepository[User, str]):
                self.user_repository = user_repository

            async def handle_async(self, query: GetUsersQuery) -> List[UserDto]:
                queryable = await self.user_repository.query_async()

                if query.active_only:
                    queryable = queryable.where(lambda u: u.is_active)

                users = queryable.skip((query.page - 1) * query.page_size) \\
                              .take(query.page_size) \\
                              .to_list()

                return [UserDto.from_entity(u) for u in users]
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Query Pattern: https://bvandewe.github.io/pyneuro/patterns/
    """


TNotification = TypeVar("TNotification", bound=object)
""" Represents the type of CQRS notification to handle """


class NotificationHandler(Generic[TNotification], ABC):
    """
    Represents the abstraction for services that handle notifications in event-driven architectures.

    Notification handlers process asynchronous messages that don't require a response,
    enabling loose coupling between components. Multiple handlers can subscribe to the
    same notification type for cross-cutting concerns and side effects.

    Type Parameters:
        TNotification: The specific type of notification this handler processes

    Examples:
        ```python
        class UserCreatedNotificationHandler(NotificationHandler[UserCreatedEvent]):
            def __init__(self, email_service: EmailService, audit_service: AuditService):
                self.email_service = email_service
                self.audit_service = audit_service

            async def handle_async(self, notification: UserCreatedEvent) -> None:
                # Send welcome email
                await self.email_service.send_welcome_email(
                    notification.user_email,
                    notification.user_name
                )

                # Log audit entry
                await self.audit_service.log_user_creation(
                    notification.user_id,
                    notification.created_at
                )

        # Multiple handlers for the same event
        class UserCreatedCacheHandler(NotificationHandler[UserCreatedEvent]):
            async def handle_async(self, notification: UserCreatedEvent) -> None:
                await self.cache.invalidate_user_statistics()
        ```

    See Also:
        - Event-Driven Architecture: https://bvandewe.github.io/pyneuro/patterns/
        - Domain Events: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
    """

    @abstractmethod
    async def handle_async(self, notification: TNotification) -> None:
        """Handles the specified notification"""
        raise NotImplementedError()


TDomainEvent = TypeVar("TDomainEvent", bound=DomainEvent)
""" Represents the type of domain event to handle """


class DomainEventHandler(Generic[TDomainEvent], NotificationHandler[TDomainEvent], ABC):
    """
    Represents the abstraction for services that handle domain events in domain-driven design.

    Domain event handlers process events raised by domain entities to maintain business
    consistency, trigger side effects, and enable reactive business processes while
    maintaining loose coupling between bounded contexts.

    Type Parameters:
        TDomainEvent: The specific domain event type this handler processes

    Examples:
        ```python
        @dataclass
        class OrderShippedEvent(DomainEvent[str]):
            order_id: str
            tracking_number: str
            shipped_at: datetime

        class OrderShippedEventHandler(DomainEventHandler[OrderShippedEvent]):
            def __init__(self,
                       email_service: EmailService,
                       inventory_service: InventoryService):
                self.email_service = email_service
                self.inventory_service = inventory_service

            async def handle_async(self, event: OrderShippedEvent) -> None:
                # Notify customer
                await self.email_service.send_shipping_notification(
                    event.order_id,
                    event.tracking_number
                )

                # Update inventory projections
                await self.inventory_service.mark_items_shipped(event.order_id)

        # Handle aggregate events
        class ProductOutOfStockHandler(DomainEventHandler[ProductOutOfStockEvent]):
            async def handle_async(self, event: ProductOutOfStockEvent) -> None:
                await self.procurement_service.trigger_reorder(event.product_id)
        ```

    See Also:
        - Domain Events: https://bvandewe.github.io/pyneuro/patterns/
        - Event-Driven Architecture: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
    """


TIntegrationEvent = TypeVar("TIntegrationEvent", bound=IntegrationEvent)
""" Represents the type of integration event to handle """


class IntegrationEventHandler(Generic[TIntegrationEvent], NotificationHandler[TIntegrationEvent], ABC):
    """
    Represents the abstraction for services that handle integration events between bounded contexts.

    Integration event handlers process events that cross bounded context boundaries,
    enabling communication between different microservices, systems, or external integrations
    while maintaining loose coupling and autonomous service boundaries.

    Type Parameters:
        TIntegrationEvent: The specific integration event type this handler processes

    Examples:
        ```python
        @dataclass
        class UserRegisteredIntegrationEvent(IntegrationEvent):
            user_id: str
            email: str
            registration_source: str
            occurred_at: datetime

        class UserRegisteredIntegrationEventHandler(IntegrationEventHandler[UserRegisteredIntegrationEvent]):
            def __init__(self,
                       crm_service: CRMService,
                       analytics_service: AnalyticsService):
                self.crm_service = crm_service
                self.analytics_service = analytics_service

            async def handle_async(self, event: UserRegisteredIntegrationEvent) -> None:
                # Sync with external CRM
                await self.crm_service.create_contact(
                    user_id=event.user_id,
                    email=event.email,
                    source=event.registration_source
                )

                # Send analytics data
                await self.analytics_service.track_user_registration(
                    event.user_id,
                    event.registration_source,
                    event.occurred_at
                )
        ```

    See Also:
        - Integration Events: https://bvandewe.github.io/pyneuro/patterns/
        - Microservices Communication: https://bvandewe.github.io/pyneuro/features/
    """


class Mediator:
    """
    Orchestrates the dispatch of commands, queries, and notifications to their respective handlers.

    The Mediator is the central component of the CQRS (Command Query Responsibility Segregation)
    pattern implementation, providing a single entry point for all request processing while
    maintaining loose coupling between request senders and handlers.

    Key Features:
        - Type-safe request routing to appropriate handlers
        - Automatic handler discovery and registration
        - Support for commands, queries, and notifications
        - Parallel execution of multiple notification handlers
        - Comprehensive error handling and logging

    Attributes:
        _service_provider (ServiceProviderBase): The dependency injection container for handler resolution

    Usage with Mediator.configure (Recommended):
        ```python
        from neuroglia.hosting.web import WebApplicationBuilder
        from neuroglia.mediation import Mediator

        builder = WebApplicationBuilder()

        # Automatic handler discovery and registration
        Mediator.configure(builder, [
            "application.commands",
            "application.queries",
            "application.events"
        ])

        app = builder.build()

        # Use mediator in controllers/handlers via DI
        mediator = app.service_provider.get_service(Mediator)

        # Execute command
        command = CreateUserCommand("John", "Doe", "john@example.com")
        result = await mediator.execute_async(command)

        # Execute query
        query = GetUserByIdQuery(result.data.id)
        user = await mediator.execute_async(query)

        # Publish notification (multiple handlers can process)
        event = UserCreatedEvent(user_id=result.data.id, email="john@example.com")
        await mediator.publish_async(event)
        ```

    Legacy Manual Setup:
        ```python
        # Manual handler registration (still supported)
        services = ServiceCollection()
        services.add_mediator()
        services.add_scoped(CreateUserHandler)
        services.add_scoped(GetUserByIdHandler)

        provider = services.build_provider()
        mediator = provider.get_service(Mediator)
        ```

    Architecture:
        ```
        Controller -> Mediator -> Handler -> Repository/Service
                  ^            ^        ^
                  |            |        |
               Single API   Type Safe  Business Logic
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Mediator Pattern: https://bvandewe.github.io/pyneuro/patterns/cqrs/
        - Getting Started Guide: https://bvandewe.github.io/pyneuro/getting-started/
    """

    _handler_registry: ClassVar[dict[type[Any], type[Any]]] = {}
    _service_provider: ServiceProviderBase

    def __init__(self, service_provider: ServiceProviderBase):
        self._service_provider = service_provider

    async def execute_async(self, request: Request) -> OperationResult:
        """Executes the specified request through the pipeline behaviors and handler"""
        log.info(f"🔍 MEDIATOR DEBUG: Starting execute_async for request: {type(request).__name__}")

        # Use the original approach but get RequestHandler services and find matching concrete handlers
        # Use a class-level handler registry approach
        request_type = type(request)

        # Check if we have a handler registry
        if not hasattr(Mediator, "_handler_registry"):
            Mediator._handler_registry = {}

        # Try to get handler from registry
        handler_class = Mediator._handler_registry.get(request_type)
        if handler_class:
            # Create service scope for BOTH handler AND pipeline behaviors
            scope = self._service_provider.create_scope()
            try:
                provider: ServiceProviderBase = scope.get_service_provider()
                handler_instance = provider.get_service(handler_class)
                if handler_instance is None:
                    raise Exception(f"Failed to resolve handler instance for '{handler_class.__name__}'")
                log.debug(f"🔍 MEDIATOR DEBUG: Successfully resolved {handler_class.__name__} from registry")

                # Get all pipeline behaviors for this request type from scoped provider
                # This allows pipeline behaviors to be scoped and access scoped dependencies
                behaviors = self._get_pipeline_behaviors(request, provider)

                if not behaviors:
                    # No behaviors, execute handler directly
                    return await handler_instance.handle_async(request)

                # Build pipeline chain with behaviors
                return await self._build_pipeline(request, handler_instance, behaviors)
            finally:
                if hasattr(scope, "dispose"):
                    scope.dispose()

        raise Exception(f"Failed to find a handler for request of type '{request_type.__name__}'. Registry has {len(Mediator._handler_registry)} handlers.")

    async def publish_async(self, notification: object):
        """
        Publishes the specified notification to all registered handlers.

        Creates a scoped service provider for this notification processing, allowing
        handlers with scoped dependencies (like repositories) to be properly resolved.
        All handlers are executed concurrently within the same scope, and the scope
        is automatically disposed after all handlers complete.

        This follows the same pattern as HTTP request processing, where each logical
        operation (HTTP request or event) gets its own isolated scope.

        Args:
            notification: The notification object to publish to handlers

        Examples:
            ```python
            # Publish domain event with scoped handler dependencies
            event = UserCreatedEvent(user_id="123", email="user@example.com")
            await mediator.publish_async(event)

            # Handler with scoped repository (now works correctly!)
            class UserCreatedHandler(NotificationHandler[UserCreatedEvent]):
                def __init__(self, repo: AsyncCacheRepository[User, str]):
                    self.repo = repo  # Scoped service resolved correctly

                async def handle_async(self, event: UserCreatedEvent):
                    async with self.repo as r:
                        await r.add_async(user)
            ```

        See Also:
            - Event-Driven Architecture: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
            - Scoped Services: https://bvandewe.github.io/pyneuro/patterns/dependency-injection
        """
        # Create a scoped service provider for this notification
        # Similar to how web frameworks create a scope per HTTP request
        async with self._service_provider.create_async_scope() as scope:
            scoped_provider = scope.get_service_provider()

            # Resolve handlers from the scoped provider (not root!)
            # This allows handlers with scoped dependencies to be resolved correctly
            handlers: list[NotificationHandler] = [candidate for candidate in scoped_provider.get_services(NotificationHandler) if self._notification_handler_matches(candidate, type(notification))]

            behaviors = self._get_pipeline_behaviors(notification, scoped_provider)

            async def invoke_handlers() -> None:
                if handlers:
                    await asyncio.gather(*(handler.handle_async(notification) for handler in handlers))

            await self._execute_notification_pipeline(notification, invoke_handlers, behaviors)
        # Scope automatically disposed here, including all scoped services

    def _handler_type_matches(self, handler_class, request_type) -> bool:
        """Check if a handler class can handle the specified request type"""
        try:
            # Get the base classes of the handler to find the RequestHandler generic
            for base in handler_class.__orig_bases__ if hasattr(handler_class, "__orig_bases__") else []:
                if hasattr(base, "__origin__") and hasattr(base, "__args__"):
                    # Check if this base is a RequestHandler generic
                    if hasattr(base.__origin__, "__name__") and base.__origin__.__name__ in [
                        "CommandHandler",
                        "QueryHandler",
                    ]:
                        handled_request_type = base.__args__[0]

                        return handled_request_type == request_type
            return False
        except Exception as e:
            log.debug(f"Error checking handler type match: {e}")
            return False

    def _request_handler_matches(self, candidate, request_type) -> bool:
        expected_request_type = request_type.__orig_class__ if hasattr(request_type, "__orig_class__") else request_type
        handler_type = TypeExtensions.get_generic_implementation(candidate, RequestHandler)
        handled_request_type = handler_type.__args__[0]
        if type(handled_request_type) is type(expected_request_type):
            matches = handled_request_type == expected_request_type
            return matches
        else:
            return handled_request_type == type(expected_request_type)

    def _notification_handler_matches(self, candidate, request_type) -> bool:
        candidate_type = type(candidate)
        try:
            handler_type = next(base for base in candidate_type.__orig_bases__ if (issubclass(base.__origin__, NotificationHandler) if hasattr(base, "__origin__") else issubclass(base, NotificationHandler)))
            handled_notification_type = handler_type.__args__[0]

            if isinstance(handled_notification_type, UnionType):
                return any(issubclass(t, request_type) for t in handled_notification_type.__args__)
            else:
                return issubclass(handled_notification_type.__origin__, request_type) if hasattr(handled_notification_type, "__origin__") else issubclass(handled_notification_type, request_type)
        except Exception as e:
            log.debug(f"Error matching notification handler {candidate_type.__name__} to {request_type.__name__}: {e}")
            return False

    def _get_pipeline_behaviors(self, request: object, provider: Optional[ServiceProviderBase] = None) -> list[PipelineBehavior]:
        """
        Gets all registered pipeline behaviors that can handle the specified request type.

        Args:
            request: The request being processed
            provider: Optional scoped provider to use for resolution. If not provided,
                     falls back to root provider for backward compatibility.

        Returns:
            List of pipeline behaviors that can handle this request
        """
        behaviors = []
        try:
            # Use provided scoped provider if available, otherwise fall back to root provider
            # This allows pipeline behaviors to be scoped and access scoped dependencies
            service_provider = provider if provider is not None else self._service_provider

            # Get all registered pipeline behaviors from appropriate provider
            all_behaviors = service_provider.get_services(PipelineBehavior)
            if all_behaviors:
                # Filter behaviors that can handle this request type
                for behavior in all_behaviors:
                    if self._pipeline_behavior_matches(behavior, request):
                        behaviors.append(behavior)

            log.debug(f"Found {len(behaviors)} pipeline behaviors for {type(request).__name__}")
        except Exception as e:
            log.warning(f"Error getting pipeline behaviors: {e}", exc_info=True)

        return behaviors

    def _pipeline_behavior_matches(self, behavior: PipelineBehavior, request: object) -> bool:
        """Determines if a pipeline behavior can handle the specified request type"""
        try:
            # For now, assume all behaviors can handle all requests
            # This can be enhanced later with more sophisticated type checking
            return True
        except Exception as e:
            behavior_type = type(behavior)
            behavior_name = getattr(behavior_type, "__name__", "Unknown")
            log.debug(f"Error matching pipeline behavior {behavior_name}: {e}")
            return False

    async def _build_pipeline(self, request: Request, handler: RequestHandler, behaviors: list[PipelineBehavior]) -> OperationResult:
        """Builds and executes the pipeline chain with the specified behaviors and handler"""
        if not behaviors:
            return await handler.handle_async(request)

        # Sort behaviors by priority if they have one (optional ordering)
        sorted_behaviors = self._sort_behaviors(behaviors)

        # Build the pipeline chain from the end (handler) backward to the beginning
        async def build_handler_delegate(current_index: int) -> Any:
            if current_index >= len(sorted_behaviors):
                # Final handler in the chain
                return await handler.handle_async(request)
            else:
                # Intermediate behavior in the chain
                current_behavior = sorted_behaviors[current_index]

                async def next_handler():
                    return await build_handler_delegate(current_index + 1)

                return await current_behavior.handle_async(request, next_handler)

        # Execute the pipeline starting from the first behavior
        return await build_handler_delegate(0)

    def _sort_behaviors(self, behaviors: list[PipelineBehavior]) -> list[PipelineBehavior]:
        """Sorts pipeline behaviors by priority. Override to customize ordering."""
        # Default implementation: preserve registration order
        # Can be extended to support priority attributes or specific ordering rules
        return behaviors

    async def _execute_notification_pipeline(self, notification: object, handler_callable: Callable[[], Awaitable[Any]], behaviors: list[PipelineBehavior]) -> Any:
        """Executes notification pipeline behaviors around event handlers."""

        if not behaviors:
            return await handler_callable()

        sorted_behaviors = self._sort_behaviors(behaviors)

        async def invoke(index: int) -> Any:
            if index >= len(sorted_behaviors):
                return await handler_callable()

            current_behavior = sorted_behaviors[index]

            async def next_handler() -> Any:
                return await invoke(index + 1)

            return await current_behavior.handle_async(notification, next_handler)

        return await invoke(0)

    @staticmethod
    def _discover_submodules(package_name: str) -> list[str]:
        """Discover individual modules within a package without importing the package."""
        submodules = []
        try:
            package_path = package_name.replace(".", "/")
            for search_path in ["src", ".", "app"]:
                full_package_path = Path(search_path) / package_path
                if full_package_path.exists() and full_package_path.is_dir():
                    for py_file in full_package_path.glob("*.py"):
                        if py_file.name != "__init__.py":
                            module_name = f"{package_name}.{py_file.stem}"
                            submodules.append(module_name)
                            log.debug(f"Discovered submodule: {module_name}")
                    break
        except Exception as e:
            log.debug(f"Error discovering submodules for {package_name}: {e}")
        return submodules

    @staticmethod
    def _register_handlers_from_module(app: ApplicationBuilderBase, module, module_name: str) -> int:
        """Register all handlers found in a specific module."""
        handlers_registered = 0
        try:
            # Command handlers
            for command_handler_type in TypeFinder.get_types(
                module,
                lambda cls: inspect.isclass(cls) and (not hasattr(cls, "__parameters__") or len(cls.__parameters__) < 1) and issubclass(cls, CommandHandler) and cls != CommandHandler,
                include_sub_modules=True,
            ):
                # Debug: Check for None types
                if command_handler_type is None:
                    log.error(f"❌ Found None command handler type in {module_name}")
                    continue

                # Register only the concrete type (for DI) and track for mediator discovery
                app.services.add_scoped(command_handler_type, command_handler_type)

                generic = TypeExtensions.get_generic_implementation(command_handler_type, CommandHandler)
                if generic is not None and hasattr(generic, "__args__") and generic.__args__:
                    command_type = generic.__args__[0]
                    Mediator._handler_registry[command_type] = command_handler_type
                    log.debug(f"🔧 Registered {command_type.__name__} -> {command_handler_type.__name__} in registry from {module_name}")
                handlers_registered += 1

            # Query handlers
            for queryhandler_type in TypeFinder.get_types(
                module,
                lambda cls: inspect.isclass(cls) and (not hasattr(cls, "__parameters__") or len(cls.__parameters__) < 1) and issubclass(cls, QueryHandler) and cls != QueryHandler,
                include_sub_modules=True,
            ):
                # Debug: Check for None types
                if queryhandler_type is None:
                    log.error(f"❌ Found None query handler type in {module_name}")
                    continue

                # Register only the concrete type (for DI) and track for mediator discovery
                app.services.add_scoped(queryhandler_type, queryhandler_type)

                generic = TypeExtensions.get_generic_implementation(queryhandler_type, QueryHandler)
                if generic is not None and hasattr(generic, "__args__") and generic.__args__:
                    query_type = generic.__args__[0]
                    Mediator._handler_registry[query_type] = queryhandler_type
                    log.debug(f"🔧 Registered {query_type.__name__} -> {queryhandler_type.__name__} in registry from {module_name}")
                handlers_registered += 1

            # Domain event handlers
            for domain_event_handler_type in TypeFinder.get_types(
                module,
                lambda cls: inspect.isclass(cls) and issubclass(cls, DomainEventHandler) and cls != DomainEventHandler,
                include_sub_modules=True,
            ):
                app.services.add_transient(NotificationHandler, domain_event_handler_type)
                handlers_registered += 1
                log.debug(f"Registered DomainEventHandler: {domain_event_handler_type.__name__} from {module_name}")

            # Integration event handlers
            for integration_event_handler_type in TypeFinder.get_types(
                module,
                lambda cls: inspect.isclass(cls) and issubclass(cls, IntegrationEventHandler) and cls != IntegrationEventHandler,
                include_sub_packages=True,
            ):
                app.services.add_transient(NotificationHandler, integration_event_handler_type)
                handlers_registered += 1
                log.debug(f"Registered IntegrationEventHandler: {integration_event_handler_type.__name__} from {module_name}")

        except Exception as e:
            log.warning(f"Error registering handlers from module {module_name}: {e}")
        return handlers_registered

    @staticmethod
    def configure(app: ApplicationBuilderBase, modules: list[str] = list[str]()) -> ApplicationBuilderBase:
        """
        Registers and configures mediation-related services with resilient handler discovery.

        This method implements a fallback strategy when package imports fail:
        1. First attempts to import the entire package (original behavior)
        2. If that fails, attempts to discover and import individual modules
        3. Logs all discovery attempts and results for debugging

        Args:
            app (ApplicationBuilderBase): The application builder to configure
            modules (List[str]): Module/package names to scan for handlers

        Returns:
            ApplicationBuilderBase: The configured application builder
        """
        total_handlers_registered = 0

        for module_name in modules:
            module_handlers_registered = 0

            try:
                # Strategy 1: Try to import the entire package (original behavior)
                log.debug(f"Attempting to load package: {module_name}")
                module = ModuleLoader.load(module_name)
                module_handlers_registered = Mediator._register_handlers_from_module(app, module, module_name)

                if module_handlers_registered > 0:
                    log.info(f"Successfully registered {module_handlers_registered} handlers from package: {module_name}")
                else:
                    log.debug(f"No handlers found in package: {module_name}")

            except ImportError as package_error:
                log.warning(f"Package import failed for '{module_name}': {package_error}")
                log.info(f"Attempting fallback: scanning individual modules in '{module_name}'")

                # Strategy 2: Fallback to individual module discovery
                try:
                    submodules = Mediator._discover_submodules(module_name)

                    if not submodules:
                        log.warning(f"No submodules discovered for package: {module_name}")
                        continue

                    log.debug(f"Found {len(submodules)} potential submodules in {module_name}")

                    for submodule_name in submodules:
                        try:
                            log.debug(f"Attempting to load submodule: {submodule_name}")
                            submodule = ModuleLoader.load(submodule_name)
                            submodule_handlers = Mediator._register_handlers_from_module(app, submodule, submodule_name)
                            module_handlers_registered += submodule_handlers

                            if submodule_handlers > 0:
                                log.info(f"Successfully registered {submodule_handlers} handlers from submodule: {submodule_name}")

                        except ImportError as submodule_error:
                            log.debug(f"Skipping submodule '{submodule_name}': {submodule_error}")
                            continue
                        except Exception as submodule_error:
                            log.warning(f"Unexpected error loading submodule '{submodule_name}': {submodule_error}")
                            continue

                    if module_handlers_registered > 0:
                        log.info(f"Fallback succeeded: registered {module_handlers_registered} handlers from individual modules in '{module_name}'")
                    else:
                        log.warning(f"Fallback failed: no handlers registered from '{module_name}' (package or individual modules)")

                except Exception as discovery_error:
                    log.error(f"Failed to discover submodules for '{module_name}': {discovery_error}")

            except Exception as unexpected_error:
                log.error(f"Unexpected error processing module '{module_name}': {unexpected_error}")

            total_handlers_registered += module_handlers_registered

        log.info(f"Handler discovery completed: {total_handlers_registered} total handlers registered from {len(modules)} module specifications")

        # Always add the Mediator singleton
        app.services.add_singleton(Mediator)
        return app
