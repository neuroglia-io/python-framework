"""Leader election implementation for distributed coordination.

This module provides Kubernetes-style leader election using distributed
leases, enabling high availability deployments with multiple controller instances.
"""
import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from .abstractions import CoordinationBackend

log = logging.getLogger(__name__)


@dataclass
class Lease:
    """Represents a distributed lease for leader election."""

    name: str
    holder_identity: str
    acquire_time: datetime
    renew_time: datetime
    lease_duration: timedelta

    def is_expired(self) -> bool:
        """Check if the lease has expired."""
        expiry = self.renew_time + self.lease_duration
        return datetime.now() > expiry

    def time_until_expiry(self) -> timedelta:
        """Get the time remaining until lease expiry."""
        expiry = self.renew_time + self.lease_duration
        remaining = expiry - datetime.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)


@dataclass
class LeaderElectionConfig:
    """Configuration for leader election."""

    lease_name: str
    identity: str = field(default_factory=lambda: f"controller-{uuid4().hex[:8]}")
    lease_duration: timedelta = field(default_factory=lambda: timedelta(seconds=15))
    renew_interval: timedelta = field(default_factory=lambda: timedelta(seconds=10))
    retry_period: timedelta = field(default_factory=lambda: timedelta(seconds=2))


class LeaderElection:
    """
    Implements leader election using distributed leases.

    This enables multiple controller instances to coordinate and ensure
    only one leader is actively reconciling resources at a time.

    Example:
        ```python
        from neuroglia.coordination import LeaderElection, LeaderElectionConfig
        from neuroglia.coordination.redis_backend import RedisCoordinationBackend

        backend = RedisCoordinationBackend("localhost", 6379)
        config = LeaderElectionConfig(lease_name="my-controller")

        election = LeaderElection(backend, config)

        async def on_started_leading():
            print("I am now the leader!")
            # Start controller operations

        async def on_stopped_leading():
            print("I am no longer the leader")
            # Stop controller operations

        await election.run(on_started_leading, on_stopped_leading)
        ```
    """

    def __init__(self, backend: CoordinationBackend, config: LeaderElectionConfig):
        self.backend = backend
        self.config = config
        self._is_leader = False
        self._running = False
        self._current_lease: Optional[Lease] = None

    async def run(
        self,
        on_started_leading: Callable[[], None],
        on_stopped_leading: Callable[[], None],
    ) -> None:
        """
        Run the leader election loop.

        Args:
            on_started_leading: Callback when this instance becomes leader
            on_stopped_leading: Callback when this instance loses leadership
        """
        self._running = True
        log.info(f"Starting leader election for lease '{self.config.lease_name}' " f"with identity '{self.config.identity}'")

        try:
            while self._running:
                try:
                    if await self._try_acquire_or_renew_lease():
                        if not self._is_leader:
                            # Transitioned to leader
                            self._is_leader = True
                            log.info(f"Acquired leadership for lease '{self.config.lease_name}'")

                            if asyncio.iscoroutinefunction(on_started_leading):
                                await on_started_leading()
                            else:
                                on_started_leading()

                        # Leader: renew after renew_interval
                        await asyncio.sleep(self.config.renew_interval.total_seconds())

                    else:
                        if self._is_leader:
                            # Lost leadership
                            self._is_leader = False
                            self._current_lease = None
                            log.warning(f"Lost leadership for lease '{self.config.lease_name}'")

                            if asyncio.iscoroutinefunction(on_stopped_leading):
                                await on_stopped_leading()
                            else:
                                on_stopped_leading()

                        # Not leader: retry after retry_period
                        await asyncio.sleep(self.config.retry_period.total_seconds())

                except Exception as e:
                    log.error(f"Error in leader election loop: {e}")
                    await asyncio.sleep(self.config.retry_period.total_seconds())

        finally:
            # Clean up on exit
            if self._is_leader:
                await self._release_lease()
                self._is_leader = False
                log.info(f"Released leadership for lease '{self.config.lease_name}'")

                if asyncio.iscoroutinefunction(on_stopped_leading):
                    await on_stopped_leading()
                else:
                    on_stopped_leading()

    async def stop(self) -> None:
        """Stop the leader election loop."""
        log.info(f"Stopping leader election for lease '{self.config.lease_name}'")
        self._running = False

    def is_leader(self) -> bool:
        """Check if this instance is currently the leader."""
        return self._is_leader

    def get_leader_identity(self) -> Optional[str]:
        """Get the identity of the current leader."""
        if self._current_lease:
            return self._current_lease.holder_identity
        return None

    async def _try_acquire_or_renew_lease(self) -> bool:
        """Try to acquire or renew the lease."""
        lease_key = f"leases:{self.config.lease_name}"
        ttl_seconds = int(self.config.lease_duration.total_seconds())

        if self._current_lease:
            # Try to renew existing lease
            renewed = await self.backend.renew_lease(lease_key, self.config.identity, ttl_seconds)

            if renewed:
                # Update lease
                self._current_lease.renew_time = datetime.now()
                log.debug(f"Renewed lease '{self.config.lease_name}' " f"(expires in {ttl_seconds}s)")
                return True
            else:
                # Lost lease
                log.warning(f"Failed to renew lease '{self.config.lease_name}', " f"may have been acquired by another instance")
                self._current_lease = None
                return False

        else:
            # Try to acquire new lease
            acquired = await self.backend.acquire_lease(lease_key, self.config.identity, ttl_seconds)

            if acquired:
                # Create lease
                now = datetime.now()
                self._current_lease = Lease(
                    name=self.config.lease_name,
                    holder_identity=self.config.identity,
                    acquire_time=now,
                    renew_time=now,
                    lease_duration=self.config.lease_duration,
                )
                log.info(f"Acquired lease '{self.config.lease_name}' " f"(expires in {ttl_seconds}s)")
                return True
            else:
                # Lease held by another instance
                current_holder = await self.backend.get_lease_holder(lease_key)
                log.debug(f"Lease '{self.config.lease_name}' is held by '{current_holder}'")
                return False

    async def _release_lease(self) -> None:
        """Release the current lease."""
        if not self._current_lease:
            return

        lease_key = f"leases:{self.config.lease_name}"
        released = await self.backend.release_lease(lease_key, self.config.identity)

        if released:
            log.info(f"Released lease '{self.config.lease_name}'")
        else:
            log.warning(f"Failed to release lease '{self.config.lease_name}', " f"may have been acquired by another instance")

        self._current_lease = None
