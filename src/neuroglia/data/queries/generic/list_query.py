from typing import Generic

from neuroglia.core.operation_result import OperationResult
from neuroglia.data.abstractions import TEntity, TKey
from neuroglia.data.infrastructure.abstractions import QueryableRepository
from neuroglia.mediation.mediator import Query, QueryHandler


class ListQuery(Generic[TEntity, TKey], Query[OperationResult[TEntity]]):
    """
    Represents a generic query for retrieving all entities of a specific type.

    This is a standard CQRS query pattern that provides type-safe collection retrieval
    with proper operation result wrapping for consistent error handling.

    Type Parameters:
        TEntity: The type of entities to retrieve
        TKey: The type of the entity's unique identifier

    Examples:
        ```python
        # Query for all users
        query = ListQuery[User, UUID]()
        result = await mediator.execute_async(query)

        if result.is_success:
            users = result.data
            print(f"Found {len(users)} users")
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Data Access Patterns: https://bvandewe.github.io/pyneuro/features/data-access/
    """


class ListQueryHandler(Generic[TEntity, TKey], QueryHandler[ListQuery[TEntity, TKey], OperationResult[TEntity]]):
    """
    Handles ListQuery instances by retrieving all entities from the queryable repository.

    This generic handler provides standard collection retrieval logic using the
    queryable repository pattern for enhanced query capabilities.

    Type Parameters:
        TEntity: The type of entities to retrieve
        TKey: The type of the entity's unique identifier

    Attributes:
        repository (QueryableRepository[TEntity, TKey]): The queryable repository for data access

    Examples:
        ```python
        # Register the handler for dependency injection
        services.add_scoped(ListQueryHandler[User, UUID])
        services.add_scoped(QueryableRepository[User, UUID], UserQueryableRepository)
        ```

    See Also:
        - CQRS Mediation: https://bvandewe.github.io/pyneuro/features/simple-cqrs/
        - Repository Pattern: https://bvandewe.github.io/pyneuro/features/data-access/
    """

    def __init__(self, repository: QueryableRepository[TEntity, TKey]):
        self.repository = repository

    repository: QueryableRepository[TEntity, TKey]

    async def handle_async(self, query: ListQuery[TEntity, TKey]) -> OperationResult[TEntity]:
        res = await self.repository.query_async()
        return self.ok(res.to_list())
