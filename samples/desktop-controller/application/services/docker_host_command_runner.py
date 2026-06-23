import logging
from typing import Any

from integration.services.secured_docker_host import HostCommand, SecuredDockerHost

log = logging.getLogger(__name__)


class DockerHostCommandRunner:
    def __init__(self, secured_docker_host: SecuredDockerHost):
        self.secured_docker_host = secured_docker_host

    secured_docker_host: SecuredDockerHost

    async def run(self, command: HostCommand) -> dict[str, Any]:
        log.debug(f"Running '{command.line}' on Docker Host...")
        data = {}
        await self.secured_docker_host.connect()
        stdout, stderr = await self.secured_docker_host.execute_command(command)
        await self.secured_docker_host.close()
        log.debug(f"stdout: {stdout}")
        log.debug(f"stderr: {stderr}")
        stdout_lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        # TODO: create output type
        data = {"command_line": command.line, "stdout": stdout_lines, "stderr": stderr.splitlines() if stderr else []}
        return data
