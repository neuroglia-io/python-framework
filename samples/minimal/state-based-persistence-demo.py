"""
Sample application demonstrating state-based persistence with domain event dispatching.

This example shows how to use the new state-based persistence features alongside
the existing CQRS and mediation infrastructure in a real-world scenario.

Key Features Demonstrated:
- State-based aggregate persistence (alternative to event sourcing)
- Automatic domain event collection via UnitOfWork
- Pipeline behavior for automatic event dispatching after successful commands
- Backward compatibility with existing Entity usage
- Integration with dependency injection and mediation patterns

Run this sample to see the complete workflow in action.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from neuroglia.core import OperationResult
from neuroglia.data.abstractions import DomainEvent, Entity
from neuroglia.data.unit_of_work import IUnitOfWork
from neuroglia.dependency_injection import ServiceCollection
from neuroglia.mediation import (
    Command,
    CommandHandler,
    DomainEventHandler,
    Query,
    QueryHandler,
)
from neuroglia.mediation.mediator import Mediator

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


# Domain Events
@dataclass
class ProductCreatedEvent(DomainEvent):
    """Event raised when a product is created."""

    product_id: str
    name: str
    price: float
    category: str


@dataclass
class ProductPriceChangedEvent(DomainEvent):
    """Event raised when a product price is updated."""

    product_id: str
    old_price: float
    new_price: float


@dataclass
class ProductCategorizedEvent(DomainEvent):
    """Event raised when a product is assigned to a category."""

    product_id: str
    category: str


# Domain Entities with State-Based Persistence
class Product(Entity):
    """Product entity with state-based persistence and domain events."""

    def __init__(self, id: str, name: str, price: float, category: str):
        super().__init__()
        self._id = id
        self.name = name
        self.price = price
        self.category = category
        self.created_at = None  # Would be set by repository
        self.updated_at = None

        # Raise domain event for product creation
        self._raise_domain_event(ProductCreatedEvent(product_id=id, name=name, price=price, category=category))

    @property
    def id(self) -> str:
        return self._id

    def update_price(self, new_price: float) -> None:
        """Updates the product price and raises domain event."""
        if new_price != self.price:
            old_price = self.price
            self.price = new_price

            self._raise_domain_event(ProductPriceChangedEvent(product_id=self.id, old_price=old_price, new_price=new_price))

    def change_category(self, new_category: str) -> None:
        """Changes the product category and raises domain event."""
        if new_category != self.category:
            self.category = new_category

            self._raise_domain_event(ProductCategorizedEvent(product_id=self.id, category=new_category))

    def _raise_domain_event(self, event: DomainEvent) -> None:
        """Raises a domain event for state-based persistence."""
        if not hasattr(self, "_pending_events"):
            self._pending_events = []
        self._pending_events.append(event)

    @property
    def domain_events(self) -> list[DomainEvent]:
        """Gets pending domain events for state-based persistence."""
        return getattr(self, "_pending_events", []).copy()

    def clear_pending_events(self) -> None:
        """Clears all pending domain events."""
        if hasattr(self, "_pending_events"):
            self._pending_events.clear()


# Simple Entity (no domain events - for compatibility demonstration)
class Category(Entity):
    """Simple category entity without domain events."""

    def __init__(self, id: str, name: str, description: str):
        super().__init__()
        self._id = id
        self.name = name
        self.description = description

    @property
    def id(self) -> str:
        return self._id


# Repositories (Mock implementations)
class ProductRepository:
    """Mock product repository for demonstration."""

    def __init__(self):
        self._products = {}

    async def get_by_id_async(self, product_id: str) -> Optional[Product]:
        """Gets a product by ID."""
        return self._products.get(product_id)

    async def save_async(self, product: Product) -> None:
        """Saves a product."""
        self._products[product.id] = product
        log.info(f"Product saved: {product.id} - {product.name}")

    async def get_all_async(self) -> list[Product]:
        """Gets all products."""
        return list(self._products.values())


class CategoryRepository:
    """Mock category repository for demonstration."""

    def __init__(self):
        self._categories = {}

    async def get_by_id_async(self, category_id: str) -> Optional[Category]:
        """Gets a category by ID."""
        return self._categories.get(category_id)

    async def save_async(self, category: Category) -> None:
        """Saves a category."""
        self._categories[category.id] = category
        log.info(f"Category saved: {category.id} - {category.name}")


# DTOs
@dataclass
class ProductDto:
    """Data transfer object for products."""

    id: str
    name: str
    price: float
    category: str


@dataclass
class CreateProductDto:
    """DTO for creating products."""

    name: str
    price: float
    category: str


@dataclass
class UpdateProductPriceDto:
    """DTO for updating product prices."""

    product_id: str
    new_price: float


# Commands with State-Based Persistence
class CreateProductCommand(Command[OperationResult[ProductDto]]):
    """Command to create a new product."""

    def __init__(self, name: str, price: float, category: str):
        self.name = name
        self.price = price
        self.category = category


class UpdateProductPriceCommand(Command[OperationResult[ProductDto]]):
    """Command to update a product's price."""

    def __init__(self, product_id: str, new_price: float):
        self.product_id = product_id
        self.new_price = new_price


# Queries (compatible with both state-based and event-sourced entities)
class GetProductByIdQuery(Query[OperationResult[Optional[ProductDto]]]):
    """Query to get a product by ID."""

    def __init__(self, product_id: str):
        self.product_id = product_id


class GetAllProductsQuery(Query[OperationResult[list[ProductDto]]]):
    """Query to get all products."""


# Command Handlers with State-Based Persistence
class CreateProductHandler(CommandHandler[CreateProductCommand, OperationResult[ProductDto]]):
    """Handler for creating products with automatic domain event dispatching."""

    def __init__(self, product_repository: ProductRepository, unit_of_work: IUnitOfWork):
        self.product_repository = product_repository
        self.unit_of_work = unit_of_work

    async def handle_async(self, command: CreateProductCommand) -> OperationResult[ProductDto]:
        """Handles product creation command."""
        try:
            # Generate unique ID (in real app, would use proper ID generation)
            import uuid

            product_id = str(uuid.uuid4())[:8]

            # Create product entity (raises ProductCreatedEvent)
            product = Product(id=product_id, name=command.name, price=command.price, category=command.category)

            # Save to repository
            await self.product_repository.save_async(product)

            # Register with unit of work for automatic event dispatching
            self.unit_of_work.register_aggregate(product)

            # Return success result
            product_dto = ProductDto(id=product.id, name=product.name, price=product.price, category=product.category)

            return self.created(product_dto)

        except Exception as e:
            log.error(f"Error creating product: {e}")
            return self.internal_server_error(f"Failed to create product: {str(e)}")


class UpdateProductPriceHandler(CommandHandler[UpdateProductPriceCommand, OperationResult[ProductDto]]):
    """Handler for updating product prices with automatic domain event dispatching."""

    def __init__(self, product_repository: ProductRepository, unit_of_work: IUnitOfWork):
        self.product_repository = product_repository
        self.unit_of_work = unit_of_work

    async def handle_async(self, command: UpdateProductPriceCommand) -> OperationResult[ProductDto]:
        """Handles product price update command."""
        try:
            # Get existing product
            product = await self.product_repository.get_by_id_async(command.product_id)
            if not product:
                return self.not_found(Product, command.product_id)

            # Update price (raises ProductPriceChangedEvent)
            product.update_price(command.new_price)

            # Save changes
            await self.product_repository.save_async(product)

            # Register with unit of work for automatic event dispatching
            self.unit_of_work.register_aggregate(product)

            # Return success result
            product_dto = ProductDto(id=product.id, name=product.name, price=product.price, category=product.category)

            return self.ok(product_dto)

        except Exception as e:
            log.error(f"Error updating product price: {e}")
            return self.internal_server_error(f"Failed to update product price: {str(e)}")


# Query Handlers (compatible with both patterns)
class GetProductByIdHandler(QueryHandler[GetProductByIdQuery, OperationResult[Optional[ProductDto]]]):
    """Handler for getting products by ID."""

    def __init__(self, product_repository: ProductRepository):
        self.product_repository = product_repository

    async def handle_async(self, query: GetProductByIdQuery) -> OperationResult[Optional[ProductDto]]:
        """Handles get product by ID query."""
        product = await self.product_repository.get_by_id_async(query.product_id)

        if product:
            product_dto = ProductDto(id=product.id, name=product.name, price=product.price, category=product.category)
            return self.ok(product_dto)
        return self.not_found(Product, query.product_id)


class GetAllProductsHandler(QueryHandler[GetAllProductsQuery, OperationResult[list[ProductDto]]]):
    """Handler for getting all products."""

    def __init__(self, product_repository: ProductRepository):
        self.product_repository = product_repository

    async def handle_async(self, query: GetAllProductsQuery) -> OperationResult[list[ProductDto]]:
        """Handles get all products query."""
        products = await self.product_repository.get_all_async()

        product_dtos = [ProductDto(id=product.id, name=product.name, price=product.price, category=product.category) for product in products]
        return self.ok(product_dtos)


# Domain Event Handlers
class ProductCreatedEventHandler(DomainEventHandler[ProductCreatedEvent]):
    """Handler for ProductCreatedEvent - demonstrates automatic event dispatching."""

    async def handle_async(self, event: ProductCreatedEvent) -> None:
        """Handles product created event."""
        log.info(f"🎉 Product created: {event.name} ({event.product_id}) - ${event.price} in {event.category}")

        # Here you could:
        # - Send welcome emails
        # - Update search indexes
        # - Trigger workflows
        # - Update read models
        # - Integrate with external systems


class ProductPriceChangedEventHandler(DomainEventHandler[ProductPriceChangedEvent]):
    """Handler for ProductPriceChangedEvent."""

    async def handle_async(self, event: ProductPriceChangedEvent) -> None:
        """Handles product price changed event."""
        log.info(f"💰 Price changed for product {event.product_id}: ${event.old_price} -> ${event.new_price}")

        # Here you could:
        # - Notify subscribers of price changes
        # - Update pricing analytics
        # - Trigger repricing workflows
        # - Log price history


class ProductCategorizedEventHandler(DomainEventHandler[ProductCategorizedEvent]):
    """Handler for ProductCategorizedEvent."""

    async def handle_async(self, event: ProductCategorizedEvent) -> None:
        """Handles product categorized event."""
        log.info(f"📂 Product {event.product_id} categorized as: {event.category}")


# Application Setup and Demo
async def setup_application():
    """Sets up the application with all dependencies and configurations."""
    log.info("🏗️  Setting up application with state-based persistence...")

    # Create service collection
    services = ServiceCollection()

    # Add core mediation services
    services.add_singleton(Mediator)

    # Add state-based persistence services (new feature!)
    # Import the extension method
    from neuroglia.extensions.state_persistence_extensions import (
        add_state_based_persistence,
    )

    add_state_based_persistence(services)

    # Register repositories
    services.add_singleton(ProductRepository)
    services.add_singleton(CategoryRepository)

    # Register command handlers
    services.add_scoped(CreateProductHandler)
    services.add_scoped(UpdateProductPriceHandler)

    # Register query handlers
    services.add_scoped(GetProductByIdHandler)
    services.add_scoped(GetAllProductsHandler)

    # Register domain event handlers
    services.add_scoped(ProductCreatedEventHandler)
    services.add_scoped(ProductPriceChangedEventHandler)
    services.add_scoped(ProductCategorizedEventHandler)

    # Build service provider
    provider = services.build()

    # Manually populate mediator's handler registry
    if not hasattr(Mediator, "_handler_registry"):
        Mediator._handler_registry = {}

    Mediator._handler_registry[CreateProductCommand] = CreateProductHandler
    Mediator._handler_registry[UpdateProductPriceCommand] = UpdateProductPriceHandler
    Mediator._handler_registry[GetProductByIdQuery] = GetProductByIdHandler
    Mediator._handler_registry[GetAllProductsQuery] = GetAllProductsHandler

    log.info("✅ Application setup complete!")
    return provider


async def run_demo_scenarios(provider):
    """Runs demonstration scenarios showing state-based persistence in action."""
    log.info("\n" + "=" * 60)
    log.info("🚀 RUNNING STATE-BASED PERSISTENCE DEMO")
    log.info("=" * 60)

    mediator = provider.get_service(Mediator)

    # Scenario 1: Create Products (demonstrates automatic event dispatching)
    log.info("\n📋 Scenario 1: Creating Products with Automatic Event Dispatching")
    log.info("-" * 60)

    products_to_create = [
        ("Laptop", 999.99, "Electronics"),
        ("Coffee Mug", 12.50, "Kitchen"),
        ("Running Shoes", 89.99, "Sports"),
    ]

    created_products = []
    for name, price, category in products_to_create:
        command = CreateProductCommand(name, price, category)
        result = await mediator.execute_async(command)

        if result.is_success:
            created_products.append(result.data)
            log.info(f"✅ Created: {result.data.name}")
        else:
            log.error(f"❌ Failed to create {name}: {result.error_message}")

    # Scenario 2: Query Products (demonstrates compatibility with existing patterns)
    log.info("\n🔍 Scenario 2: Querying Products (Compatible with Both Patterns)")
    log.info("-" * 60)

    query = GetAllProductsQuery()
    query_result = await mediator.execute_async(query)

    if query_result.is_success:
        all_products = query_result.data
        log.info(f"📦 Found {len(all_products)} products:")
        for product in all_products:
            log.info(f"   • {product.name} - ${product.price} ({product.category})")
    else:
        log.error(f"❌ Failed to query products: {query_result.error_message}")

    # Scenario 3: Update Product Prices (demonstrates state changes with events)
    log.info("\n💲 Scenario 3: Updating Prices with Automatic Event Dispatching")
    log.info("-" * 60)

    if created_products:
        product_to_update = created_products[0]
        new_price = product_to_update.price * 0.9  # 10% discount

        update_command = UpdateProductPriceCommand(product_to_update.id, new_price)
        update_result = await mediator.execute_async(update_command)

        if update_result.is_success:
            log.info(f"✅ Updated price for {product_to_update.name}")
        else:
            log.error(f"❌ Failed to update price: {update_result.error_message}")

    # Scenario 4: Query Individual Product
    log.info("\n🔎 Scenario 4: Querying Individual Product")
    log.info("-" * 60)

    if created_products:
        product_id = created_products[0].id
        get_query = GetProductByIdQuery(product_id)
        product_result = await mediator.execute_async(get_query)

        if product_result.is_success and product_result.data:
            product = product_result.data
            log.info(f"📦 Retrieved: {product.name} - ${product.price}")
        else:
            log.info(f"❌ Product not found: {product_id}")

    log.info("\n" + "=" * 60)
    log.info("🎉 DEMO COMPLETE - All scenarios executed successfully!")
    log.info("=" * 60)

    log.info("\n📚 Key Features Demonstrated:")
    log.info("   ✅ State-based aggregate persistence (alternative to event sourcing)")
    log.info("   ✅ Automatic domain event collection via UnitOfWork")
    log.info("   ✅ Pipeline behavior for automatic event dispatching")
    log.info("   ✅ Backward compatibility with existing Entity usage")
    log.info("   ✅ Integration with CQRS, mediation, and dependency injection")
    log.info("   ✅ Transactional consistency between state changes and events")


async def main():
    """Main entry point for the sample application."""
    try:
        # Setup application
        provider = await setup_application()

        # Run demo scenarios
        await run_demo_scenarios(provider)

    except Exception as e:
        log.error(f"❌ Error running demo: {e}", exc_info=True)


if __name__ == "__main__":
    print(
        """
    🌟 Neuroglia State-Based Persistence Demo 🌟

    This sample demonstrates the new state-based persistence features:
    • Alternative to event sourcing for aggregate persistence
    • Automatic domain event dispatching after successful commands
    • Full compatibility with existing Entity and CQRS patterns
    • Pipeline behaviors for cross-cutting concerns

    Watch the console for detailed execution flow and event dispatching!
    """
    )

    asyncio.run(main())
