"""Core abstractions for Resource Oriented Architecture.

This module defines the fundamental types and interfaces for managing
resources with declarative specifications, status tracking, and state machines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, Optional, TypeVar
from uuid import uuid4

from neuroglia.data.abstractions import Entity

# Type variables for resource generics
TResourceSpec = TypeVar("TResourceSpec", bound="ResourceSpec")
TResourceStatus = TypeVar("TResourceStatus", bound="ResourceStatus")
TState = TypeVar("TState", bound=Enum)


@dataclass
class ResourceMetadata:
    """Metadata for a resource, similar to Kubernetes metadata."""

    name: str
    namespace: str = "default"
    uid: str = field(default_factory=lambda: str(uuid4()))
    creation_timestamp: datetime = field(default_factory=datetime.now)
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    generation: int = 0
    resource_version: str = "1"
    finalizers: list[str] = field(default_factory=list)
    deletion_timestamp: Optional[datetime] = None

    def add_label(self, key: str, value: str) -> None:
        """Add a label to the resource metadata."""
        self.labels[key] = value

    def add_annotation(self, key: str, value: str) -> None:
        """Add an annotation to the resource metadata."""
        self.annotations[key] = value

    def increment_generation(self) -> None:
        """Increment the generation when spec changes."""
        self.generation += 1
        self.resource_version = str(int(self.resource_version) + 1)

    def add_finalizer(self, name: str) -> None:
        """Add a finalizer to block deletion until cleanup is complete."""
        if name not in self.finalizers:
            self.finalizers.append(name)

    def remove_finalizer(self, name: str) -> None:
        """Remove a finalizer to allow deletion to proceed."""
        if name in self.finalizers:
            self.finalizers.remove(name)

    def has_finalizer(self, name: str) -> bool:
        """Check if a specific finalizer is present."""
        return name in self.finalizers

    def has_finalizers(self) -> bool:
        """Check if resource has any finalizers."""
        return len(self.finalizers) > 0

    def is_being_deleted(self) -> bool:
        """Check if resource is marked for deletion."""
        return self.deletion_timestamp is not None

    def mark_for_deletion(self) -> None:
        """Mark the resource for deletion by setting deletion timestamp."""
        if self.deletion_timestamp is None:
            self.deletion_timestamp = datetime.now()


class ResourceSpec(ABC):
    """
    Abstraction defining the desired state specification for a resource.

    Represents the declarative intent of what the resource should look like,
    similar to how Kubernetes spec sections define desired state. Implementations
    should provide validation logic to ensure specifications are valid.
    """

    @abstractmethod
    def validate(self) -> list[str]:
        """Validate the resource specification. Returns list of validation errors."""
        raise NotImplementedError()


class ResourceStatus(ABC):
    """
    Abstraction representing the current observed state of a resource.

    Captures the actual state as observed by controllers, including reconciliation
    metadata like observed generation and last update times. This enables proper
    drift detection and reconciliation loop behavior.
    """

    def __init__(self):
        self.observed_generation: int = 0
        self.last_updated: datetime = datetime.now()

    def update_observed_generation(self, generation: int) -> None:
        """Update the observed generation when status is reconciled."""
        self.observed_generation = generation
        self.last_updated = datetime.now()


@dataclass
class StateTransition(Generic[TState]):
    """Represents a state transition in a state machine."""

    from_state: TState
    to_state: TState
    condition: Optional[str] = None
    action: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.from_state} -> {self.to_state}"


class StateMachine(Generic[TState], ABC):
    """
    Abstraction for defining valid state transitions in resource lifecycle management.

    Provides a framework for modeling complex resource state transitions with
    validation rules, ensuring resources can only move through valid state paths.
    Essential for modeling workflows and lifecycle management.
    """

    def __init__(self, initial_state: TState, transitions: dict[TState, list[TState]]):
        self.initial_state = initial_state
        self.transitions = transitions

    @abstractmethod
    def can_transition_to(self, current: TState, target: TState) -> bool:
        """Check if transition from current to target state is valid."""
        raise NotImplementedError()

    @abstractmethod
    def get_valid_transitions(self, current: TState) -> list[TState]:
        """Get all valid transitions from the current state."""
        raise NotImplementedError()

    def is_terminal_state(self, state: TState) -> bool:
        """Check if the state is terminal (no outgoing transitions)."""
        return len(self.transitions.get(state, [])) == 0


class Resource(Generic[TResourceSpec, TResourceStatus], Entity[str], ABC):
    """
    Core abstraction representing a manageable resource in the system.

    Combines Kubernetes-style declarative specification (spec) with observed
    state (status) and optional state machine behavior. Provides the foundation
    for resource-oriented architecture with reconciliation loop support.
    """

    def __init__(
        self,
        api_version: str,
        kind: str,
        metadata: ResourceMetadata,
        spec: TResourceSpec,
        status: Optional[TResourceStatus] = None,
        state_machine: Optional[StateMachine] = None,
    ):
        super().__init__()
        self.api_version = api_version
        self.kind = kind
        self.metadata = metadata
        self.spec = spec
        self.status = status
        self.state_machine = state_machine

        # Use metadata.uid as the entity ID
        self.id = metadata.uid

    def validate_spec(self) -> list[str]:
        """Validate the resource specification."""
        return self.spec.validate() if self.spec else []

    def needs_reconciliation(self) -> bool:
        """Check if resource needs reconciliation (spec changed)."""
        if not self.status:
            return True
        return self.metadata.generation > self.status.observed_generation

    def update_spec(self, new_spec: TResourceSpec) -> None:
        """Update the resource specification and increment generation."""
        self.spec = new_spec
        self.metadata.increment_generation()

    def to_dict(self) -> dict[str, Any]:
        """Convert resource to dictionary representation."""
        return {
            "apiVersion": self.api_version,
            "kind": self.kind,
            "metadata": self.metadata.__dict__,
            "spec": self.spec.__dict__ if self.spec else None,
            "status": self.status.__dict__ if self.status else None,
        }


class ResourceEvent(ABC):
    """
    Abstraction for events that occur during resource lifecycle operations.

    Provides a standard way to represent significant occurrences in resource
    management, enabling event-driven architecture and audit trail capabilities
    for debugging and monitoring resource operations.
    """

    def __init__(self, resource_uid: str, event_time: Optional[datetime] = None):
        self.resource_uid = resource_uid
        self.event_time = event_time or datetime.now()


class ResourceConflictError(Exception):
    """Raised when a resource update conflicts with current state."""

    def __init__(self, resource_id: str, expected_version: str, actual_version: str):
        self.resource_id = resource_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(f"Resource {resource_id} conflict: expected version {expected_version}, " f"but current version is {actual_version}")


class ResourceController(Generic[TResourceSpec, TResourceStatus], ABC):
    """
    Base controller for resource-oriented architecture patterns.

    Implements Kubernetes-style resource controllers with reconciliation
    loops for managing distributed system state.

    For detailed information about resource-oriented architecture, see:
    https://bvandewe.github.io/pyneuro/patterns/resource-oriented-architecture/
    """

    @abstractmethod
    async def reconcile(self, resource: Resource[TResourceSpec, TResourceStatus]) -> None:
        """Reconcile the resource to its desired state."""
        raise NotImplementedError()

    @abstractmethod
    async def finalize(self, resource: Resource[TResourceSpec, TResourceStatus]) -> bool:
        """Finalize resource cleanup. Returns True if cleanup is complete."""
        raise NotImplementedError()


class ResourceWatcher(Generic[TResourceSpec, TResourceStatus], ABC):
    """
    Watches for changes in resource state and triggers reconciliation.

    Implements the watcher pattern for detecting resource changes
    and coordinating with resource controllers.

    For detailed information about watcher patterns, see:
    https://bvandewe.github.io/pyneuro/patterns/watcher-reconciliation-patterns/
    """

    @abstractmethod
    async def watch(self, namespace: Optional[str] = None, label_selector: Optional[dict[str, str]] = None) -> None:
        """Start watching for resource changes."""
        raise NotImplementedError()

    @abstractmethod
    async def stop_watching(self) -> None:
        """Stop watching for resource changes."""
        raise NotImplementedError()
