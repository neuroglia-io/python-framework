"""Repository interface for managing kitchen state"""

from abc import ABC, abstractmethod

from neuroglia.data.infrastructure.abstractions import Repository
from domain.entities import Kitchen


class IKitchenRepository(Repository[Kitchen, str], ABC):
    """Repository interface for managing kitchen state"""

    @abstractmethod
    async def get_kitchen_state_async(self) -> Kitchen:
        """Get the current kitchen state (singleton)"""
        pass

    @abstractmethod
    async def update_kitchen_state_async(self, kitchen: Kitchen) -> Kitchen:
        """Update the kitchen state"""
        pass
