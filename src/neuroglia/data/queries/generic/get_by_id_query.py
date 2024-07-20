from typing import Any, Generic
from neuroglia.core.operation_result import OperationResult
from neuroglia.data.abstractions import TEntity, TKey
from neuroglia.data.infrastructure.abstractions import QueryableRepository, Repository
from neuroglia.mediation.mediator import Query, QueryHandler


class GetByIdQuery(Generic[TEntity, TKey], Query[OperationResult[TEntity]]):
    ''' Represents the query used to get an entity by id'''

    def __init__(self, id: Any):
        self.id = id

    id: Any
    ''' Gets the id of the entity to get '''


class GetByIdQueryHandler(Generic[TEntity, TKey], QueryHandler[GetByIdQuery[TEntity, TKey], OperationResult[TEntity]]):
    ''' Represents the service used to handle GetByIdQuery instances '''

    def __init__(self, repository: Repository[TEntity, TKey]):
        self.repository = repository

    repository: Repository[TEntity, TKey]

    async def handle_async(self, query: GetByIdQuery[TEntity, TKey]) -> OperationResult[TEntity]:
        entity = await self.repository.get_async(query.id)
        if entity is None:
            return self.not_found(self.repository.__orig_class__.__args__[0], query.id)
        return self.ok(entity)
