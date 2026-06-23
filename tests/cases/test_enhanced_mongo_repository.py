"""
Tests for EnhancedMongoRepository - Advanced MongoDB repository implementation.

This test suite validates the enhanced MongoDB repository functionality including
advanced querying, bulk operations, and integration with the MongoDB serialization helper.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

from neuroglia.data.infrastructure.mongo.enhanced_mongo_repository import EnhancedMongoRepository
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepositoryOptions
from neuroglia.data.infrastructure.mongo.serialization_helper import MongoSerializationHelper


class StatusEnum(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"


@dataclass
class TestEntity:
    """Test entity for repository operations"""

    id: str
    name: str = ""
    email: str = ""
    status: StatusEnum = StatusEnum.PENDING
    created_at: Optional[datetime] = None
    birth_date: Optional[date] = None
    score: Optional[Decimal] = None
    tags: Optional[List[str]] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class MoneyEntity:
    """Nested entity for testing complex objects"""

    amount: Decimal
    currency: str


@dataclass
class ComplexEntity:
    """Complex entity with nested objects"""

    id: str
    name: str = ""
    balance: Optional[MoneyEntity] = None


class TestEnhancedMongoRepository:
    """Test suite for EnhancedMongoRepository"""

    def setup_method(self):
        """Setup test environment for each test"""
        self.mock_mongo_client = Mock()
        self.mock_database = Mock()
        self.mock_collection = Mock()

        # Setup the mock chain: client -> database -> collection
        self.mock_mongo_client.__getitem__ = Mock(return_value=self.mock_database)
        self.mock_database.__getitem__ = Mock(return_value=self.mock_collection)

        # Create repository options
        self.options = MongoRepositoryOptions[TestEntity, str](database_name="test_db")

        # Create repository instance
        self.repository = EnhancedMongoRepository[TestEntity, str](
            mongo_client=self.mock_mongo_client, options=self.options, entity_type=TestEntity
        )

    def test_repository_initialization(self):
        """Test repository initialization with proper configuration"""
        assert self.repository._mongo_client == self.mock_mongo_client
        assert self.repository._options == self.options
        assert self.repository._entity_type == TestEntity
        assert self.repository._collection_name == "testentity"

    @pytest.mark.asyncio
    async def test_contains_async(self):
        """Test checking if entity exists by ID"""
        # Setup mock return value
        self.mock_collection.find_one.return_value = {"_id": "mongo_id", "id": "test_id"}

        result = await self.repository.contains_async("test_id")

        assert result is True
        self.mock_collection.find_one.assert_called_once_with(
            {"id": "test_id"}, projection={"_id": 1}
        )

    @pytest.mark.asyncio
    async def test_contains_async_not_found(self):
        """Test checking if entity exists when it doesn't"""
        self.mock_collection.find_one.return_value = None

        result = await self.repository.contains_async("nonexistent_id")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_async(self):
        """Test getting an entity by ID"""
        mock_document = {
            "_id": "mongo_id",
            "id": "test_id",
            "name": "John",
            "email": "john@test.com",
        }
        self.mock_collection.find_one.return_value = mock_document

        expected_entity = TestEntity(id="test_id", name="John", email="john@test.com")

        with patch.object(MongoSerializationHelper, "deserialize_to_entity") as mock_deserialize:
            mock_deserialize.return_value = expected_entity

            result = await self.repository.get_async("test_id")

            assert result == expected_entity
            self.mock_collection.find_one.assert_called_once_with({"id": "test_id"})
            mock_deserialize.assert_called_once_with(mock_document, TestEntity)

    @pytest.mark.asyncio
    async def test_get_async_not_found(self):
        """Test getting an entity that doesn't exist"""
        self.mock_collection.find_one.return_value = None

        result = await self.repository.get_async("nonexistent_id")

        assert result is None

    @pytest.mark.asyncio
    async def test_add_async(self):
        """Test adding a new entity"""
        entity = TestEntity(id="new_id", name="John", email="john@test.com")

        # Mock contains_async to return False (entity doesn't exist)
        with patch.object(self.repository, "contains_async", return_value=False):
            # Mock serialization
            with patch.object(MongoSerializationHelper, "serialize_to_dict") as mock_serialize:
                mock_serialize.return_value = {
                    "id": "new_id",
                    "name": "John",
                    "email": "john@test.com",
                }

                # Mock insert result
                mock_result = Mock()
                mock_result.inserted_id = "mongo_id"
                self.mock_collection.insert_one.return_value = mock_result

                result = await self.repository.add_async(entity)

                assert result == entity
                mock_serialize.assert_called_once_with(entity)
                self.mock_collection.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_async_already_exists(self):
        """Test adding an entity that already exists"""
        entity = TestEntity(id="existing_id", name="John")

        with patch.object(self.repository, "contains_async", return_value=True):
            with pytest.raises(ValueError) as exc_info:
                await self.repository.add_async(entity)

            assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_async(self):
        """Test updating an existing entity"""
        entity = TestEntity(id="existing_id", name="John Updated", email="updated@test.com")

        with patch.object(self.repository, "contains_async", return_value=True):
            with patch.object(MongoSerializationHelper, "serialize_to_dict") as mock_serialize:
                mock_serialize.return_value = {
                    "id": "existing_id",
                    "name": "John Updated",
                    "email": "updated@test.com",
                }

                mock_result = Mock()
                mock_result.modified_count = 1
                self.mock_collection.replace_one.return_value = mock_result

                result = await self.repository.update_async(entity)

                assert result == entity
                mock_serialize.assert_called_once_with(entity)
                self.mock_collection.replace_one.assert_called_once_with(
                    {"id": "existing_id"}, mock_serialize.return_value
                )

    @pytest.mark.asyncio
    async def test_remove_async(self):
        """Test removing an entity by ID"""
        entity_id = "remove_id"

        with patch.object(self.repository, "contains_async", return_value=True):
            mock_result = Mock()
            mock_result.deleted_count = 1
            self.mock_collection.delete_one.return_value = mock_result

            await self.repository.remove_async(entity_id)

            self.mock_collection.delete_one.assert_called_once_with({"id": entity_id})

    @pytest.mark.asyncio
    async def test_find_async_simple_filter(self):
        """Test find operation with basic filtering"""
        mock_cursor = Mock()
        mock_documents = [
            {"_id": "1", "id": "1", "name": "John", "status": "ACTIVE"},
            {"_id": "2", "id": "2", "name": "Jane", "status": "ACTIVE"},
        ]
        mock_cursor.__iter__ = Mock(return_value=iter(mock_documents))
        self.mock_collection.find.return_value = mock_cursor

        expected_entities = [
            TestEntity(id="1", name="John", status=StatusEnum.ACTIVE),
            TestEntity(id="2", name="Jane", status=StatusEnum.ACTIVE),
        ]

        with patch.object(MongoSerializationHelper, "deserialize_to_entity") as mock_deserialize:
            mock_deserialize.side_effect = expected_entities

            results = await self.repository.find_async({"status": "ACTIVE"})

            assert len(results) == 2
            assert results == expected_entities
            self.mock_collection.find.assert_called_once_with({"status": "ACTIVE"})

    @pytest.mark.asyncio
    async def test_find_async_with_pagination_and_sorting(self):
        """Test find operation with pagination and sorting"""
        mock_cursor = Mock()
        mock_documents = [{"_id": "1", "id": "1", "name": "Alice"}]

        # Setup method chaining for cursor operations
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.__iter__ = Mock(return_value=iter(mock_documents))

        self.mock_collection.find.return_value = mock_cursor

        with patch.object(MongoSerializationHelper, "deserialize_to_entity") as mock_deserialize:
            expected_entity = TestEntity(id="1", name="Alice")
            mock_deserialize.return_value = expected_entity

            results = await self.repository.find_async(
                filter_dict={}, skip=10, limit=5, sort_by={"name": 1, "created_at": -1}
            )

            assert len(results) == 1
            self.mock_collection.find.assert_called_once_with({})
            mock_cursor.skip.assert_called_once_with(10)
            mock_cursor.limit.assert_called_once_with(5)
            mock_cursor.sort.assert_called_once_with([("name", 1), ("created_at", -1)])

    @pytest.mark.asyncio
    async def test_find_one_async(self):
        """Test finding a single entity"""
        mock_document = {"_id": "1", "id": "1", "name": "John", "email": "john@test.com"}
        self.mock_collection.find_one.return_value = mock_document

        expected_entity = TestEntity(id="1", name="John", email="john@test.com")

        with patch.object(MongoSerializationHelper, "deserialize_to_entity") as mock_deserialize:
            mock_deserialize.return_value = expected_entity

            result = await self.repository.find_one_async({"name": "John"})

            assert result == expected_entity
            self.mock_collection.find_one.assert_called_once_with({"name": "John"})
            mock_deserialize.assert_called_once_with(mock_document, TestEntity)

    @pytest.mark.asyncio
    async def test_count_async(self):
        """Test counting documents with filter"""
        self.mock_collection.count_documents.return_value = 42

        count = await self.repository.count_async({"status": "ACTIVE"})

        assert count == 42
        self.mock_collection.count_documents.assert_called_once_with({"status": "ACTIVE"})

    @pytest.mark.asyncio
    async def test_aggregate_async(self):
        """Test aggregation pipeline execution"""
        pipeline = [
            {"$match": {"status": "ACTIVE"}},
            {"$group": {"_id": "$department", "count": {"$sum": 1}}},
        ]
        mock_results = [{"_id": "Engineering", "count": 5}, {"_id": "Sales", "count": 3}]
        self.mock_collection.aggregate.return_value = iter(mock_results)

        results = await self.repository.aggregate_async(pipeline)

        assert results == mock_results
        self.mock_collection.aggregate.assert_called_once_with(pipeline)

    @pytest.mark.asyncio
    async def test_upsert_async(self):
        """Test upsert operation"""
        entity = TestEntity(id="upsert_id", name="John", email="john@test.com")

        with patch.object(MongoSerializationHelper, "serialize_to_dict") as mock_serialize:
            mock_serialize.return_value = {
                "id": "upsert_id",
                "name": "John",
                "email": "john@test.com",
            }

            mock_result = Mock()
            mock_result.modified_count = 0
            mock_result.upserted_id = "mongo_id"
            self.mock_collection.replace_one.return_value = mock_result

            result = await self.repository.upsert_async(entity)

            assert result == entity
            mock_serialize.assert_called_once_with(entity)
            self.mock_collection.replace_one.assert_called_once_with(
                {"id": "upsert_id"}, mock_serialize.return_value, upsert=True
            )

    @pytest.mark.asyncio
    async def test_bulk_insert_async(self):
        """Test bulk insert operation"""
        entities = [
            TestEntity(id="1", name="John", email="john@test.com"),
            TestEntity(id="2", name="Jane", email="jane@test.com"),
        ]

        with patch.object(MongoSerializationHelper, "serialize_to_dict") as mock_serialize:
            mock_serialize.side_effect = [
                {"id": "1", "name": "John", "email": "john@test.com"},
                {"id": "2", "name": "Jane", "email": "jane@test.com"},
            ]

            mock_result = Mock()
            mock_result.inserted_ids = ["mongo_id1", "mongo_id2"]
            self.mock_collection.insert_many.return_value = mock_result

            result = await self.repository.bulk_insert_async(entities)

            assert result == entities
            assert mock_serialize.call_count == 2
            self.mock_collection.insert_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_many_async(self):
        """Test bulk update operation"""
        mock_result = Mock()
        mock_result.modified_count = 5
        self.mock_collection.update_many.return_value = mock_result

        filter_criteria = {"status": "PENDING"}
        update_data = {"$set": {"status": "ACTIVE"}}

        result = await self.repository.update_many_async(filter_criteria, update_data)

        assert result == 5
        self.mock_collection.update_many.assert_called_once_with(filter_criteria, update_data)

    @pytest.mark.asyncio
    async def test_delete_many_async(self):
        """Test bulk delete operation"""
        mock_result = Mock()
        mock_result.deleted_count = 10
        self.mock_collection.delete_many.return_value = mock_result

        result = await self.repository.delete_many_async({"status": "INACTIVE"})

        assert result == 10
        self.mock_collection.delete_many.assert_called_once_with({"status": "INACTIVE"})

    @pytest.mark.asyncio
    async def test_distinct_async(self):
        """Test distinct values operation"""
        distinct_values = ["Engineering", "Sales", "Marketing"]
        self.mock_collection.distinct.return_value = distinct_values

        results = await self.repository.distinct_async("department", {"status": "ACTIVE"})

        assert results == distinct_values
        self.mock_collection.distinct.assert_called_once_with("department", {"status": "ACTIVE"})

    @pytest.mark.asyncio
    async def test_bulk_insert_async_empty_list(self):
        """Test bulk insert with empty list"""
        result = await self.repository.bulk_insert_async([])
        assert result == []

    @pytest.mark.asyncio
    async def test_serialization_integration(self):
        """Test integration with MongoDB serialization helper"""
        entity = TestEntity(
            id="test_id",
            name="John",
            email="john@test.com",
            status=StatusEnum.ACTIVE,
            birth_date=date(1990, 5, 15),
            score=Decimal("95.5"),
        )

        expected_serialized = {
            "id": "test_id",
            "name": "John",
            "email": "john@test.com",
            "status": "ACTIVE",
            "birth_date": date(1990, 5, 15),
            "score": "95.5",
        }

        with patch.object(self.repository, "contains_async", return_value=False):
            with patch.object(MongoSerializationHelper, "serialize_to_dict") as mock_serialize:
                mock_serialize.return_value = expected_serialized
                mock_result = Mock()
                mock_result.inserted_id = "mongo_id"
                self.mock_collection.insert_one.return_value = mock_result

                await self.repository.add_async(entity)

                mock_serialize.assert_called_once_with(entity)


class TestEnhancedMongoRepositoryComplexScenarios:
    """Test suite for complex scenarios and edge cases"""

    def setup_method(self):
        """Setup test environment"""
        self.mock_mongo_client = Mock()
        self.mock_database = Mock()
        self.mock_collection = Mock()

        self.mock_mongo_client.__getitem__ = Mock(return_value=self.mock_database)
        self.mock_database.__getitem__ = Mock(return_value=self.mock_collection)

        self.options = MongoRepositoryOptions[ComplexEntity, str](database_name="test_db")
        self.repository = EnhancedMongoRepository[ComplexEntity, str](
            mongo_client=self.mock_mongo_client, options=self.options, entity_type=ComplexEntity
        )

    @pytest.mark.asyncio
    async def test_complex_aggregation_pipeline(self):
        """Test complex aggregation with multiple stages"""
        pipeline = [
            {"$match": {"status": "ACTIVE"}},
            {
                "$lookup": {
                    "from": "departments",
                    "localField": "dept_id",
                    "foreignField": "_id",
                    "as": "department",
                }
            },
            {"$unwind": "$department"},
            {
                "$group": {
                    "_id": "$department.name",
                    "employee_count": {"$sum": 1},
                    "avg_salary": {"$avg": "$salary"},
                }
            },
            {"$sort": {"employee_count": -1}},
            {"$limit": 10},
        ]

        expected_results = [
            {"_id": "Engineering", "employee_count": 25, "avg_salary": 95000},
            {"_id": "Sales", "employee_count": 20, "avg_salary": 75000},
        ]

        self.mock_collection.aggregate.return_value = iter(expected_results)

        results = await self.repository.aggregate_async(pipeline)

        assert results == expected_results
        self.mock_collection.aggregate.assert_called_once_with(pipeline)

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in repository operations"""
        self.mock_collection.find_one.side_effect = Exception("Database connection error")

        with pytest.raises(Exception) as exc_info:
            await self.repository.find_one_async({"name": "test"})

        assert "Database connection error" in str(exc_info.value)

    def test_type_safety(self):
        """Test that repository maintains type safety"""
        assert self.repository._entity_type == ComplexEntity
        assert self.repository._collection_name == "complexentity"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
