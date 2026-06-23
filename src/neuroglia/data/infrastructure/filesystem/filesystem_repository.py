"""Generic file system repository implementation for the Neuroglia framework."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Generic, Optional

from neuroglia.data.abstractions import Entity, TEntity, TKey
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.serialization.json import JsonSerializer


class FileSystemRepository(Generic[TEntity, TKey], Repository[TEntity, TKey]):
    """
    Generic file system repository that stores entities using clean state persistence.

    This repository automatically handles:
    - Entity and AggregateRoot serialization/deserialization
    - File organization by entity type (type = folder name)
    - Index management for efficient lookups
    - ID generation for new entities (if needed)
    - Automatic state extraction for AggregateRoot (via JsonSerializer)

    Storage Format:
    - Clean state JSON (no metadata wrappers)
    - Type identity encoded in folder structure: data/{entity_type}/
    - Example: data/orders/order-123.json contains pure Order state

    Supports both:
    - Simple Entity objects (with id property)
    - AggregateRoot objects (with id() method and state)

    Examples:
        ```python
        # For simple entities
        class CustomerRepository(FileSystemRepository[Customer, str]):
            def __init__(self):
                super().__init__(
                    data_directory="data",
                    entity_type=Customer,
                    key_type=str
                )

        # For aggregates
        class OrderRepository(FileSystemRepository[Order, str]):
            def __init__(self):
                super().__init__(
                    data_directory="data",
                    entity_type=Order,
                    key_type=str
                )

        # Usage - same for both Entity and AggregateRoot
        repo = OrderRepository()
        order = Order(customer_id="c1")
        await repo.add_async(order)  # Stores clean state
        retrieved = await repo.get_async(order.id())  # Reconstructs aggregate
        ```
    """

    def __init__(
        self,
        data_directory: str = "data",
        entity_type: Optional[type[TEntity]] = None,
        key_type: Optional[type[TKey]] = None,
        serializer: Optional[JsonSerializer] = None,
    ):
        """
        Initialize the file system repository.

        Args:
            data_directory: Base directory for data storage
            entity_type: The entity type this repository manages (determines subdirectory)
            key_type: The key type used for entity IDs
            serializer: Optional custom serializer (defaults to JsonSerializer)
        """
        self.data_directory = Path(data_directory)
        self.entity_type = entity_type
        self.key_type = key_type
        self.serializer = serializer or JsonSerializer()

        # Create entity-specific subdirectory
        # Type identity is encoded in the folder structure, not in the data
        if entity_type:
            self.entity_directory = self.data_directory / entity_type.__name__.lower()
        else:
            self.entity_directory = self.data_directory / "entities"

        self.entity_directory.mkdir(parents=True, exist_ok=True)
        self.index_file = self.entity_directory / "index.json"
        self._ensure_index_exists()

    def _get_id(self, entity: TEntity) -> TKey | None:
        """
        Extract ID from Entity or AggregateRoot.

        Supports multiple patterns:
        - AggregateRoot with id() method
        - AggregateRoot with state.id property
        - Entity with id property

        Args:
            entity: The entity to extract ID from

        Returns:
            The entity's ID, or None if not set yet (including empty strings)

        Note:
            For new entities without IDs, this returns None so the repository
            can generate an ID. This is normal behavior, not an error.
            Empty strings are also treated as "no ID" for string-keyed entities.
        """
        # Try method call first (AggregateRoot pattern)
        if hasattr(entity, "id") and callable(getattr(entity, "id")):
            result = entity.id()
            # Treat None and empty string as "no ID"
            if result is None or result == "":
                return None
            return result

        # Try state.id (AggregateRoot alternative)
        if hasattr(entity, "state"):
            state = entity.state  # type: ignore
            if hasattr(state, "id"):
                result = state.id
                # Treat None and empty string as "no ID"
                if result is None or result == "":
                    return None
                return result

        # Try direct property (Entity pattern)
        # Note: Entity base class declares 'id: TKey' but doesn't set it in __init__
        # So new entities won't have this attribute at all until it's set
        if hasattr(entity, "id") and not callable(getattr(entity, "id")):
            result = entity.id
            # Treat None and empty string as "no ID"
            if result is None or result == "":
                return None
            return result

        # No ID set yet - return None so we can generate one
        return None

    def _is_aggregate_root(self, entity: TEntity) -> bool:
        """
        Check if entity is an AggregateRoot.

        AggregateRoot is detected by:
        - Having a 'state' attribute
        - Having an id() method (not just property)

        Args:
            entity: The entity to check

        Returns:
            True if entity is an AggregateRoot
        """
        # Check for AggregateRoot signature: state attribute and id() method
        has_state = hasattr(entity, "state")
        has_id_method = hasattr(entity, "id") and callable(getattr(entity, "id"))
        return has_state and has_id_method

    def _ensure_index_exists(self):
        """Ensure the index file exists."""
        if not self.index_file.exists():
            with open(self.index_file, "w") as f:
                json.dump({"entities": [], "last_updated": datetime.now().isoformat()}, f)

    def _generate_id(self) -> TKey:
        """Generate a new ID for an entity."""
        if self.key_type == str:
            return str(uuid.uuid4())  # type: ignore
        elif self.key_type == int:
            # For int keys, find the maximum ID and increment
            with open(self.index_file, "r") as f:
                index_data = json.load(f)
                entities = index_data.get("entities", [])
                if not entities:
                    return 1  # type: ignore
                max_id = max(int(entity_id) for entity_id in entities)
                return max_id + 1  # type: ignore
        else:
            # For other types, use string representation of UUID
            return str(uuid.uuid4())  # type: ignore

    def _update_index(self, entity_id: TKey, operation: str = "add"):
        """Update the index file with entity ID operations."""
        with open(self.index_file, "r") as f:
            index_data = json.load(f)

        entities = set(index_data.get("entities", []))

        if operation == "add":
            entities.add(str(entity_id))
        elif operation == "remove":
            entities.discard(str(entity_id))

        index_data["entities"] = list(entities)
        index_data["last_updated"] = datetime.now().isoformat()

        with open(self.index_file, "w") as f:
            json.dump(index_data, f, indent=2)

    async def contains_async(self, id: TKey) -> bool:
        """Determines whether or not the repository contains an entity with the specified id."""
        entity_file = self.entity_directory / f"{id}.json"
        return entity_file.exists()

    async def get_async(self, id: TKey) -> Optional[TEntity]:
        """Gets the entity with the specified id, if any."""
        entity_file = self.entity_directory / f"{id}.json"
        if not entity_file.exists():
            return None

        try:
            with open(entity_file, "r") as f:
                json_content = f.read()

                # Use the AggregateSerializer for proper deserialization
                if self.entity_type:
                    return self.serializer.deserialize_from_text(json_content, self.entity_type)
                else:
                    # Fallback for cases without entity type
                    return json.loads(json_content)
        except Exception:
            return None

    async def add_async(self, entity: TEntity) -> TEntity:
        """Adds the specified entity."""
        # Get entity ID using the helper method
        entity_id = self._get_id(entity)

        # Generate ID if needed
        if entity_id is None:
            entity_id = self._generate_id()
            # Set the ID on the entity
            if self._is_aggregate_root(entity):
                # For AggregateRoot, set on state
                entity.state.id = entity_id  # type: ignore
            else:
                # For Entity, set directly
                entity.id = entity_id  # type: ignore

        # Set created_at if it's an Entity
        if isinstance(entity, Entity) and not hasattr(entity, "created_at"):
            entity.created_at = datetime.now()

        # Use JsonSerializer for serialization (automatically extracts state)
        json_content = self.serializer.serialize_to_text(entity)
        entity_file = self.entity_directory / f"{entity_id}.json"

        with open(entity_file, "w") as f:
            f.write(json_content)

        # Update index
        self._update_index(entity_id, "add")

        return entity

    async def update_async(self, entity: TEntity) -> TEntity:
        """Persists the changes that were made to the specified entity."""
        entity_id = self._get_id(entity)
        if entity_id is None:
            raise ValueError("Entity must have an ID to be updated")

        # Set last_modified if it's an Entity
        if isinstance(entity, Entity):
            entity.last_modified = datetime.now()

        # Use JsonSerializer for serialization (automatically extracts state)
        json_content = self.serializer.serialize_to_text(entity)
        entity_file = self.entity_directory / f"{entity_id}.json"

        with open(entity_file, "w") as f:
            f.write(json_content)

        # Update index (ensure it's there)
        self._update_index(entity_id, "add")

        return entity

    async def remove_async(self, id: TKey) -> None:
        """Removes the entity with the specified key."""
        entity_file = self.entity_directory / f"{id}.json"
        if entity_file.exists():
            entity_file.unlink()

        # Update index
        self._update_index(id, "remove")

    async def get_all_async(self) -> list[TEntity]:
        """Gets all entities in the repository."""
        entities = []

        try:
            with open(self.index_file, "r") as f:
                index_data = json.load(f)
                entity_ids = index_data.get("entities", [])
        except (FileNotFoundError, json.JSONDecodeError):
            entity_ids = []

        for entity_id in entity_ids:
            entity = await self.get_async(entity_id)
            if entity:
                entities.append(entity)

        return entities
