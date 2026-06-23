"""Coordination primitives for distributed systems.

This module provides coordination mechanisms for distributed Neuroglia
applications, including leader election and distributed locking.
"""

from .abstractions import CoordinationBackend
from .leader_election import LeaderElection, LeaderElectionConfig, Lease
from .redis_backend import RedisCoordinationBackend

__all__ = [
    "Lease",
    "LeaderElection",
    "LeaderElectionConfig",
    "CoordinationBackend",
    "RedisCoordinationBackend",
]
