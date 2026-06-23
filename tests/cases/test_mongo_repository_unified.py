"""
Test MongoRepository with unified JsonSerializer approach.

This test validates that MongoRepository:
1. Uses JsonSerializer for automatic state extraction (not AggregateSerializer)
2. Has _get_id() helper method to handle both Entity and AggregateRoot
3. Properly extracts IDs from entities before CRUD operations

Note: These are structural tests. Full integration tests require MongoDB instance.
"""

from typing import Optional
from unittest.mock import MagicMock, Mock

import pytest

from neuroglia.data.abstractions import AggregateRoot, AggregateState, Entity
from neuroglia.data.infrastructure.mongo import MongoRepository, MongoRepositoryOptions
from neuroglia.serialization.json import JsonSerializer


# Test Entities
class Customer(Entity[str]):
    """Simple Entity for testing."""

    def __init__(self, name: str, email: str):
        super().__init__()
        self.name = name
        self.email = email


# Test AggregateRoot
class OrderState(AggregateState[str]):
    """State object for Order aggregate."""

    # Class-level type annotations (required for JsonSerializer)
    id: str
    customer_id: str
    total: float
    status: str

    def __init__(self):
        super().__init__()
        self.id = ""
        self.customer_id = ""
        self.total = 0.0
        self.status = "PENDING"


class Order(AggregateRoot[OrderState, str]):
    """AggregateRoot for testing."""

    def __init__(self, customer_id: Optional[str] = None):
        super().__init__()
        # State is created automatically, now set fields
        if customer_id:
            self.state.customer_id = customer_id
        self.state.total = 0.0
        self.state.status = "PENDING"


class TestMongoRepositoryStructure:
    """Test suite for MongoRepository structure and helpers."""

    def test_mongo_repository_uses_json_serializer(self):
        """Verify MongoRepository uses JsonSerializer (unified approach)."""
        # Mock dependencies
        mock_client = Mock()
        mock_db = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_db)

        options = MongoRepositoryOptions[Customer, str](database_name="test_db")
        serializer = JsonSerializer()

        repo = MongoRepository[Customer, str](options=options, mongo_client=mock_client, serializer=serializer)

        # Verify serializer is JsonSerializer
        assert isinstance(repo._serializer, JsonSerializer)
        assert repo._serializer is serializer

    def test_mongo_repository_has_get_id_helper(self):
        """Verify MongoRepository has _get_id() helper method."""
        # Mock dependencies
        mock_client = Mock()
        mock_db = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_db)

        options = MongoRepositoryOptions[Customer, str](database_name="test_db")
        repo = MongoRepository[Customer, str](options=options, mongo_client=mock_client, serializer=JsonSerializer())

        # Verify _get_id method exists
        assert hasattr(repo, "_get_id")
        assert callable(repo._get_id)

    def test_get_id_extracts_from_entity(self):
        """Test _get_id() extracts ID from Entity."""
        # Mock dependencies
        mock_client = Mock()
        mock_db = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_db)

        options = MongoRepositoryOptions[Customer, str](database_name="test_db")
        repo = MongoRepository[Customer, str](options=options, mongo_client=mock_client, serializer=JsonSerializer())

        # Create entity with ID
        customer = Customer(name="Test", email="test@example.com")
        customer.id = "c123"

        # Extract ID
        entity_id = repo._get_id(customer)
        assert entity_id == "c123"

    def test_get_id_extracts_from_aggregate_root(self):
        """Test _get_id() extracts ID from AggregateRoot."""
        # Mock dependencies
        mock_client = Mock()
        mock_db = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_db)

        options = MongoRepositoryOptions[Order, str](database_name="test_db")
        repo = MongoRepository[Order, str](options=options, mongo_client=mock_client, serializer=JsonSerializer())

        # Create aggregate with ID
        order = Order(customer_id="c456")
        order.state.id = "o789"

        # Extract ID
        entity_id = repo._get_id(order)
        assert entity_id == "o789"

    def test_get_id_returns_none_for_entity_without_id(self):
        """Test _get_id() returns None for Entity without ID."""
        # Mock dependencies
        mock_client = Mock()
        mock_db = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_db)

        options = MongoRepositoryOptions[Customer, str](database_name="test_db")
        repo = MongoRepository[Customer, str](options=options, mongo_client=mock_client, serializer=JsonSerializer())

        # Create entity without ID
        customer = Customer(name="No ID", email="noid@example.com")

        # Extract ID - should return None
        entity_id = repo._get_id(customer)
        assert entity_id is None

    def test_get_id_returns_none_for_aggregate_without_id(self):
        """Test _get_id() returns None for AggregateRoot without ID (empty string)."""
        # Mock dependencies
        mock_client = Mock()
        mock_db = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_db)

        options = MongoRepositoryOptions[Order, str](database_name="test_db")
        repo = MongoRepository[Order, str](options=options, mongo_client=mock_client, serializer=JsonSerializer())

        # Create aggregate without setting ID (empty string by default)
        order = Order(customer_id="c999")
        # order.state.id is "" by default

        # Extract ID - should return None (empty string treated as no ID)
        entity_id = repo._get_id(order)
        assert entity_id is None

    def test_get_id_handles_none_id(self):
        """Test _get_id() handles None ID value."""
        # Mock dependencies
        mock_client = Mock()
        mock_db = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_db)

        options = MongoRepositoryOptions[Customer, str](database_name="test_db")
        repo = MongoRepository[Customer, str](options=options, mongo_client=mock_client, serializer=JsonSerializer())

        # Create entity with None ID
        customer = Customer(name="None ID", email="noneid@example.com")
        customer.id = None  # type: ignore

        # Extract ID - should return None
        entity_id = repo._get_id(customer)
        assert entity_id is None


class TestMongoRepositoryDocumentation:
    """Test documentation and comments are correct."""

    def test_get_id_docstring_mentions_aggregate_root(self):
        """Verify _get_id() docstring mentions AggregateRoot support."""
        # Mock dependencies
        mock_client = Mock()
        mock_db = MagicMock()
        mock_client.__getitem__ = Mock(return_value=mock_db)

        options = MongoRepositoryOptions[Customer, str](database_name="test_db")
        repo = MongoRepository[Customer, str](options=options, mongo_client=mock_client, serializer=JsonSerializer())

        # Check docstring
        docstring = repo._get_id.__doc__
        assert docstring is not None
        assert "AggregateRoot" in docstring
        assert "Entity" in docstring
        assert "id() method" in docstring


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
