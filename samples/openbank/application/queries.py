from typing import Any, Generic
from neuroglia.core.operation_result import OperationResult
from neuroglia.data.abstractions import TEntity, TKey
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.mediation.mediator import Query, QueryHandler

class GetByIdQuery(Query[OperationResult[TEntity]], Generic[TEntity, TKey]):
    ''' Represents the query used to get an entity by id'''
    
    def __init__(self, id: Any):
        self.id = id

    id : Any
    ''' Gets the id of the entity to get '''
    
class GetByIdQueryHandler(QueryHandler[GetByIdQuery[TEntity, TKey], OperationResult[TEntity]], Generic[TEntity, TKey]):
    ''' Represents the service used to handle GetByIdQuery instances '''
    
    def __init__(self, repository : Repository[TEntity, TKey]):
        self.repository = repository
        
    repository : Repository[TEntity, TKey]

    async def handle_async(self, query : GetByIdQuery[TEntity, TKey]) -> OperationResult[TEntity]:
        entity = await self.repository.get_async(query.id)
        result = OperationResult[str]('NOT FOUND', 404) if entity is None else OperationResult[str]('OK', 200)
        result.data = entity
        return result   