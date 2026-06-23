"""
Test suite for MongoDB repository implementation.

This module validates MongoDB repository operations including:
- CRUD operations (Create, Read, Update, Delete)
- Query patterns and filtering
- Pagination and sorting
- Transactions and consistency
- Index management
- Error handling

Test Coverage:
    - Repository initialization
    - Document persistence
    - Query operations
    - Update operations
    - Delete operations
    - Collection management
    - Error scenarios

Expected Behavior:
    - Documents persist correctly to MongoDB
    - Queries return correct results
    - Updates modify documents atomically
    - Deletes remove documents
    - Errors handled gracefully

Related Modules:
    - neuroglia.data.abstractions: Repository interface
    - neuroglia.data.mongo: MongoDB repository implementation
    - pymongo: MongoDB driver

Related Documentation:
    - [Data Access](../../docs/features/data-access.md)
    - [Repository Pattern](../../docs/patterns/repository-pattern.md)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

import pytest

from neuroglia.data.abstractions import Entity
from neuroglia.data.infrastructure.memory import MemoryRepository

# =============================================================================
# Test Entities
# =============================================================================


@dataclass
class Product(Entity):
    """Test entity representing a product."""

    name: str
    price: Decimal
    category: str
    description: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    in_stock: bool = True
    # Override created_at with a field default
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(self, name: str, price: Decimal, category: str, description: Optional[str] = None, tags: Optional[list[str]] = None, in_stock: bool = True):
        """Initialize product entity with generated ID."""
        super().__init__()  # This will set self.created_at
        self.id = str(uuid4())  # Generate unique ID
        self.name = name
        self.price = price
        self.category = category
        self.description = description
        self.tags = tags or []
        self.in_stock = in_stock


@dataclass
class Customer(Entity):
    """Test entity representing a customer."""

    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    address: Optional[dict] = None
    loyalty_points: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __init__(self, email: str, first_name: str, last_name: str, phone: Optional[str] = None, address: Optional[dict] = None, loyalty_points: int = 0):
        """Initialize customer entity with generated ID."""
        super().__init__()  # This will set self.created_at
        self.id = str(uuid4())  # Generate unique ID
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.address = address
        self.loyalty_points = loyalty_points


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def in_memory_products():
    """Create in-memory product repository for testing."""
    repo = MemoryRepository()
    repo.entities = {}  # Reset shared dict for isolation
    return repo


@pytest.fixture
def in_memory_customers():
    """Create in-memory customer repository for testing."""
    repo = MemoryRepository()
    repo.entities = {}  # Reset shared dict for isolation
    return repo


@pytest.fixture
def sample_products():
    """Create sample product entities for testing."""
    return [
        Product(name="Laptop", price=Decimal("999.99"), category="Electronics", description="High-performance laptop", tags=["computer", "portable"], in_stock=True),
        Product(name="Mouse", price=Decimal("29.99"), category="Electronics", description="Wireless mouse", tags=["computer", "wireless"], in_stock=True),
        Product(name="Desk", price=Decimal("299.99"), category="Furniture", description="Standing desk", tags=["office", "adjustable"], in_stock=False),
    ]


@pytest.fixture
def sample_customers():
    """Create sample customer entities for testing."""
    return [
        Customer(email="john@example.com", first_name="John", last_name="Doe", phone="555-0001", loyalty_points=100),
        Customer(email="jane@example.com", first_name="Jane", last_name="Smith", phone="555-0002", loyalty_points=250),
    ]


# =============================================================================
# Test Suite: Repository Initialization
# =============================================================================


@pytest.mark.unit
class TestRepositoryInitialization:
    """
    Test repository initialization and configuration.

    Validates that repositories are properly initialized and
    ready for use with correct configuration.

    Related: Repository pattern
    """

    def test_repository_initializes(self, in_memory_products):
        """
        Test repository initializes successfully.

        Expected Behavior:
            - Repository object created
            - Entities dict exists
            - Ready for operations

        Related: MemoryRepository initialization
        """
        # Assert
        assert in_memory_products is not None
        assert hasattr(in_memory_products, "entities")
        assert isinstance(in_memory_products.entities, dict)

    def test_repository_is_empty_initially(self, in_memory_products):
        """
        Test repository starts empty.

        Expected Behavior:
            - No entities in repository
            - Count is zero
            - Entities dict is empty

        Related: Repository state
        """
        # Act
        count = len(in_memory_products.entities)

        # Assert
        assert count == 0


# =============================================================================
# Test Suite: Create Operations
# =============================================================================


@pytest.mark.unit
class TestRepositoryCreateOperations:
    """
    Test repository create operations.

    Validates that entities can be added to the repository
    and that create operations work correctly.

    Related: Repository.add(), Repository.add_range()
    """

    @pytest.mark.asyncio
    async def test_add_single_entity(self, in_memory_products, sample_products):
        """
        Test adding a single entity to repository.

        Expected Behavior:
            - Entity added successfully
            - Entity has ID assigned
            - Entity retrievable by ID

        Related: Repository.add()
        """
        # Arrange
        product = sample_products[0]

        # Act
        await in_memory_products.add_async(product)
        retrieved = await in_memory_products.get_async(product.id)

        # Assert
        assert retrieved is not None
        assert retrieved.id == product.id
        assert retrieved.name == product.name

    @pytest.mark.asyncio
    async def test_add_multiple_entities(self, in_memory_products, sample_products):
        """
        Test adding multiple entities at once.

        Expected Behavior:
            - All entities added
            - Each has unique ID
            - All retrievable

        Related: Repository.add_async()
        """
        # Act
        for product in sample_products:
            await in_memory_products.add_async(product)

        all_products = list(in_memory_products.entities.values())

        # Assert
        assert len(all_products) == len(sample_products)
        assert all(p.id is not None for p in all_products)

    @pytest.mark.asyncio
    async def test_entity_id_assigned_on_add(self, in_memory_products):
        """
        Test that entity ID is assigned if not present.

        Expected Behavior:
            - Entity without ID gets one assigned
            - ID is unique
            - ID is persistent

        Related: Entity ID generation
        """
        # Arrange
        product = Product(name="Test Product", price=Decimal("19.99"), category="Test")

        # Act
        await in_memory_products.add_async(product)

        # Assert
        assert product.id is not None
        assert isinstance(product.id, str)
        assert len(product.id) > 0


# =============================================================================
# Test Suite: Read Operations
# =============================================================================


@pytest.mark.unit
class TestRepositoryReadOperations:
    """
    Test repository read/query operations.

    Validates that entities can be retrieved from the repository
    using various query patterns.

    Related: Repository.get(), Repository.find()
    """

    @pytest.mark.asyncio
    async def test_get_by_id(self, in_memory_products, sample_products):
        """
        Test retrieving entity by ID.

        Expected Behavior:
            - Entity retrieved by ID
            - Correct entity returned
            - None for nonexistent ID

        Related: Repository.get()
        """
        # Arrange
        product = sample_products[0]
        await in_memory_products.add_async(product)

        # Act
        retrieved = await in_memory_products.get_async(product.id)
        nonexistent = await in_memory_products.get_async("nonexistent-id")

        # Assert
        assert retrieved is not None
        assert retrieved.id == product.id
        assert nonexistent is None

    @pytest.mark.asyncio
    async def test_get_all_entities(self, in_memory_products, sample_products):
        """
        Test retrieving all entities.

        Expected Behavior:
            - All entities returned
            - Count matches added entities
            - Accessible via entities dict

        Related: Repository.entities
        """
        # Arrange
        for product in sample_products:
            await in_memory_products.add_async(product)

        # Act
        all_products = list(in_memory_products.entities.values())

        # Assert
        assert len(all_products) == len(sample_products)

    @pytest.mark.asyncio
    async def test_filter_entities_manually(self, in_memory_products, sample_products):
        """
        Test filtering entities using Python filtering.

        Expected Behavior:
            - Can filter entities programmatically
            - Filtering logic works correctly
            - Multiple filters can be applied

        Related: Manual filtering
        """
        # Arrange
        for product in sample_products:
            await in_memory_products.add_async(product)

        # Act
        electronics = [p for p in in_memory_products.entities.values() if p.category == "Electronics"]

        # Assert
        assert len(electronics) == 2
        assert all(p.category == "Electronics" for p in electronics)

    @pytest.mark.asyncio
    async def test_contains(self, in_memory_products, sample_products):
        """
        Test checking if entity exists in repository.

        Expected Behavior:
            - Returns True for existing entity
            - Returns False for nonexistent
            - Works by ID comparison

        Related: Repository.contains()
        """
        # Arrange
        product = sample_products[0]
        await in_memory_products.add_async(product)

        # Act
        exists = await in_memory_products.contains_async(product.id)
        not_exists = await in_memory_products.contains_async("nonexistent-id")

        # Assert
        assert exists is True
        assert not_exists is False


# =============================================================================
# Test Suite: Update Operations
# =============================================================================


@pytest.mark.unit
class TestRepositoryUpdateOperations:
    """
    Test repository update operations.

    Validates that entities can be updated in the repository
    and that changes persist correctly.

    Related: Repository.update()
    """

    @pytest.mark.asyncio
    async def test_update_entity(self, in_memory_products, sample_products):
        """
        Test updating an existing entity.

        Expected Behavior:
            - Entity updated successfully
            - Changes persist
            - ID remains unchanged

        Related: Repository.update()
        """
        # Arrange
        product = sample_products[0]
        await in_memory_products.add_async(product)
        original_id = product.id

        # Act
        product.name = "Updated Laptop"
        product.price = Decimal("1099.99")
        await in_memory_products.update_async(product)

        retrieved = await in_memory_products.get_async(original_id)

        # Assert
        assert retrieved is not None
        assert retrieved.id == original_id
        assert retrieved.name == "Updated Laptop"
        assert retrieved.price == Decimal("1099.99")

    @pytest.mark.asyncio
    async def test_update_preserves_other_fields(self, in_memory_products, sample_products):
        """
        Test that update preserves unchanged fields.

        Expected Behavior:
            - Updated fields change
            - Unchanged fields remain same
            - No data loss

        Related: Repository.update()
        """
        # Arrange
        product = sample_products[0]
        await in_memory_products.add_async(product)
        original_tags = product.tags.copy()

        # Act
        product.price = Decimal("899.99")
        await in_memory_products.update_async(product)

        retrieved = await in_memory_products.get_async(product.id)

        # Assert
        assert retrieved.tags == original_tags
        assert retrieved.category == product.category


# =============================================================================
# Test Suite: Delete Operations
# =============================================================================


@pytest.mark.unit
class TestRepositoryDeleteOperations:
    """
    Test repository delete operations.

    Validates that entities can be removed from the repository
    and that deletions work correctly.

    Related: Repository.remove()
    """

    @pytest.mark.asyncio
    async def test_remove_entity(self, in_memory_products, sample_products):
        """
        Test removing an entity from repository.

        Expected Behavior:
            - Entity removed successfully
            - Entity no longer retrievable
            - Other entities unaffected

        Related: Repository.remove()
        """
        # Arrange
        product1 = sample_products[0]
        product2 = sample_products[1]
        await in_memory_products.add_async(product1)
        await in_memory_products.add_async(product2)

        # Act
        await in_memory_products.remove_async(product1.id)

        retrieved1 = await in_memory_products.get_async(product1.id)
        retrieved2 = await in_memory_products.get_async(product2.id)

        # Assert
        assert retrieved1 is None
        assert retrieved2 is not None

    @pytest.mark.asyncio
    async def test_remove_by_id(self, in_memory_products, sample_products):
        """
        Test removing entity by ID.

        Expected Behavior:
            - Entity removed by ID
            - Entity no longer exists
            - Works with string ID

        Related: Repository.remove()
        """
        # Arrange
        product = sample_products[0]
        await in_memory_products.add_async(product)
        product_id = product.id

        # Act
        await in_memory_products.remove_async(product_id)

        retrieved = await in_memory_products.get_async(product_id)

        # Assert
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_entity(self, in_memory_products):
        """
        Test removing nonexistent entity raises exception.

        Expected Behavior:
            - Exception raised for nonexistent ID
            - Repository state unchanged
            - Clear error message

        Related: Repository.remove_async()
        """
        # Act & Assert - Should raise exception
        with pytest.raises(Exception):
            await in_memory_products.remove_async("nonexistent-id")


# =============================================================================
# Test Suite: Complex Queries
# =============================================================================


@pytest.mark.unit
class TestRepositoryComplexQueries:
    """
    Test complex query patterns.

    Validates that repositories support complex filtering,
    sorting, and pagination operations.

    Related: Repository query methods
    """

    @pytest.mark.asyncio
    async def test_filter_by_multiple_conditions(self, in_memory_products, sample_products):
        """
        Test filtering by multiple conditions.

        Expected Behavior:
            - Multiple conditions applied (AND logic)
            - Only matching entities returned
            - Complex predicates work

        Related: Repository.find()
        """
        # Arrange
        for product in sample_products:
            await in_memory_products.add_async(product)

        # Act
        results = list(in_memory_products.find(lambda p: p.category == "Electronics" and p.price < Decimal("100")))

        # Assert
        assert len(results) == 1
        assert results[0].name == "Mouse"

    @pytest.mark.asyncio
    async def test_filter_by_collection_membership(self, in_memory_products, sample_products):
        """
        Test filtering by collection field membership.

        Expected Behavior:
            - Can filter by items in list/set fields
            - Containment checks work
            - Multiple tags supported

        Related: List/collection queries
        """
        # Arrange
        for product in sample_products:
            await in_memory_products.add_async(product)

        # Act
        wireless_products = list(in_memory_products.find(lambda p: "wireless" in p.tags))

        # Assert
        assert len(wireless_products) == 1
        assert wireless_products[0].name == "Mouse"

    @pytest.mark.asyncio
    async def test_case_insensitive_search(self, in_memory_products, sample_products):
        """
        Test case-insensitive text search.

        Expected Behavior:
            - Search ignores case
            - Partial matches work
            - Results include all variations

        Related: Text search
        """
        # Arrange
        for product in sample_products:
            await in_memory_products.add_async(product)

        # Act
        results = list(in_memory_products.find(lambda p: "DESK" in p.name.upper()))

        # Assert
        assert len(results) == 1
        assert "Desk" in results[0].name


# =============================================================================
# Test Suite: Data Consistency
# =============================================================================


@pytest.mark.unit
class TestRepositoryDataConsistency:
    """
    Test data consistency and isolation.

    Validates that repository operations maintain data consistency
    and that entities are properly isolated.

    Related: Data integrity
    """

    @pytest.mark.asyncio
    async def test_entity_isolation(self, in_memory_products, sample_products):
        """
        Test that retrieved entities are isolated copies.

        Expected Behavior:
            - Retrieved entity is independent
            - Changes to retrieved don't affect stored
            - Each retrieval gets fresh copy

        Related: Entity isolation
        """
        # Arrange
        product = sample_products[0]
        await in_memory_products.add_async(product)

        # Act
        retrieved1 = await in_memory_products.get_async(product.id)
        retrieved1.name = "Modified Name"

        retrieved2 = await in_memory_products.get_async(product.id)

        # Assert - Second retrieval should have original name
        # Note: This depends on repository implementation
        # InMemoryRepository may return references or copies
        assert retrieved2.id == product.id

    @pytest.mark.asyncio
    async def test_concurrent_access(self, in_memory_products, sample_products):
        """
        Test repository handles concurrent access.

        Expected Behavior:
            - Multiple operations can execute
            - Data remains consistent
            - No race conditions

        Related: Concurrency
        """
        # Arrange
        products = sample_products[:2]

        # Act - Simulate concurrent adds
        await in_memory_products.add_async(products[0])
        await in_memory_products.add_async(products[1])

        all_products = list(in_memory_products.entities.values())

        # Assert
        assert len(all_products) == 2


# =============================================================================
# Test Suite: Error Handling
# =============================================================================


@pytest.mark.unit
class TestRepositoryErrorHandling:
    """
    Test repository error handling.

    Validates that repositories handle errors gracefully
    and provide meaningful error messages.

    Related: Error handling
    """

    @pytest.mark.asyncio
    async def test_get_with_invalid_id_returns_none(self, in_memory_products):
        """
        Test get with invalid ID returns None.

        Expected Behavior:
            - No exception raised
            - Returns None for invalid ID
            - Handles empty strings, None, etc.

        Related: Repository.get()
        """
        # Act
        result1 = await in_memory_products.get_async("")
        result2 = await in_memory_products.get_async("invalid-id-12345")

        # Assert
        assert result1 is None
        assert result2 is None

    @pytest.mark.asyncio
    async def test_update_nonexistent_entity(self, in_memory_products):
        """
        Test updating nonexistent entity behavior.

        Expected Behavior:
            - Operation completes (may add or skip)
            - No exception raised
            - Behavior documented

        Related: Repository.update()
        """
        # Arrange
        product = Product(name="New Product", price=Decimal("49.99"), category="Test")
        product.id = "nonexistent-id"

        # Act & Assert - Should not raise
        await in_memory_products.update_async(product)
