#!/usr/bin/env python3
"""
OpenBank Docker Compose Management Script

This script provides a portable, cross-platform way to manage OpenBank
sample application and its dependencies using Docker Compose.

Usage:
    python openbank.py [command]

Commands:
    start      - Start OpenBank with shared infrastructure
    stop       - Stop OpenBank (keeps infrastructure running)
    restart    - Restart OpenBank
    status     - Check status of services
    logs       - View application logs
    clean      - Stop and remove volumes
    build      - Rebuild Docker images
    reset      - Complete reset (clean + start)
"""

import argparse
import subprocess
import sys
from pathlib import Path


class DockerComposeManager:
    """Manages Docker Compose operations for OpenBank."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.compose_dir = project_root / "deployment" / "docker-compose"
        self.shared_compose = self.compose_dir / "docker-compose.shared.yml"
        self.openbank_compose = self.compose_dir / "docker-compose.openbank.yml"
        self.env_file = project_root / ".env"

    def _run_command(self, command: list[str], check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess:
        """Run a shell command."""
        try:
            # Run docker-compose commands from the compose directory to ensure correct relative paths
            cwd = self.compose_dir if command[0] == "docker-compose" else self.project_root
            result = subprocess.run(command, cwd=cwd, check=check, capture_output=capture_output, text=True)
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {' '.join(command)}")
            print(f"Error: {e.stderr if capture_output else e}")
            sys.exit(1)

    def _docker_compose(self, args: list[str], use_shared: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess:
        """Run docker-compose with the appropriate compose files."""
        cmd = ["docker-compose"]

        # Add env file (use absolute path since we run from compose_dir)
        if self.env_file.exists():
            cmd.extend(["--env-file", str(self.env_file.absolute())])

        # Add compose files (use absolute paths to be safe)
        if use_shared:
            cmd.extend(["-f", str(self.shared_compose.absolute())])
        cmd.extend(["-f", str(self.openbank_compose.absolute())])

        # Add the actual command
        cmd.extend(args)

        return self._run_command(cmd, capture_output=capture_output)

    def start(self):
        """Start OpenBank with shared infrastructure."""
        print("🏦 Starting OpenBank...")
        self._docker_compose(["up", "-d"])
        print("✅ OpenBank started!")
        print()
        print("📊 Access Points:")
        print("   🏦 Application: http://localhost:8899")
        print("   📖 API Docs: http://localhost:8899/api/docs")
        print("   🎬 Event Player: http://localhost:8085")
        print("   📊 EventStoreDB: http://localhost:2113")
        print("   📊 Grafana: http://localhost:3001")
        print("   🗄️  MongoDB Express: http://localhost:8081")
        print("   🔐 Keycloak: http://localhost:8090")

    def stop(self):
        """Stop OpenBank and all running services."""
        print("⏹️  Stopping OpenBank...")
        # Note: use_shared=True is required to resolve network references
        self._docker_compose(["down"], use_shared=True)
        print("✅ OpenBank stopped!")

    def restart(self):
        """Restart OpenBank."""
        print("🔄 Restarting OpenBank...")
        self._docker_compose(["restart", "openbank-app"], use_shared=False)
        print("✅ OpenBank restarted!")

    def status(self):
        """Check status of services."""
        print("📊 OpenBank Status:")
        self._docker_compose(["ps"])

    def logs(self, follow: bool = True):
        """View application logs."""
        print("📝 OpenBank Logs:")
        args = ["logs"]
        if follow:
            args.append("-f")
        args.append("openbank-app")
        self._docker_compose(args)

    def clean(self):
        """Stop and remove volumes."""
        print("🧹 Cleaning OpenBank (removing volumes)...")
        self._docker_compose(["down", "-v"])
        print("✅ OpenBank cleaned!")

    def build(self):
        """Rebuild Docker images."""
        print("🔨 Building OpenBank Docker images...")
        self._docker_compose(["build", "--no-cache"])
        print("✅ OpenBank images built!")

    def reset(self):
        """Complete reset (clean + start)."""
        print("🔄 Resetting OpenBank...")
        self.clean()
        self.start()


def main():
    """Main entry point."""
    # Detect project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent

    manager = DockerComposeManager(project_root)

    parser = argparse.ArgumentParser(
        description="OpenBank Docker Compose Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "command",
        choices=["start", "stop", "restart", "status", "logs", "clean", "build", "reset"],
        help="Command to execute",
    )
    parser.add_argument(
        "--no-follow",
        action="store_true",
        help="Don't follow logs (only with 'logs' command)",
    )

    args = parser.parse_args()

    # Execute command
    try:
        if args.command == "start":
            manager.start()
        elif args.command == "stop":
            manager.stop()
        elif args.command == "restart":
            manager.restart()
        elif args.command == "status":
            manager.status()
        elif args.command == "logs":
            manager.logs(follow=not args.no_follow)
        elif args.command == "clean":
            manager.clean()
        elif args.command == "build":
            manager.build()
        elif args.command == "reset":
            manager.reset()
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
