"""
THIS IS DEPRECATED - USE MOTOR BASED REPOSITORY INSTEAD

Enhanced MongoDB repository implementation with advanced querying capabilities.

This module provides an enhanced MongoDB repository that extends the base MongoRepository
with additional features like bulk operations, aggregation support, native MongoDB filtering,
and comprehensive serialization handling for complex domain objects.
"""

import logging
from typing import Any, Generic, Optional, TypeVar

from pymongo import MongoClient
from pymongo.collection import Collection

from neuroglia.data.abstractions import TEntity, TKey
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.data.infrastructure.mongo.mongo_repository import MongoRepositoryOptions
from neuroglia.data.infrastructure.mongo.serialization_helper import (
    MongoSerializationHelper,
)
from neuroglia.hosting.abstractions import ApplicationBuilderBase

log = logging.getLogger(__name__)

T = TypeVar("T")


class EnhancedMongoRepository(Generic[TEntity, TKey], Repository[TEntity, TKey]):
    """
    An enhanced MongoDB repository implementation with advanced querying capabilities
    and proper type handling for complex domain objects.

    This repository provides:
    - Advanced MongoDB operations (bulk operations, aggregation, upserts)
    - Comprehensive serialization for complex types (enums, value objects, nested entities)
    - Native MongoDB filtering capabilities
    - Production-ready features (pagination, sorting, counting)
    """

    def __init__(
        self,
        mongo_client: MongoClient,
        options: MongoRepositoryOptions[TEntity, TKey],
        entity_type: Optional[type[TEntity]] = None,
    ):
        """
        Initialize the enhanced MongoDB repository.

        Args:
            mongo_client: MongoDB client connection
            options: Repository configuration options
            entity_type: Optional explicit entity type (recommended for type safety)
        """
        self._mongo_client = mongo_client
        self._options = options
        self._mongo_database = self._mongo_client[self._options.database_name]

        # Store the entity type explicitly if provided
        if entity_type is not None:
            self._entity_type = entity_type
        else:
            # Fallback to try inferring the type from generics
            try:
                bases = self.__class__.__orig_bases__  # type: ignore
                for base in bases:
                    if hasattr(base, "__origin__") and base.__origin__ is EnhancedMongoRepository:
                        self._entity_type = base.__args__[0]  # type: ignore
                        break
                else:
                    raise TypeError("Unable to determine entity type. Please provide the entity_type parameter.")
            except (AttributeError, IndexError, TypeError) as e:
                log.error(f"Failed to infer entity type: {e}")
                raise TypeError("Unable to determine entity type. Please provide the entity_type parameter.")

        # Get collection name from entity type
        collection_name = self._entity_type.__name__.lower()
        if collection_name.endswith("dto"):
            collection_name = collection_name[:-3]
        self._collection_name = collection_name

    def _get_entity_type(self) -> type[TEntity]:
        """Get the entity type for this repository"""
        return self._entity_type

    def _get_mongo_collection(self) -> Collection:
        """Get the MongoDB collection for this repository"""
        return self._mongo_database[self._collection_name]

    async def contains_async(self, id: TKey) -> bool:
        """Check if an entity with the specified ID exists"""
        result = self._get_mongo_collection().find_one({"id": id}, projection={"_id": 1})
        return result is not None

    async def get_async(self, id: TKey) -> Optional[TEntity]:
        """Get an entity by its ID with proper type conversion"""
        data = self._get_mongo_collection().find_one({"id": id})
        if data is None:
            return None

        return MongoSerializationHelper.deserialize_to_entity(data, self._entity_type)

    async def add_async(self, entity: TEntity) -> TEntity:
        """Add a new entity with proper serialization"""
        if await self.contains_async(entity.id):  # type: ignore
            raise ValueError(f"An entity with ID {entity.id} already exists")  # type: ignore

        # Convert entity to dictionary
        entity_dict = MongoSerializationHelper.serialize_to_dict(entity)

        # Insert into MongoDB
        result = self._get_mongo_collection().insert_one(entity_dict)
        log.info(f"Inserted entity with ID {entity.id}, MongoDB ID: {result.inserted_id}")  # type: ignore

        # Return the original entity
        return entity

    async def update_async(self, entity: TEntity) -> TEntity:
        """Update an existing entity with proper serialization"""
        if not await self.contains_async(entity.id):  # type: ignore
            raise ValueError(f"Failed to find entity with ID {entity.id}")  # type: ignore

        # Convert entity to dictionary
        entity_dict = MongoSerializationHelper.serialize_to_dict(entity)

        # Update in MongoDB
        result = self._get_mongo_collection().replace_one({"id": entity.id}, entity_dict)  # type: ignore
        log.info(f"Updated entity with ID {entity.id}, modified count: {result.modified_count}")  # type: ignore

        # Return the updated entity
        return entity

    async def remove_async(self, id: TKey) -> None:
        """Remove an entity by its ID"""
        if not await self.contains_async(id):
            raise ValueError(f"Failed to find entity with ID {id}")

        result = self._get_mongo_collection().delete_one({"id": id})
        log.info(f"Deleted entity with ID {id}, deleted count: {result.deleted_count}")

    # Enhanced MongoDB querying capabilities

    async def find_async(
        self,
        filter_dict: dict[str, Any],
        skip: int = 0,
        limit: Optional[int] = None,
        sort_by: Optional[dict[str, int]] = None,
    ) -> list[TEntity]:
        """
        Find entities using MongoDB native filtering.

        Args:
            filter_dict: MongoDB filter dictionary
            skip: Number of results to skip (pagination)
            limit: Maximum number of results to return
            sort_by: Dictionary mapping field names to sort direction (1=asc, -1=desc)

        Returns:
            A list of properly typed entity objects
        """
        collection = self._get_mongo_collection()
        cursor = collection.find(filter_dict)

        # Apply skip and limit
        if skip > 0:
            cursor = cursor.skip(skip)
        if limit is not None:
            cursor = cursor.limit(limit)

        # Apply sorting
        if sort_by:
            cursor = cursor.sort(list(sort_by.items()))

        # Execute query and deserialize results
        results = []
        for doc in cursor:
            entity = MongoSerializationHelper.deserialize_to_entity(doc, self._entity_type)
            results.append(entity)

        return results

    async def find_one_async(self, filter_dict: dict[str, Any]) -> Optional[TEntity]:
        """
        Find a single entity using MongoDB native filtering.

        Args:
            filter_dict: MongoDB filter dictionary

        Returns:
            Entity object or None if not found
        """
        doc = self._get_mongo_collection().find_one(filter_dict)
        if doc is None:
            return None

        return MongoSerializationHelper.deserialize_to_entity(doc, self._entity_type)

    async def count_async(self, filter_dict: dict[str, Any]) -> int:
        """
        Count documents matching a filter.

        Args:
            filter_dict: MongoDB filter dictionary

        Returns:
            Count of matching documents
        """
        return self._get_mongo_collection().count_documents(filter_dict)

    async def aggregate_async(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Execute a MongoDB aggregation pipeline.

        Args:
            pipeline: MongoDB aggregation pipeline

        Returns:
            List of documents resulting from the aggregation
        """
        return list(self._get_mongo_collection().aggregate(pipeline))

    async def upsert_async(self, entity: TEntity) -> TEntity:
        """
        Insert or update an entity (upsert operation).

        Args:
            entity: The entity to insert or update

        Returns:
            The upserted entity
        """
        entity_dict = MongoSerializationHelper.serialize_to_dict(entity)
        result = self._get_mongo_collection().replace_one({"id": entity.id}, entity_dict, upsert=True)  # type: ignore
        log.info(f"Upserted entity with ID {entity.id}, modified count: {result.modified_count}, " f"upserted ID: {result.upserted_id}")  # type: ignore
        return entity

    async def bulk_insert_async(self, entities: list[TEntity]) -> list[TEntity]:
        """
        Insert multiple entities in bulk operation.

        Args:
            entities: List of entities to insert

        Returns:
            The list of inserted entities
        """
        if not entities:
            return []

        entity_dicts = [MongoSerializationHelper.serialize_to_dict(entity) for entity in entities]
        result = self._get_mongo_collection().insert_many(entity_dicts)
        log.info(f"Bulk inserted {len(result.inserted_ids)} entities")
        return entities

    async def update_many_async(self, filter_dict: dict[str, Any], update_dict: dict[str, Any]) -> int:
        """
        Update many documents matching a filter.

        Args:
            filter_dict: MongoDB filter dictionary
            update_dict: MongoDB update dictionary (use $set, $inc, etc.)

        Returns:
            Number of documents modified
        """
        result = self._get_mongo_collection().update_many(filter_dict, update_dict)
        log.info(f"Updated {result.modified_count} documents matching filter {filter_dict}")
        return result.modified_count

    async def delete_many_async(self, filter_dict: dict[str, Any]) -> int:
        """
        Delete many documents matching a filter.

        Args:
            filter_dict: MongoDB filter dictionary

        Returns:
            Number of documents deleted
        """
        result = self._get_mongo_collection().delete_many(filter_dict)
        log.info(f"Deleted {result.deleted_count} documents matching filter {filter_dict}")
        return result.deleted_count

    async def distinct_async(self, field: str, filter_dict: Optional[dict[str, Any]] = None) -> list[Any]:
        """
        Get distinct values for a field.

        Args:
            field: Field to get distinct values for
            filter_dict: Optional filter to apply

        Returns:
            List of distinct values
        """
        return self._get_mongo_collection().distinct(field, filter_dict)

    @staticmethod
    def configure(builder: ApplicationBuilderBase, entity_type: type, key_type: type, database_name: str) -> ApplicationBuilderBase:
        """
        Configure the application to use EnhancedMongoRepository.

        Args:
            builder: Application builder
            entity_type: Entity type for repository
            key_type: Key type for repository
            database_name: Database name

        Returns:
            Configured application builder
        """
        connection_string_name = "mongo"
        connection_string = builder.settings.connection_strings.get(connection_string_name, None)
        if connection_string is None:
            raise Exception(f"Missing '{connection_string_name}' connection string")

        # Register MongoClient (using try_add to avoid duplicates)
        builder.services.try_add_singleton(
            MongoClient,
            singleton=MongoClient(connection_string),
        )

        # Register the repository options for this specific type
        builder.services.add_singleton(
            MongoRepositoryOptions[entity_type, key_type],
            singleton=MongoRepositoryOptions[entity_type, key_type](database_name),
        )

        # Create a factory function to avoid lambda issues with closures
        def create_enhanced_repository(sp):
            return EnhancedMongoRepository(
                mongo_client=sp.get_required_service(MongoClient),
                options=sp.get_required_service(MongoRepositoryOptions[entity_type, key_type]),
                entity_type=entity_type,
            )

        def get_repository_interface(sp):
            return sp.get_required_service(EnhancedMongoRepository[entity_type, key_type])

        # Register the concrete repository
        builder.services.add_transient(
            EnhancedMongoRepository[entity_type, key_type],
            implementation_factory=create_enhanced_repository,
        )

        # Register the abstract Repository interface that handlers expect
        builder.services.add_transient(
            Repository[entity_type, key_type],
            implementation_factory=get_repository_interface,
        )

        return builder
