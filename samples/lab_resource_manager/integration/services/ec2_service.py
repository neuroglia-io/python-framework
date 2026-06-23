"""AWS EC2 Provisioning Service.

This service handles the provisioning and management of EC2 instances
for CML LabWorker resources using boto3.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from domain.resources.lab_worker import AwsEc2Config

log = logging.getLogger(__name__)


@dataclass
class Ec2InstanceInfo:
    """Information about a provisioned EC2 instance."""

    instance_id: str
    public_ip: Optional[str]
    private_ip: str
    state: str  # "pending", "running", "stopping", "stopped", "terminated"
    availability_zone: str
    launch_time: str


class Ec2ProvisioningError(Exception):
    """Exception raised when EC2 provisioning fails."""


class Ec2ProvisioningService:
    """Service for provisioning and managing EC2 instances for CML workers."""

    def __init__(self, aws_access_key_id: Optional[str] = None, aws_secret_access_key: Optional[str] = None, region_name: str = "us-west-2"):
        """
        Initialize EC2 provisioning service.

        Args:
            aws_access_key_id: AWS access key (if None, uses default credentials)
            aws_secret_access_key: AWS secret key (if None, uses default credentials)
            region_name: AWS region name
        """
        self.region_name = region_name

        # Initialize boto3 EC2 client
        session_kwargs = {"region_name": region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.ec2_client = boto3.client("ec2", **session_kwargs)
        self.ec2_resource = boto3.resource("ec2", **session_kwargs)

        log.info(f"EC2ProvisioningService initialized for region {region_name}")

    async def provision_instance(self, config: AwsEc2Config, worker_name: str, worker_namespace: str) -> Ec2InstanceInfo:
        """
        Provision a new EC2 instance for a CML worker.

        Args:
            config: AWS EC2 configuration
            worker_name: Name of the LabWorker resource
            worker_namespace: Namespace of the LabWorker resource

        Returns:
            Ec2InstanceInfo with instance details

        Raises:
            Ec2ProvisioningError: If provisioning fails
        """
        log.info(f"Provisioning EC2 instance for worker {worker_namespace}/{worker_name}")

        try:
            # Prepare block device mappings for EBS volume
            block_device_mappings = [
                {
                    "DeviceName": "/dev/sda1",
                    "Ebs": {
                        "VolumeSize": config.ebs_volume_size_gb,
                        "VolumeType": config.ebs_volume_type,
                        "DeleteOnTermination": True,
                    },
                }
            ]

            # Add IOPS if using io1/io2 volume type
            if config.ebs_volume_type in ["io1", "io2"]:
                block_device_mappings[0]["Ebs"]["Iops"] = config.ebs_iops

            # Prepare tags
            tags = {"Name": f"cml-worker-{worker_name}", "LabWorkerName": worker_name, "LabWorkerNamespace": worker_namespace, "ManagedBy": "neuroglia-lab-manager", **config.tags}

            tag_specifications = [{"ResourceType": "instance", "Tags": [{"Key": k, "Value": v} for k, v in tags.items()]}]

            # Prepare network interfaces configuration
            network_interfaces = []
            if config.subnet_id:
                network_interface = {
                    "DeviceIndex": 0,
                    "SubnetId": config.subnet_id,
                    "AssociatePublicIpAddress": config.assign_public_ip,
                }
                if config.security_group_ids:
                    network_interface["Groups"] = config.security_group_ids
                network_interfaces.append(network_interface)

            # Prepare launch parameters
            launch_params = {
                "ImageId": config.ami_id,
                "InstanceType": config.instance_type,
                "MinCount": 1,
                "MaxCount": 1,
                "BlockDeviceMappings": block_device_mappings,
                "TagSpecifications": tag_specifications,
            }

            # Add key pair if specified
            if config.key_name:
                launch_params["KeyName"] = config.key_name

            # Add IAM instance profile if specified
            if config.iam_instance_profile:
                launch_params["IamInstanceProfile"] = {"Arn": config.iam_instance_profile}

            # Add network configuration
            if network_interfaces:
                launch_params["NetworkInterfaces"] = network_interfaces
            elif config.security_group_ids:
                launch_params["SecurityGroupIds"] = config.security_group_ids

            # Launch instance (synchronous boto3 call in executor)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.ec2_client.run_instances(**launch_params))

            instance_data = response["Instances"][0]
            instance_id = instance_data["InstanceId"]

            log.info(f"EC2 instance {instance_id} launched successfully for worker {worker_name}")

            # Wait for instance to have IP addresses (may take a few seconds)
            await asyncio.sleep(2)

            # Get updated instance information
            instance_info = await self.get_instance_info(instance_id)

            return instance_info

        except ClientError as e:
            error_msg = f"AWS ClientError provisioning instance: {e.response['Error']['Message']}"
            log.error(error_msg)
            raise Ec2ProvisioningError(error_msg) from e
        except BotoCoreError as e:
            error_msg = f"AWS BotoCoreError provisioning instance: {str(e)}"
            log.error(error_msg)
            raise Ec2ProvisioningError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error provisioning instance: {str(e)}"
            log.error(error_msg)
            raise Ec2ProvisioningError(error_msg) from e

    async def get_instance_info(self, instance_id: str) -> Ec2InstanceInfo:
        """
        Get information about an EC2 instance.

        Args:
            instance_id: EC2 instance ID

        Returns:
            Ec2InstanceInfo with current instance details

        Raises:
            Ec2ProvisioningError: If instance not found or error occurs
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.ec2_client.describe_instances(InstanceIds=[instance_id]))

            if not response["Reservations"]:
                raise Ec2ProvisioningError(f"Instance {instance_id} not found")

            instance_data = response["Reservations"][0]["Instances"][0]

            return Ec2InstanceInfo(instance_id=instance_data["InstanceId"], public_ip=instance_data.get("PublicIpAddress"), private_ip=instance_data.get("PrivateIpAddress", ""), state=instance_data["State"]["Name"], availability_zone=instance_data["Placement"]["AvailabilityZone"], launch_time=instance_data["LaunchTime"].isoformat())

        except ClientError as e:
            error_msg = f"Error getting instance info: {e.response['Error']['Message']}"
            log.error(error_msg)
            raise Ec2ProvisioningError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error getting instance info: {str(e)}"
            log.error(error_msg)
            raise Ec2ProvisioningError(error_msg) from e

    async def wait_for_instance_running(self, instance_id: str, timeout_seconds: int = 600, poll_interval: int = 10) -> Ec2InstanceInfo:
        """
        Wait for an EC2 instance to reach 'running' state.

        Args:
            instance_id: EC2 instance ID
            timeout_seconds: Maximum time to wait (default 600 seconds / 10 minutes)
            poll_interval: Time between polls (default 10 seconds)

        Returns:
            Ec2InstanceInfo when instance is running

        Raises:
            Ec2ProvisioningError: If timeout or instance fails to start
        """
        log.info(f"Waiting for instance {instance_id} to reach 'running' state...")

        elapsed = 0
        while elapsed < timeout_seconds:
            instance_info = await self.get_instance_info(instance_id)

            if instance_info.state == "running":
                log.info(f"Instance {instance_id} is now running")
                return instance_info

            if instance_info.state in ["terminated", "stopped"]:
                raise Ec2ProvisioningError(f"Instance {instance_id} entered unexpected state: {instance_info.state}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise Ec2ProvisioningError(f"Timeout waiting for instance {instance_id} to start (waited {timeout_seconds}s)")

    async def stop_instance(self, instance_id: str) -> bool:
        """
        Stop an EC2 instance.

        Args:
            instance_id: EC2 instance ID

        Returns:
            True if stop was initiated successfully

        Raises:
            Ec2ProvisioningError: If stop operation fails
        """
        log.info(f"Stopping EC2 instance {instance_id}")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.ec2_client.stop_instances(InstanceIds=[instance_id]))
            log.info(f"Stop initiated for instance {instance_id}")
            return True

        except ClientError as e:
            error_msg = f"Error stopping instance: {e.response['Error']['Message']}"
            log.error(error_msg)
            raise Ec2ProvisioningError(error_msg) from e

    async def terminate_instance(self, instance_id: str) -> bool:
        """
        Terminate an EC2 instance.

        Args:
            instance_id: EC2 instance ID

        Returns:
            True if termination was initiated successfully

        Raises:
            Ec2ProvisioningError: If termination operation fails
        """
        log.info(f"Terminating EC2 instance {instance_id}")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.ec2_client.terminate_instances(InstanceIds=[instance_id]))
            log.info(f"Termination initiated for instance {instance_id}")
            return True

        except ClientError as e:
            error_msg = f"Error terminating instance: {e.response['Error']['Message']}"
            log.error(error_msg)
            raise Ec2ProvisioningError(error_msg) from e

    async def wait_for_instance_terminated(self, instance_id: str, timeout_seconds: int = 300, poll_interval: int = 10) -> bool:
        """
        Wait for an EC2 instance to reach 'terminated' state.

        Args:
            instance_id: EC2 instance ID
            timeout_seconds: Maximum time to wait (default 300 seconds / 5 minutes)
            poll_interval: Time between polls (default 10 seconds)

        Returns:
            True if instance reached terminated state

        Raises:
            Ec2ProvisioningError: If timeout occurs
        """
        log.info(f"Waiting for instance {instance_id} to terminate...")

        elapsed = 0
        while elapsed < timeout_seconds:
            try:
                instance_info = await self.get_instance_info(instance_id)

                if instance_info.state == "terminated":
                    log.info(f"Instance {instance_id} is now terminated")
                    return True

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            except Ec2ProvisioningError:
                # Instance may not be found after termination
                log.info(f"Instance {instance_id} no longer found (assumed terminated)")
                return True

        raise Ec2ProvisioningError(f"Timeout waiting for instance {instance_id} to terminate (waited {timeout_seconds}s)")

    async def add_tags(self, instance_id: str, tags: dict[str, str]) -> bool:
        """
        Add tags to an EC2 instance.

        Args:
            instance_id: EC2 instance ID
            tags: Dictionary of tags to add

        Returns:
            True if tags were added successfully
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.ec2_client.create_tags(Resources=[instance_id], Tags=[{"Key": k, "Value": v} for k, v in tags.items()]))
            log.info(f"Tags added to instance {instance_id}: {tags}")
            return True

        except ClientError as e:
            log.error(f"Error adding tags: {e.response['Error']['Message']}")
            return False

    async def get_instance_console_output(self, instance_id: str) -> Optional[str]:
        """
        Get console output from an EC2 instance (useful for debugging).

        Args:
            instance_id: EC2 instance ID

        Returns:
            Console output text if available, None otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.ec2_client.get_console_output(InstanceId=instance_id))
            return response.get("Output")

        except ClientError as e:
            log.warning(f"Could not get console output: {e.response['Error']['Message']}")
            return None

    async def list_instances_by_tags(self, tags: dict[str, str]) -> list[Ec2InstanceInfo]:
        """
        List EC2 instances matching specific tags.

        Args:
            tags: Dictionary of tag key-value pairs to filter by

        Returns:
            List of Ec2InstanceInfo for matching instances
        """
        try:
            filters = [{"Name": f"tag:{key}", "Values": [value]} for key, value in tags.items()]
            filters.append({"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]})

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.ec2_client.describe_instances(Filters=filters))

            instances = []
            for reservation in response["Reservations"]:
                for instance_data in reservation["Instances"]:
                    instances.append(Ec2InstanceInfo(instance_id=instance_data["InstanceId"], public_ip=instance_data.get("PublicIpAddress"), private_ip=instance_data.get("PrivateIpAddress", ""), state=instance_data["State"]["Name"], availability_zone=instance_data["Placement"]["AvailabilityZone"], launch_time=instance_data["LaunchTime"].isoformat()))

            return instances

        except ClientError as e:
            log.error(f"Error listing instances: {e.response['Error']['Message']}")
            return []
