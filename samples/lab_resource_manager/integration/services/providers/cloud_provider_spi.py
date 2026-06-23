"""Cloud Provider Service Provider Interface.

This module defines the abstract interface for cloud infrastructure provisioning,
abstracting away specific cloud provider implementations (AWS, Azure, GCP, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class InstanceState(str, Enum):
    """Generic instance states across cloud providers."""

    PENDING = "pending"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    UNKNOWN = "unknown"


class VolumeType(str, Enum):
    """Generic volume types."""

    STANDARD = "standard"  # Standard magnetic disk
    SSD = "ssd"  # General purpose SSD
    PROVISIONED_IOPS_SSD = "provisioned_iops_ssd"  # High-performance SSD with guaranteed IOPS
    THROUGHPUT_OPTIMIZED = "throughput_optimized"  # HDD optimized for throughput
    COLD_STORAGE = "cold_storage"  # Infrequent access storage


@dataclass
class VolumeConfiguration:
    """Configuration for storage volumes."""

    size_gb: int
    volume_type: VolumeType = VolumeType.SSD
    iops: Optional[int] = None  # For provisioned IOPS volumes
    throughput_mbps: Optional[int] = None  # For throughput-optimized volumes
    encrypted: bool = True
    delete_on_termination: bool = True

    def validate(self) -> list[str]:
        """Validate volume configuration."""
        errors = []

        if self.size_gb < 1:
            errors.append("size_gb must be at least 1")

        if self.volume_type == VolumeType.PROVISIONED_IOPS_SSD:
            if not self.iops:
                errors.append("iops is required for provisioned_iops_ssd volume type")
            elif self.iops < 100:
                errors.append("iops must be at least 100 for provisioned_iops_ssd")

        if self.throughput_mbps is not None and self.throughput_mbps < 1:
            errors.append("throughput_mbps must be positive")

        return errors


@dataclass
class NetworkConfiguration:
    """Network configuration for instance."""

    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    security_group_ids: list[str] = field(default_factory=list)
    assign_public_ip: bool = True
    private_ip: Optional[str] = None

    def validate(self) -> list[str]:
        """Validate network configuration."""
        errors = []

        if self.private_ip:
            # Basic IP validation
            parts = self.private_ip.split(".")
            if len(parts) != 4:
                errors.append("private_ip must be a valid IPv4 address")

        return errors


@dataclass
class InstanceConfiguration:
    """Configuration for provisioning a cloud instance."""

    # Instance identification
    name: str
    namespace: str

    # Compute configuration
    image_id: str  # AMI ID, Image ID, etc.
    instance_type: str  # m5zn.metal, Standard_D32s_v3, n1-standard-32, etc.

    # Storage configuration
    root_volume: VolumeConfiguration
    additional_volumes: list[VolumeConfiguration] = field(default_factory=list)

    # Network configuration
    network: NetworkConfiguration = field(default_factory=NetworkConfiguration)

    # Access and permissions
    key_pair_name: Optional[str] = None
    iam_instance_profile: Optional[str] = None
    service_account: Optional[str] = None  # For GCP

    # Metadata and organization
    tags: dict[str, str] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)

    # User data / startup script
    user_data: Optional[str] = None

    def validate(self) -> list[str]:
        """Validate instance configuration."""
        errors = []

        if not self.name:
            errors.append("name is required")
        if not self.namespace:
            errors.append("namespace is required")
        if not self.image_id:
            errors.append("image_id is required")
        if not self.instance_type:
            errors.append("instance_type is required")

        errors.extend(self.root_volume.validate())

        for i, volume in enumerate(self.additional_volumes):
            volume_errors = volume.validate()
            errors.extend([f"additional_volumes[{i}]: {e}" for e in volume_errors])

        errors.extend(self.network.validate())

        return errors


@dataclass
class InstanceInfo:
    """Information about a provisioned instance."""

    instance_id: str
    name: str
    state: InstanceState
    instance_type: str

    # Network information
    public_ip: Optional[str] = None
    private_ip: Optional[str] = None
    public_dns: Optional[str] = None
    private_dns: Optional[str] = None

    # Location information
    availability_zone: Optional[str] = None
    region: Optional[str] = None

    # Lifecycle information
    launch_time: Optional[datetime] = None
    termination_time: Optional[datetime] = None

    # Provider-specific information
    provider_data: dict[str, str] = field(default_factory=dict)

    def is_running(self) -> bool:
        """Check if instance is running."""
        return self.state == InstanceState.RUNNING

    def is_terminated(self) -> bool:
        """Check if instance is terminated."""
        return self.state == InstanceState.TERMINATED

    def is_transitioning(self) -> bool:
        """Check if instance is in a transitional state."""
        return self.state in [
            InstanceState.PENDING,
            InstanceState.STOPPING,
            InstanceState.TERMINATING,
        ]


class CloudProvisioningError(Exception):
    """Base exception for cloud provisioning errors."""


class InstanceNotFoundError(CloudProvisioningError):
    """Instance not found in cloud provider."""


class InstanceProvisioningError(CloudProvisioningError):
    """Error provisioning instance."""


class InstanceOperationError(CloudProvisioningError):
    """Error performing operation on instance."""


class CloudProviderSPI(ABC):
    """
    Service Provider Interface for cloud infrastructure provisioning.

    This abstract interface defines the contract for provisioning and managing
    compute instances across different cloud providers (AWS, Azure, GCP, etc.).

    Implementations should handle provider-specific details while presenting
    a consistent interface to the application layer.
    """

    @abstractmethod
    async def provision_instance(self, config: InstanceConfiguration) -> InstanceInfo:
        """
        Provision a new compute instance.

        Args:
            config: Instance configuration

        Returns:
            InstanceInfo with details of the provisioned instance

        Raises:
            InstanceProvisioningError: If provisioning fails
        """

    @abstractmethod
    async def get_instance_info(self, instance_id: str) -> InstanceInfo:
        """
        Get information about an instance.

        Args:
            instance_id: Instance identifier

        Returns:
            InstanceInfo with current instance details

        Raises:
            InstanceNotFoundError: If instance does not exist
        """

    @abstractmethod
    async def wait_for_instance_running(self, instance_id: str, timeout_seconds: int = 600) -> InstanceInfo:
        """
        Wait for instance to reach running state.

        Args:
            instance_id: Instance identifier
            timeout_seconds: Maximum time to wait

        Returns:
            InstanceInfo when instance is running

        Raises:
            InstanceOperationError: If instance fails to start or timeout
        """

    @abstractmethod
    async def stop_instance(self, instance_id: str) -> None:
        """
        Stop a running instance.

        Args:
            instance_id: Instance identifier

        Raises:
            InstanceNotFoundError: If instance does not exist
            InstanceOperationError: If stop operation fails
        """

    @abstractmethod
    async def start_instance(self, instance_id: str) -> None:
        """
        Start a stopped instance.

        Args:
            instance_id: Instance identifier

        Raises:
            InstanceNotFoundError: If instance does not exist
            InstanceOperationError: If start operation fails
        """

    @abstractmethod
    async def terminate_instance(self, instance_id: str) -> None:
        """
        Terminate an instance (permanent deletion).

        Args:
            instance_id: Instance identifier

        Raises:
            InstanceNotFoundError: If instance does not exist
            InstanceOperationError: If termination fails
        """

    @abstractmethod
    async def wait_for_instance_terminated(self, instance_id: str, timeout_seconds: int = 300) -> None:
        """
        Wait for instance to be fully terminated.

        Args:
            instance_id: Instance identifier
            timeout_seconds: Maximum time to wait

        Raises:
            InstanceOperationError: If timeout occurs
        """

    @abstractmethod
    async def add_tags(self, instance_id: str, tags: dict[str, str]) -> None:
        """
        Add or update tags/labels on an instance.

        Args:
            instance_id: Instance identifier
            tags: Tags to add or update

        Raises:
            InstanceNotFoundError: If instance does not exist
            InstanceOperationError: If tagging fails
        """

    @abstractmethod
    async def list_instances(self, filters: Optional[dict[str, str]] = None) -> list[InstanceInfo]:
        """
        List instances with optional filtering.

        Args:
            filters: Optional filters (tags, state, etc.)

        Returns:
            List of InstanceInfo objects
        """

    @abstractmethod
    async def get_console_output(self, instance_id: str) -> str:
        """
        Get console output from an instance (for debugging).

        Args:
            instance_id: Instance identifier

        Returns:
            Console output text

        Raises:
            InstanceNotFoundError: If instance does not exist
        """

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the cloud provider name.

        Returns:
            Provider name (e.g., "AWS", "Azure", "GCP")
        """
