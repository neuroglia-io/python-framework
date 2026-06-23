"""Lab Instance Request resource definition.

This module defines the LabInstanceRequest resource with its specification,
status, and state machine for managing laboratory instance lifecycles.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from neuroglia.data.resources.abstractions import (
    Resource,
    ResourceMetadata,
    ResourceSpec,
    ResourceStatus,
)
from neuroglia.data.resources.state_machine import StateMachineEngine


class LabInstancePhase(Enum):
    """Phases of a lab instance lifecycle."""

    PENDING = "Pending"  # Just created, waiting for resources
    SCHEDULING = "Scheduling"  # Waiting for worker assignment
    PROVISIONING = "Provisioning"  # Resources being allocated
    RUNNING = "Running"  # Lab instance is active
    STOPPING = "Stopping"  # Graceful shutdown in progress
    COMPLETED = "Completed"  # Successfully finished
    FAILED = "Failed"  # Error occurred
    EXPIRED = "Expired"  # Timed out


class LabInstanceType(Enum):
    """Type of lab instance deployment."""

    CML = "CML"  # Cisco Modeling Labs (network simulation)
    CONTAINER = "Container"  # Container-based lab
    VM = "VM"  # Virtual machine-based lab
    HYBRID = "Hybrid"  # Combination of types


@dataclass
class LabInstanceCondition:
    """Condition representing the state of a specific aspect of the lab instance."""

    type: str  # e.g., "ResourcesAvailable", "ContainerReady"
    status: bool  # True/False
    last_transition: datetime
    reason: str
    message: str


@dataclass
class LabInstanceRequestSpec(ResourceSpec):
    """Specification for a lab instance request (desired state)."""

    lab_template: str  # e.g., "python-data-science-v1.2"
    duration_minutes: int  # e.g., 120
    student_email: str  # e.g., "student@university.edu"

    # Lab type and track
    lab_instance_type: LabInstanceType = LabInstanceType.CONTAINER  # Default to container
    lab_track: Optional[str] = None  # e.g., "network-automation", "data-science"

    # Scheduling
    scheduled_start: Optional[datetime] = None  # None = on-demand

    # Resource configuration
    resource_limits: dict[str, str] = field(default_factory=lambda: {"cpu": "1", "memory": "2Gi"})
    environment_variables: dict[str, str] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate the lab instance specification."""
        errors = []

        if not self.lab_template:
            errors.append("lab_template is required")

        if self.duration_minutes <= 0:
            errors.append("duration_minutes must be positive")

        if self.duration_minutes > 480:  # Max 8 hours
            errors.append("duration_minutes cannot exceed 480 (8 hours)")

        if not self.student_email or "@" not in self.student_email:
            errors.append("valid student_email is required")

        # Validate resource limits
        if self.resource_limits:
            if "cpu" in self.resource_limits:
                try:
                    cpu_value = float(self.resource_limits["cpu"])
                    if cpu_value <= 0 or cpu_value > 8:
                        errors.append("cpu must be between 0 and 8")
                except ValueError:
                    errors.append("cpu must be a valid number")

            if "memory" in self.resource_limits:
                memory = self.resource_limits["memory"]
                if not memory.endswith(("Mi", "Gi")) or not memory[:-2].isdigit():
                    errors.append("memory must be in format like '2Gi' or '512Mi'")

        return errors


@dataclass
class LabInstanceRequestStatus(ResourceStatus):
    """Status of a lab instance request (current state)."""

    def __init__(self):
        super().__init__()
        self.phase: LabInstancePhase = LabInstancePhase.PENDING
        self.conditions: list[LabInstanceCondition] = []

        # Worker assignment
        self.worker_ref: Optional[str] = None  # Reference to assigned LabWorker (namespace/name)
        self.worker_name: Optional[str] = None  # Name of assigned worker
        self.worker_namespace: Optional[str] = None  # Namespace of assigned worker

        # Lifecycle timestamps
        self.start_time: Optional[datetime] = None
        self.completion_time: Optional[datetime] = None
        self.scheduled_at: Optional[datetime] = None
        self.assigned_at: Optional[datetime] = None  # When worker was assigned

        # Runtime information
        self.container_id: Optional[str] = None
        self.access_url: Optional[str] = None
        self.cml_lab_id: Optional[str] = None  # For CML-type labs

        # Resource allocation
        self.resource_allocation: Optional[dict[str, str]] = None

        # Error tracking
        self.error_message: Optional[str] = None
        self.retry_count: int = 0

    def add_condition(self, condition: LabInstanceCondition) -> None:
        """Add or update a condition."""
        # Remove existing condition of the same type
        self.conditions = [c for c in self.conditions if c.type != condition.type]
        self.conditions.append(condition)
        self.last_updated = datetime.now()

    def get_condition(self, condition_type: str) -> Optional[LabInstanceCondition]:
        """Get a condition by type."""
        for condition in self.conditions:
            if condition.type == condition_type:
                return condition
        return None

    def is_condition_true(self, condition_type: str) -> bool:
        """Check if a condition is true."""
        condition = self.get_condition(condition_type)
        return condition is not None and condition.status


class LabInstanceStateMachine(StateMachineEngine[LabInstancePhase]):
    """State machine for lab instance lifecycle management."""

    def __init__(self):
        # Define valid state transitions
        transitions = {
            LabInstancePhase.PENDING: [LabInstancePhase.SCHEDULING, LabInstancePhase.FAILED],
            LabInstancePhase.SCHEDULING: [LabInstancePhase.PROVISIONING, LabInstancePhase.PENDING, LabInstancePhase.FAILED],  # Can go back if worker assignment fails
            LabInstancePhase.PROVISIONING: [LabInstancePhase.RUNNING, LabInstancePhase.FAILED],
            LabInstancePhase.RUNNING: [LabInstancePhase.STOPPING, LabInstancePhase.EXPIRED, LabInstancePhase.FAILED],
            LabInstancePhase.STOPPING: [LabInstancePhase.COMPLETED, LabInstancePhase.FAILED],
            LabInstancePhase.COMPLETED: [],  # Terminal state
            LabInstancePhase.FAILED: [],  # Terminal state
            LabInstancePhase.EXPIRED: [],  # Terminal state
        }

        super().__init__(initial_state=LabInstancePhase.PENDING, transitions=transitions)


class LabInstanceRequest(Resource[LabInstanceRequestSpec, LabInstanceRequestStatus]):
    """Complete lab instance resource with spec, status, and state machine."""

    def __init__(self, metadata: ResourceMetadata, spec: LabInstanceRequestSpec, status: Optional[LabInstanceRequestStatus] = None):
        super().__init__(api_version="lab.neuroglia.io/v1", kind="LabInstanceRequest", metadata=metadata, spec=spec, status=status or LabInstanceRequestStatus(), state_machine=LabInstanceStateMachine())

    def is_scheduled(self) -> bool:
        """Check if this is a scheduled lab instance."""
        return self.spec.scheduled_start is not None

    def is_on_demand(self) -> bool:
        """Check if this is an on-demand lab instance."""
        return not self.is_scheduled()

    def is_expired(self) -> bool:
        """Check if lab instance has exceeded its duration."""
        if not self.status.start_time:
            return False

        expected_end = self.status.start_time + timedelta(minutes=self.spec.duration_minutes)
        return datetime.now() > expected_end

    def get_expected_end_time(self) -> Optional[datetime]:
        """Get the expected end time of the lab instance."""
        if not self.status.start_time:
            return None

        return self.status.start_time + timedelta(minutes=self.spec.duration_minutes)

    def should_start_now(self) -> bool:
        """Check if a scheduled lab instance should start now."""
        if not self.is_scheduled():
            return False

        if self.status.phase != LabInstancePhase.PENDING:
            return False

        # Allow starting up to 5 minutes early
        start_window = self.spec.scheduled_start - timedelta(minutes=5)
        return datetime.now() >= start_window

    def get_runtime_duration(self) -> Optional[timedelta]:
        """Get the current runtime duration."""
        if not self.status.start_time:
            return None

        end_time = self.status.completion_time or datetime.now()
        return end_time - self.status.start_time

    def can_transition_to_phase(self, target_phase: LabInstancePhase) -> bool:
        """Check if transition to target phase is valid."""
        return self.state_machine.can_transition_to(self.status.phase, target_phase)

    def transition_to_phase(self, target_phase: LabInstancePhase, reason: Optional[str] = None) -> None:
        """Transition to a new phase with validation."""
        if not self.can_transition_to_phase(target_phase):
            raise ValueError(f"Invalid transition from {self.status.phase} to {target_phase}")

        old_phase = self.status.phase
        self.status.phase = target_phase
        self.status.last_updated = datetime.now()

        # Add state transition condition
        condition = LabInstanceCondition(type="PhaseTransition", status=True, last_transition=datetime.now(), reason=reason or f"TransitionTo{target_phase.value}", message=f"Transitioned from {old_phase.value} to {target_phase.value}")
        self.status.add_condition(condition)

        # Record the transition in state machine
        if self.state_machine:
            self.state_machine.execute_transition(current=old_phase, target=target_phase, action=reason)

    # Worker assignment methods

    def assign_to_worker(self, worker_namespace: str, worker_name: str) -> None:
        """Assign this lab instance to a specific worker."""
        self.status.worker_namespace = worker_namespace
        self.status.worker_name = worker_name
        self.status.worker_ref = f"{worker_namespace}/{worker_name}"
        self.status.assigned_at = datetime.now()

        # Add condition
        condition = LabInstanceCondition(type="WorkerAssigned", status=True, last_transition=datetime.now(), reason="AssignedToWorker", message=f"Assigned to worker {worker_namespace}/{worker_name}")
        self.status.add_condition(condition)

    def unassign_from_worker(self) -> None:
        """Remove worker assignment."""
        self.status.worker_namespace = None
        self.status.worker_name = None
        self.status.worker_ref = None

        # Add condition
        condition = LabInstanceCondition(type="WorkerAssigned", status=False, last_transition=datetime.now(), reason="WorkerUnassigned", message="Worker assignment removed")
        self.status.add_condition(condition)

    def is_assigned_to_worker(self) -> bool:
        """Check if lab is assigned to a worker."""
        return self.status.worker_ref is not None

    def get_worker_ref(self) -> Optional[str]:
        """Get the worker reference (namespace/name)."""
        return self.status.worker_ref

    def is_cml_type(self) -> bool:
        """Check if this is a CML-type lab instance."""
        return self.spec.lab_instance_type == LabInstanceType.CML

    def is_container_type(self) -> bool:
        """Check if this is a container-type lab instance."""
        return self.spec.lab_instance_type == LabInstanceType.CONTAINER

    def is_vm_type(self) -> bool:
        """Check if this is a VM-type lab instance."""
        return self.spec.lab_instance_type == LabInstanceType.VM

    def requires_worker_assignment(self) -> bool:
        """Check if this lab type requires worker assignment."""
        # CML and VM types require worker assignment
        return self.spec.lab_instance_type in [LabInstanceType.CML, LabInstanceType.VM, LabInstanceType.HYBRID]

    def get_lab_track(self) -> Optional[str]:
        """Get the lab track for this instance."""
        return self.spec.lab_track
