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


class FlexibleRepository(Generic[TEntity, TKey], Repository[TEntity, TKey], ABC):
    ''' Defines the fundamentals of a flexible repository '''

    @abstractmethod
    async def set_database(self, database: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def get_database(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def contains_by_collection_name_async(self, collection_nam: str, id: TKey) -> bool:
        ''' Determines whether or not the repository contains an entity with the specified id '''
        raise NotImplementedError()

    @abstractmethod
    async def get_by_collection_name_async(self, collection_name: str, id: TKey) -> Optional[TEntity]:
        ''' Gets the entity with the specified id, if any '''
        raise NotImplementedError()

    @abstractmethod
    async def add_by_collection_name_async(self, collection_name: str, entity: TEntity) -> TEntity:
        ''' Adds the specified entity '''
        raise NotImplementedError()

    @abstractmethod
    async def update_by_collection_name_async(self, collection_name: str, entity: TEntity) -> TEntity:
        ''' Persists the changes that were made to the specified entity '''
        raise NotImplementedError()

    @abstractmethod
    async def remove_by_collection_name_async(self, collection_name: str, id: TKey) -> None:
        ''' Removes the entity with the specified key '''
        raise NotImplementedError()
