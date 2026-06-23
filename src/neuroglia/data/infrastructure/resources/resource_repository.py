"""Resource repository implementation with multi-format serialization.

This module provides a concrete implementation of resource repositories
that supports multiple serialization formats and storage backends.
"""

import logging
from typing import Generic, Optional

from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.data.resources.abstractions import (
    Resource,
    ResourceConflictError,
    TResourceSpec,
    TResourceStatus,
)
from neuroglia.serialization.abstractions import TextSerializer

log = logging.getLogger(__name__)


class ResourceRepository(
    Generic[TResourceSpec, TResourceStatus],
    Repository[Resource[TResourceSpec, TResourceStatus], str],
):
    """Repository for managing resources with multi-format serialization support."""

    def __init__(
        self,
        storage_backend: any,  # Storage implementation (Redis, Postgres, etc.)
        serializer: TextSerializer,
        resource_type: str = "Resource",
    ):
        self.storage_backend = storage_backend
        self.serializer = serializer
        self.resource_type = resource_type

        # Key prefix for organizing resources in storage
        self.key_prefix = f"resources:{resource_type.lower()}"

    async def contains_async(self, id: str) -> bool:
        """Determines whether the repository contains a resource with the specified id."""
        try:
            storage_key = self._get_storage_key(id)
            return await self.storage_backend.exists(storage_key)
        except Exception as e:
            log.error(f"Failed to check if resource {id} exists: {e}")
            return False

    async def get_async(self, id: str) -> Optional[Resource[TResourceSpec, TResourceStatus]]:
        """Gets the resource with the specified id, if any."""
        try:
            storage_key = self._get_storage_key(id)
            serialized_data = await self.storage_backend.get(storage_key)

            if serialized_data is None:
                return None

            # Deserialize the resource
            resource_dict = self.serializer.deserialize_from_text(serialized_data)
            return self._dict_to_resource(resource_dict)

        except Exception as e:
            log.error(f"Failed to get resource {id}: {e}")
            return None

    async def add_async(self, entity: Resource[TResourceSpec, TResourceStatus]) -> Resource[TResourceSpec, TResourceStatus]:
        """Adds the specified resource."""
        try:
            storage_key = self._get_storage_key(entity.id)

            # Check if resource already exists
            if await self.storage_backend.exists(storage_key):
                raise ValueError(f"Resource with id {entity.id} already exists")

            # Serialize and store
            serialized_data = self.serializer.serialize_to_text(entity.to_dict())
            await self.storage_backend.set(storage_key, serialized_data)

            log.info(f"Added resource {entity.metadata.namespace}/{entity.metadata.name}")
            return entity

        except Exception as e:
            log.error(f"Failed to add resource {entity.id}: {e}")
            raise

    async def update_async(self, entity: Resource[TResourceSpec, TResourceStatus]) -> Resource[TResourceSpec, TResourceStatus]:
        """Persists the changes that were made to the specified resource with optimistic locking."""
        try:
            storage_key = self._get_storage_key(entity.id)

            # Get current version from storage for conflict detection
            current = await self.get_async(entity.id)

            if current is None:
                raise ValueError(f"Resource {entity.id} not found")

            # Check for version conflict (optimistic locking)
            if current.metadata.resource_version != entity.metadata.resource_version:
                raise ResourceConflictError(entity.id, entity.metadata.resource_version, current.metadata.resource_version)

            # Increment version
            entity.metadata.resource_version = str(int(entity.metadata.resource_version) + 1)

            # Serialize and store
            serialized_data = self.serializer.serialize_to_text(entity.to_dict())
            await self.storage_backend.set(storage_key, serialized_data)

            log.debug(f"Updated resource {entity.metadata.namespace}/{entity.metadata.name} " f"to version {entity.metadata.resource_version}")
            return entity

        except Exception as e:
            log.error(f"Failed to update resource {entity.id}: {e}")
            raise

    async def update_with_retry_async(self, entity: Resource[TResourceSpec, TResourceStatus], max_retries: int = 3) -> Resource[TResourceSpec, TResourceStatus]:
        """Update resource with automatic conflict retry."""
        for attempt in range(max_retries):
            try:
                return await self.update_async(entity)
            except ResourceConflictError as e:
                if attempt == max_retries - 1:
                    # Last attempt failed
                    log.error(f"Failed to update resource {entity.id} after {max_retries} retries")
                    raise

                # Reload current version and retry
                log.warning(f"Update conflict on attempt {attempt + 1}/{max_retries}, retrying...")
                current = await self.get_async(entity.id)
                if current:
                    entity.metadata.resource_version = current.metadata.resource_version
                else:
                    raise ValueError(f"Resource {entity.id} was deleted during update")

        # Should not reach here
        raise RuntimeError("update_with_retry_async failed unexpectedly")

    async def remove_async(self, id: str) -> None:
        """Removes the resource with the specified key."""
        try:
            storage_key = self._get_storage_key(id)
            await self.storage_backend.delete(storage_key)

            log.info(f"Removed resource {id}")

        except Exception as e:
            log.error(f"Failed to remove resource {id}: {e}")
            raise

    async def list_async(self, namespace: Optional[str] = None, label_selector: Optional[dict[str, str]] = None) -> list[Resource[TResourceSpec, TResourceStatus]]:
        """List all resources matching the specified criteria."""
        try:
            # Get all keys for this resource type
            pattern = f"{self.key_prefix}:*"
            keys = await self.storage_backend.keys(pattern)

            resources = []
            for key in keys:
                try:
                    serialized_data = await self.storage_backend.get(key)
                    if serialized_data:
                        resource_dict = self.serializer.deserialize_from_text(serialized_data)
                        resource = self._dict_to_resource(resource_dict)

                        # Apply namespace filter
                        if namespace and resource.metadata.namespace != namespace:
                            continue

                        # Apply label selector filter
                        if label_selector and not self._matches_labels(resource, label_selector):
                            continue

                        resources.append(resource)

                except Exception as e:
                    log.warning(f"Failed to deserialize resource from key {key}: {e}")
                    continue

            return resources

        except Exception as e:
            log.error(f"Failed to list resources: {e}")
            return []

    async def get_by_namespace_async(self, namespace: str) -> list[Resource[TResourceSpec, TResourceStatus]]:
        """Get all resources in the specified namespace."""
        return await self.list_async(namespace=namespace)

    async def get_by_labels_async(self, labels: dict[str, str]) -> list[Resource[TResourceSpec, TResourceStatus]]:
        """Get all resources matching the specified labels."""
        return await self.list_async(label_selector=labels)

    def _get_storage_key(self, resource_id: str) -> str:
        """Generate a storage key for the resource."""
        return f"{self.key_prefix}:{resource_id}"

    def _matches_labels(self, resource: Resource[TResourceSpec, TResourceStatus], label_selector: dict[str, str]) -> bool:
        """Check if resource labels match the selector."""
        if not label_selector:
            return True

        resource_labels = resource.metadata.labels
        for key, value in label_selector.items():
            if resource_labels.get(key) != value:
                return False

        return True

    def _dict_to_resource(self, resource_dict: dict) -> Resource[TResourceSpec, TResourceStatus]:
        """Convert a dictionary back to a Resource object."""
        # This is a simplified implementation
        # In a real implementation, you would use proper deserialization
        # with type information to reconstruct the exact resource type

        # For now, we'll create a generic resource structure
        # This would need to be enhanced for specific resource types
        from neuroglia.data.resources.abstractions import ResourceMetadata

        metadata_dict = resource_dict.get("metadata", {})
        metadata = ResourceMetadata(
            name=metadata_dict.get("name", ""),
            namespace=metadata_dict.get("namespace", "default"),
            uid=metadata_dict.get("uid", ""),
            labels=metadata_dict.get("labels", {}),
            annotations=metadata_dict.get("annotations", {}),
            generation=metadata_dict.get("generation", 0),
            resource_version=metadata_dict.get("resource_version", "1"),
        )

        # This is a placeholder - in practice, you'd reconstruct the specific resource type
        # based on the kind and apiVersion fields
        class GenericResource(Resource):
            def __init__(self, api_version, kind, metadata, spec=None, status=None):
                super().__init__(api_version, kind, metadata, spec, status)

        return GenericResource(
            api_version=resource_dict.get("apiVersion", "v1"),
            kind=resource_dict.get("kind", "Resource"),
            metadata=metadata,
            spec=resource_dict.get("spec"),
            status=resource_dict.get("status"),
        )
