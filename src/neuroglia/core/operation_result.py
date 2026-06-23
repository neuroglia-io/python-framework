from typing import Generic, Optional, TypeVar

from .problem_details import ProblemDetails

TData = TypeVar("TData")


class OperationResult(Generic[TData], ProblemDetails):
    """Represents the result of an operation with optional typed data payload.

    ⚠️  IMPORTANT: DO NOT CONSTRUCT THIS CLASS MANUALLY ⚠️
    ═══════════════════════════════════════════════════════════════════════════

    OperationResult instances should ONLY be created using the helper methods
    provided by RequestHandler, CommandHandler, or QueryHandler base classes:

        ✅ CORRECT - Use handler helper methods:
        ```python
        return self.ok(data)              # 200 OK
        return self.created(data)         # 201 Created
        return self.bad_request("error")  # 400 Bad Request
        return self.not_found(User, id)   # 404 Not Found
        ```

        ❌ WRONG - Don't construct manually:
        ```python
        result = OperationResult("OK", 200)  # DON'T DO THIS
        result.data = data
        return result
        ```

        ❌ WRONG - These static methods don't exist:
        ```python
        return OperationResult.success(data)  # DOESN'T EXIST
        return OperationResult.fail("error")  # DOESN'T EXIST
        ```

    See RequestHandler class for available helper methods:
        • ok(data)                      → 200 OK
        • created(data)                 → 201 Created
        • accepted(data)                → 202 Accepted
        • no_content()                  → 204 No Content
        • bad_request(detail)           → 400 Bad Request
        • unauthorized(detail)          → 401 Unauthorized
        • forbidden(detail)             → 403 Forbidden
        • not_found(type, key, name)    → 404 Not Found
        • conflict(message)             → 409 Conflict
        • unprocessable_entity(detail)  → 422 Unprocessable Entity
        • internal_server_error(detail) → 500 Internal Server Error
        • service_unavailable(detail)   → 503 Service Unavailable

    ═══════════════════════════════════════════════════════════════════════════

    About OperationResult
    ---------------------

    OperationResult is a generic wrapper around ProblemDetails that adds support
    for carrying successful operation results alongside error information. It serves
    as the standard return type for all command and query handlers in the Neuroglia
    framework, providing a consistent way to handle both success and failure cases.

    This class inherits from ProblemDetails (RFC 7807) to maintain compatibility
    with HTTP API standards while extending it for internal operation results. It
    provides a type-safe way to return either success data or error information
    from business operations.

    Type Parameters:
        TData: The type of data returned in successful operations. Can be any type
               including primitives, DTOs, entities, or collections.

    Attributes:
        data: The data payload returned by successful operations. This will be
              None for error cases and contain the actual result for success cases.
              The type is constrained by the TData generic parameter.

    Properties (computed from inherited ProblemDetails):
        is_success: True if the operation succeeded (status 2xx), False otherwise
        error_message: Alias for the 'detail' field from ProblemDetails
        status_code: Alias for the 'status' field from ProblemDetails

    Common Usage Patterns:

        In Command/Query Handlers:

        >>> class CreateUserHandler(CommandHandler):
        ...     async def handle_async(self, command) -> OperationResult[UserDto]:
        ...         try:
        ...             user = await self.create_user(command)
        ...             return self.created(user)  # Returns OperationResult[UserDto]
        ...         except ValidationError as e:
        ...             return self.bad_request(str(e))

        In Controllers:

        >>> @post("/users")
        ... async def create_user(self, dto: CreateUserDto) -> UserDto:
        ...     command = self.mapper.map(dto, CreateUserCommand)
        ...     result = await self.mediator.execute_async(command)
        ...     return self.process(result)  # Handles success/error automatically

        Manual Construction (less common):

        >>> # Success result
        >>> success_result = OperationResult[str]("OK", 200)
        >>> success_result.data = "Operation completed"
        >>> success_result.is_success  # True

        >>> # Error result
        >>> error_result = OperationResult[str]("Bad Request", 400, "Invalid input")
        >>> error_result.is_success  # False
        >>> error_result.error_message  # "Invalid input"

    Framework Integration:

        The OperationResult is deeply integrated with the framework's CQRS pattern:

        - RequestHandler base class provides helper methods (ok, created, bad_request)
        - ControllerBase.process() method handles OperationResult responses automatically
        - Mediator passes OperationResult instances between handlers and controllers
        - Repository methods can return OperationResult for consistent error handling

    Best Practices:

        1. Always use helper methods from RequestHandler when possible:
           - Use self.ok(data) instead of manually creating success results
           - Use self.bad_request(message) instead of manually creating error results

        2. Check is_success before accessing data:
           >>> if result.is_success:
           ...     user = result.data  # Safe to access
           ... else:
           ...     log.error(f"Operation failed: {result.error_message}")

        3. Use type hints for better IDE support:
           >>> def process_users() -> OperationResult[List[UserDto]]:
           ...     # TypeScript-like type safety in Python

        4. Leverage the process() method in controllers:
           >>> return self.process(result)  # Handles all status codes automatically

    Error Handling:

        OperationResult provides a functional approach to error handling that avoids
        exceptions for business logic errors:

        >>> result = await some_operation()
        >>> match result.status:
        ...     case 200: return result.data
        ...     case 400: raise ValidationError(result.error_message)
        ...     case 404: raise NotFoundError(result.error_message)
        ...     case _: raise InternalError(result.error_message)

    Thread Safety:

        OperationResult instances are immutable after construction and safe for
        concurrent access. However, the contained data object may have its own
        thread safety considerations.

    See Also:
        - ProblemDetails: Base class providing RFC 7807 compliance
        - RequestHandler: Provides factory methods for creating OperationResult instances
        - ControllerBase.process(): Handles OperationResult responses in web APIs
        - Command/Query: Request types that return OperationResult instances

    References:
        - RFC 7807: https://tools.ietf.org/html/rfc7807
        - CQRS Pattern: https://martinfowler.com/bliki/CQRS.html
    """

    data: Optional[TData]
    """The data payload returned by successful operations.

    This field contains the actual result data when the operation succeeds
    (status codes 2xx). For error cases, this will be None and error information
    is available through the inherited ProblemDetails fields.

    The type is constrained by the TData generic parameter, providing compile-time
    type safety for the expected return data.

    Examples:
        >>> # String result
        >>> result: OperationResult[str] = handler.handle_async(command)
        >>> if result.is_success:
        ...     message: str = result.data  # Type-safe access

        >>> # DTO result
        >>> result: OperationResult[UserDto] = handler.handle_async(command)
        >>> if result.is_success:
        ...     user: UserDto = result.data  # Type-safe access

        >>> # Collection result
        >>> result: OperationResult[List[UserDto]] = handler.handle_async(query)
        >>> if result.is_success:
        ...     users: List[UserDto] = result.data  # Type-safe access
    """

    @property
    def is_success(self) -> bool:
        """Determines whether the operation succeeded.

        This is a convenience property that delegates to the inherited
        is_success_status_code() method from ProblemDetails. It returns True
        for HTTP status codes in the 2xx range (200-299) and False otherwise.

        Returns:
            bool: True if the operation succeeded, False if it failed.

        Example:
            >>> result = await handler.handle_async(command)
            >>> if result.is_success:
            ...     process_success(result.data)
            ... else:
            ...     handle_error(result.error_message)
        """
        return self.is_success_status_code()

    @property
    def error_message(self) -> Optional[str]:
        """Gets the error message for failed operations.

        This is a convenience property that provides access to the 'detail' field
        from the inherited ProblemDetails class. It contains a human-readable
        explanation of what went wrong during the operation.

        Returns:
            Optional[str]: The error message if available, None otherwise.
                          For successful operations, this is typically None.

        Example:
            >>> result = await handler.handle_async(command)
            >>> if not result.is_success:
            ...     log.error(f"Operation failed: {result.error_message}")
            ...     return result.error_message
        """
        return self.detail

    @property
    def status_code(self) -> int:
        """Gets the HTTP status code for the operation result.

        This is a convenience property that provides access to the 'status' field
        from the inherited ProblemDetails class. It follows HTTP status code
        conventions for indicating the outcome of the operation.

        Returns:
            int: The HTTP status code (e.g., 200 for OK, 400 for Bad Request,
                 404 for Not Found, 500 for Internal Server Error).

        Common Status Codes:
            - 200: OK (successful operation)
            - 201: Created (successful creation)
            - 400: Bad Request (client error/validation failure)
            - 404: Not Found (requested resource doesn't exist)
            - 409: Conflict (operation conflicts with current state)
            - 500: Internal Server Error (unexpected server error)

        Example:
            >>> result = await handler.handle_async(command)
            >>> match result.status_code:
            ...     case 200 | 201:
            ...         return result.data
            ...     case 400:
            ...         raise ValidationException(result.error_message)
            ...     case 404:
            ...         raise NotFoundException(result.error_message)
            ...     case _:
            ...         raise InternalException(result.error_message)
        """
        return self.status
