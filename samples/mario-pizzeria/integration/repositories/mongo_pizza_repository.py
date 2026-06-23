"""
MongoDB repository for Pizza aggregates using Neuroglia's MotorRepository.

This extends the framework's MotorRepository to provide Pizza-specific queries
while inheriting all standard CRUD operations with automatic domain event publishing.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from domain.entities import Pizza, PizzaSize
from domain.repositories import IPizzaRepository
from motor.motor_asyncio import AsyncIOMotorClient

from neuroglia.data.infrastructure.mongo import MotorRepository
from neuroglia.data.infrastructure.tracing_mixin import TracedRepositoryMixin
from neuroglia.serialization.json import JsonSerializer

if TYPE_CHECKING:
    from neuroglia.mediation.mediator import Mediator


class MongoPizzaRepository(TracedRepositoryMixin, MotorRepository[Pizza, str], IPizzaRepository):
    """
    Motor-based async MongoDB repository for Pizza aggregates with automatic tracing
    and domain event publishing.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations with
    automatic event publishing and adds Pizza-specific queries. TracedRepositoryMixin
    provides automatic OpenTelemetry instrumentation for all repository operations.
    """

    def __init__(
        self,
        client: AsyncIOMotorClient,
        database_name: str,
        collection_name: str,
        serializer: JsonSerializer,
        entity_type: type[Pizza],
        mediator: Optional["Mediator"] = None,
    ):
        """
        Initialize the Pizza repository.

        Args:
            client: Motor async MongoDB client
            database_name: Name of the MongoDB database
            collection_name: Name of the collection for pizzas
            serializer: JSON serializer for entity conversion
            entity_type: The Pizza entity type
            mediator: Optional Mediator for automatic domain event publishing
        """
        super().__init__(
            client=client,
            database_name=database_name,
            collection_name=collection_name,
            serializer=serializer,
            mediator=mediator,
        )
        # Flag to track if initialization has been attempted
        self._initialized = False

    # Custom Pizza-specific queries
    # Note: Standard CRUD operations (add_async, update_async, delete_async, etc.)
    # are inherited from MotorRepository

    async def get_by_name_async(self, name: str) -> Optional[Pizza]:
        """Get a pizza by name"""
        pizzas = await self.find_async({"state.name": {"$regex": f"^{name}$", "$options": "i"}})
        return pizzas[0] if pizzas else None

    async def get_available_pizzas_async(self) -> list[Pizza]:
        """
        Get all available pizzas for ordering.
        Initializes default menu if needed on first call.
        """
        if not self._initialized:
            # Check if we need to initialize data
            existing_pizzas = await self.find_async({})
            if len(existing_pizzas) == 0:
                await self._ensure_default_menu_exists()
            self._initialized = True

        return await self.find_async({})

    async def search_by_toppings_async(self, toppings: list[str]) -> list[Pizza]:
        """
        Search pizzas by toppings.
        Returns pizzas that contain all specified toppings.
        """
        if not toppings:
            return []

        # MongoDB query to find pizzas that contain all specified toppings
        query = {"state.toppings": {"$all": toppings}}
        return await self.find_async(query)

    async def get_by_size_async(self, size: PizzaSize) -> list[Pizza]:
        """Get all pizzas of a specific size"""
        return await self.find_async({"state.size": size.value})

    async def get_by_price_range_async(self, min_price: Decimal, max_price: Decimal) -> list[Pizza]:
        """
        Get pizzas within a price range.
        Note: Since total_price is calculated, we need to filter after retrieval.
        """
        all_pizzas = await self.find_async({})
        return [pizza for pizza in all_pizzas if min_price <= pizza.total_price <= max_price]

    async def _ensure_default_menu_exists(self) -> None:
        """Initialize the database with default menu items if empty"""
        default_pizzas = [
            Pizza(
                name="Margherita",
                base_price=Decimal("12.99"),
                size=PizzaSize.MEDIUM,
                description="Classic pizza with tomato sauce, mozzarella, and fresh basil",
            ),
            Pizza(
                name="Pepperoni",
                base_price=Decimal("14.99"),
                size=PizzaSize.MEDIUM,
                description="Traditional pepperoni with mozzarella cheese",
            ),
            Pizza(
                name="Vegetarian",
                base_price=Decimal("13.99"),
                size=PizzaSize.MEDIUM,
                description="Fresh vegetables including bell peppers, mushrooms, onions, and olives",
            ),
            Pizza(
                name="Hawaiian",
                base_price=Decimal("14.99"),
                size=PizzaSize.MEDIUM,
                description="Ham and pineapple with mozzarella cheese",
            ),
            Pizza(
                name="BBQ Chicken",
                base_price=Decimal("15.99"),
                size=PizzaSize.MEDIUM,
                description="Grilled chicken with BBQ sauce, red onions, and cilantro",
            ),
            Pizza(
                name="Meat Lovers",
                base_price=Decimal("16.99"),
                size=PizzaSize.MEDIUM,
                description="Loaded with pepperoni, sausage, bacon, and ham",
            ),
        ]

        # Add toppings to some pizzas
        default_pizzas[1].add_topping("Pepperoni")  # Pepperoni
        default_pizzas[2].add_topping("Bell Peppers")  # Vegetarian
        default_pizzas[2].add_topping("Mushrooms")
        default_pizzas[2].add_topping("Onions")
        default_pizzas[2].add_topping("Olives")
        default_pizzas[3].add_topping("Ham")  # Hawaiian
        default_pizzas[3].add_topping("Pineapple")
        default_pizzas[4].add_topping("Chicken")  # BBQ Chicken
        default_pizzas[4].add_topping("Red Onions")
        default_pizzas[5].add_topping("Pepperoni")  # Meat Lovers
        default_pizzas[5].add_topping("Sausage")
        default_pizzas[5].add_topping("Bacon")
        default_pizzas[5].add_topping("Ham")

        # Save all default pizzas
        for pizza in default_pizzas:
            await self.add_async(pizza)
