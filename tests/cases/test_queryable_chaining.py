"""
Test queryable chaining with type propagation.

This test validates the fix for the bug where chaining queryable operations
(e.g., .where() followed by .order_by()) would lose type information and
raise AttributeError: 'MotorQuery' object has no attribute '__orig_class__'.

Bug Context:
    When chaining operations like:
        queryable.where(...).order_by(...).to_list_async()

    The intermediate query object created by .where() would not have
    __orig_class__ set, causing .order_by() to fail when calling
    get_element_type().

The fix:
    - Queryable now explicitly stores _element_type
    - get_element_type() tries _element_type first, falls back to __orig_class__
    - create_query() propagates element_type to new query instances
"""

from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, Mock

import pytest

from neuroglia.data.infrastructure.mongo.motor_query import (
    MotorQuery,
    MotorQueryProvider,
)
from neuroglia.data.infrastructure.mongo.motor_repository import MotorRepository
from neuroglia.serialization.json import JsonSerializer


@dataclass
class Product:
    """Test entity for chaining tests."""

    id: str
    name: str
    price: float
    is_enabled: bool
    category: Optional[str] = None


@pytest.mark.asyncio
class TestQueryableChaining:
    """Test queryable operation chaining."""

    @pytest.fixture
    def mock_collection(self):
        """Create a mock Motor collection."""
        collection = AsyncMock()
        mock_cursor = AsyncMock()

        async def async_iter():
            yield {"id": "1", "name": "ProductA", "price": 10.0, "is_enabled": True}
            yield {"id": "2", "name": "ProductB", "price": 20.0, "is_enabled": True}
            yield {"id": "3", "name": "ProductC", "price": 30.0, "is_enabled": False}

        mock_cursor.__aiter__ = lambda self: async_iter()
        collection.find = Mock(return_value=mock_cursor)
        return collection

    @pytest.fixture
    def repository(self, mock_collection):
        """Create a mock MotorRepository."""
        mock_client = Mock()
        mock_client.__getitem__ = Mock(return_value=Mock(__getitem__=Mock(return_value=mock_collection)))

        repo = MotorRepository[Product, str](
            client=mock_client,
            database_name="test_db",
            collection_name="products",
            serializer=JsonSerializer(),
            entity_type=Product,
            mediator=None,
        )
        return repo

    async def test_single_where_clause(self, repository: MotorRepository):
        """Single where clause should work (baseline test)."""
        queryable = await repository.query_async()
        result = await queryable.where(lambda x: x.is_enabled == True).to_list_async()

        assert result is not None
        assert isinstance(result, list)

    async def test_where_then_order_by_chaining(self, repository: MotorRepository):
        """Chaining where() followed by order_by() should work (main fix validation)."""
        queryable = await repository.query_async()

        # This pattern was failing before the fix
        result = await queryable.where(lambda x: x.is_enabled == True).order_by(lambda x: x.name).to_list_async()

        assert result is not None
        assert isinstance(result, list)

    async def test_where_then_order_by_descending_chaining(self, repository: MotorRepository):
        """Chaining where() followed by order_by_descending() should work."""
        queryable = await repository.query_async()

        result = await queryable.where(lambda x: x.is_enabled == True).order_by_descending(lambda x: x.price).to_list_async()

        assert result is not None
        assert isinstance(result, list)

    async def test_multiple_where_clauses_chaining(self, repository: MotorRepository):
        """Chaining multiple where() clauses should work."""
        queryable = await repository.query_async()

        result = await queryable.where(lambda x: x.is_enabled == True).where(lambda x: x.price > 15.0).to_list_async()

        assert result is not None
        assert isinstance(result, list)

    async def test_complex_chaining_with_skip_take(self, repository: MotorRepository):
        """Complex chaining with where, order_by, skip, take should work."""
        queryable = await repository.query_async()

        result = await queryable.where(lambda x: x.is_enabled == True).order_by(lambda x: x.price).skip(1).take(5).to_list_async()

        assert result is not None
        assert isinstance(result, list)

    async def test_where_then_select_chaining(self, repository: MotorRepository):
        """Chaining where() followed by select() should work."""
        queryable = await repository.query_async()

        # Select with attribute projection
        result = await queryable.where(lambda x: x.is_enabled == True).select(lambda x: x.name).to_list_async()

        assert result is not None
        assert isinstance(result, list)

    async def test_order_by_then_where_chaining(self, repository: MotorRepository):
        """Chaining order_by() followed by where() should work."""
        queryable = await repository.query_async()

        # Order first, then filter
        result = await queryable.order_by(lambda x: x.name).where(lambda x: x.is_enabled == True).to_list_async()

        assert result is not None
        assert isinstance(result, list)

    async def test_three_operation_chain(self, repository: MotorRepository):
        """Chaining three operations should work."""
        queryable = await repository.query_async()

        result = await queryable.where(lambda x: x.is_enabled == True).order_by(lambda x: x.name).skip(0).to_list_async()

        assert result is not None
        assert isinstance(result, list)

    async def test_where_then_first_or_default(self, repository: MotorRepository):
        """Chaining where() followed by first_or_default_async() should work."""
        queryable = await repository.query_async()

        result = await queryable.where(lambda x: x.is_enabled == True).first_or_default_async()

        # Mock returns items, so should get one
        assert result is not None
        assert isinstance(result, Product)


@pytest.mark.asyncio
class TestQueryableTypePropagation:
    """Test that element type is properly propagated through query chains."""

    @pytest.fixture
    def mock_collection(self):
        """Create a mock Motor collection."""
        collection = AsyncMock()
        return collection

    def test_queryable_get_element_type_with_explicit_type(self, mock_collection):
        """Test get_element_type() with explicitly set element type."""
        provider = MotorQueryProvider(mock_collection, Product, JsonSerializer())

        # Create query with explicit element type
        query = provider.create_query(Product, None)

        # Should return the explicitly set type
        assert query.get_element_type() == Product

    def test_queryable_get_element_type_fallback_to_orig_class(self, mock_collection):
        """Test get_element_type() falls back to __orig_class__ when available."""
        provider = MotorQueryProvider(mock_collection, Product, JsonSerializer())

        # Create MotorQuery with generic subscript (sets __orig_class__)
        query = MotorQuery[Product](provider)

        # Should fall back to __orig_class__
        assert query.get_element_type() == Product

    def test_chained_query_preserves_element_type(self, mock_collection):
        """Test that chained queries preserve element type."""
        provider = MotorQueryProvider(mock_collection, Product, JsonSerializer())

        # Initial query with element type
        query1 = provider.create_query(Product, None)
        assert query1.get_element_type() == Product

        # Create chained query (simulates what where() does)
        import ast

        query2 = provider.create_query(Product, ast.parse("test").body[0].value)
        assert query2.get_element_type() == Product

    def test_element_type_takes_precedence_over_orig_class(self, mock_collection):
        """Test that explicit element_type takes precedence over __orig_class__."""
        provider = MotorQueryProvider(mock_collection, Product, JsonSerializer())

        # Create query with explicit element type
        query = MotorQuery[Product](provider, None, Product)

        # Even though __orig_class__ might be set, explicit type should win
        assert query.get_element_type() == Product
        assert hasattr(query, "_element_type")
        assert query._element_type == Product


@pytest.mark.asyncio
class TestRealWorldChainingScenarios:
    """Test real-world repository patterns with chaining."""

    @pytest.fixture
    def mock_collection(self):
        """Create a mock Motor collection."""
        collection = AsyncMock()
        mock_cursor = AsyncMock()

        async def async_iter():
            yield {"id": "1", "name": "Active", "is_enabled": True, "price": 10.0}
            yield {"id": "2", "name": "Inactive", "is_enabled": False, "price": 20.0}

        mock_cursor.__aiter__ = lambda self: async_iter()
        collection.find = Mock(return_value=mock_cursor)
        return collection

    @pytest.fixture
    def repository(self, mock_collection):
        """Create a mock MotorRepository."""
        mock_client = Mock()
        mock_client.__getitem__ = Mock(return_value=Mock(__getitem__=Mock(return_value=mock_collection)))

        repo = MotorRepository[Product, str](
            client=mock_client,
            database_name="test_db",
            collection_name="products",
            serializer=JsonSerializer(),
            entity_type=Product,
            mediator=None,
        )
        return repo

    async def test_repository_method_with_chained_query(self, repository: MotorRepository):
        """Test typical repository method pattern with chained operations."""

        async def get_enabled_products_sorted():
            """Repository method that chains where and order_by."""
            queryable = await repository.query_async()
            return await queryable.where(lambda x: x.is_enabled == True).order_by(lambda x: x.name).to_list_async()

        result = await get_enabled_products_sorted()

        assert result is not None
        assert isinstance(result, list)

    async def test_repository_paginated_query(self, repository: MotorRepository):
        """Test repository pagination with chaining."""

        async def get_products_page(skip: int, take: int):
            """Repository method with pagination."""
            queryable = await repository.query_async()
            return await queryable.where(lambda x: x.is_enabled == True).order_by(lambda x: x.name).skip(skip).take(take).to_list_async()

        result = await get_products_page(0, 10)

        assert result is not None
        assert isinstance(result, list)

    async def test_repository_filtered_and_sorted_query(self, repository: MotorRepository):
        """Test repository method with multiple filters and sorting."""

        async def get_expensive_enabled_products():
            """Repository method with complex filtering."""
            queryable = await repository.query_async()
            return await queryable.where(lambda x: x.is_enabled == True).where(lambda x: x.price > 15.0).order_by_descending(lambda x: x.price).to_list_async()

        result = await get_expensive_enabled_products()

        assert result is not None
        assert isinstance(result, list)
