from typing import Any, Generic

from neuroglia.core.operation_result import OperationResult
from neuroglia.data.abstractions import TEntity, TKey
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation.mediator import Query, QueryHandler


class GetByIdQuery(Generic[TEntity, TKey], Query[OperationResult[TEntity]]):
    """
    Represents a generic query for retrieving an entity by its unique identifier.

    This is a standard CQRS query pattern that provides type-safe entity retrieval
    with proper error handling and operation result wrapping.

    Type Parameters:
        TEntity: The type of entity to retrieve
        TKey: The type of the entity's unique identifier

    Attributes:
        id (Any): The unique identifier of the entity to retrieve

    Examples:
        ```python
        # Query for a specific user
        query = GetByIdQuery[User, UUID](uuid4())
        result = await mediator.execute_async(query)

        if result.is_success:
            user = result.data
            print(f"Found user: {user.name}")
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Data Access Patterns: https://bvandewe.github.io/pyneuro/features/data-access/
    """

    def __init__(self, id: Any):
        self.id = id

    id: Any
    """ Gets the id of the entity to get """


class GetByIdQueryHandler(Generic[TEntity, TKey], QueryHandler[GetByIdQuery[TEntity, TKey], OperationResult[TEntity]]):
    """
    Handles GetByIdQuery instances by retrieving entities from the repository.

    This generic handler provides standard entity retrieval logic with proper
    not-found handling and success/failure result wrapping.

    Type Parameters:
        TEntity: The type of entity to retrieve
        TKey: The type of the entity's unique identifier

    Attributes:
        repository (Repository[TEntity, TKey]): The repository for data access

    Examples:
        ```python
        # Register the handler for dependency injection
        services.add_scoped(GetByIdQueryHandler[User, UUID])
        services.add_scoped(Repository[User, UUID], UserRepository)
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Repository Pattern: https://bvandewe.github.io/pyneuro/features/data-access/
    """

    def __init__(self, repository: Repository[TEntity, TKey]):
        self.repository = repository

    repository: Repository[TEntity, TKey]

    async def handle_async(self, query: GetByIdQuery[TEntity, TKey]) -> OperationResult[TEntity]:
        entity = await self.repository.get_async(query.id)
        if entity is None:
            return self.not_found(self.repository.__orig_class__.__args__[0], query.id)
        return self.ok(entity)
