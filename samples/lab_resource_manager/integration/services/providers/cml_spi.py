"""CML Lab Workers Service Provider Interface (SPI).

This module defines the abstract interface for CML worker operations.
Implementations of this interface handle CML-specific operations like
licensing, system monitoring, and lab provisioning.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class CmlSystemStats:
    """System statistics from CML worker."""

    cpu_usage_percent: float
    memory_total_mb: int
    memory_used_mb: int
    memory_available_mb: int
    disk_total_gb: int
    disk_used_gb: int
    disk_available_gb: int
    node_count: int  # Currently running nodes
    lab_count: int  # Currently running labs


@dataclass
class CmlLicenseInfo:
    """CML license information."""

    is_licensed: bool
    license_type: Optional[str] = None  # "permanent", "subscription", "evaluation"
    expiration_date: Optional[str] = None
    max_nodes: int = 5  # Max nodes (5 for unlicensed)
    features: list[str] = None  # List of licensed features


@dataclass
class CmlLabInstance:
    """CML lab instance information."""

    lab_id: str
    lab_title: str
    state: str  # "STOPPED", "STARTED", "DEFINED_ON_CORE"
    node_count: int
    owner: str
    created_at: str


@dataclass
class CmlAuthToken:
    """CML authentication token."""

    token: str
    expires_at: Optional[str] = None


class CmlLabWorkersSPI(ABC):
    """
    Service Provider Interface for CML Worker operations.

    This abstract interface defines the contract for interacting with
    Cisco Modeling Labs workers. Implementations must provide methods
    for authentication, licensing, monitoring, and lab management.
    """

    @abstractmethod
    async def authenticate(self, base_url: str, username: str, password: str) -> CmlAuthToken:
        """
        Authenticate to the CML worker and obtain an API token.

        Args:
            base_url: CML API base URL (e.g., "http://10.0.0.1/api/v0")
            username: CML admin username
            password: CML admin password

        Returns:
            CmlAuthToken containing the JWT token

        Raises:
            AuthenticationError: If authentication fails
        """

    @abstractmethod
    async def check_system_ready(self, base_url: str, token: str) -> bool:
        """
        Check if the CML system is ready to accept requests.

        Args:
            base_url: CML API base URL
            token: Authentication token

        Returns:
            True if system is ready, False otherwise
        """

    @abstractmethod
    async def get_system_information(self, base_url: str, token: str) -> dict:
        """
        Get CML system information (version, ready state, etc.).

        Args:
            base_url: CML API base URL
            token: Authentication token

        Returns:
            Dictionary with system information including version and ready state
        """

    @abstractmethod
    async def get_system_stats(self, base_url: str, token: str) -> CmlSystemStats:
        """
        Get system resource utilization statistics.

        Args:
            base_url: CML API base URL
            token: Authentication token

        Returns:
            CmlSystemStats with CPU, memory, disk, and lab statistics
        """

    @abstractmethod
    async def get_license_status(self, base_url: str, token: str) -> CmlLicenseInfo:
        """
        Get current licensing status.

        Args:
            base_url: CML API base URL
            token: Authentication token

        Returns:
            CmlLicenseInfo with licensing details
        """

    @abstractmethod
    async def set_license(self, base_url: str, token: str, license_token: str) -> bool:
        """
        Apply a license to the CML worker.

        Args:
            base_url: CML API base URL
            token: Authentication token
            license_token: CML license token string

        Returns:
            True if license was applied successfully

        Raises:
            LicensingError: If license application fails
        """

    @abstractmethod
    async def remove_license(self, base_url: str, token: str) -> bool:
        """
        Remove the license from the CML worker.

        Args:
            base_url: CML API base URL
            token: Authentication token

        Returns:
            True if license was removed successfully
        """

    @abstractmethod
    async def list_labs(self, base_url: str, token: str) -> list[CmlLabInstance]:
        """
        List all labs on the CML worker.

        Args:
            base_url: CML API base URL
            token: Authentication token

        Returns:
            List of CmlLabInstance objects
        """

    @abstractmethod
    async def create_lab(self, base_url: str, token: str, lab_title: str, lab_description: str, topology_data: Optional[dict] = None) -> str:
        """
        Create a new lab on the CML worker.

        Args:
            base_url: CML API base URL
            token: Authentication token
            lab_title: Title for the lab
            lab_description: Description for the lab
            topology_data: Optional topology configuration

        Returns:
            Lab ID of the created lab

        Raises:
            LabCreationError: If lab creation fails
        """

    @abstractmethod
    async def start_lab(self, base_url: str, token: str, lab_id: str) -> bool:
        """
        Start a lab on the CML worker.

        Args:
            base_url: CML API base URL
            token: Authentication token
            lab_id: ID of the lab to start

        Returns:
            True if lab was started successfully
        """

    @abstractmethod
    async def stop_lab(self, base_url: str, token: str, lab_id: str) -> bool:
        """
        Stop a lab on the CML worker.

        Args:
            base_url: CML API base URL
            token: Authentication token
            lab_id: ID of the lab to stop

        Returns:
            True if lab was stopped successfully
        """

    @abstractmethod
    async def delete_lab(self, base_url: str, token: str, lab_id: str) -> bool:
        """
        Delete a lab from the CML worker.

        Args:
            base_url: CML API base URL
            token: Authentication token
            lab_id: ID of the lab to delete

        Returns:
            True if lab was deleted successfully
        """

    @abstractmethod
    async def get_lab_details(self, base_url: str, token: str, lab_id: str) -> CmlLabInstance:
        """
        Get detailed information about a specific lab.

        Args:
            base_url: CML API base URL
            token: Authentication token
            lab_id: ID of the lab

        Returns:
            CmlLabInstance with lab details
        """

    @abstractmethod
    async def health_check(self, base_url: str, token: str) -> bool:
        """
        Perform a health check on the CML worker.

        Args:
            base_url: CML API base URL
            token: Authentication token

        Returns:
            True if worker is healthy, False otherwise
        """
