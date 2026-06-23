"""Kitchen entity for Mario's Pizzeria domain"""


from api.dtos import KitchenStatusDto

from neuroglia.data.abstractions import Entity
from neuroglia.mapping.mapper import map_from, map_to


@map_from(KitchenStatusDto)
@map_to(KitchenStatusDto)
class Kitchen(Entity[str]):
    """Kitchen state and capacity management"""

    def __init__(self, max_concurrent_orders: int = 3):
        super().__init__()
        self.id = "kitchen"  # Singleton kitchen
        self.active_orders: list[str] = []  # Order IDs currently being prepared
        self.max_concurrent_orders = max_concurrent_orders
        self.total_orders_processed = 0

    @property
    def current_capacity(self) -> int:
        """Get current number of orders being prepared"""
        return len(self.active_orders)

    @property
    def available_capacity(self) -> int:
        """Get remaining capacity for new orders"""
        return self.max_concurrent_orders - self.current_capacity

    @property
    def is_at_capacity(self) -> bool:
        """Check if kitchen is at maximum capacity"""
        return self.current_capacity >= self.max_concurrent_orders

    def start_order(self, order_id: str) -> bool:
        """Start preparing an order if capacity allows"""
        if self.is_at_capacity:
            return False

        if order_id not in self.active_orders:
            self.active_orders.append(order_id)

        return True

    def complete_order(self, order_id: str) -> None:
        """Mark an order as completed and free up capacity"""
        if order_id in self.active_orders:
            self.active_orders.remove(order_id)
            self.total_orders_processed += 1
