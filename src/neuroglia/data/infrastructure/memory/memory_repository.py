from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Optional

from neuroglia.data.abstractions import TEntity, TKey
from neuroglia.data.infrastructure.abstractions import Repository

if TYPE_CHECKING:
    from neuroglia.mediation.mediator import Mediator


class MemoryRepository(Repository[TEntity, TKey]):
    """
    In-memory repository implementation for testing and rapid prototyping.

    This repository stores entities in a dictionary and provides full CRUD
    operations with automatic domain event publishing support.

    Examples:
        ```python
        # With event publishing
        repo = MemoryRepository[Order, str](mediator=mediator)
        order = Order.create(customer_id="123")
        await repo.add_async(order)  # Events published automatically

        # For testing - disable events
        test_repo = MemoryRepository[Order, str](mediator=None)
        await test_repo.add_async(order)  # No events published
        ```
    """

    def __init__(self, mediator: Optional["Mediator"] = None):
        """
        Initialize the memory repository.

        Args:
            mediator: Optional Mediator instance for publishing domain events
        """
        super().__init__(mediator)
        self.entities: dict = {}

    def _get_entity_id(self, entity: TEntity) -> TKey:
        """Get the entity's ID, handling both property and method access."""
        entity_id = entity.id
        # If id is a method, call it to get the actual ID value
        if callable(entity_id):
            entity_id = entity_id()
        return entity_id

    async def contains_async(self, id: TKey) -> bool:
        return self.entities.get(id) is not None

    async def get_async(self, id: TKey) -> Optional[TEntity]:
        return self.entities.get(id, None)

    async def _do_add_async(self, entity: TEntity) -> TEntity:
        entity_id = self._get_entity_id(entity)
        if entity_id in self.entities:
            raise Exception()
        self.entities[entity_id] = entity
        return entity

    async def _do_update_async(self, entity: TEntity) -> TEntity:
        entity_id = self._get_entity_id(entity)
        self.entities[entity_id] = entity
        return entity

    async def _do_remove_async(self, id: TKey) -> None:
        if id not in self.entities:
            raise Exception()
        del self.entities[id]

    def find(self, predicate: Callable[[TEntity], bool]) -> Iterable[TEntity]:
        """
        Find entities matching a predicate.

        Args:
            predicate: A function that takes an entity and returns True if it matches

        Returns:
            An iterable of matching entities

        Example:
            # Find all products in Electronics category with price < 100
            results = repository.find(lambda p: p.category == "Electronics" and p.price < 100)
        """
        return (entity for entity in self.entities.values() if predicate(entity))
