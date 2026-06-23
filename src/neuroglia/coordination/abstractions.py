"""Abstract coordination backend interface.

This module defines the interface for coordination backends
used for leader election and distributed locking.
"""

from abc import ABC, abstractmethod
from typing import Optional


class CoordinationBackend(ABC):
    """Abstract interface for coordination backends (Redis, etcd, etc.)."""

    @abstractmethod
    async def acquire_lease(self, key: str, holder_identity: str, ttl_seconds: int) -> bool:
        """
        Try to acquire a lease.

        Args:
            key: The lease key
            holder_identity: Identity of the lease holder
            ttl_seconds: Time-to-live for the lease in seconds

        Returns:
            True if lease was acquired, False otherwise
        """
        raise NotImplementedError()

    @abstractmethod
    async def renew_lease(self, key: str, holder_identity: str, ttl_seconds: int) -> bool:
        """
        Renew an existing lease.

        Args:
            key: The lease key
            holder_identity: Identity of the lease holder
            ttl_seconds: Time-to-live for the lease in seconds

        Returns:
            True if lease was renewed, False if not held by this identity
        """
        raise NotImplementedError()

    @abstractmethod
    async def release_lease(self, key: str, holder_identity: str) -> bool:
        """
        Release a lease.

        Args:
            key: The lease key
            holder_identity: Identity of the lease holder

        Returns:
            True if lease was released, False otherwise
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_lease_holder(self, key: str) -> Optional[str]:
        """
        Get the current lease holder.

        Args:
            key: The lease key

        Returns:
            Identity of the current lease holder, or None if no holder
        """
        raise NotImplementedError()
