"""LabWorkerPool Resource Definition.

This module defines the LabWorkerPool resource, which manages a pool of LabWorker
resources for a specific LabTrack. It handles capacity planning, auto-scaling,
and worker lifecycle management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from neuroglia.data.resources import Resource, ResourceSpec, ResourceStatus

from .lab_worker import AwsEc2Config, CmlConfig, LabWorkerPhase


class LabWorkerPoolPhase(str, Enum):
    """Phases in the LabWorkerPool lifecycle."""

    PENDING = "Pending"
    INITIALIZING = "Initializing"
    READY = "Ready"
    SCALING_UP = "ScalingUp"
    SCALING_DOWN = "ScalingDown"
    DRAINING = "Draining"
    TERMINATING = "Terminating"
    TERMINATED = "Terminated"
    FAILED = "Failed"


class ScalingPolicy(str, Enum):
    """Auto-scaling policy types."""

    NONE = "None"  # No auto-scaling
    CAPACITY_BASED = "CapacityBased"  # Scale based on capacity utilization
    LAB_COUNT_BASED = "LabCountBased"  # Scale based on active lab count
    SCHEDULED = "Scheduled"  # Scale based on schedule
    HYBRID = "Hybrid"  # Combination of policies


@dataclass
class CapacityThresholds:
    """Capacity thresholds for auto-scaling decisions."""

    # Utilization thresholds (0.0 to 1.0)
    cpu_scale_up_threshold: float = 0.75
    cpu_scale_down_threshold: float = 0.30
    memory_scale_up_threshold: float = 0.80
    memory_scale_down_threshold: float = 0.40

    # Lab count thresholds
    max_labs_per_worker: int = 15
    min_labs_per_worker: int = 3

    # Time-based thresholds
    scale_up_cooldown_minutes: int = 10
    scale_down_cooldown_minutes: int = 20

    def validate(self) -> list[str]:
        """Validate threshold configuration."""
        errors = []

        if not 0.0 <= self.cpu_scale_up_threshold <= 1.0:
            errors.append("cpu_scale_up_threshold must be between 0.0 and 1.0")
        if not 0.0 <= self.cpu_scale_down_threshold <= 1.0:
            errors.append("cpu_scale_down_threshold must be between 0.0 and 1.0")
        if not 0.0 <= self.memory_scale_up_threshold <= 1.0:
            errors.append("memory_scale_up_threshold must be between 0.0 and 1.0")
        if not 0.0 <= self.memory_scale_down_threshold <= 1.0:
            errors.append("memory_scale_down_threshold must be between 0.0 and 1.0")

        if self.cpu_scale_up_threshold <= self.cpu_scale_down_threshold:
            errors.append("cpu_scale_up_threshold must be > cpu_scale_down_threshold")
        if self.memory_scale_up_threshold <= self.memory_scale_down_threshold:
            errors.append("memory_scale_up_threshold must be > memory_scale_down_threshold")

        if self.max_labs_per_worker < 1:
            errors.append("max_labs_per_worker must be at least 1")
        if self.min_labs_per_worker < 0:
            errors.append("min_labs_per_worker must be non-negative")
        if self.max_labs_per_worker <= self.min_labs_per_worker:
            errors.append("max_labs_per_worker must be > min_labs_per_worker")

        if self.scale_up_cooldown_minutes < 0:
            errors.append("scale_up_cooldown_minutes must be non-negative")
        if self.scale_down_cooldown_minutes < 0:
            errors.append("scale_down_cooldown_minutes must be non-negative")

        return errors


@dataclass
class ScalingConfiguration:
    """Configuration for auto-scaling behavior."""

    # Scaling policy
    policy: ScalingPolicy = ScalingPolicy.NONE

    # Min/max worker count
    min_workers: int = 1
    max_workers: int = 10

    # Capacity thresholds
    thresholds: CapacityThresholds = field(default_factory=CapacityThresholds)

    # Enable/disable auto-scaling
    enabled: bool = False

    # Only scale during specific hours (24-hour format)
    allowed_hours_start: Optional[int] = None  # e.g., 8 (8 AM)
    allowed_hours_end: Optional[int] = None  # e.g., 20 (8 PM)

    def validate(self) -> list[str]:
        """Validate scaling configuration."""
        errors = []

        if self.min_workers < 0:
            errors.append("min_workers must be non-negative")
        if self.max_workers < 1:
            errors.append("max_workers must be at least 1")
        if self.min_workers > self.max_workers:
            errors.append("min_workers must be <= max_workers")

        if self.allowed_hours_start is not None:
            if not 0 <= self.allowed_hours_start <= 23:
                errors.append("allowed_hours_start must be between 0 and 23")
        if self.allowed_hours_end is not None:
            if not 0 <= self.allowed_hours_end <= 23:
                errors.append("allowed_hours_end must be between 0 and 23")

        errors.extend(self.thresholds.validate())

        return errors


@dataclass
class WorkerTemplate:
    """Template for creating new LabWorker resources."""

    # AWS configuration template
    aws_config: AwsEc2Config

    # CML configuration template
    cml_config: CmlConfig

    # Auto-license new workers
    auto_license: bool = True

    # Worker name prefix
    name_prefix: str = "lab-worker"

    # Additional labels to apply
    labels: dict[str, str] = field(default_factory=dict)

    # Additional annotations to apply
    annotations: dict[str, str] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate worker template."""
        errors = []
        errors.extend(self.aws_config.validate())
        # CML config validation would go here if needed
        if not self.name_prefix:
            errors.append("name_prefix cannot be empty")
        return errors


@dataclass
class LabWorkerPoolSpec(ResourceSpec):
    """Specification for LabWorkerPool resource."""

    # Target LabTrack this pool serves
    lab_track: str

    # Worker template for creating new workers
    worker_template: WorkerTemplate

    # Scaling configuration
    scaling: ScalingConfiguration = field(default_factory=ScalingConfiguration)

    # Desired phase (for administrative control)
    desired_phase: Optional[LabWorkerPoolPhase] = None

    def validate(self) -> list[str]:
        """Validate the pool specification."""
        errors = []

        if not self.lab_track:
            errors.append("lab_track is required")

        errors.extend(self.worker_template.validate())
        errors.extend(self.scaling.validate())

        return errors


@dataclass
class WorkerInfo:
    """Information about a worker in the pool."""

    name: str
    namespace: str
    phase: LabWorkerPhase
    active_lab_count: int
    cpu_utilization_percent: float
    memory_utilization_percent: float
    storage_utilization_percent: float
    is_licensed: bool
    created_at: datetime
    last_updated: datetime


@dataclass
class PoolCapacitySummary:
    """Summary of pool-wide capacity."""

    # Total capacity across all workers
    total_workers: int = 0
    ready_workers: int = 0
    active_workers: int = 0
    draining_workers: int = 0
    failed_workers: int = 0

    # Aggregate capacity
    total_cpu_cores: float = 0.0
    available_cpu_cores: float = 0.0
    total_memory_mb: float = 0.0
    available_memory_mb: float = 0.0
    total_storage_gb: float = 0.0
    available_storage_gb: float = 0.0

    # Lab hosting
    total_labs_hosted: int = 0
    max_concurrent_labs: int = 0

    # Average utilization across pool
    avg_cpu_utilization_percent: float = 0.0
    avg_memory_utilization_percent: float = 0.0
    avg_storage_utilization_percent: float = 0.0

    def get_overall_utilization(self) -> float:
        """Get overall utilization score (0.0 to 1.0)."""
        if self.ready_workers == 0:
            return 0.0

        # Weighted average of resource utilization
        cpu_weight = 0.4
        memory_weight = 0.4
        storage_weight = 0.2

        return (self.avg_cpu_utilization_percent / 100.0) * cpu_weight + (self.avg_memory_utilization_percent / 100.0) * memory_weight + (self.avg_storage_utilization_percent / 100.0) * storage_weight

    def needs_scale_up(self, thresholds: CapacityThresholds) -> bool:
        """Determine if pool needs to scale up."""
        if self.ready_workers == 0:
            return True

        cpu_util = self.avg_cpu_utilization_percent / 100.0
        mem_util = self.avg_memory_utilization_percent / 100.0

        # Scale up if any resource exceeds threshold
        if cpu_util > thresholds.cpu_scale_up_threshold:
            return True
        if mem_util > thresholds.memory_scale_up_threshold:
            return True

        # Scale up if average labs per worker exceeds threshold
        if self.ready_workers > 0:
            avg_labs = self.total_labs_hosted / self.ready_workers
            if avg_labs > thresholds.max_labs_per_worker:
                return True

        return False

    def needs_scale_down(self, thresholds: CapacityThresholds) -> bool:
        """Determine if pool needs to scale down."""
        if self.ready_workers <= 1:
            return False  # Don't scale below 1 worker

        cpu_util = self.avg_cpu_utilization_percent / 100.0
        mem_util = self.avg_memory_utilization_percent / 100.0

        # Scale down if all resources below threshold
        if cpu_util < thresholds.cpu_scale_down_threshold and mem_util < thresholds.memory_scale_down_threshold:
            # Also check lab count
            if self.ready_workers > 0:
                avg_labs = self.total_labs_hosted / self.ready_workers
                if avg_labs < thresholds.min_labs_per_worker:
                    return True

        return False


@dataclass
class ScalingEvent:
    """Record of a scaling event."""

    timestamp: datetime
    event_type: str  # "scale_up", "scale_down", "scale_failed"
    reason: str
    old_worker_count: int
    new_worker_count: int
    triggered_by: str  # "capacity", "lab_count", "manual", "schedule"


@dataclass
class LabWorkerPoolStatus(ResourceStatus):
    """Status of LabWorkerPool resource."""

    # Current phase
    phase: LabWorkerPoolPhase = LabWorkerPoolPhase.PENDING

    # Worker tracking
    workers: list[WorkerInfo] = field(default_factory=list)
    worker_names: list[str] = field(default_factory=list)

    # Capacity summary
    capacity: PoolCapacitySummary = field(default_factory=PoolCapacitySummary)

    # Scaling history
    last_scale_up: Optional[datetime] = None
    last_scale_down: Optional[datetime] = None
    scaling_events: list[ScalingEvent] = field(default_factory=list)

    # Health and readiness
    ready_condition: bool = False
    ready_workers_count: int = 0
    total_workers_count: int = 0

    # Timestamps
    initialized_at: Optional[datetime] = None
    last_reconciled: Optional[datetime] = None

    # Error tracking
    error_message: Optional[str] = None
    error_count: int = 0

    def add_scaling_event(self, event: ScalingEvent) -> None:
        """Add a scaling event to history (keep last 50)."""
        self.scaling_events.append(event)
        if len(self.scaling_events) > 50:
            self.scaling_events = self.scaling_events[-50:]

    def can_scale_up(self, config: ScalingConfiguration) -> bool:
        """Check if pool can scale up based on configuration and cooldown."""
        if not config.enabled:
            return False

        if self.total_workers_count >= config.max_workers:
            return False

        # Check cooldown
        if self.last_scale_up:
            from datetime import timedelta

            cooldown = timedelta(minutes=config.thresholds.scale_up_cooldown_minutes)
            if datetime.now() - self.last_scale_up < cooldown:
                return False

        # Check allowed hours
        if config.allowed_hours_start is not None and config.allowed_hours_end is not None:
            current_hour = datetime.now().hour
            if config.allowed_hours_start <= config.allowed_hours_end:
                # Normal range (e.g., 8 to 20)
                if not (config.allowed_hours_start <= current_hour < config.allowed_hours_end):
                    return False
            else:
                # Overnight range (e.g., 20 to 8)
                if not (current_hour >= config.allowed_hours_start or current_hour < config.allowed_hours_end):
                    return False

        return True

    def can_scale_down(self, config: ScalingConfiguration) -> bool:
        """Check if pool can scale down based on configuration and cooldown."""
        if not config.enabled:
            return False

        if self.total_workers_count <= config.min_workers:
            return False

        # Check cooldown
        if self.last_scale_down:
            from datetime import timedelta

            cooldown = timedelta(minutes=config.thresholds.scale_down_cooldown_minutes)
            if datetime.now() - self.last_scale_down < cooldown:
                return False

        # Check allowed hours
        if config.allowed_hours_start is not None and config.allowed_hours_end is not None:
            current_hour = datetime.now().hour
            if config.allowed_hours_start <= config.allowed_hours_end:
                # Normal range (e.g., 8 to 20)
                if not (config.allowed_hours_start <= current_hour < config.allowed_hours_end):
                    return False
            else:
                # Overnight range (e.g., 20 to 8)
                if not (current_hour >= config.allowed_hours_start or current_hour < config.allowed_hours_end):
                    return False

        return True

    def get_least_utilized_worker(self) -> Optional[WorkerInfo]:
        """Get the worker with lowest utilization (for scale-down)."""
        ready_workers = [w for w in self.workers if w.phase in [LabWorkerPhase.READY, LabWorkerPhase.READY_UNLICENSED] and w.active_lab_count == 0]

        if not ready_workers:
            return None

        # Sort by utilization (lowest first)
        ready_workers.sort(key=lambda w: (w.cpu_utilization_percent + w.memory_utilization_percent + w.storage_utilization_percent) / 3.0)

        return ready_workers[0]

    def get_best_worker_for_lab(self) -> Optional[WorkerInfo]:
        """Get the best worker to host a new lab."""
        available_workers = [w for w in self.workers if w.phase in [LabWorkerPhase.READY, LabWorkerPhase.ACTIVE] and w.cpu_utilization_percent < 80.0 and w.memory_utilization_percent < 80.0]

        if not available_workers:
            return None

        # Sort by utilization (lowest first) and lab count
        available_workers.sort(key=lambda w: (w.active_lab_count, (w.cpu_utilization_percent + w.memory_utilization_percent) / 2.0))

        return available_workers[0]


class LabWorkerPool(Resource[LabWorkerPoolSpec, LabWorkerPoolStatus]):
    """
    LabWorkerPool Resource - manages a pool of LabWorkers for a specific LabTrack.

    Responsibilities:
    - Maintain desired worker count based on scaling policy
    - Monitor aggregate capacity across all workers
    - Trigger auto-scaling based on utilization
    - Assign labs to appropriate workers
    - Handle worker failures and replacement
    """

    def __init__(self, namespace: str, name: str, spec: LabWorkerPoolSpec, status: Optional[LabWorkerPoolStatus] = None):
        super().__init__(api_version="lab.neuroglia.io/v1", kind="LabWorkerPool", namespace=namespace, name=name, spec=spec, status=status or LabWorkerPoolStatus())

    def should_scale_up(self) -> bool:
        """Determine if pool should scale up."""
        if not self.status.can_scale_up(self.spec.scaling):
            return False

        if self.spec.scaling.policy == ScalingPolicy.NONE:
            return False

        if self.spec.scaling.policy in [ScalingPolicy.CAPACITY_BASED, ScalingPolicy.LAB_COUNT_BASED, ScalingPolicy.HYBRID]:
            return self.status.capacity.needs_scale_up(self.spec.scaling.thresholds)

        return False

    def should_scale_down(self) -> bool:
        """Determine if pool should scale down."""
        if not self.status.can_scale_down(self.spec.scaling):
            return False

        if self.spec.scaling.policy == ScalingPolicy.NONE:
            return False

        if self.spec.scaling.policy in [ScalingPolicy.CAPACITY_BASED, ScalingPolicy.LAB_COUNT_BASED, ScalingPolicy.HYBRID]:
            return self.status.capacity.needs_scale_down(self.spec.scaling.thresholds)

        return False

    def get_target_worker_count(self) -> int:
        """Calculate target worker count based on current state."""
        if self.should_scale_up():
            return min(self.status.total_workers_count + 1, self.spec.scaling.max_workers)
        elif self.should_scale_down():
            return max(self.status.total_workers_count - 1, self.spec.scaling.min_workers)
        else:
            return self.status.total_workers_count

    def generate_worker_name(self, index: int) -> str:
        """Generate a unique worker name."""
        prefix = self.spec.worker_template.name_prefix
        track = self.spec.lab_track.lower().replace("_", "-")
        return f"{prefix}-{track}-{index:03d}"

    def is_ready(self) -> bool:
        """Check if pool is ready to host labs."""
        return self.status.phase in [LabWorkerPoolPhase.READY, LabWorkerPoolPhase.SCALING_UP, LabWorkerPoolPhase.SCALING_DOWN] and self.status.ready_workers_count > 0

    def is_draining(self) -> bool:
        """Check if pool is draining."""
        return self.status.phase == LabWorkerPoolPhase.DRAINING
