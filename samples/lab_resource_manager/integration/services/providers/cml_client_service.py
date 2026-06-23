"""CML Client Service.

This service implements the CmlLabWorkersSPI interface to interact with
Cisco Modeling Labs (CML) API using httpx for async HTTP requests.
"""

import logging
from typing import Optional

import httpx
from integration.services.providers.cml_spi import (
    CmlAuthToken,
    CmlLabInstance,
    CmlLabWorkersSPI,
    CmlLicenseInfo,
    CmlSystemStats,
)

log = logging.getLogger(__name__)


class CmlAuthenticationError(Exception):
    """Exception raised when CML authentication fails."""


class CmlLicensingError(Exception):
    """Exception raised when CML licensing operation fails."""


class CmlLabCreationError(Exception):
    """Exception raised when lab creation fails."""


class CmlApiError(Exception):
    """Exception raised for general CML API errors."""


class CmlClientService(CmlLabWorkersSPI):
    """
    CML client service implementing the CmlLabWorkersSPI interface.

    This service provides async HTTP client functionality for interacting
    with the CML API using httpx.
    """

    def __init__(self, timeout_seconds: int = 30):
        """
        Initialize CML client service.

        Args:
            timeout_seconds: HTTP request timeout in seconds
        """
        self.timeout = timeout_seconds
        log.info(f"CmlClientService initialized with {timeout_seconds}s timeout")

    def _get_headers(self, token: Optional[str] = None) -> dict[str, str]:
        """Get HTTP headers for CML API requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def authenticate(self, base_url: str, username: str, password: str) -> CmlAuthToken:
        """
        Authenticate to the CML worker and obtain an API token.

        CML API: POST /api/v0/authenticate
        """
        url = f"{base_url}/authenticate"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.post(url, json={"username": username, "password": password}, headers=self._get_headers())

                if response.status_code == 200:
                    token = response.text.strip('"')  # Remove quotes from JWT
                    log.info(f"Successfully authenticated to CML at {base_url}")
                    return CmlAuthToken(token=token)

                elif response.status_code == 403:
                    error_msg = f"Authentication failed: Invalid credentials for {username}"
                    log.error(error_msg)
                    raise CmlAuthenticationError(error_msg)

                else:
                    error_msg = f"Authentication failed with status {response.status_code}: {response.text}"
                    log.error(error_msg)
                    raise CmlAuthenticationError(error_msg)

        except httpx.RequestError as e:
            error_msg = f"Network error during authentication: {str(e)}"
            log.error(error_msg)
            raise CmlAuthenticationError(error_msg) from e

    async def check_system_ready(self, base_url: str, token: str) -> bool:
        """
        Check if the CML system is ready to accept requests.

        CML API: GET /api/v0/system_information
        """
        try:
            system_info = await self.get_system_information(base_url, token)
            return system_info.get("ready", False)
        except Exception as e:
            log.warning(f"Error checking system ready: {e}")
            return False

    async def get_system_information(self, base_url: str, token: str) -> dict:
        """
        Get CML system information (version, ready state, etc.).

        CML API: GET /api/v0/system_information
        """
        url = f"{base_url}/system_information"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.get(url, headers=self._get_headers(token))

                if response.status_code == 200:
                    return response.json()
                else:
                    raise CmlApiError(f"Failed to get system information: {response.status_code}")

        except httpx.RequestError as e:
            raise CmlApiError(f"Network error getting system information: {str(e)}") from e

    async def get_system_stats(self, base_url: str, token: str) -> CmlSystemStats:
        """
        Get system resource utilization statistics.

        CML API: GET /api/v0/system_stats
        """
        url = f"{base_url}/system_stats"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.get(url, headers=self._get_headers(token))

                if response.status_code == 200:
                    data = response.json()

                    # Parse the nested compute stats structure
                    all_stats = data.get("all", {})

                    # Extract compute resources
                    cpu_usage = all_stats.get("cpu_usage", 0.0)
                    memory_stats = all_stats.get("memory", {})
                    disk_stats = all_stats.get("disk", {})

                    # Count nodes and labs (from computes)
                    computes = data.get("computes", {})
                    node_count = sum(compute.get("nodes_in_use", 0) for compute in computes.values())
                    lab_count = sum(compute.get("labs_in_use", 0) for compute in computes.values())

                    return CmlSystemStats(
                        cpu_usage_percent=cpu_usage, memory_total_mb=memory_stats.get("total", 0) // (1024 * 1024), memory_used_mb=memory_stats.get("used", 0) // (1024 * 1024), memory_available_mb=memory_stats.get("available", 0) // (1024 * 1024), disk_total_gb=disk_stats.get("total", 0) // (1024 * 1024 * 1024), disk_used_gb=disk_stats.get("used", 0) // (1024 * 1024 * 1024), disk_available_gb=disk_stats.get("free", 0) // (1024 * 1024 * 1024), node_count=node_count, lab_count=lab_count
                    )
                else:
                    raise CmlApiError(f"Failed to get system stats: {response.status_code}")

        except httpx.RequestError as e:
            raise CmlApiError(f"Network error getting system stats: {str(e)}") from e

    async def get_license_status(self, base_url: str, token: str) -> CmlLicenseInfo:
        """
        Get current licensing status.

        CML API: GET /api/v0/licensing
        """
        url = f"{base_url}/licensing"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.get(url, headers=self._get_headers(token))

                if response.status_code == 200:
                    data = response.json()

                    registration = data.get("registration", {})
                    status = registration.get("status", "UNREGISTERED")
                    is_licensed = status in ["AUTHORIZED", "AUTHORIZED_EXPIRED"]

                    features = data.get("features", {})
                    nodes = features.get("nodes", {})

                    return CmlLicenseInfo(is_licensed=is_licensed, license_type=registration.get("license_type"), expiration_date=registration.get("expires"), max_nodes=nodes.get("limit", 5), features=list(features.keys()) if features else [])
                else:
                    raise CmlApiError(f"Failed to get license status: {response.status_code}")

        except httpx.RequestError as e:
            raise CmlApiError(f"Network error getting license status: {str(e)}") from e

    async def set_license(self, base_url: str, token: str, license_token: str) -> bool:
        """
        Apply a license to the CML worker.

        CML API: PUT /api/v0/licensing/product_license
        """
        url = f"{base_url}/licensing/product_license"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.put(url, json=license_token, headers=self._get_headers(token))

                if response.status_code == 204:
                    log.info("License applied successfully")
                    return True
                elif response.status_code == 400:
                    error_msg = f"Invalid license token: {response.text}"
                    log.error(error_msg)
                    raise CmlLicensingError(error_msg)
                else:
                    error_msg = f"Failed to set license: {response.status_code} - {response.text}"
                    log.error(error_msg)
                    raise CmlLicensingError(error_msg)

        except httpx.RequestError as e:
            raise CmlLicensingError(f"Network error setting license: {str(e)}") from e

    async def remove_license(self, base_url: str, token: str) -> bool:
        """
        Remove the license from the CML worker.

        CML API: DELETE /api/v0/licensing/product_license (if available)
        or PATCH /api/v0/licensing/features to set to unlicensed limits
        """
        # Note: The exact API for license removal may vary by CML version
        # This implementation sets features to unlicensed mode
        url = f"{base_url}/licensing/features"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                # Set nodes to unlicensed limit (5)
                response = await client.patch(url, json=[{"feature": "nodes", "count": 5}], headers=self._get_headers(token))

                if response.status_code == 204:
                    log.info("License removed (set to unlicensed mode)")
                    return True
                else:
                    log.error(f"Failed to remove license: {response.status_code}")
                    return False

        except httpx.RequestError as e:
            log.error(f"Network error removing license: {str(e)}")
            return False

    async def list_labs(self, base_url: str, token: str) -> list[CmlLabInstance]:
        """
        List all labs on the CML worker.

        CML API: GET /api/v0/labs
        """
        url = f"{base_url}/labs"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.get(url, headers=self._get_headers(token))

                if response.status_code == 200:
                    labs_data = response.json()
                    return [CmlLabInstance(lab_id=lab.get("id"), lab_title=lab.get("title", ""), state=lab.get("state", "UNKNOWN"), node_count=lab.get("node_count", 0), owner=lab.get("owner", ""), created_at=lab.get("created", "")) for lab in labs_data]
                else:
                    raise CmlApiError(f"Failed to list labs: {response.status_code}")

        except httpx.RequestError as e:
            raise CmlApiError(f"Network error listing labs: {str(e)}") from e

    async def create_lab(self, base_url: str, token: str, lab_title: str, lab_description: str, topology_data: Optional[dict] = None) -> str:
        """
        Create a new lab on the CML worker.

        CML API: POST /api/v0/labs
        """
        url = f"{base_url}/labs"

        lab_data = {
            "title": lab_title,
            "description": lab_description,
        }

        if topology_data:
            lab_data["topology"] = topology_data

        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.post(url, json=lab_data, headers=self._get_headers(token))

                if response.status_code == 200:
                    lab_id = response.json().get("id")
                    log.info(f"Lab created successfully: {lab_id}")
                    return lab_id
                else:
                    error_msg = f"Failed to create lab: {response.status_code} - {response.text}"
                    log.error(error_msg)
                    raise CmlLabCreationError(error_msg)

        except httpx.RequestError as e:
            raise CmlLabCreationError(f"Network error creating lab: {str(e)}") from e

    async def start_lab(self, base_url: str, token: str, lab_id: str) -> bool:
        """
        Start a lab on the CML worker.

        CML API: PUT /api/v0/labs/{lab_id}/start
        """
        url = f"{base_url}/labs/{lab_id}/start"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.put(url, headers=self._get_headers(token))

                if response.status_code == 204:
                    log.info(f"Lab {lab_id} started successfully")
                    return True
                else:
                    log.error(f"Failed to start lab: {response.status_code}")
                    return False

        except httpx.RequestError as e:
            log.error(f"Network error starting lab: {str(e)}")
            return False

    async def stop_lab(self, base_url: str, token: str, lab_id: str) -> bool:
        """
        Stop a lab on the CML worker.

        CML API: PUT /api/v0/labs/{lab_id}/stop
        """
        url = f"{base_url}/labs/{lab_id}/stop"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.put(url, headers=self._get_headers(token))

                if response.status_code == 204:
                    log.info(f"Lab {lab_id} stopped successfully")
                    return True
                else:
                    log.error(f"Failed to stop lab: {response.status_code}")
                    return False

        except httpx.RequestError as e:
            log.error(f"Network error stopping lab: {str(e)}")
            return False

    async def delete_lab(self, base_url: str, token: str, lab_id: str) -> bool:
        """
        Delete a lab from the CML worker.

        CML API: DELETE /api/v0/labs/{lab_id}
        """
        url = f"{base_url}/labs/{lab_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.delete(url, headers=self._get_headers(token))

                if response.status_code == 204:
                    log.info(f"Lab {lab_id} deleted successfully")
                    return True
                else:
                    log.error(f"Failed to delete lab: {response.status_code}")
                    return False

        except httpx.RequestError as e:
            log.error(f"Network error deleting lab: {str(e)}")
            return False

    async def get_lab_details(self, base_url: str, token: str, lab_id: str) -> CmlLabInstance:
        """
        Get detailed information about a specific lab.

        CML API: GET /api/v0/labs/{lab_id}
        """
        url = f"{base_url}/labs/{lab_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.get(url, headers=self._get_headers(token))

                if response.status_code == 200:
                    lab = response.json()
                    return CmlLabInstance(lab_id=lab.get("id"), lab_title=lab.get("title", ""), state=lab.get("state", "UNKNOWN"), node_count=len(lab.get("nodes", [])), owner=lab.get("owner", ""), created_at=lab.get("created", ""))
                else:
                    raise CmlApiError(f"Failed to get lab details: {response.status_code}")

        except httpx.RequestError as e:
            raise CmlApiError(f"Network error getting lab details: {str(e)}") from e

    async def health_check(self, base_url: str, token: str) -> bool:
        """
        Perform a health check on the CML worker.

        Uses the /authok endpoint to verify authentication and system responsiveness.
        CML API: GET /api/v0/authok
        """
        url = f"{base_url}/authok"

        try:
            async with httpx.AsyncClient(timeout=10, verify=False) as client:
                response = await client.get(url, headers=self._get_headers(token))

                return response.status_code == 200

        except Exception:
            return False
