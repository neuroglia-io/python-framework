"""File-based implementation of pizza repository using generic FileSystemRepository"""

from decimal import Decimal
from typing import Optional

from domain.entities import Pizza, PizzaSize
from domain.repositories import IPizzaRepository

from neuroglia.data.infrastructure.filesystem import FileSystemRepository


class FilePizzaRepository(FileSystemRepository[Pizza, str], IPizzaRepository):
    """File-based implementation of pizza repository using generic FileSystemRepository"""

    def __init__(self, data_directory: str = "data"):
        super().__init__(data_directory=data_directory, entity_type=Pizza, key_type=str)
        # Flag to track if initialization has been attempted
        self._initialized = False

    async def get_by_name_async(self, name: str) -> Optional[Pizza]:
        """Get a pizza by name"""
        all_pizzas = await self.get_all_async()
        for pizza in all_pizzas:
            if pizza.name.lower() == name.lower():
                return pizza
        return None

    async def get_by_size_async(self, size: PizzaSize) -> list[Pizza]:
        """Get all pizzas of a specific size"""
        all_pizzas = await self.get_all_async()
        return [pizza for pizza in all_pizzas if pizza.size == size]

    async def get_by_price_range_async(self, min_price: Decimal, max_price: Decimal) -> list[Pizza]:
        """Get pizzas within a price range"""
        all_pizzas = await self.get_all_async()
        return [pizza for pizza in all_pizzas if min_price <= pizza.total_price <= max_price]

    async def get_menu_pizzas_async(self) -> list[Pizza]:
        """Get all pizzas available on the menu"""
        return await self.get_all_async()

    async def get_all_async(self) -> list[Pizza]:
        """Get all pizzas, initializing default menu if needed"""
        if not self._initialized:
            # Check if we need to initialize data
            existing_pizzas = await super().get_all_async()
            if len(existing_pizzas) == 0:
                await self._ensure_default_menu_exists()
            self._initialized = True
        return await super().get_all_async()

    async def get_available_pizzas_async(self) -> list[Pizza]:
        """Get all available pizzas for ordering"""
        return await self.get_all_async()

    async def search_by_toppings_async(self, toppings: list[str]) -> list[Pizza]:
        """Search pizzas by toppings"""
        all_pizzas = await self.get_all_async()
        matching_pizzas = []
        for pizza in all_pizzas:
            if any(topping in pizza.toppings for topping in toppings):
                matching_pizzas.append(pizza)
        return matching_pizzas

    async def _ensure_default_menu_exists(self):
        """Initialize default menu if no pizzas exist"""
        try:
            # Create default pizzas
            margherita = Pizza(
                "Margherita",
                Decimal("15.99"),
                PizzaSize.LARGE,
                "Classic tomato sauce, mozzarella, and fresh basil",
            )
            margherita.toppings = ["tomato sauce", "mozzarella", "basil"]

            pepperoni = Pizza(
                "Pepperoni",
                Decimal("17.99"),
                PizzaSize.LARGE,
                "Tomato sauce, mozzarella, and pepperoni",
            )
            pepperoni.toppings = ["tomato sauce", "mozzarella", "pepperoni"]

            quattro = Pizza(
                "Quattro Stagioni",
                Decimal("19.99"),
                PizzaSize.LARGE,
                "Four seasons pizza with mushrooms, ham, artichokes, and olives",
            )
            quattro.toppings = [
                "tomato sauce",
                "mozzarella",
                "mushrooms",
                "ham",
                "artichokes",
                "olives",
            ]

            # Add to repository
            await self.add_async(margherita)
            await self.add_async(pepperoni)
            await self.add_async(quattro)
        except Exception:
            # Ignore initialization errors to avoid blocking the application
            pass
