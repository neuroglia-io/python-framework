"""AWS EC2 Cloud Provider Implementation.

This service implements the CloudProviderSPI for AWS EC2,
handling provisioning and management of EC2 instances.
"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

    # Define dummy exceptions for type checking
    class BotoCoreError(Exception):  # type: ignore
        pass

    class ClientError(Exception):  # type: ignore
        pass


from integration.services.providers.cloud_provider_spi import (
    CloudProviderSPI,
    InstanceConfiguration,
    InstanceInfo,
    InstanceNotFoundError,
    InstanceOperationError,
    InstanceProvisioningError,
    InstanceState,
    VolumeType,
)

log = logging.getLogger(__name__)


class AwsEc2CloudProvider(CloudProviderSPI):
    """AWS EC2 implementation of CloudProviderSPI."""

    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-west-2",
    ):
        """
        Initialize AWS EC2 cloud provider.

        Args:
            aws_access_key_id: AWS access key (if None, uses default credentials)
            aws_secret_access_key: AWS secret key (if None, uses default credentials)
            region_name: AWS region name
        """
        if not AWS_AVAILABLE:
            raise ImportError("boto3 is required for AWS EC2 cloud provider. " "Install with: pip install neuroglia-python[aws] or pip install boto3")

        self.region_name = region_name

        # Initialize EC2 client
        if aws_access_key_id and aws_secret_access_key:
            self.ec2_client = boto3.client(
                "ec2",
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name,
            )
        else:
            # Use default credentials from environment/IAM role
            self.ec2_client = boto3.client("ec2", region_name=region_name)

    def get_provider_name(self) -> str:
        """Get the cloud provider name."""
        return "AWS"

    async def provision_instance(self, config: InstanceConfiguration) -> InstanceInfo:
        """
        Provision a new EC2 instance.

        Args:
            config: Instance configuration

        Returns:
            InstanceInfo with details of the provisioned instance

        Raises:
            InstanceProvisioningError: If provisioning fails
        """
        log.info(f"Provisioning EC2 instance: {config.name}")

        # Validate configuration
        validation_errors = config.validate()
        if validation_errors:
            raise InstanceProvisioningError(f"Invalid configuration: {'; '.join(validation_errors)}")

        try:
            # Build block device mappings for volumes
            block_device_mappings = self._build_block_device_mappings(config)

            # Build network interfaces
            network_interfaces = self._build_network_interfaces(config)

            # Prepare tags
            tags = self._build_tags(config)

            # Prepare run_instances parameters
            run_params = {
                "ImageId": config.image_id,
                "InstanceType": config.instance_type,
                "MinCount": 1,
                "MaxCount": 1,
                "BlockDeviceMappings": block_device_mappings,
                "TagSpecifications": [
                    {"ResourceType": "instance", "Tags": tags},
                    {"ResourceType": "volume", "Tags": tags},
                ],
            }

            # Add network interfaces if specified
            if network_interfaces:
                run_params["NetworkInterfaces"] = network_interfaces
            else:
                # Simple networking
                if config.network.security_group_ids:
                    run_params["SecurityGroupIds"] = config.network.security_group_ids
                if config.network.subnet_id:
                    run_params["SubnetId"] = config.network.subnet_id

            # Add IAM instance profile if specified
            if config.iam_instance_profile:
                run_params["IamInstanceProfile"] = {"Name": config.iam_instance_profile}

            # Add key pair if specified
            if config.key_pair_name:
                run_params["KeyName"] = config.key_pair_name

            # Add user data if specified
            if config.user_data:
                run_params["UserData"] = config.user_data

            # Provision the instance
            response = await asyncio.get_event_loop().run_in_executor(None, lambda: self.ec2_client.run_instances(**run_params))

            instance_data = response["Instances"][0]
            instance_id = instance_data["InstanceId"]

            log.info(f"EC2 instance provisioned: {instance_id}")

            # Return instance info
            return self._instance_data_to_info(instance_data)

        except ClientError as e:
            error_msg = f"Failed to provision EC2 instance: {e}"
            log.error(error_msg)
            raise InstanceProvisioningError(error_msg) from e
        except BotoCoreError as e:
            error_msg = f"AWS service error: {e}"
            log.error(error_msg)
            raise InstanceProvisioningError(error_msg) from e

    async def get_instance_info(self, instance_id: str) -> InstanceInfo:
        """
        Get information about an EC2 instance.

        Args:
            instance_id: EC2 instance ID

        Returns:
            InstanceInfo with current instance details

        Raises:
            InstanceNotFoundError: If instance does not exist
        """
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.ec2_client.describe_instances(InstanceIds=[instance_id]),
            )

            if not response["Reservations"]:
                raise InstanceNotFoundError(f"Instance {instance_id} not found")

            instance_data = response["Reservations"][0]["Instances"][0]
            return self._instance_data_to_info(instance_data)

        except ClientError as e:
            if e.response["Error"]["Code"] == "InvalidInstanceID.NotFound":
                raise InstanceNotFoundError(f"Instance {instance_id} not found") from e
            error_msg = f"Failed to get instance info: {e}"
            log.error(error_msg)
            raise InstanceOperationError(error_msg) from e

    async def wait_for_instance_running(self, instance_id: str, timeout_seconds: int = 600) -> InstanceInfo:
        """
        Wait for EC2 instance to reach running state.

        Args:
            instance_id: EC2 instance ID
            timeout_seconds: Maximum time to wait (default: 10 minutes)

        Returns:
            InstanceInfo when instance is running

        Raises:
            InstanceOperationError: If instance fails to start or timeout
        """
        log.info(f"Waiting for EC2 instance {instance_id} to reach running state " f"(timeout: {timeout_seconds}s)")

        start_time = asyncio.get_event_loop().time()

        while True:
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                raise InstanceOperationError(f"Timeout waiting for instance {instance_id} to start")

            # Get current instance state
            instance_info = await self.get_instance_info(instance_id)

            if instance_info.state == InstanceState.RUNNING:
                log.info(f"EC2 instance {instance_id} is now running")
                return instance_info
            elif instance_info.state in [
                InstanceState.TERMINATED,
                InstanceState.TERMINATING,
            ]:
                raise InstanceOperationError(f"Instance {instance_id} terminated before reaching running state")

            # Wait before next check
            await asyncio.sleep(10)

    async def stop_instance(self, instance_id: str) -> None:
        """
        Stop an EC2 instance.

        Args:
            instance_id: EC2 instance ID

        Raises:
            InstanceNotFoundError: If instance does not exist
            InstanceOperationError: If stop operation fails
        """
        log.info(f"Stopping EC2 instance: {instance_id}")

        try:
            await asyncio.get_event_loop().run_in_executor(None, lambda: self.ec2_client.stop_instances(InstanceIds=[instance_id]))
            log.info(f"EC2 instance {instance_id} stop initiated")

        except ClientError as e:
            if e.response["Error"]["Code"] == "InvalidInstanceID.NotFound":
                raise InstanceNotFoundError(f"Instance {instance_id} not found") from e
            error_msg = f"Failed to stop instance: {e}"
            log.error(error_msg)
            raise InstanceOperationError(error_msg) from e

    async def start_instance(self, instance_id: str) -> None:
        """
        Start a stopped EC2 instance.

        Args:
            instance_id: EC2 instance ID

        Raises:
            InstanceNotFoundError: If instance does not exist
            InstanceOperationError: If start operation fails
        """
        log.info(f"Starting EC2 instance: {instance_id}")

        try:
            await asyncio.get_event_loop().run_in_executor(None, lambda: self.ec2_client.start_instances(InstanceIds=[instance_id]))
            log.info(f"EC2 instance {instance_id} start initiated")

        except ClientError as e:
            if e.response["Error"]["Code"] == "InvalidInstanceID.NotFound":
                raise InstanceNotFoundError(f"Instance {instance_id} not found") from e
            error_msg = f"Failed to start instance: {e}"
            log.error(error_msg)
            raise InstanceOperationError(error_msg) from e

    async def terminate_instance(self, instance_id: str) -> None:
        """
        Terminate an EC2 instance (permanent deletion).

        Args:
            instance_id: EC2 instance ID

        Raises:
            InstanceNotFoundError: If instance does not exist
            InstanceOperationError: If termination fails
        """
        log.info(f"Terminating EC2 instance: {instance_id}")

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.ec2_client.terminate_instances(InstanceIds=[instance_id]),
            )
            log.info(f"EC2 instance {instance_id} termination initiated")

        except ClientError as e:
            if e.response["Error"]["Code"] == "InvalidInstanceID.NotFound":
                raise InstanceNotFoundError(f"Instance {instance_id} not found") from e
            error_msg = f"Failed to terminate instance: {e}"
            log.error(error_msg)
            raise InstanceOperationError(error_msg) from e

    async def wait_for_instance_terminated(self, instance_id: str, timeout_seconds: int = 300) -> None:
        """
        Wait for EC2 instance to be fully terminated.

        Args:
            instance_id: EC2 instance ID
            timeout_seconds: Maximum time to wait (default: 5 minutes)

        Raises:
            InstanceOperationError: If timeout occurs
        """
        log.info(f"Waiting for EC2 instance {instance_id} to terminate " f"(timeout: {timeout_seconds}s)")

        start_time = asyncio.get_event_loop().time()

        while True:
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                raise InstanceOperationError(f"Timeout waiting for instance {instance_id} to terminate")

            try:
                instance_info = await self.get_instance_info(instance_id)

                if instance_info.state == InstanceState.TERMINATED:
                    log.info(f"EC2 instance {instance_id} is now terminated")
                    return

            except InstanceNotFoundError:
                # Instance no longer exists, consider it terminated
                log.info(f"EC2 instance {instance_id} not found (terminated)")
                return

            # Wait before next check
            await asyncio.sleep(10)

    async def add_tags(self, instance_id: str, tags: dict[str, str]) -> None:
        """
        Add or update tags on an EC2 instance.

        Args:
            instance_id: EC2 instance ID
            tags: Tags to add or update

        Raises:
            InstanceNotFoundError: If instance does not exist
            InstanceOperationError: If tagging fails
        """
        log.debug(f"Adding tags to EC2 instance {instance_id}: {tags}")

        try:
            tag_list = [{"Key": k, "Value": v} for k, v in tags.items()]

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.ec2_client.create_tags(Resources=[instance_id], Tags=tag_list),
            )

        except ClientError as e:
            if e.response["Error"]["Code"] == "InvalidInstanceID.NotFound":
                raise InstanceNotFoundError(f"Instance {instance_id} not found") from e
            error_msg = f"Failed to add tags: {e}"
            log.error(error_msg)
            raise InstanceOperationError(error_msg) from e

    async def list_instances(self, filters: Optional[dict[str, str]] = None) -> list[InstanceInfo]:
        """
        List EC2 instances with optional tag filtering.

        Args:
            filters: Optional tag filters (key=value pairs)

        Returns:
            List of InstanceInfo objects
        """
        log.debug(f"Listing EC2 instances with filters: {filters}")

        try:
            # Build EC2 filters
            ec2_filters = []
            if filters:
                for key, value in filters.items():
                    ec2_filters.append({"Name": f"tag:{key}", "Values": [value]})

            # Query instances
            if ec2_filters:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.ec2_client.describe_instances(Filters=ec2_filters),
                )
            else:
                response = await asyncio.get_event_loop().run_in_executor(None, lambda: self.ec2_client.describe_instances())

            # Extract instance info
            instances = []
            for reservation in response["Reservations"]:
                for instance_data in reservation["Instances"]:
                    instances.append(self._instance_data_to_info(instance_data))

            return instances

        except ClientError as e:
            error_msg = f"Failed to list instances: {e}"
            log.error(error_msg)
            raise InstanceOperationError(error_msg) from e

    async def get_console_output(self, instance_id: str) -> str:
        """
        Get console output from an EC2 instance (for debugging).

        Args:
            instance_id: EC2 instance ID

        Returns:
            Console output text

        Raises:
            InstanceNotFoundError: If instance does not exist
        """
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.ec2_client.get_console_output(InstanceId=instance_id),
            )

            return response.get("Output", "")

        except ClientError as e:
            if e.response["Error"]["Code"] == "InvalidInstanceID.NotFound":
                raise InstanceNotFoundError(f"Instance {instance_id} not found") from e
            error_msg = f"Failed to get console output: {e}"
            log.error(error_msg)
            raise InstanceOperationError(error_msg) from e

    # Helper methods

    def _build_block_device_mappings(self, config: InstanceConfiguration) -> list[dict]:
        """Build EC2 block device mappings from configuration."""
        mappings = []

        # Root volume
        root_mapping = {
            "DeviceName": "/dev/sda1",
            "Ebs": {
                "VolumeSize": config.root_volume.size_gb,
                "VolumeType": self._map_volume_type(config.root_volume.volume_type),
                "DeleteOnTermination": config.root_volume.delete_on_termination,
                "Encrypted": config.root_volume.encrypted,
            },
        }

        # Add IOPS if specified
        if config.root_volume.iops:
            root_mapping["Ebs"]["Iops"] = config.root_volume.iops

        # Add throughput if specified
        if config.root_volume.throughput_mbps:
            root_mapping["Ebs"]["Throughput"] = config.root_volume.throughput_mbps

        mappings.append(root_mapping)

        # Additional volumes
        device_names = ["/dev/sdb", "/dev/sdc", "/dev/sdd", "/dev/sde"]
        for i, volume in enumerate(config.additional_volumes):
            if i >= len(device_names):
                break

            volume_mapping = {
                "DeviceName": device_names[i],
                "Ebs": {
                    "VolumeSize": volume.size_gb,
                    "VolumeType": self._map_volume_type(volume.volume_type),
                    "DeleteOnTermination": volume.delete_on_termination,
                    "Encrypted": volume.encrypted,
                },
            }

            if volume.iops:
                volume_mapping["Ebs"]["Iops"] = volume.iops
            if volume.throughput_mbps:
                volume_mapping["Ebs"]["Throughput"] = volume.throughput_mbps

            mappings.append(volume_mapping)

        return mappings

    def _map_volume_type(self, volume_type: VolumeType) -> str:
        """Map generic volume type to EC2 volume type."""
        mapping = {
            VolumeType.STANDARD: "standard",
            VolumeType.SSD: "gp3",
            VolumeType.PROVISIONED_IOPS_SSD: "io1",
            VolumeType.THROUGHPUT_OPTIMIZED: "st1",
            VolumeType.COLD_STORAGE: "sc1",
        }
        return mapping.get(volume_type, "gp3")

    def _build_network_interfaces(self, config: InstanceConfiguration) -> Optional[list[dict]]:
        """Build EC2 network interfaces from configuration."""
        if not config.network.subnet_id:
            return None

        interface = {
            "DeviceIndex": 0,
            "SubnetId": config.network.subnet_id,
            "AssociatePublicIpAddress": config.network.assign_public_ip,
        }

        if config.network.security_group_ids:
            interface["Groups"] = config.network.security_group_ids

        if config.network.private_ip:
            interface["PrivateIpAddress"] = config.network.private_ip

        return [interface]

    def _build_tags(self, config: InstanceConfiguration) -> list[dict]:
        """Build EC2 tags from configuration."""
        tags = [
            {"Key": "Name", "Value": config.name},
            {"Key": "Namespace", "Value": config.namespace},
            {"Key": "ManagedBy", "Value": "lab-worker-controller"},
        ]

        # Add custom tags
        for key, value in config.tags.items():
            tags.append({"Key": key, "Value": value})

        return tags

    def _instance_data_to_info(self, instance_data: dict) -> InstanceInfo:
        """Convert EC2 instance data to InstanceInfo."""
        # Map EC2 state to generic state
        ec2_state = instance_data["State"]["Name"]
        state_mapping = {
            "pending": InstanceState.PENDING,
            "running": InstanceState.RUNNING,
            "stopping": InstanceState.STOPPING,
            "stopped": InstanceState.STOPPED,
            "shutting-down": InstanceState.TERMINATING,
            "terminated": InstanceState.TERMINATED,
        }
        state = state_mapping.get(ec2_state, InstanceState.UNKNOWN)

        # Extract name from tags
        name = instance_data["InstanceId"]
        for tag in instance_data.get("Tags", []):
            if tag["Key"] == "Name":
                name = tag["Value"]
                break

        # Parse launch time
        launch_time = None
        if "LaunchTime" in instance_data:
            launch_time = instance_data["LaunchTime"]
            if isinstance(launch_time, str):
                launch_time = datetime.fromisoformat(launch_time.replace("Z", "+00:00"))

        return InstanceInfo(
            instance_id=instance_data["InstanceId"],
            name=name,
            state=state,
            instance_type=instance_data["InstanceType"],
            public_ip=instance_data.get("PublicIpAddress"),
            private_ip=instance_data.get("PrivateIpAddress"),
            public_dns=instance_data.get("PublicDnsName"),
            private_dns=instance_data.get("PrivateDnsName"),
            availability_zone=instance_data["Placement"]["AvailabilityZone"],
            region=self.region_name,
            launch_time=launch_time,
            provider_data={"ec2_state": ec2_state},
        )
