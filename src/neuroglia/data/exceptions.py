"""
Data access exceptions for the Neuroglia framework.

This module provides specialized exceptions for data access operations,
particularly for concurrency control and entity lifecycle management.
"""

from typing import Any, Optional


class DataAccessException(Exception):
    """Base exception for all data access operations."""


class OptimisticConcurrencyException(DataAccessException):
    """
    Exception raised when an optimistic concurrency conflict is detected.

    This occurs when attempting to update an aggregate whose state has been
    modified by another process since it was loaded. The exception includes
    both the expected and actual versions to help with conflict resolution.

    Attributes:
        entity_id: The unique identifier of the entity that had a conflict
        expected_version: The version the update operation expected to find
        actual_version: The actual current version in the data store
        message: Human-readable description of the conflict

    Examples:
        ```python
        try:
            await repository.update_async(order)
        except OptimisticConcurrencyException as ex:
            # Log conflict details
            logger.warning(
                f"Concurrency conflict for {ex.entity_id}: "
                f"expected v{ex.expected_version}, found v{ex.actual_version}"
            )

            # Return HTTP 409 Conflict
            return OperationResult.conflict(
                f"Order was modified by another process. Please reload and try again."
            )
        ```

    See Also:
        - Data Access Patterns: https://bvandewe.github.io/pyneuro/features/data-access/
        - Optimistic Concurrency: https://bvandewe.github.io/pyneuro/patterns/concurrency/
    """

    def __init__(
        self,
        entity_id: Any,
        expected_version: int,
        actual_version: int,
        message: Optional[str] = None,
    ):
        """
        Initialize an optimistic concurrency exception.

        Args:
            entity_id: The unique identifier of the entity
            expected_version: The version expected during the update
            actual_version: The actual current version in storage
            message: Optional custom error message
        """
        self.entity_id = entity_id
        self.expected_version = expected_version
        self.actual_version = actual_version

        if message is None:
            message = f"Optimistic concurrency conflict for entity '{entity_id}': " f"expected version {expected_version}, but found version {actual_version}. " f"The entity was modified by another process."

        super().__init__(message)


class EntityNotFoundException(DataAccessException):
    """
    Exception raised when an entity cannot be found in the data store.

    This is distinct from returning None - it indicates an error condition
    where an entity was expected to exist but was not found.

    Attributes:
        entity_id: The unique identifier of the missing entity
        entity_type: Optional type name of the entity

    Examples:
        ```python
        try:
            await repository.update_async(order)
        except EntityNotFoundException as ex:
            logger.error(f"Entity {ex.entity_id} not found")
            return OperationResult.not_found(f"Order {ex.entity_id} does not exist")
        ```
    """

    def __init__(self, entity_id: Any, entity_type: Optional[str] = None):
        """
        Initialize an entity not found exception.

        Args:
            entity_id: The unique identifier of the missing entity
            entity_type: Optional type name for better error messages
        """
        self.entity_id = entity_id
        self.entity_type = entity_type

        message = f"Entity '{entity_id}' not found"
        if entity_type:
            message = f"{entity_type} '{entity_id}' not found"

        super().__init__(message)
