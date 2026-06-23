import asyncio
import logging

import paramiko
from pydantic import BaseModel

logging.getLogger("paramiko").setLevel(logging.WARNING)


class HostCommand(BaseModel):
    line: str = ""


class SshClientSettings(BaseModel):
    username: str
    hostname: str
    port: int = 22
    private_key_filename: str = "/app/id_rsa"


class SecuredHost:
    """Service that Securely provides access to a remote host Shell via SSH. It is simply an async wrapper for a SSH client for which the settings are provided by DI."""

    def __init__(self, ssh_client: paramiko.SSHClient, ssh_client_settings: SshClientSettings):
        self.hostname: str = ssh_client_settings.hostname
        self.port: int = ssh_client_settings.port
        self.username: str = ssh_client_settings.username
        self.private_key_filename: str = ssh_client_settings.private_key_filename
        self.ssh_client: paramiko.SSHClient = ssh_client
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    async def connect(self):
        await asyncio.get_event_loop().run_in_executor(None, lambda: self.ssh_client.connect(hostname=self.hostname, username=self.username, key_filename=self.private_key_filename))

    async def execute_command(self, command: HostCommand):
        async def run_command(command_line: str):
            stdin, stdout, stderr = await asyncio.get_event_loop().run_in_executor(None, self.ssh_client.exec_command, command_line)
            return await asyncio.get_event_loop().run_in_executor(None, stdout.read), await asyncio.get_event_loop().run_in_executor(None, stderr.read)

        stdout, stderr = await run_command(command.line)
        return stdout.decode(), stderr.decode()

    def __del__(self):
        self.ssh_client.close()

    async def close(self):
        await asyncio.get_event_loop().run_in_executor(None, self.ssh_client.close)


class DockerHostSshClientSettings(BaseModel):
    username: str
    hostname: str = "host.docker.internal"
    port: int = 22
    private_key_filename: str = "/app/id_rsa"


class SecuredDockerHost(SecuredHost):
    """Service that Securely provides access to the Docker Host's Shell via SSH. It is simply an async wrapper for a SSH client for which the hostname is set by default to the Docker Host..."""

    def __init__(self, ssh_client: paramiko.SSHClient, ssh_client_settings: DockerHostSshClientSettings):
        super().__init__(ssh_client=ssh_client, ssh_client_settings=ssh_client_settings)


# class SecuredDockerHost:
#     """Service that Securely provides access to the Docker Host's Shell via SSH. It is simply an async wrapper for a SSH client for which the hostname is set by default to the Docker Host... """

#     def __init__(self, ssh_client: paramiko.SSHClient, ssh_client_settings: DockerHostSshClientSettings):
#         self.hostname: str = ssh_client_settings.hostname
#         self.port: int = ssh_client_settings.port
#         self.username: str = ssh_client_settings.username
#         self.private_key_filename: str = ssh_client_settings.private_key_filename
#         self.ssh_client: paramiko.SSHClient = ssh_client
#         self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

#     async def connect(self):
#         await asyncio.get_event_loop().run_in_executor(None, lambda: self.ssh_client.connect(hostname=self.hostname, username=self.username, key_filename=self.private_key_filename))

#     async def execute_command(self, command: HostCommand):
#         async def run_command(command_line: str):
#             stdin, stdout, stderr = await asyncio.get_event_loop().run_in_executor(None, self.ssh_client.exec_command, command_line)
#             return await asyncio.get_event_loop().run_in_executor(None, stdout.read), await asyncio.get_event_loop().run_in_executor(None, stderr.read)

#         stdout, stderr = await run_command(command.line)
#         return stdout.decode(), stderr.decode()

#     def __del__(self):
#         self.ssh_client.close()

#     async def close(self):
#         await asyncio.get_event_loop().run_in_executor(None, self.ssh_client.close)
