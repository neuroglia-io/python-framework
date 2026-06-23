"""Repository interface for managing pizza menu items"""

from abc import ABC, abstractmethod
from typing import List, Optional

from neuroglia.data.infrastructure.abstractions import Repository
from domain.entities import Pizza


class IPizzaRepository(Repository[Pizza, str], ABC):
    """Repository interface for managing pizza menu items"""

    @abstractmethod
    async def get_by_name_async(self, name: str) -> Optional[Pizza]:
        """Get a pizza by name"""
        pass

    @abstractmethod
    async def get_available_pizzas_async(self) -> List[Pizza]:
        """Get all available pizzas for ordering"""
        pass

    @abstractmethod
    async def search_by_toppings_async(self, toppings: List[str]) -> List[Pizza]:
        """Search pizzas by toppings"""
        pass
