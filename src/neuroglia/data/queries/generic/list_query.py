from typing import Any, Generic
from neuroglia.core.operation_result import OperationResult
from neuroglia.data.abstractions import TEntity, TKey
from neuroglia.data.infrastructure.abstractions import QueryableRepository
from neuroglia.mediation.mediator import Query, QueryHandler


class ListQuery(Generic[TEntity, TKey], Query[OperationResult[TEntity]]):
    ''' Represents the query used to get an entity by id'''
    pass


class ListQueryHandler(Generic[TEntity, TKey], QueryHandler[ListQuery[TEntity, TKey], OperationResult[TEntity]]):
    ''' Represents the service used to handle ListQuery instances '''

    def __init__(self, repository: QueryableRepository[TEntity, TKey]):
        self.repository = repository

    repository: QueryableRepository[TEntity, TKey]

    async def handle_async(self, query: ListQuery[TEntity, TKey]) -> OperationResult[TEntity]:
        res = await self.repository.query_async()
        return self.ok(res.to_list())
