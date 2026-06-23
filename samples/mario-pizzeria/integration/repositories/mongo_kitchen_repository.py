"""
MongoDB repository for Kitchen entity using Neuroglia's MotorRepository.

The Kitchen is a singleton entity that manages kitchen capacity and order processing state.
This repository ensures only one Kitchen instance exists in the database with automatic
domain event publishing.
"""

from typing import TYPE_CHECKING, Optional

from domain.entities import Kitchen
from domain.repositories import IKitchenRepository
from motor.motor_asyncio import AsyncIOMotorClient

from neuroglia.data.infrastructure.mongo import MotorRepository
from neuroglia.data.infrastructure.tracing_mixin import TracedRepositoryMixin
from neuroglia.serialization.json import JsonSerializer

if TYPE_CHECKING:
    from neuroglia.mediation.mediator import Mediator


class MongoKitchenRepository(TracedRepositoryMixin, MotorRepository[Kitchen, str], IKitchenRepository):
    """
    Motor-based async MongoDB repository for Kitchen entity (singleton) with automatic tracing
    and domain event publishing.

    The Kitchen is a singleton entity with a fixed ID of "kitchen".
    This repository handles initialization and ensures only one Kitchen exists.
    TracedRepositoryMixin provides automatic OpenTelemetry instrumentation.
    """

    def __init__(
        self,
        client: AsyncIOMotorClient,
        database_name: str,
        collection_name: str,
        serializer: JsonSerializer,
        entity_type: type[Kitchen],
        mediator: Optional["Mediator"] = None,
    ):
        """
        Initialize the Kitchen repository.

        Args:
            client: Motor async MongoDB client
            database_name: Name of the database
            collection_name: Name of the collection
            serializer: JSON serializer for entity conversion
            entity_type: Type of entity stored in this repository
            mediator: Optional Mediator for automatic domain event publishing
        """
        super().__init__(
            client=client,
            database_name=database_name,
            collection_name=collection_name,
            serializer=serializer,
            mediator=mediator,
        )

    # Custom Kitchen-specific methods
    # Note: Standard CRUD operations (get_async, add_async, update_async, etc.)
    # are inherited from MotorRepository

    async def get_kitchen_state_async(self) -> Kitchen:
        """
        Get the current kitchen state (singleton).

        Returns the single Kitchen instance, creating it with default settings
        if it doesn't exist yet.

        Returns:
            Kitchen: The singleton kitchen instance

        Raises:
            RuntimeError: If kitchen cannot be retrieved or created
        """
        # Try to get existing kitchen
        kitchen = await self.get_async("kitchen")

        if kitchen is None:
            # Create default kitchen on first access
            kitchen = Kitchen(max_concurrent_orders=5)
            kitchen.id = "kitchen"  # Ensure singleton ID
            await self.add_async(kitchen)

        return kitchen

    async def update_kitchen_state_async(self, kitchen: Kitchen) -> Kitchen:
        """
        Update the kitchen state.

        Args:
            kitchen: Kitchen entity with updated state

        Returns:
            Kitchen: The updated kitchen instance
        """
        # Ensure the kitchen ID is always "kitchen" (singleton)
        if kitchen.id != "kitchen":
            kitchen.id = "kitchen"

        await self.update_async(kitchen)
        return kitchen

    async def get_kitchen_async(self) -> Optional[Kitchen]:
        """
        Get the kitchen instance (singleton).

        Convenience method that returns None if kitchen doesn't exist,
        rather than creating a default one.

        Returns:
            Optional[Kitchen]: The kitchen instance or None
        """
        return await self.get_async("kitchen")

    async def save_kitchen_async(self, kitchen: Kitchen) -> Kitchen:
        """
        Save the kitchen state.

        Alias for update_kitchen_state_async for backward compatibility.

        Args:
            kitchen: Kitchen entity to save

        Returns:
            Kitchen: The saved kitchen instance
        """
        return await self.update_kitchen_state_async(kitchen)
