"""
Motor (async) MongoDB Repository implementation for Neuroglia.

This module provides async MongoDB repository patterns using Motor (PyMongo's async driver).
Motor is the recommended MongoDB driver for async Python applications (FastAPI, asyncio).

Key differences from sync MongoRepository:
- All operations are async (await required)
- Uses Motor's AsyncIOMotorClient instead of PyMongo's MongoClient
- Better performance in async applications (non-blocking I/O)
- Native asyncio integration

Example:
    ```python
    from motor.motor_asyncio import AsyncIOMotorClient
    from neuroglia.data.infrastructure.mongo import MotorRepository
    from neuroglia.serialization.json import JsonSerializer

    # Setup
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    serializer = JsonSerializer()
    repository = MotorRepository[User, str](
        client=client,
        database_name="myapp",
        collection_name="users",
        serializer=serializer
    )

    # Usage
    user = User(id="123", name="John")
    await repository.add_async(user)
    found_user = await repository.get_async("123")
    ```

See Also:
    - Motor Documentation: https://motor.readthedocs.io/
    - Data Access Patterns: https://bvandewe.github.io/pyneuro/features/data-access/
"""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Generic, Optional, cast

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from neuroglia.data.abstractions import AggregateRoot, TEntity, TKey
from neuroglia.data.infrastructure.abstractions import QueryableRepository, Repository
from neuroglia.data.queryable import Queryable
from neuroglia.hosting.abstractions import ApplicationBuilderBase
from neuroglia.mediation.mediator import Mediator
from neuroglia.serialization.json import JsonSerializer

if TYPE_CHECKING:
    from neuroglia.mediation.mediator import Mediator

log = logging.getLogger(__name__)


class MotorRepository(Generic[TEntity, TKey], QueryableRepository[TEntity, TKey]):
    """
    Async MongoDB repository implementation using Motor driver with queryable support.

    Motor is PyMongo's async driver and the recommended choice for async Python
    applications using FastAPI, asyncio, or any async framework.

    This repository provides full CRUD operations with proper async/await support,
    automatic JSON serialization/deserialization of domain entities, and LINQ-style
    queryable support for complex queries.

    Type Parameters:
        TEntity: The type of entities managed by this repository
        TKey: The type of the entity's unique identifier

    Attributes:
        _client: Motor async MongoDB client
        _database_name: Name of the MongoDB database
        _collection_name: Name of the MongoDB collection
        _serializer: JSON serializer for entity conversion
        _collection: Cached collection reference

    Examples:
        ```python
        # Basic setup
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        repo = MotorRepository[Product, str](
            client=client,
            database_name="shop",
            collection_name="products",
            serializer=JsonSerializer()
        )

        # CRUD operations
        product = Product(id="p1", name="Widget", price=9.99)
        await repo.add_async(product)

        found = await repo.get_async("p1")
        if found:
            found.price = 12.99
            await repo.update_async(found)

        await repo.remove_async("p1")

        # Queryable support (LINQ-style)
        expensive_products = await repo.query_async() \\
            .where(lambda p: p.price > 100) \\
            .order_by(lambda p: p.name) \\
            .to_list_async()
        ```

    See Also:
        - Motor Documentation: https://motor.readthedocs.io/
        - MongoDB Async Patterns: https://motor.readthedocs.io/en/stable/tutorial-asyncio.html
    """

    def __init__(
        self,
        client: AsyncIOMotorClient,
        database_name: str,
        collection_name: str,
        serializer: JsonSerializer,
        entity_type: Optional[type[TEntity]] = None,
        mediator: Optional["Mediator"] = None,
    ):
        """
        Initialize the Motor repository.

        Args:
            client: Async Motor MongoDB client instance
            database_name: Name of the MongoDB database
            collection_name: Name of the collection for this entity type
            serializer: JSON serializer for entity conversion
            entity_type: Optional explicit entity type (for proper deserialization)
            mediator: Optional Mediator instance for publishing domain events
        """
        super().__init__(mediator)
        self._client = client
        self._database_name = database_name
        self._collection_name = collection_name
        self._serializer = serializer
        self._collection: Optional[AsyncIOMotorCollection] = None

        # Store entity type if provided, otherwise try to infer it
        if entity_type is not None:
            self._entity_type: Optional[type[TEntity]] = entity_type
        else:
            # Try to infer from generic parameters
            # Search through all base classes to find one with generic type args
            inferred_type: Optional[type[TEntity]] = None
            try:
                for base in self.__orig_bases__:  # type: ignore[attr-defined]
                    if hasattr(base, "__args__") and len(base.__args__) > 0:
                        inferred_type = base.__args__[0]
                        break
            except (AttributeError, IndexError):
                pass
            self._entity_type = inferred_type

    @property
    def collection(self) -> AsyncIOMotorCollection:
        """
        Get the Motor collection instance (lazy-loaded).

        Returns:
            Async Motor collection for this repository
        """
        if self._collection is None:
            self._collection = self._client[self._database_name][self._collection_name]
        return self._collection

    def _is_aggregate_root(self, obj: object) -> bool:
        """
        Check if an object is an AggregateRoot instance.

        Args:
            obj: Object to check

        Returns:
            True if object is an AggregateRoot
        """
        return isinstance(obj, AggregateRoot)

    def _normalize_id(self, id: Any) -> str:
        """
        Normalize an ID to string format for MongoDB queries.

        MongoDB documents store IDs as strings after JSON serialization.
        This method ensures query IDs match the serialized format.

        Args:
            id: The ID to normalize (UUID, str, or other type)

        Returns:
            String representation of the ID
        """
        return str(id)

    def _serialize_entity(self, entity: TEntity) -> dict:
        """
        Serialize an entity to a dictionary, handling both Entity and AggregateRoot.

        For AggregateRoot: Serializes only the state (not the wrapper)
        For Entity: Serializes the entire entity

        Preserves Python datetime objects for proper MongoDB storage and querying.

        Args:
            entity: Entity or AggregateRoot to serialize

        Returns:
            Dictionary ready for MongoDB storage with datetime objects preserved
        """
        import json

        if self._is_aggregate_root(entity):
            # For AggregateRoot, serialize only the state
            json_str = self._serializer.serialize_to_text(entity.state)  # type: ignore[attr-defined]
        else:
            # For Entity, serialize the whole object
            json_str = self._serializer.serialize_to_text(entity)

        # Parse JSON but preserve datetime objects for MongoDB
        doc = cast(dict[str, Any], self._restore_datetime_objects(json.loads(json_str)))
        return doc

    def _restore_datetime_objects(self, obj):
        """
        Recursively restore datetime objects from ISO strings for MongoDB storage.

        MongoDB stores datetime as ISODate objects, not strings. This method converts
        ISO format strings back to Python datetime objects so MongoDB queries work correctly.

        Handles both timezone-aware (2025-10-23T20:06:48+00:00) and naive (2025-10-23T20:06:48)
        datetime strings. Naive datetimes are assumed to be UTC.

        Args:
            obj: Dictionary, list, or primitive value

        Returns:
            Object with datetime strings converted to datetime objects
        """
        if isinstance(obj, dict):
            return {k: self._restore_datetime_objects(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._restore_datetime_objects(item) for item in obj]
        elif isinstance(obj, str):
            # Try to parse as ISO datetime
            try:
                # Handle timezone-aware strings
                if obj.endswith("+00:00") or obj.endswith("Z"):
                    return datetime.fromisoformat(obj.replace("Z", "+00:00"))
                # Check if it looks like a datetime string (with T separator)
                elif "T" in obj and len(obj) >= 19:
                    # Try to parse as datetime (might be naive)
                    dt = datetime.fromisoformat(obj)
                    # If naive, assume UTC
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
            except (ValueError, AttributeError):
                pass
        return obj

    def _deserialize_entity(self, doc: dict) -> TEntity:
        """
        Deserialize a MongoDB document to an entity, handling both Entity and AggregateRoot.

        For AggregateRoot: Reconstructs from state
        For Entity: Deserializes directly

        Args:
            doc: MongoDB document dictionary

        Returns:
            Reconstructed entity or aggregate
        """
        # Remove MongoDB's _id field
        doc.pop("_id", None)

        # Serialize dict back to JSON for deserialization
        json_str = self._serializer.serialize_to_text(doc)

        # Use stored entity type or try to infer
        entity_type = self._entity_type
        if entity_type is None:
            # Search through all base classes to find one with generic type args
            try:
                for base in self.__orig_bases__:  # type: ignore[attr-defined]
                    if hasattr(base, "__args__") and len(base.__args__) > 0:
                        entity_type = base.__args__[0]
                        break
                if entity_type is None:
                    raise TypeError("Cannot determine entity type for deserialization")
            except (AttributeError, IndexError):
                raise TypeError("Cannot determine entity type for deserialization")

        # Deserialize using JsonSerializer (which handles AggregateRoot automatically)
        return self._serializer.deserialize_from_text(json_str, entity_type)

    async def contains_async(self, id: TKey) -> bool:
        """
        Check if an entity with the specified ID exists.

        Args:
            id: The unique identifier to check

        Returns:
            True if entity exists, False otherwise

        Example:
            ```python
            exists = await repository.contains_async("user123")
            if exists:
                print("User already exists")
            ```
        """
        count = await self.collection.count_documents({"id": self._normalize_id(id)}, limit=1)
        return count > 0

    async def get_async(self, id: TKey) -> Optional[TEntity]:
        """
        Retrieve an entity by its unique identifier.

        Handles both Entity and AggregateRoot types:
        - Entity: Deserializes directly from document
        - AggregateRoot: Reconstructs from state data

        Args:
            id: The unique identifier of the entity to retrieve

        Returns:
            The entity if found, None otherwise

        Example:
            ```python
            user = await repository.get_async("user123")
            if user:
                print(f"Found user: {user.name}")
            else:
                print("User not found")
            ```
        """
        doc = await self.collection.find_one({"id": self._normalize_id(id)})
        if doc is None:
            return None

        return self._deserialize_entity(doc)

    async def _do_add_async(self, entity: TEntity) -> TEntity:
        """
        Add a new entity to the repository.

        For AggregateRoot: Ensures state_version starts at 0 and persists only the state
        For Entity: Persists the entire entity

        Args:
            entity: The entity to add

        Returns:
            The added entity

        Raises:
            DuplicateKeyError: If entity with same ID already exists

        Example:
            ```python
            new_order = Order(customer_id="cust123")
            await repository.add_async(new_order)
            print("Order added with initial version 0")
            ```
        """
        # For AggregateRoot, ensure version starts at 0
        if self._is_aggregate_root(entity):
            aggregate = cast(AggregateRoot, entity)
            # State should already be initialized with version 0 by AggregateState.__init__
            # But ensure timestamps are set
            if not hasattr(aggregate.state, "created_at") or aggregate.state.created_at is None:
                aggregate.state.created_at = datetime.now(timezone.utc)
            if not hasattr(aggregate.state, "last_modified") or aggregate.state.last_modified is None:
                aggregate.state.last_modified = aggregate.state.created_at

        # Serialize entity (handles both Entity and AggregateRoot)
        doc = self._serialize_entity(entity)

        # Insert into MongoDB
        await self.collection.insert_one(doc)
        return entity

    async def _do_update_async(self, entity: TEntity) -> TEntity:
        """
        Update an existing entity in the repository with optimistic concurrency control.

        For AggregateRoot instances with state_version tracking, this method implements
        optimistic concurrency control by checking that the version hasn't changed since
        the entity was loaded. This prevents lost updates when multiple processes modify
        the same aggregate concurrently.

        For Entity instances (non-AggregateRoot), performs a simple replace without
        version checking.

        Args:
            entity: The entity with updated values

        Returns:
            The updated entity with incremented state_version (for AggregateRoot)

        Raises:
            OptimisticConcurrencyException: When version mismatch indicates concurrent modification
            EntityNotFoundException: When the entity doesn't exist in the database

        Example:
            ```python
            # With optimistic concurrency control
            try:
                order = await repository.get_async("order123")
                order.add_item("Pizza")
                await repository.update_async(order)
            except OptimisticConcurrencyException as ex:
                # Handle conflict - reload and retry
                logger.warning(f"Conflict: {ex}")
                return OperationResult.conflict("Order was modified, please retry")
            ```
        """
        # Get entity ID (handle both Entity.id and AggregateRoot.id())
        if self._is_aggregate_root(entity):
            # Cast to AggregateRoot for type checking
            aggregate = cast(AggregateRoot, entity)
            entity_id = aggregate.id()

            # Optimistic Concurrency Control for AggregateRoot
            old_version = aggregate.state.state_version

            # Update last_modified timestamp
            aggregate.state.last_modified = datetime.now(timezone.utc)

            # Increment version for this save operation
            aggregate.state.state_version = old_version + 1

            # Serialize with new version
            doc = self._serialize_entity(entity)
            doc.pop("_id", None)

            # Convert entity_id to string to match serialized format in MongoDB
            # (JsonSerializer converts UUIDs to strings during serialization)
            entity_id_str = str(entity_id)

            # Atomic update with version check
            # Handle documents that don't have state_version field (legacy data)
            # Use $or to match either explicit version or missing version (treated as 0)
            if old_version == 0:
                query = {"id": entity_id_str, "$or": [{"state_version": 0}, {"state_version": {"$exists": False}}]}
            else:
                query = {"id": entity_id_str, "state_version": old_version}

            result = await self.collection.replace_one(query, doc)

            if result.matched_count == 0:
                # Check if entity exists at all
                existing = await self.collection.find_one({"id": entity_id_str})

                if existing is None:
                    # Entity doesn't exist
                    from neuroglia.data.exceptions import EntityNotFoundException

                    entity_type_name = type(entity).__name__
                    raise EntityNotFoundException(entity_id=entity_id, entity_type=entity_type_name)
                else:
                    # Entity exists but version mismatch = concurrency conflict
                    actual_version = existing.get("state_version", 0)
                    from neuroglia.data.exceptions import OptimisticConcurrencyException

                    raise OptimisticConcurrencyException(
                        entity_id=entity_id,
                        expected_version=old_version,
                        actual_version=actual_version,
                    )

            return entity

        else:
            # Simple Entity without version tracking
            entity_id = entity.id if hasattr(entity, "id") else str(entity.id())  # type: ignore

            # Update last_modified if present
            if hasattr(entity, "last_modified"):
                entity.last_modified = datetime.now(timezone.utc)  # type: ignore

            doc = self._serialize_entity(entity)
            doc.pop("_id", None)

            # Simple replace without version check (normalize ID for query)
            await self.collection.replace_one({"id": self._normalize_id(entity_id)}, doc)
            return entity

    async def _do_remove_async(self, id: TKey) -> None:
        """
        Remove an entity by its unique identifier.

        Args:
            id: The unique identifier of the entity to remove

        Example:
            ```python
            await repository.remove_async("user123")
            print("User removed")
            ```
        """
        await self.collection.delete_one({"id": self._normalize_id(id)})

    async def query_async(self) -> Queryable[TEntity]:
        """
        Returns a queryable for fluent LINQ-style queries.

        This method provides async queryable support, enabling complex queries
        using Python lambda expressions that are translated to MongoDB operations.

        Returns:
            Queryable instance for building queries fluently

        Example:
            ```python
            # Complex query with filtering, sorting, pagination
            products = await repository.query_async() \\
                .where(lambda p: p.price > 10 and p.in_stock) \\
                .order_by(lambda p: p.name) \\
                .skip(10) \\
                .take(5) \\
                .to_list_async()

            # Projection (select specific fields)
            names = await repository.query_async() \\
                .select(lambda p: [p.name, p.price]) \\
                .to_list_async()

            # Single result
            first_product = await repository.query_async() \\
                .where(lambda p: p.id == "prod123") \\
                .first_or_default_async()
            ```

        Notes:
            - Lambda expressions are translated to JavaScript for MongoDB $where
            - Supports .where(), .order_by(), .skip(), .take(), .select()
            - Use .to_list_async() or .first_or_default_async() to execute
        """
        from neuroglia.data.infrastructure.mongo.motor_query import (
            MotorQuery,
            MotorQueryProvider,
        )

        # Determine entity type (raise if not available)
        entity_type = self._entity_type
        if entity_type is None:
            raise TypeError("Cannot create query: entity type not set. Pass entity_type to constructor.")

        return MotorQuery[TEntity](MotorQueryProvider(self.collection, entity_type, self._serializer))

    async def get_all_async(self) -> list[TEntity]:
        """
        Retrieve all entities from the repository.

        Warning:
            This loads all documents into memory. Use with caution on large collections.
            Consider pagination for production use.

        Returns:
            List of all entities in the collection

        Example:
            ```python
            all_users = await repository.get_all_async()
            print(f"Total users: {len(all_users)}")
            ```
        """
        entities = []
        async for doc in self.collection.find():
            entity = self._deserialize_entity(doc)
            entities.append(entity)

        return entities

    async def find_async(
        self,
        filter_dict: dict,
        sort: Optional[list[tuple[str, int]]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        projection: Optional[dict] = None,
    ) -> list[TEntity]:
        """
        Find entities matching a MongoDB filter query with optional sorting, pagination, and projection.

        This provides direct access to MongoDB's query language for complex queries
        with full support for cursor operations.

        Args:
            filter_dict: MongoDB query filter (e.g., {"state.email": "user@example.com"})
            sort: List of (field, direction) tuples. Direction: 1 for ascending, -1 for descending.
                  Example: [("name", 1), ("created_at", -1)]
            limit: Maximum number of documents to return
            skip: Number of documents to skip (for pagination)
            projection: Fields to include/exclude. Example: {"name": 1, "email": 1}

        Returns:
            List of entities matching the filter

        Examples:
            ```python
            # Find all active users
            active_users = await repository.find_async({"state.is_active": True})

            # Find users by email domain with sorting
            gmail_users = await repository.find_async(
                {"state.email": {"$regex": "@gmail.com$"}},
                sort=[("state.name", 1)]
            )

            # Paginated query with sorting
            page_2_users = await repository.find_async(
                {"state.is_active": True},
                sort=[("state.created_at", -1)],
                skip=20,
                limit=10
            )

            # Query with field projection (only return specific fields)
            users = await repository.find_async(
                {"state.is_active": True},
                projection={"state.name": 1, "state.email": 1}
            )
            ```
        """
        cursor = self.collection.find(filter_dict, projection)

        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)

        entities = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            entities.append(entity)

        return entities

    async def find_one_async(self, filter_dict: dict) -> Optional[TEntity]:
        """
        Find a single entity matching a MongoDB filter query.

        Args:
            filter_dict: MongoDB query filter

        Returns:
            The first entity matching the filter, or None

        Example:
            ```python
            user = await repository.find_one_async({"state.email": "john@example.com"})
            if user:
                print(f"Found user: {user.state.name}")
            ```
        """
        doc = await self.collection.find_one(filter_dict)
        if doc is None:
            return None

        return self._deserialize_entity(doc)

    async def count_async(self, filter_dict: Optional[dict] = None) -> int:
        """
        Count documents matching a MongoDB filter query.

        Args:
            filter_dict: MongoDB query filter. If None or empty dict, counts all documents.

        Returns:
            Count of documents matching the filter

        Examples:
            ```python
            # Count all documents
            total_count = await repository.count_async()

            # Count with filter
            active_count = await repository.count_async({"state.is_active": True})

            # Useful for pagination
            filter_query = {"state.status": "pending"}
            total_pages = (await repository.count_async(filter_query) + page_size - 1) // page_size
            ```
        """
        filter_dict = filter_dict or {}
        return await self.collection.count_documents(filter_dict)

    async def exists_async(self, filter_dict: dict) -> bool:
        """
        Check if any document matches the MongoDB filter query.

        This is more efficient than count_async for existence checks as it
        stops after finding the first match.

        Args:
            filter_dict: MongoDB query filter

        Returns:
            True if at least one document matches, False otherwise

        Examples:
            ```python
            # Check if email already exists
            email_exists = await repository.exists_async({"state.email": "user@example.com"})
            if email_exists:
                raise ValueError("Email already registered")

            # Check if any active users exist
            has_active = await repository.exists_async({"state.is_active": True})
            ```
        """
        return await self.collection.count_documents(filter_dict, limit=1) > 0

    @staticmethod
    def configure(
        builder: ApplicationBuilderBase,
        entity_type: type[TEntity],
        key_type: type[TKey],
        database_name: str,
        collection_name: Optional[str] = None,
        connection_string_name: str = "mongo",
        domain_repository_type: Optional[type] = None,
        implementation_type: Optional[type] = None,
    ) -> ApplicationBuilderBase:
        """
        Configure the application to use MotorRepository for a specific entity type.

        This static method provides a fluent API for registering Motor repositories
        with the dependency injection container, following Neuroglia's configuration patterns.

        **Important**: Repositories are registered with SCOPED lifetime to ensure:
        - One repository instance per request/scope
        - Proper async context management
        - Integration with UnitOfWork for domain event collection
        - Request-scoped caching and transaction boundaries

        Args:
            builder: Application builder instance
            entity_type: The entity type this repository will manage
            key_type: The type of the entity's unique identifier
            database_name: Name of the MongoDB database
            collection_name: Optional collection name (defaults to lowercase entity name)
            connection_string_name: Name of connection string in settings (default: "mongo")
            domain_repository_type: Optional domain-layer repository interface to register
                (e.g., TaskRepository). When provided, the interface resolves to the
                configured MotorRepository instance, preserving clean architecture boundaries.
            implementation_type: Optional custom repository implementation class.
                If provided with domain_repository_type, this implementation will be
                registered for the domain interface instead of base MotorRepository.
                Must extend MotorRepository[entity_type, key_type]. Enables single-line
                registration of custom repositories with domain-specific query methods.

        Returns:
            The configured application builder (for fluent chaining)

        Raises:
            Exception: If connection string is missing from application settings

        Example:
            ```python
            from neuroglia.hosting.web import WebApplicationBuilder
            from neuroglia.data.infrastructure.mongo import MotorRepository
            from domain.entities import Customer

            # Basic configuration
            builder = WebApplicationBuilder()
            MotorRepository.configure(
                builder,
                entity_type=Customer,
                key_type=str,
                database_name="mario_pizzeria"
            )

            # Custom collection name and domain interface registration
            MotorRepository.configure(
                builder,
                entity_type=Order,
                key_type=str,
                database_name="mario_pizzeria",
                collection_name="pizza_orders",
                domain_repository_type=OrderRepository
            )

            # Custom repository implementation with domain-specific methods
            MotorRepository.configure(
                builder,
                entity_type=Task,
                key_type=str,
                database_name="starter_app",
                collection_name="tasks",
                domain_repository_type=TaskRepository,
                implementation_type=MongoTaskRepository
            )

            # Usage in handlers (automatically scoped per request)
            class GetCustomerHandler(QueryHandler[GetCustomerQuery, CustomerDto]):
                def __init__(self, repository: Repository[Customer, str]):
                    self.repository = repository  # Injected scoped MotorRepository
            ```

        Notes:
            - AsyncIOMotorClient is registered as SINGLETON (shared connection pool)
            - Repository instances are SCOPED (one per request for proper async context)
            - This pattern ensures efficient connection pooling while maintaining request isolation

        See Also:
            - EnhancedMongoRepository.configure() - Similar pattern for sync repositories
            - Service Lifetimes: https://bvandewe.github.io/pyneuro/features/dependency-injection/
            - Async Patterns: https://bvandewe.github.io/pyneuro/patterns/async/
        """
        # Get connection string from settings
        connection_string = builder.settings.connection_strings.get(connection_string_name, None)
        if connection_string is None:
            raise Exception(f"Missing '{connection_string_name}' connection string in application settings")

        # Import Motor client here to avoid circular imports
        from motor.motor_asyncio import AsyncIOMotorClient

        # Validate implementation_type if provided
        if implementation_type is not None:
            # Check if it's a subclass of MotorRepository (duck typing check)
            try:
                if not issubclass(implementation_type, MotorRepository):
                    raise ValueError(f"implementation_type {implementation_type.__name__} must extend " f"MotorRepository[{entity_type.__name__}, {key_type.__name__}]")
            except TypeError:
                # issubclass fails for generics, check __bases__ instead
                is_motor_repo = any(base.__name__ == "MotorRepository" or (hasattr(base, "__origin__") and base.__origin__.__name__ == "MotorRepository") for base in getattr(implementation_type, "__mro__", []))
                if not is_motor_repo:
                    raise ValueError(f"implementation_type {implementation_type.__name__} must extend " f"MotorRepository[{entity_type.__name__}, {key_type.__name__}]")

        # Register AsyncIOMotorClient as singleton (shared across all repositories)
        builder.services.try_add_singleton(
            AsyncIOMotorClient,
            singleton=AsyncIOMotorClient(connection_string),
        )

        # Determine collection name (default to lowercase entity name)
        if collection_name is None:
            collection_name = entity_type.__name__.lower()
            # Remove common suffixes
            if collection_name.endswith("dto"):
                collection_name = collection_name[:-3]

        # Factory function to create MotorRepository or custom implementation with proper entity type
        def create_motor_repository(sp):
            # Attempt to resolve Mediator optionally first (tests may skip registration)
            mediator = sp.get_service(Mediator)
            if mediator is None:
                mediator = sp.get_required_service(Mediator)

            # Use custom implementation if provided, otherwise base MotorRepository
            if implementation_type is not None:
                return implementation_type(
                    client=sp.get_required_service(AsyncIOMotorClient),
                    database_name=database_name,
                    collection_name=collection_name,
                    serializer=sp.get_required_service(JsonSerializer),
                    entity_type=entity_type,
                    mediator=mediator,
                )
            else:
                return MotorRepository(
                    client=sp.get_required_service(AsyncIOMotorClient),
                    database_name=database_name,
                    collection_name=collection_name,
                    serializer=sp.get_required_service(JsonSerializer),
                    entity_type=entity_type,
                    mediator=mediator,
                )

        # Factory function to resolve abstract Repository interface
        def get_repository_interface(sp):
            return sp.get_required_service(MotorRepository[entity_type, key_type])

        # Register the concrete MotorRepository with SCOPED lifetime
        # Scoped ensures proper async context per request and integration with UnitOfWork
        builder.services.add_scoped(
            MotorRepository[entity_type, key_type],  # type: ignore
            implementation_factory=create_motor_repository,
        )

        # Register the abstract Repository interface that handlers expect (also SCOPED)
        builder.services.add_scoped(
            Repository[entity_type, key_type],  # type: ignore
            implementation_factory=get_repository_interface,
        )

        if domain_repository_type is not None:

            def get_domain_repository(sp):
                return sp.get_required_service(MotorRepository[entity_type, key_type])

            builder.services.add_scoped(
                domain_repository_type,
                implementation_factory=get_domain_repository,
            )

            impl_name = implementation_type.__name__ if implementation_type else "MotorRepository"
            log.debug(
                "Registered domain repository interface %s -> %s[%s, %s]",
                getattr(domain_repository_type, "__name__", str(domain_repository_type)),
                impl_name,
                entity_type.__name__,
                key_type.__name__,
            )

        return builder
