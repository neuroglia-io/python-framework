# 🏛️ Python Object-Oriented Programming Reference

Object-Oriented Programming (OOP) is fundamental to the Neuroglia framework's design. Understanding these concepts is essential for building maintainable, extensible applications.

## 🎯 What is Object-Oriented Programming?

OOP is a programming paradigm that organizes code around objects (data and methods that work on that data) rather than functions and logic. Think of it as creating blueprints (classes) for real-world entities.

### The Pizza Restaurant Analogy

```python
# Real world: A pizza restaurant has different roles and responsibilities

# ❌ Procedural approach - everything is functions:
def make_pizza(name, ingredients, size):
    pass

def take_order(customer_name, items):
    pass

def calculate_bill(items, discounts):
    pass

def manage_inventory(ingredient, quantity):
    pass

# ✅ Object-oriented approach - organize by entities:
class Pizza:
    """A pizza entity with its own data and behaviors."""
    def __init__(self, name, ingredients, size):
        self.name = name
        self.ingredients = ingredients
        self.size = size

    def calculate_price(self):
        # Pizza knows how to calculate its own price
        pass

    def add_ingredient(self, ingredient):
        # Pizza knows how to modify itself
        pass

class Chef:
    """A chef entity that knows how to make pizzas."""
    def make_pizza(self, pizza_order):
        # Chef knows how to make pizzas
        pass

class Waiter:
    """A waiter entity that handles customer interactions."""
    def take_order(self, customer, menu):
        # Waiter knows how to interact with customers
        pass

class CashRegister:
    """A cash register that handles billing."""
    def calculate_bill(self, order):
        # Cash register knows how to calculate bills
        pass
```

## 🔧 Core OOP Concepts

### 1. Classes and Objects

A **class** is a blueprint, an **object** is an instance of that blueprint:

```python
from typing import List
from datetime import datetime
from dataclasses import dataclass

# Class definition - the blueprint
@dataclass
class Pizza:
    """Blueprint for creating pizza objects."""
    name: str
    price: float
    ingredients: List[str]
    size: str = "medium"
    created_at: datetime = None

    def __post_init__(self):
        """Called after object creation."""
        if self.created_at is None:
            self.created_at = datetime.now()

    # Methods - what pizzas can do
    def add_ingredient(self, ingredient: str) -> None:
        """Add an ingredient to this pizza."""
        if ingredient not in self.ingredients:
            self.ingredients.append(ingredient)

    def remove_ingredient(self, ingredient: str) -> None:
        """Remove an ingredient from this pizza."""
        if ingredient in self.ingredients:
            self.ingredients.remove(ingredient)

    def calculate_cost(self) -> float:
        """Calculate the cost to make this pizza."""
        base_cost = {"small": 6.0, "medium": 8.0, "large": 10.0}
        ingredient_cost = len(self.ingredients) * 0.75
        return base_cost[self.size] + ingredient_cost

    def __str__(self) -> str:
        """String representation of the pizza."""
        return f"{self.size.title()} {self.name} - ${self.price:.2f}"

# Creating objects - instances of the class
margherita = Pizza(
    name="Margherita",
    price=12.99,
    ingredients=["tomato sauce", "mozzarella", "basil"]
)

pepperoni = Pizza(
    name="Pepperoni",
    price=14.99,
    ingredients=["tomato sauce", "mozzarella", "pepperoni"],
    size="large"
)

# Objects have their own data and can perform actions
margherita.add_ingredient("extra cheese")
print(f"Margherita cost to make: ${margherita.calculate_cost():.2f}")
print(f"Pepperoni: {pepperoni}")

# Each object is independent
print(f"Margherita ingredients: {margherita.ingredients}")
print(f"Pepperoni ingredients: {pepperoni.ingredients}")
```

### 2. Encapsulation - Data Hiding

Encapsulation bundles data and methods together and controls access to them:

```python
from typing import Optional

class Customer:
    """Customer entity with controlled access to data."""

    def __init__(self, name: str, email: str):
        self._name = name           # Protected attribute (internal use)
        self._email = email         # Protected attribute
        self.__loyalty_points = 0   # Private attribute (name mangling)
        self._orders = []           # Protected attribute

    # Public interface - how external code interacts with Customer
    @property
    def name(self) -> str:
        """Get customer name (read-only)."""
        return self._name

    @property
    def email(self) -> str:
        """Get customer email."""
        return self._email

    @email.setter
    def email(self, new_email: str) -> None:
        """Set customer email with validation."""
        if "@" not in new_email or "." not in new_email:
            raise ValueError("Invalid email format")
        self._email = new_email

    @property
    def loyalty_points(self) -> int:
        """Get loyalty points (read-only from outside)."""
        return self.__loyalty_points

    def add_loyalty_points(self, points: int) -> None:
        """Add loyalty points (controlled method)."""
        if points > 0:
            self.__loyalty_points += points

    def redeem_points(self, points: int) -> bool:
        """Redeem loyalty points."""
        if points > 0 and points <= self.__loyalty_points:
            self.__loyalty_points -= points
            return True
        return False

    def place_order(self, order: 'Order') -> None:
        """Place an order and earn points."""
        self._orders.append(order)
        # Earn 1 point per dollar spent
        points_earned = int(order.total_amount())
        self.add_loyalty_points(points_earned)

    def get_order_history(self) -> List['Order']:
        """Get copy of order history (don't expose internal list)."""
        return self._orders.copy()

# Usage demonstrates encapsulation:
customer = Customer("Mario", "mario@email.com")

# ✅ Public interface works correctly:
print(f"Customer: {customer.name}")
print(f"Points: {customer.loyalty_points}")

customer.add_loyalty_points(100)
print(f"Points after addition: {customer.loyalty_points}")

# ✅ Validation works:
try:
    customer.email = "invalid-email"
except ValueError as e:
    print(f"Error: {e}")

# ❌ Direct access to private data is discouraged:
# customer.__loyalty_points = 1000  # This won't work as expected
# customer._orders.clear()          # Breaks encapsulation, but possible
```

### 3. Inheritance - Extending Behavior

Inheritance allows classes to inherit properties and methods from parent classes:

```python
from abc import ABC, abstractmethod
from typing import List, Dict
from enum import Enum

class MenuItemType(Enum):
    PIZZA = "pizza"
    DRINK = "drink"
    DESSERT = "dessert"
    APPETIZER = "appetizer"

# Base class - common behavior for all menu items
class MenuItem(ABC):
    """Abstract base class for all menu items."""

    def __init__(self, name: str, price: float, description: str):
        self.name = name
        self.price = price
        self.description = description
        self.is_available = True

    @abstractmethod
    def get_type(self) -> MenuItemType:
        """Each menu item must specify its type."""
        pass

    @abstractmethod
    def calculate_preparation_time(self) -> int:
        """Each menu item must specify preparation time in minutes."""
        pass

    def apply_discount(self, percentage: float) -> float:
        """Common discount calculation."""
        if 0 <= percentage <= 100:
            return self.price * (1 - percentage / 100)
        return self.price

    def __str__(self) -> str:
        status = "Available" if self.is_available else "Unavailable"
        return f"{self.name} - ${self.price:.2f} ({status})"

# Derived classes - specialized menu items
class Pizza(MenuItem):
    """Pizza menu item with pizza-specific behavior."""

    def __init__(self, name: str, price: float, description: str,
                 ingredients: List[str], size: str = "medium"):
        super().__init__(name, price, description)  # Call parent constructor
        self.ingredients = ingredients
        self.size = size
        self.crust_type = "regular"

    def get_type(self) -> MenuItemType:
        """Pizzas are PIZZA type."""
        return MenuItemType.PIZZA

    def calculate_preparation_time(self) -> int:
        """Pizza prep time depends on size and toppings."""
        base_time = {"small": 12, "medium": 15, "large": 18}
        topping_time = len(self.ingredients) * 2
        return base_time.get(self.size, 15) + topping_time

    # Pizza-specific methods
    def add_ingredient(self, ingredient: str) -> None:
        """Add ingredient to pizza."""
        if ingredient not in self.ingredients:
            self.ingredients.append(ingredient)
            self.price += 1.50  # Extra topping cost

    def set_crust_type(self, crust: str) -> None:
        """Change crust type."""
        crust_options = ["thin", "regular", "thick", "gluten-free"]
        if crust in crust_options:
            self.crust_type = crust
            if crust == "gluten-free":
                self.price += 2.00

class Drink(MenuItem):
    """Drink menu item."""

    def __init__(self, name: str, price: float, description: str,
                 size: str = "medium", is_alcoholic: bool = False):
        super().__init__(name, price, description)
        self.size = size
        self.is_alcoholic = is_alcoholic
        self.temperature = "cold"

    def get_type(self) -> MenuItemType:
        return MenuItemType.DRINK

    def calculate_preparation_time(self) -> int:
        """Drinks are quick to prepare."""
        return 2 if not self.is_alcoholic else 5

    def set_temperature(self, temp: str) -> None:
        """Set drink temperature."""
        if temp in ["hot", "cold", "room temperature"]:
            self.temperature = temp

class Dessert(MenuItem):
    """Dessert menu item."""

    def __init__(self, name: str, price: float, description: str,
                 serving_size: str = "individual"):
        super().__init__(name, price, description)
        self.serving_size = serving_size
        self.is_homemade = True

    def get_type(self) -> MenuItemType:
        return MenuItemType.DESSERT

    def calculate_preparation_time(self) -> int:
        """Dessert prep time varies by type."""
        if "cake" in self.name.lower():
            return 10
        elif "ice cream" in self.name.lower():
            return 3
        return 5

# Polymorphism - treating different types the same way
def create_sample_menu() -> List[MenuItem]:
    """Create a sample menu with different item types."""
    return [
        Pizza("Margherita", 12.99, "Classic tomato and mozzarella",
              ["tomato sauce", "mozzarella", "basil"]),
        Pizza("Pepperoni", 14.99, "Pepperoni with mozzarella",
              ["tomato sauce", "mozzarella", "pepperoni"], size="large"),
        Drink("Coca Cola", 2.99, "Classic soft drink", size="large"),
        Drink("House Wine", 8.99, "Italian red wine", is_alcoholic=True),
        Dessert("Tiramisu", 6.99, "Classic Italian dessert"),
        Dessert("Gelato", 4.99, "Italian ice cream")
    ]

# Usage - polymorphism in action
menu = create_sample_menu()

print("=== Mario's Menu ===")
total_prep_time = 0

for item in menu:  # Each item behaves according to its specific type
    print(f"{item}")
    print(f"  Type: {item.get_type().value}")
    print(f"  Prep time: {item.calculate_preparation_time()} minutes")
    print(f"  With 10% discount: ${item.apply_discount(10):.2f}")
    print()

    total_prep_time += item.calculate_preparation_time()

print(f"Total preparation time for all items: {total_prep_time} minutes")
```

### 4. Composition - "Has-A" Relationships

Composition builds objects by combining other objects:

```python
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from enum import Enum

class OrderStatus(Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class OrderItem:
    """Represents one item in an order."""

    def __init__(self, menu_item: MenuItem, quantity: int = 1,
                 special_instructions: str = ""):
        self.menu_item = menu_item
        self.quantity = quantity
        self.special_instructions = special_instructions
        self.unit_price = menu_item.price
        self.created_at = datetime.now()

    def get_total_price(self) -> float:
        """Calculate total price for this item."""
        return self.unit_price * self.quantity

    def get_preparation_time(self) -> int:
        """Calculate total preparation time."""
        return self.menu_item.calculate_preparation_time() * self.quantity

    def __str__(self) -> str:
        special = f" ({self.special_instructions})" if self.special_instructions else ""
        return f"{self.quantity}x {self.menu_item.name}{special} - ${self.get_total_price():.2f}"

class Order:
    """Order composed of multiple order items, customer, and status."""

    def __init__(self, customer: Customer, order_id: str = None):
        self.customer = customer              # Composition: Order HAS-A Customer
        self.order_id = order_id or self._generate_id()
        self.items: List[OrderItem] = []      # Composition: Order HAS-MANY OrderItems
        self.status = OrderStatus.PENDING
        self.created_at = datetime.now()
        self.estimated_ready_time: Optional[datetime] = None
        self.discount_percentage = 0.0
        self.tax_rate = 0.08  # 8% tax

    def add_item(self, menu_item: MenuItem, quantity: int = 1,
                 special_instructions: str = "") -> None:
        """Add an item to the order."""
        order_item = OrderItem(menu_item, quantity, special_instructions)
        self.items.append(order_item)
        self._update_estimated_time()

    def remove_item(self, item_index: int) -> bool:
        """Remove an item from the order."""
        if 0 <= item_index < len(self.items):
            del self.items[item_index]
            self._update_estimated_time()
            return True
        return False

    def apply_discount(self, percentage: float) -> None:
        """Apply discount to the entire order."""
        if 0 <= percentage <= 50:  # Max 50% discount
            self.discount_percentage = percentage

    def calculate_subtotal(self) -> float:
        """Calculate order subtotal."""
        return sum(item.get_total_price() for item in self.items)

    def calculate_discount_amount(self) -> float:
        """Calculate discount amount."""
        return self.calculate_subtotal() * (self.discount_percentage / 100)

    def calculate_tax_amount(self) -> float:
        """Calculate tax amount."""
        subtotal_after_discount = self.calculate_subtotal() - self.calculate_discount_amount()
        return subtotal_after_discount * self.tax_rate

    def calculate_total(self) -> float:
        """Calculate final total."""
        subtotal = self.calculate_subtotal()
        discount = self.calculate_discount_amount()
        tax = self.calculate_tax_amount()
        return subtotal - discount + tax

    def update_status(self, new_status: OrderStatus) -> None:
        """Update order status."""
        self.status = new_status
        if new_status == OrderStatus.PREPARING:
            self._update_estimated_time()

    def _generate_id(self) -> str:
        """Generate unique order ID."""
        import uuid
        return f"ORD-{str(uuid.uuid4())[:8].upper()}"

    def _update_estimated_time(self) -> None:
        """Calculate estimated ready time based on items."""
        if not self.items:
            self.estimated_ready_time = None
            return

        total_prep_time = sum(item.get_preparation_time() for item in self.items)
        # Add buffer time for coordination
        total_prep_time += 5
        self.estimated_ready_time = datetime.now() + timedelta(minutes=total_prep_time)

    def get_receipt(self) -> str:
        """Generate order receipt."""
        lines = [
            f"=== Mario's Pizzeria Receipt ===",
            f"Order ID: {self.order_id}",
            f"Customer: {self.customer.name}",
            f"Date: {self.created_at.strftime('%Y-%m-%d %H:%M')}",
            f"Status: {self.status.value.title()}",
            "",
            "Items:"
        ]

        for i, item in enumerate(self.items, 1):
            lines.append(f"  {i}. {item}")

        lines.extend([
            "",
            f"Subtotal: ${self.calculate_subtotal():.2f}",
            f"Discount ({self.discount_percentage}%): -${self.calculate_discount_amount():.2f}",
            f"Tax: ${self.calculate_tax_amount():.2f}",
            f"TOTAL: ${self.calculate_total():.2f}"
        ])

        if self.estimated_ready_time:
            lines.append(f"Estimated ready: {self.estimated_ready_time.strftime('%H:%M')}")

        return "\n".join(lines)

# Kitchen class that manages orders
class Kitchen:
    """Kitchen that processes orders - composed of orders and equipment."""

    def __init__(self, max_concurrent_orders: int = 10):
        self.active_orders: List[Order] = []    # Composition: Kitchen HAS-MANY Orders
        self.completed_orders: List[Order] = []
        self.max_concurrent_orders = max_concurrent_orders
        self.equipment = {                      # Composition: Kitchen HAS equipment
            "ovens": 3,
            "prep_stations": 5,
            "fryers": 2
        }

    def accept_order(self, order: Order) -> bool:
        """Accept an order if kitchen has capacity."""
        if len(self.active_orders) < self.max_concurrent_orders:
            order.update_status(OrderStatus.PREPARING)
            self.active_orders.append(order)
            return True
        return False

    def complete_order(self, order_id: str) -> Optional[Order]:
        """Mark an order as complete."""
        for i, order in enumerate(self.active_orders):
            if order.order_id == order_id:
                order.update_status(OrderStatus.READY)
                completed_order = self.active_orders.pop(i)
                self.completed_orders.append(completed_order)
                return completed_order
        return None

    def get_queue_status(self) -> Dict[str, any]:
        """Get kitchen queue status."""
        return {
            "active_orders": len(self.active_orders),
            "max_capacity": self.max_concurrent_orders,
            "queue_full": len(self.active_orders) >= self.max_concurrent_orders,
            "estimated_wait_minutes": len(self.active_orders) * 3  # Rough estimate
        }

# Usage example showing composition:
def demonstrate_composition():
    """Show how objects work together through composition."""

    # Create components
    customer = Customer("Luigi", "luigi@email.com")
    kitchen = Kitchen(max_concurrent_orders=5)

    # Create menu items
    margherita = Pizza("Margherita", 12.99, "Classic pizza",
                      ["tomato", "mozzarella", "basil"])
    coke = Drink("Coke", 2.99, "Soft drink")
    tiramisu = Dessert("Tiramisu", 6.99, "Italian dessert")

    # Create order (composition in action)
    order = Order(customer)  # Order contains Customer
    order.add_item(margherita, quantity=2, special_instructions="Extra cheese")
    order.add_item(coke, quantity=2)
    order.add_item(tiramisu, quantity=1)

    # Apply discount for loyalty customer
    if customer.loyalty_points > 50:
        order.apply_discount(10)

    print(order.get_receipt())
    print()

    # Kitchen processes the order
    if kitchen.accept_order(order):
        print(f"✅ Order {order.order_id} accepted by kitchen")
        print(f"Kitchen status: {kitchen.get_queue_status()}")

        # Simulate completing the order
        completed_order = kitchen.complete_order(order.order_id)
        if completed_order:
            print(f"✅ Order {completed_order.order_id} is ready!")
            customer.place_order(completed_order)  # Customer gets loyalty points
            print(f"Customer {customer.name} now has {customer.loyalty_points} loyalty points")
    else:
        print(f"❌ Kitchen is full, cannot accept order {order.order_id}")

# Run the demonstration
demonstrate_composition()
```

## 🏗️ OOP in Neuroglia Framework

### Entity Base Classes

The framework uses OOP extensively for domain entities:

```python
from abc import ABC, abstractmethod
from typing import List, Any, Dict
from datetime import datetime
import uuid

class Entity(ABC):
    """Base class for all domain entities."""

    def __init__(self, id: str = None):
        self.id = id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self._domain_events: List['DomainEvent'] = []

    def raise_event(self, event: 'DomainEvent') -> None:
        """Raise a domain event."""
        self._domain_events.append(event)

    def get_uncommitted_events(self) -> List['DomainEvent']:
        """Get events that haven't been processed yet."""
        return self._domain_events.copy()

    def mark_events_as_committed(self) -> None:
        """Mark all events as processed."""
        self._domain_events.clear()

    def update_timestamp(self) -> None:
        """Update the entity's last modified timestamp."""
        self.updated_at = datetime.now()

    def __eq__(self, other) -> bool:
        """Two entities are equal if they have the same ID and type."""
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self) -> int:
        """Hash based on entity ID."""
        return hash(self.id)

# Domain entities inherit from Entity
class Pizza(Entity):
    """Pizza domain entity with business logic."""

    def __init__(self, name: str, price: float, ingredients: List[str], id: str = None):
        super().__init__(id)
        self.name = name
        self.price = price
        self.ingredients = ingredients.copy()
        self.is_available = True

        # Raise domain event
        self.raise_event(PizzaCreatedEvent(self.id, self.name))

    def add_ingredient(self, ingredient: str) -> None:
        """Add ingredient with business rules."""
        if len(self.ingredients) >= 10:
            raise ValueError("Pizza cannot have more than 10 ingredients")

        if ingredient not in self.ingredients:
            self.ingredients.append(ingredient)
            self.price += 1.50  # Business rule: each extra ingredient costs $1.50
            self.update_timestamp()
            self.raise_event(PizzaIngredientAddedEvent(self.id, ingredient))

    def change_price(self, new_price: float) -> None:
        """Change price with validation."""
        if new_price < 5.0:
            raise ValueError("Pizza price cannot be less than $5.00")

        old_price = self.price
        self.price = new_price
        self.update_timestamp()
        self.raise_event(PizzaPriceChangedEvent(self.id, old_price, new_price))

    def discontinue(self) -> None:
        """Discontinue the pizza."""
        self.is_available = False
        self.update_timestamp()
        self.raise_event(PizzaDiscontinuedEvent(self.id, self.name))

class Customer(Entity):
    """Customer domain entity."""

    def __init__(self, name: str, email: str, id: str = None):
        super().__init__(id)
        self.name = name
        self.email = email
        self.loyalty_points = 0
        self.total_orders = 0

        self.raise_event(CustomerRegisteredEvent(self.id, self.name, self.email))

    def place_order(self, order_total: float) -> None:
        """Process an order and update customer state."""
        self.total_orders += 1
        points_earned = int(order_total)  # 1 point per dollar
        self.loyalty_points += points_earned
        self.update_timestamp()

        self.raise_event(OrderPlacedEvent(self.id, order_total, points_earned))

        # Check for loyalty tier changes
        if self.total_orders == 5:
            self.raise_event(CustomerPromotedEvent(self.id, "Bronze"))
        elif self.total_orders == 15:
            self.raise_event(CustomerPromotedEvent(self.id, "Silver"))
        elif self.total_orders == 30:
            self.raise_event(CustomerPromotedEvent(self.id, "Gold"))
```

### Repository Pattern with Inheritance

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List

TEntity = TypeVar('TEntity', bound=Entity)
TId = TypeVar('TId')

class Repository(Generic[TEntity, TId], ABC):
    """Abstract repository pattern."""

    @abstractmethod
    async def get_by_id_async(self, id: TId) -> Optional[TEntity]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def save_async(self, entity: TEntity) -> None:
        """Save entity."""
        pass

    @abstractmethod
    async def delete_async(self, id: TId) -> bool:
        """Delete entity."""
        pass

    @abstractmethod
    async def get_all_async(self) -> List[TEntity]:
        """Get all entities."""
        pass

# Concrete repository implementations
class InMemoryRepository(Repository[TEntity, str]):
    """In-memory repository implementation."""

    def __init__(self):
        self._entities: Dict[str, TEntity] = {}

    async def get_by_id_async(self, id: str) -> Optional[TEntity]:
        return self._entities.get(id)

    async def save_async(self, entity: TEntity) -> None:
        self._entities[entity.id] = entity
        # Publish domain events
        await self._publish_events(entity)

    async def delete_async(self, id: str) -> bool:
        if id in self._entities:
            del self._entities[id]
            return True
        return False

    async def get_all_async(self) -> List[TEntity]:
        return list(self._entities.values())

    async def _publish_events(self, entity: TEntity) -> None:
        """Publish domain events from entity."""
        events = entity.get_uncommitted_events()
        for event in events:
            # Publish to event bus
            await self._event_bus.publish_async(event)
        entity.mark_events_as_committed()

class PizzaRepository(InMemoryRepository[Pizza]):
    """Specialized pizza repository."""

    async def get_available_pizzas_async(self) -> List[Pizza]:
        """Get only available pizzas."""
        all_pizzas = await self.get_all_async()
        return [pizza for pizza in all_pizzas if pizza.is_available]

    async def get_pizzas_by_ingredient_async(self, ingredient: str) -> List[Pizza]:
        """Find pizzas containing a specific ingredient."""
        all_pizzas = await self.get_all_async()
        return [pizza for pizza in all_pizzas
                if ingredient in pizza.ingredients and pizza.is_available]

    async def get_pizzas_in_price_range_async(self, min_price: float, max_price: float) -> List[Pizza]:
        """Find pizzas within a price range."""
        all_pizzas = await self.get_all_async()
        return [pizza for pizza in all_pizzas
                if min_price <= pizza.price <= max_price and pizza.is_available]
```

### Command and Query Handlers with Inheritance

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TCommand = TypeVar('TCommand')
TQuery = TypeVar('TQuery')
TResult = TypeVar('TResult')

class CommandHandler(Generic[TCommand, TResult], ABC):
    """Base class for command handlers."""

    @abstractmethod
    async def handle_async(self, command: TCommand) -> TResult:
        """Handle the command."""
        pass

class QueryHandler(Generic[TQuery, TResult], ABC):
    """Base class for query handlers."""

    @abstractmethod
    async def handle_async(self, query: TQuery) -> TResult:
        """Handle the query."""
        pass

# Specific handlers inherit from base classes
class CreatePizzaHandler(CommandHandler[CreatePizzaCommand, Pizza]):
    """Handler for creating pizzas."""

    def __init__(self, repository: PizzaRepository, validator: 'PizzaValidator'):
        self._repository = repository
        self._validator = validator

    async def handle_async(self, command: CreatePizzaCommand) -> Pizza:
        """Create and save a new pizza."""
        # Validation
        validation_result = await self._validator.validate_async(command)
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)

        # Create pizza entity
        pizza = Pizza(
            name=command.name,
            price=command.price,
            ingredients=command.ingredients
        )

        # Save to repository
        await self._repository.save_async(pizza)

        return pizza

class GetAvailablePizzasHandler(QueryHandler[GetAvailablePizzasQuery, List[Pizza]]):
    """Handler for getting available pizzas."""

    def __init__(self, repository: PizzaRepository):
        self._repository = repository

    async def handle_async(self, query: GetAvailablePizzasQuery) -> List[Pizza]:
        """Get all available pizzas."""
        return await self._repository.get_available_pizzas_async()

class GetPizzasByIngredientHandler(QueryHandler[GetPizzasByIngredientQuery, List[Pizza]]):
    """Handler for finding pizzas by ingredient."""

    def __init__(self, repository: PizzaRepository):
        self._repository = repository

    async def handle_async(self, query: GetPizzasByIngredientQuery) -> List[Pizza]:
        """Find pizzas containing the specified ingredient."""
        return await self._repository.get_pizzas_by_ingredient_async(query.ingredient)
```

## 🎨 Advanced OOP Patterns

### Abstract Factory Pattern

```python
from abc import ABC, abstractmethod
from enum import Enum

class PizzaStyle(Enum):
    ITALIAN = "italian"
    AMERICAN = "american"
    CHICAGO = "chicago"

class PizzaFactory(ABC):
    """Abstract factory for creating different styles of pizzas."""

    @abstractmethod
    def create_margherita(self) -> Pizza:
        pass

    @abstractmethod
    def create_pepperoni(self) -> Pizza:
        pass

    @abstractmethod
    def create_supreme(self) -> Pizza:
        pass

class ItalianPizzaFactory(PizzaFactory):
    """Factory for authentic Italian-style pizzas."""

    def create_margherita(self) -> Pizza:
        return Pizza(
            name="Margherita Italiana",
            price=15.99,
            ingredients=["San Marzano tomatoes", "Buffalo mozzarella", "Fresh basil", "Extra virgin olive oil"]
        )

    def create_pepperoni(self) -> Pizza:
        return Pizza(
            name="Diavola",
            price=17.99,
            ingredients=["San Marzano tomatoes", "Mozzarella di bufala", "Spicy salami", "Chili flakes"]
        )

    def create_supreme(self) -> Pizza:
        return Pizza(
            name="Quattro Stagioni",
            price=19.99,
            ingredients=["Tomato sauce", "Mozzarella", "Prosciutto", "Mushrooms", "Artichokes", "Olives"]
        )

class AmericanPizzaFactory(PizzaFactory):
    """Factory for American-style pizzas."""

    def create_margherita(self) -> Pizza:
        return Pizza(
            name="Classic Margherita",
            price=12.99,
            ingredients=["Tomato sauce", "Mozzarella cheese", "Dried basil"]
        )

    def create_pepperoni(self) -> Pizza:
        return Pizza(
            name="Pepperoni Classic",
            price=14.99,
            ingredients=["Tomato sauce", "Mozzarella cheese", "Pepperoni"]
        )

    def create_supreme(self) -> Pizza:
        return Pizza(
            name="Supreme Deluxe",
            price=18.99,
            ingredients=["Tomato sauce", "Mozzarella", "Pepperoni", "Sausage", "Bell peppers", "Onions", "Mushrooms"]
        )

# Factory selector
class PizzaFactoryProvider:
    """Provides the appropriate pizza factory based on style."""

    @staticmethod
    def get_factory(style: PizzaStyle) -> PizzaFactory:
        """Get the appropriate factory for the pizza style."""
        factories = {
            PizzaStyle.ITALIAN: ItalianPizzaFactory(),
            PizzaStyle.AMERICAN: AmericanPizzaFactory(),
            # PizzaStyle.CHICAGO: ChicagoPizzaFactory(),  # Could add more
        }

        if style not in factories:
            raise ValueError(f"Unsupported pizza style: {style}")

        return factories[style]

# Usage
def demonstrate_factory_pattern():
    """Show how factory pattern works."""

    # Customer chooses style
    chosen_style = PizzaStyle.ITALIAN
    factory = PizzaFactoryProvider.get_factory(chosen_style)

    # Create pizzas using the appropriate factory
    margherita = factory.create_margherita()
    pepperoni = factory.create_pepperoni()
    supreme = factory.create_supreme()

    print(f"=== {chosen_style.value.title()} Style Pizzas ===")
    print(f"Margherita: {margherita.name} - ${margherita.price}")
    print(f"Pepperoni: {pepperoni.name} - ${pepperoni.price}")
    print(f"Supreme: {supreme.name} - ${supreme.price}")
```

### Strategy Pattern

```python
from abc import ABC, abstractmethod

class PricingStrategy(ABC):
    """Abstract strategy for pizza pricing."""

    @abstractmethod
    def calculate_price(self, base_price: float, pizza: Pizza) -> float:
        pass

class RegularPricingStrategy(PricingStrategy):
    """Standard pricing - no modifications."""

    def calculate_price(self, base_price: float, pizza: Pizza) -> float:
        return base_price

class HappyHourPricingStrategy(PricingStrategy):
    """Happy hour pricing - 20% discount."""

    def calculate_price(self, base_price: float, pizza: Pizza) -> float:
        return base_price * 0.8

class LoyaltyPricingStrategy(PricingStrategy):
    """Loyalty customer pricing - discount based on ingredients."""

    def __init__(self, loyalty_level: str):
        self.loyalty_level = loyalty_level
        self.discounts = {
            "bronze": 0.05,  # 5% discount
            "silver": 0.10,  # 10% discount
            "gold": 0.15     # 15% discount
        }

    def calculate_price(self, base_price: float, pizza: Pizza) -> float:
        discount = self.discounts.get(self.loyalty_level.lower(), 0)
        return base_price * (1 - discount)

class GroupOrderPricingStrategy(PricingStrategy):
    """Group order pricing - bulk discount."""

    def __init__(self, order_quantity: int):
        self.order_quantity = order_quantity

    def calculate_price(self, base_price: float, pizza: Pizza) -> float:
        if self.order_quantity >= 5:
            return base_price * 0.85  # 15% discount for 5+ pizzas
        elif self.order_quantity >= 3:
            return base_price * 0.90  # 10% discount for 3+ pizzas
        return base_price

class PizzaPricer:
    """Context class that uses pricing strategies."""

    def __init__(self, strategy: PricingStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: PricingStrategy) -> None:
        """Change pricing strategy at runtime."""
        self._strategy = strategy

    def calculate_pizza_price(self, pizza: Pizza) -> float:
        """Calculate pizza price using current strategy."""
        return self._strategy.calculate_price(pizza.price, pizza)

    def calculate_order_total(self, pizzas: List[Pizza]) -> float:
        """Calculate total for multiple pizzas."""
        return sum(self.calculate_pizza_price(pizza) for pizza in pizzas)

# Usage example
def demonstrate_strategy_pattern():
    """Show how strategy pattern works."""

    # Create some pizzas
    margherita = Pizza("Margherita", 12.99, ["tomato", "mozzarella", "basil"])
    pepperoni = Pizza("Pepperoni", 14.99, ["tomato", "mozzarella", "pepperoni"])
    pizzas = [margherita, pepperoni]

    # Different pricing strategies
    regular_pricer = PizzaPricer(RegularPricingStrategy())
    happy_hour_pricer = PizzaPricer(HappyHourPricingStrategy())
    loyalty_pricer = PizzaPricer(LoyaltyPricingStrategy("gold"))
    group_pricer = PizzaPricer(GroupOrderPricingStrategy(order_quantity=5))

    print("=== Pizza Pricing Comparison ===")
    print(f"Regular pricing: ${regular_pricer.calculate_order_total(pizzas):.2f}")
    print(f"Happy hour pricing: ${happy_hour_pricer.calculate_order_total(pizzas):.2f}")
    print(f"Gold loyalty pricing: ${loyalty_pricer.calculate_order_total(pizzas):.2f}")
    print(f"Group order pricing: ${group_pricer.calculate_order_total(pizzas):.2f}")

    # Strategy can be changed at runtime
    pricer = PizzaPricer(RegularPricingStrategy())
    print(f"\nUsing initial strategy: ${pricer.calculate_order_total(pizzas):.2f}")

    pricer.set_strategy(HappyHourPricingStrategy())
    print(f"After switching to happy hour: ${pricer.calculate_order_total(pizzas):.2f}")
```

## 🧪 Testing OOP Code

Testing object-oriented code requires understanding inheritance and composition:

```python
import pytest
from unittest.mock import Mock, patch
from typing import List

class TestPizza:
    """Test the Pizza entity class."""

    def setup_method(self):
        """Setup for each test method."""
        self.pizza = Pizza("Test Pizza", 10.0, ["cheese", "tomato"])

    def test_pizza_creation(self):
        """Test pizza object creation."""
        assert self.pizza.name == "Test Pizza"
        assert self.pizza.price == 10.0
        assert self.pizza.ingredients == ["cheese", "tomato"]
        assert self.pizza.is_available == True
        assert self.pizza.id is not None

    def test_add_ingredient(self):
        """Test adding ingredient to pizza."""
        self.pizza.add_ingredient("pepperoni")

        assert "pepperoni" in self.pizza.ingredients
        assert self.pizza.price == 11.50  # Original price + $1.50
        assert len(self.pizza.get_uncommitted_events()) == 2  # Created + Ingredient added

    def test_add_ingredient_duplicate(self):
        """Test adding duplicate ingredient doesn't change price."""
        original_price = self.pizza.price
        self.pizza.add_ingredient("cheese")  # Already exists

        assert self.pizza.price == original_price
        assert self.pizza.ingredients.count("cheese") == 1

    def test_add_too_many_ingredients(self):
        """Test business rule: max 10 ingredients."""
        # Add 8 more ingredients (already has 2)
        for i in range(8):
            self.pizza.add_ingredient(f"ingredient_{i}")

        # Adding 9th should fail
        with pytest.raises(ValueError, match="cannot have more than 10 ingredients"):
            self.pizza.add_ingredient("too_many")

    def test_change_price(self):
        """Test price change with validation."""
        self.pizza.change_price(15.99)

        assert self.pizza.price == 15.99
        events = self.pizza.get_uncommitted_events()
        price_change_events = [e for e in events if isinstance(e, PizzaPriceChangedEvent)]
        assert len(price_change_events) == 1

    def test_change_price_too_low(self):
        """Test price validation."""
        with pytest.raises(ValueError, match="cannot be less than"):
            self.pizza.change_price(3.0)

    def test_discontinue(self):
        """Test discontinuing pizza."""
        self.pizza.discontinue()

        assert self.pizza.is_available == False
        events = self.pizza.get_uncommitted_events()
        discontinue_events = [e for e in events if isinstance(e, PizzaDiscontinuedEvent)]
        assert len(discontinue_events) == 1

class TestOrder:
    """Test the Order composition class."""

    def setup_method(self):
        """Setup for each test method."""
        self.customer = Customer("Test Customer", "test@example.com")
        self.order = Order(self.customer)
        self.pizza = Pizza("Test Pizza", 12.99, ["cheese", "tomato"])
        self.drink = Drink("Coke", 2.99, "Soft drink")

    def test_order_creation(self):
        """Test order object creation."""
        assert self.order.customer == self.customer
        assert self.order.order_id is not None
        assert len(self.order.items) == 0
        assert self.order.status == OrderStatus.PENDING

    def test_add_item(self):
        """Test adding items to order."""
        self.order.add_item(self.pizza, quantity=2)
        self.order.add_item(self.drink, quantity=1)

        assert len(self.order.items) == 2
        assert self.order.items[0].quantity == 2
        assert self.order.items[1].quantity == 1
        assert self.order.estimated_ready_time is not None

    def test_calculate_totals(self):
        """Test order total calculations."""
        self.order.add_item(self.pizza, quantity=2)  # 2 * 12.99 = 25.98
        self.order.add_item(self.drink, quantity=1)  # 1 * 2.99 = 2.99

        subtotal = self.order.calculate_subtotal()
        assert subtotal == 28.97

        self.order.apply_discount(10)  # 10% discount
        discount = self.order.calculate_discount_amount()
        assert discount == 2.897  # 10% of 28.97

        tax = self.order.calculate_tax_amount()
        expected_tax = (28.97 - 2.897) * 0.08  # 8% tax on discounted amount
        assert abs(tax - expected_tax) < 0.01

    def test_remove_item(self):
        """Test removing items from order."""
        self.order.add_item(self.pizza)
        self.order.add_item(self.drink)

        removed = self.order.remove_item(0)  # Remove first item

        assert removed == True
        assert len(self.order.items) == 1
        assert self.order.items[0].menu_item == self.drink

class TestPizzaRepository:
    """Test the repository with inheritance and composition."""

    def setup_method(self):
        """Setup for each test method."""
        self.repository = PizzaRepository()
        self.pizza1 = Pizza("Margherita", 12.99, ["tomato", "mozzarella"])
        self.pizza2 = Pizza("Pepperoni", 14.99, ["tomato", "mozzarella", "pepperoni"])
        self.pizza2.is_available = False  # Discontinued

    @pytest.mark.asyncio
    async def test_save_and_retrieve(self):
        """Test saving and retrieving pizzas."""
        await self.repository.save_async(self.pizza1)

        retrieved = await self.repository.get_by_id_async(self.pizza1.id)

        assert retrieved is not None
        assert retrieved.id == self.pizza1.id
        assert retrieved.name == self.pizza1.name

    @pytest.mark.asyncio
    async def test_get_available_pizzas(self):
        """Test getting only available pizzas."""
        await self.repository.save_async(self.pizza1)  # Available
        await self.repository.save_async(self.pizza2)  # Not available

        available_pizzas = await self.repository.get_available_pizzas_async()

        assert len(available_pizzas) == 1
        assert available_pizzas[0].id == self.pizza1.id

    @pytest.mark.asyncio
    async def test_get_pizzas_by_ingredient(self):
        """Test finding pizzas by ingredient."""
        await self.repository.save_async(self.pizza1)
        await self.repository.save_async(self.pizza2)

        pizzas_with_pepperoni = await self.repository.get_pizzas_by_ingredient_async("pepperoni")

        # Should not include pizza2 because it's not available
        assert len(pizzas_with_pepperoni) == 0

        pizzas_with_mozzarella = await self.repository.get_pizzas_by_ingredient_async("mozzarella")
        assert len(pizzas_with_mozzarella) == 1  # Only available pizza1

class TestCommandHandlers:
    """Test command handlers with mocking."""

    def setup_method(self):
        """Setup for each test method."""
        self.mock_repository = Mock(spec=PizzaRepository)
        self.mock_validator = Mock()
        self.handler = CreatePizzaHandler(self.mock_repository, self.mock_validator)

    @pytest.mark.asyncio
    async def test_successful_pizza_creation(self):
        """Test successful pizza creation."""
        # Setup mocks
        self.mock_validator.validate_async.return_value = Mock(is_valid=True)
        self.mock_repository.save_async = Mock()

        command = CreatePizzaCommand(
            name="Test Pizza",
            price=12.99,
            ingredients=["cheese", "tomato"]
        )

        # Execute handler
        result = await self.handler.handle_async(command)

        # Verify results
        assert isinstance(result, Pizza)
        assert result.name == "Test Pizza"
        assert result.price == 12.99

        # Verify mocks were called
        self.mock_validator.validate_async.assert_called_once_with(command)
        self.mock_repository.save_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_validation_failure(self):
        """Test handling validation errors."""
        # Setup mock to return validation failure
        validation_result = Mock(is_valid=False, errors=["Invalid pizza name"])
        self.mock_validator.validate_async.return_value = validation_result

        command = CreatePizzaCommand(name="", price=12.99, ingredients=[])

        # Should raise validation error
        with pytest.raises(ValidationError):
            await self.handler.handle_async(command)

        # Repository should not be called
        self.mock_repository.save_async.assert_not_called()
```

## 🚀 Best Practices for OOP

### 1. Follow SOLID Principles

```python
# Single Responsibility Principle - each class has one job
class PizzaPriceCalculator:
    """Only responsible for price calculations."""
    def calculate_price(self, pizza: Pizza) -> float:
        pass

class PizzaValidator:
    """Only responsible for pizza validation."""
    def validate(self, pizza: Pizza) -> ValidationResult:
        pass

# Open/Closed Principle - open for extension, closed for modification
class NotificationService(ABC):
    @abstractmethod
    async def send_notification(self, message: str, recipient: str) -> None:
        pass

class EmailNotificationService(NotificationService):
    async def send_notification(self, message: str, recipient: str) -> None:
        # Email implementation
        pass

class SmsNotificationService(NotificationService):
    async def send_notification(self, message: str, recipient: str) -> None:
        # SMS implementation
        pass

# Liskov Substitution Principle - derived classes must be substitutable
def send_welcome_message(notification_service: NotificationService, customer: Customer):
    # Works with any NotificationService implementation
    await notification_service.send_notification(
        f"Welcome {customer.name}!",
        customer.email
    )

# Interface Segregation Principle - many specific interfaces
class Readable(Protocol):
    def read(self) -> str: ...

class Writable(Protocol):
    def write(self, data: str) -> None: ...

class ReadWritable(Readable, Writable, Protocol):
    pass

# Dependency Inversion Principle - depend on abstractions
class OrderService:
    def __init__(self,
                 repository: Repository[Order, str],  # Abstract dependency
                 notifier: NotificationService):      # Abstract dependency
        self._repository = repository
        self._notifier = notifier
```

### 2. Use Composition over Inheritance

```python
# ✅ Good - composition
class Order:
    def __init__(self, customer: Customer):
        self.customer = customer          # HAS-A relationship
        self.payment_method = None        # HAS-A relationship
        self.items = []                   # HAS-A relationship

# ❌ Avoid deep inheritance hierarchies
class Animal:
    pass

class Mammal(Animal):
    pass

class Carnivore(Mammal):
    pass

class Feline(Carnivore):
    pass

class Cat(Feline):  # Too deep!
    pass
```

### 3. Keep Classes Focused and Small

```python
# ✅ Good - focused class
class Pizza:
    """Represents a pizza with its properties and behaviors."""
    def __init__(self, name: str, price: float, ingredients: List[str]):
        self.name = name
        self.price = price
        self.ingredients = ingredients

    def add_ingredient(self, ingredient: str) -> None:
        """Add ingredient to pizza."""
        pass

    def calculate_cost(self) -> float:
        """Calculate cost to make pizza."""
        pass

# ❌ Bad - doing too much
class PizzaEverything:
    """Class that tries to do everything - violates SRP."""
    def create_pizza(self): pass
    def save_to_database(self): pass
    def send_email(self): pass
    def process_payment(self): pass
    def manage_inventory(self): pass
    def generate_reports(self): pass
```

### 4. Use Properties for Controlled Access

```python
class Customer:
    def __init__(self, name: str, email: str):
        self._name = name
        self._email = email
        self._loyalty_points = 0

    @property
    def name(self) -> str:
        """Get customer name."""
        return self._name

    @property
    def email(self) -> str:
        """Get customer email."""
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        """Set email with validation."""
        if "@" not in value:
            raise ValueError("Invalid email format")
        self._email = value

    @property
    def loyalty_points(self) -> int:
        """Get loyalty points (read-only)."""
        return self._loyalty_points

    def add_loyalty_points(self, points: int) -> None:
        """Add loyalty points through controlled method."""
        if points > 0:
            self._loyalty_points += points
```

## 🔗 Related Documentation

- [Python Typing Guide](python_typing_guide.md) - Type safety, generics, and inheritance patterns
- [Python Modular Code](python_modular_code.md) - Organizing classes across modules
- [Dependency Injection](../patterns/dependency-injection.md) - OOP with dependency management
- [CQRS & Mediation](../patterns/cqrs.md) - Object-oriented command/query patterns

## 📚 Further Reading

- [Python Classes Documentation](https://docs.python.org/3/tutorial/classes.html)
- [SOLID Principles in Python](https://realpython.com/solid-principles-python/)
- [Design Patterns in Python](https://refactoring.guru/design-patterns/python)
- [Clean Code by Robert Martin](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350884)
