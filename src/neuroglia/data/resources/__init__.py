"""Resource Oriented Architecture module for Neuroglia framework.

This module provides Kubernetes-inspired resource management capabilities
including declarative specifications, status tracking, state machines,
and reconciliation controllers.
"""

from .abstractions import (
    Resource,
    ResourceConflictError,
    ResourceController,
    ResourceEvent,
    ResourceMetadata,
    ResourceSpec,
    ResourceStatus,
    ResourceWatcher,
    StateMachine,
    StateTransition,
    TResourceSpec,
    TResourceStatus,
    TState,
)
from .controller import (
    ReconciliationResult,
    ReconciliationStatus,
    ResourceControllerBase,
)
from .state_machine import (
    InvalidStateTransitionError,
    StateMachineEngine,
    StateTransitionError,
    TransitionValidator,
)
from .watcher import ResourceChangeEvent, ResourceChangeType, ResourceWatcherBase

__all__ = [
    # Core abstractions
    "Resource",
    "ResourceSpec",
    "ResourceStatus",
    "ResourceMetadata",
    "StateMachine",
    "StateTransition",
    "ResourceController",
    "ResourceWatcher",
    "ResourceEvent",
    "ResourceConflictError",
    "TResourceSpec",
    "TResourceStatus",
    "TState",
    # State machine
    "StateMachineEngine",
    "TransitionValidator",
    "StateTransitionError",
    "InvalidStateTransitionError",
    # Controller
    "ResourceControllerBase",
    "ReconciliationResult",
    "ReconciliationStatus",
    # Watcher
    "ResourceWatcherBase",
    "ResourceChangeEvent",
    "ResourceChangeType",
]
