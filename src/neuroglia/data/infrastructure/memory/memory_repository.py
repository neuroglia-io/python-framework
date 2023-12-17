from typing import Optional
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.data.abstractions import TEntity, TKey
    
class MemoryRepository(Repository[TEntity, TKey]):
   
    entities: dict = {}

    def get(self, id: TKey) -> Optional[TEntity]:
        return self.entities[id];

    def add(self, entity: TEntity) -> TEntity:
        if entity.id in self.entities: raise Exception();
        self.entities[entity.id] = entity;
        return entity;

    def update(self, entity: TEntity) -> TEntity:
        self.entities[entity.id] = entity;
        return entity;

    def remove(self, id: TKey) -> None:
        if not id in self.entities: raise Exception();
        del self.entities[id]