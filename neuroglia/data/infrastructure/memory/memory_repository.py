from typing import Optional
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.data.abstractions import TEntity, TKey


class MemoryRepository(Repository[TEntity, TKey]):

    entities: dict = {}

    async def contains_async(self, id: TKey) -> bool:
        return self.entities.get(id) is not None

    async def get_async(self, id: TKey) -> Optional[TEntity]:
        return self.entities.get(id, None)

    async def add_async(self, entity: TEntity) -> TEntity:
        if entity.id in self.entities:
            raise Exception()
        self.entities[entity.id] = entity
        return entity

    async def update_async(self, entity: TEntity) -> TEntity:
        self.entities[entity.id] = entity
        return entity

    async def remove_async(self, id: TKey) -> None:
        if not id in self.entities:
            raise Exception()
        del self.entities[id]
