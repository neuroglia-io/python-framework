"""File-based implementation of kitchen repository using generic FileSystemRepository"""

from typing import Optional

from domain.entities import Kitchen
from domain.repositories import IKitchenRepository

from neuroglia.data.infrastructure.filesystem import FileSystemRepository


class FileKitchenRepository(FileSystemRepository[Kitchen, str], IKitchenRepository):
    """File-based implementation of kitchen repository using generic FileSystemRepository"""

    def __init__(self, data_directory: str = "data"):
        super().__init__(data_directory=data_directory, entity_type=Kitchen, key_type=str)

    async def get_kitchen_async(self) -> Optional[Kitchen]:
        """Get the kitchen instance (singleton)"""
        kitchen = await self.get_async("kitchen")
        if kitchen is None:
            # Create default kitchen
            kitchen = Kitchen(max_concurrent_orders=5)
            kitchen.id = "kitchen"  # Ensure singleton ID
            kitchen = await self.add_async(kitchen)
        return kitchen

    async def save_kitchen_async(self, kitchen: Kitchen) -> Kitchen:
        """Save the kitchen state"""
        return await self.update_async(kitchen)

    async def get_kitchen_state_async(self) -> Kitchen:
        """Get the current kitchen state (singleton)"""
        kitchen = await self.get_kitchen_async()
        if kitchen is None:
            raise RuntimeError("Kitchen not found")
        return kitchen

    async def update_kitchen_state_async(self, kitchen: Kitchen) -> Kitchen:
        """Update the kitchen state"""
        return await self.update_async(kitchen)
