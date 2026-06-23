"""Pizza entity for Mario's Pizzeria domain"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from api.dtos import PizzaDto
from domain.entities.enums import PizzaSize
from domain.events import PizzaCreatedEvent, ToppingsUpdatedEvent
from multipledispatch import dispatch

from neuroglia.data.abstractions import AggregateRoot, AggregateState
from neuroglia.mapping.mapper import map_from, map_to


@dataclass
class PizzaState(AggregateState[str]):
    """
    State object for Pizza aggregate.

    Contains all pizza data that needs to be persisted, without any behavior.
    This is the data structure that gets serialized to MongoDB/files.

    Attributes:
        id: Unique identifier for the pizza
        name: Name of the pizza (e.g., "Margherita", "Pepperoni")
        base_price: Base price before size multiplier and toppings
        size: Size of the pizza (SMALL, MEDIUM, or LARGE)
        description: Optional description of the pizza
        toppings: List of topping names added to the pizza
        state_version: Version number for optimistic concurrency control (inherited)
        created_at: Timestamp when the pizza was created (inherited)

    Note:
        - Calculated fields like total_price are NOT stored here (computed in aggregate)
        - Methods and business logic belong in the Pizza aggregate, not here
        - This state is what gets serialized and persisted to storage
        - All fields have Optional defaults to support empty initialization by framework
    """

    # Core pizza data - all Optional with defaults for framework compatibility
    name: Optional[str] = None
    base_price: Optional[Decimal] = None
    size: Optional[PizzaSize] = None
    description: str = ""
    toppings: list[str] = field(default_factory=list)

    @dispatch(PizzaCreatedEvent)
    def on(self, event: PizzaCreatedEvent) -> None:
        """Handle PizzaCreatedEvent to initialize pizza state"""
        self.id = event.aggregate_id
        self.name = event.name
        self.base_price = event.base_price
        self.size = PizzaSize(event.size)  # Convert string to enum
        self.description = event.description or ""
        self.toppings = event.toppings.copy()

    @dispatch(ToppingsUpdatedEvent)
    def on(self, event: ToppingsUpdatedEvent) -> None:
        """Handle ToppingsUpdatedEvent to update toppings list"""
        self.toppings = event.toppings.copy()


@map_from(PizzaDto)
@map_to(PizzaDto)
class Pizza(AggregateRoot[PizzaState, str]):
    """
    Pizza aggregate root with pricing and toppings.

    Uses Neuroglia's AggregateRoot with state separation pattern:
    - All data in PizzaState (persisted)
    - All behavior in Pizza aggregate (not persisted)
    - Domain events registered and applied to state via multipledispatch
    """

    def __init__(self, name: str, base_price: Decimal, size: PizzaSize, description: Optional[str] = None):
        super().__init__()

        # Register event and apply it to state using multipledispatch
        self.state.on(
            self.register_event(
                PizzaCreatedEvent(
                    aggregate_id=str(uuid4()),
                    name=name,
                    size=size.value,
                    base_price=base_price,
                    description=description or "",
                    toppings=[],
                )
            )
        )

    @property
    def size_multiplier(self) -> Decimal:
        """Get price multiplier based on pizza size"""
        if self.state.size is None:
            return Decimal("1.0")
        multipliers = {
            PizzaSize.SMALL: Decimal("1.0"),
            PizzaSize.MEDIUM: Decimal("1.3"),
            PizzaSize.LARGE: Decimal("1.6"),
        }
        return multipliers[self.state.size]

    @property
    def topping_price(self) -> Decimal:
        """Calculate total price for all toppings"""
        return Decimal(str(len(self.state.toppings))) * Decimal("2.50")

    @property
    def total_price(self) -> Decimal:
        """Calculate total pizza price including size and toppings"""
        if self.state.base_price is None:
            return Decimal("0.00")
        base_with_size = self.state.base_price * self.size_multiplier
        return base_with_size + self.topping_price

    def add_topping(self, topping: str) -> None:
        """Add a topping to the pizza"""
        if topping not in self.state.toppings:
            new_toppings = self.state.toppings.copy()
            new_toppings.append(topping)

            # Register event and apply it to state
            self.state.on(self.register_event(ToppingsUpdatedEvent(aggregate_id=self.id(), toppings=new_toppings)))

    def remove_topping(self, topping: str) -> None:
        """Remove a topping from the pizza"""
        if topping in self.state.toppings:
            new_toppings = [t for t in self.state.toppings if t != topping]

            # Register event and apply it to state
            self.state.on(self.register_event(ToppingsUpdatedEvent(aggregate_id=self.id(), toppings=new_toppings)))

    def __str__(self) -> str:
        toppings_str = f" with {', '.join(self.state.toppings)}" if self.state.toppings else ""
        size_str = self.state.size.value.capitalize() if self.state.size else "Unknown"
        name_str = self.state.name if self.state.name else "Unnamed"
        return f"{size_str} {name_str}{toppings_str} - ${self.total_price:.2f}"
