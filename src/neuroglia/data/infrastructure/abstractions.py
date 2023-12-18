from abc import ABC, abstractmethod
from typing import Generic, List, Optional
from neuroglia.data.abstractions import TEntity, TKey

class Repository(Generic[TEntity, TKey], ABC):
    ''' Defines the fundamentals of a repository '''

    @abstractmethod
    def contains(self, id: TKey) -> bool:
        ''' Determines whether or not the repository contains an entity with the specified id '''
        raise NotImplementedError()

    @abstractmethod
    def get(self, id: TKey) -> Optional[TEntity]:
        ''' Gets the entity with the specified id, if any '''
        raise NotImplementedError()

    @abstractmethod
    def add(self, entity: TEntity) -> TEntity:
        ''' Adds the specified entity '''
        raise NotImplementedError()

    @abstractmethod
    def update(self, entity: TEntity) -> TEntity:
        ''' Persists the changes that were made to the specified entity '''
        raise NotImplementedError()

    @abstractmethod
    def remove(self, id: TKey) -> None:
        ''' Removes the entity with the specified key '''
        raise NotImplementedError()
    
class QueryableRepository(Generic[TEntity, TKey], Repository[TEntity, TKey], ABC):
    ''' Defines the fundamentals of a queryable repository '''
    
    @abstractmethod
    def query(self) -> List[TEntity]:
        raise NotImplementedError()