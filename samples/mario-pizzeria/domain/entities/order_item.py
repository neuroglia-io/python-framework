"""OrderItem value object for Mario's Pizzeria domain"""

from dataclasses import dataclass
from decimal import Decimal

from .enums import PizzaSize


@dataclass(frozen=True)
class OrderItem:
    """
    Value object representing a pizza item in an order.

    This is a snapshot of pizza data at the time of order creation.
    It does NOT reference the Pizza aggregate - it captures the relevant
    data needed for the order.

    This follows proper DDD: Orders and Pizzas are separate aggregates,
    and we use value objects to capture cross-aggregate data.
    """

    line_item_id: str  # Unique identifier for this line item in the order
    name: str
    size: PizzaSize
    base_price: Decimal
    toppings: list[str]

    @property
    def topping_price(self) -> Decimal:
        """Calculate price for all toppings (each topping adds 20% to base)"""
        return self.base_price * Decimal("0.2") * len(self.toppings)

    @property
    def size_multiplier(self) -> Decimal:
        """Get size multiplier"""
        multipliers = {
            PizzaSize.SMALL: Decimal("0.8"),
            PizzaSize.MEDIUM: Decimal("1.0"),
            PizzaSize.LARGE: Decimal("1.6"),
        }
        return multipliers.get(self.size, Decimal("1.0"))

    @property
    def total_price(self) -> Decimal:
        """Calculate total price: (base + toppings) * size_multiplier"""
        base_with_toppings = self.base_price + self.topping_price
        return base_with_toppings * self.size_multiplier

    def __post_init__(self):
        """Validate the order item"""
        if not self.line_item_id:
            raise ValueError("line_item_id is required")
        if not self.name:
            raise ValueError("name is required")
        if self.base_price <= 0:
            raise ValueError("base_price must be positive")
        # Convert toppings to immutable tuple for frozen dataclass
        object.__setattr__(
            self,
            "toppings",
            tuple(self.toppings) if isinstance(self.toppings, list) else self.toppings,
        )
