from abc import ABC, abstractmethod
from typing import Generic, List, Optional
from neuroglia.data.abstractions import TEntity, TKey
from neuroglia.data.queryable import Queryable


class Repository(Generic[TEntity, TKey], ABC):
    ''' Defines the fundamentals of a repository '''

    @abstractmethod
    async def contains_async(self, id: TKey) -> bool:
        ''' Determines whether or not the repository contains an entity with the specified id '''
        raise NotImplementedError()

    @abstractmethod
    async def get_async(self, id: TKey) -> Optional[TEntity]:
        ''' Gets the entity with the specified id, if any '''
        raise NotImplementedError()

    @abstractmethod
    async def add_async(self, entity: TEntity) -> TEntity:
        ''' Adds the specified entity '''
        raise NotImplementedError()

    @abstractmethod
    async def update_async(self, entity: TEntity) -> TEntity:
        ''' Persists the changes that were made to the specified entity '''
        raise NotImplementedError()

    @abstractmethod
    async def remove_async(self, id: TKey) -> None:
        ''' Removes the entity with the specified key '''
        raise NotImplementedError()


class QueryableRepository(Generic[TEntity, TKey], Repository[TEntity, TKey], ABC):
    ''' Defines the fundamentals of a queryable repository '''

    @abstractmethod
    async def query_async(self) -> Queryable[TEntity]:
        raise NotImplementedError()
