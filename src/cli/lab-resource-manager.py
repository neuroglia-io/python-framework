#!/usr/bin/env python3
"""
Lab Resource Manager Docker Compose Management Script

This script provides a portable, cross-platform way to manage the Lab Resource Manager
sample application and its dependencies using Docker Compose.

Usage:
    python lab-resource-manager.py [command]

Commands:
    start      - Start Lab Resource Manager with shared infrastructure
    stop       - Stop Lab Resource Manager (keeps infrastructure running)
    restart    - Restart Lab Resource Manager
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
    """Manages Docker Compose operations for Lab Resource Manager."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.compose_dir = project_root / "deployment" / "docker-compose"
        self.shared_compose = self.compose_dir / "docker-compose.shared.yml"
        self.lab_compose = self.compose_dir / "docker-compose.lab-resource-manager.yml"
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
        cmd.extend(["-f", str(self.lab_compose.absolute())])

        # Add the actual command
        cmd.extend(args)

        return self._run_command(cmd, capture_output=capture_output)

    def start(self):
        """Start Lab Resource Manager with shared infrastructure."""
        print("🧪 Starting Lab Resource Manager...")
        self._docker_compose(["up", "-d"])
        print("✅ Lab Resource Manager started!")
        print()
        print("📊 Access Points:")
        print("   🧪 Application: http://localhost:8003")
        print("   📖 API Docs: http://localhost:8003/docs")
        print("   📖 OpenAPI: http://localhost:8003/api/docs")
        print("   🎬 Event Player: http://localhost:8085")
        print("   📊 Grafana: http://localhost:3001")
        print("   🗄️  MongoDB Express: http://localhost:8081")
        print("   🔐 Keycloak: http://localhost:8090")

    def stop(self):
        """Stop Lab Resource Manager and all running services."""
        print("⏹️  Stopping Lab Resource Manager...")
        self._docker_compose(["down"], use_shared=True)
        print("✅ Lab Resource Manager stopped!")

    def restart(self):
        """Restart Lab Resource Manager."""
        print("🔄 Restarting Lab Resource Manager...")
        self._docker_compose(["restart", "lab-resource-manager-app"], use_shared=True)
        print("✅ Lab Resource Manager restarted!")

    def status(self):
        """Check status of services."""
        print("📊 Lab Resource Manager Status:")
        self._docker_compose(["ps"])

    def logs(self, follow: bool = True):
        """View application logs."""
        print("📝 Lab Resource Manager Logs:")
        args = ["logs"]
        if follow:
            args.append("-f")
        args.append("lab-resource-manager-app")
        self._docker_compose(args, use_shared=True, capture_output=False)

    def clean(self):
        """Stop and remove volumes."""
        print("🧹 Cleaning Lab Resource Manager...")
        self._docker_compose(["down", "-v", "lab-resource-manager-app"], use_shared=True)
        print("✅ Lab Resource Manager cleaned!")

    def build(self):
        """Rebuild Docker images."""
        print("🔨 Building Lab Resource Manager...")
        self._docker_compose(["build"], use_shared=True)
        print("✅ Lab Resource Manager built!")

    def reset(self):
        """Complete reset (clean + start)."""
        print("🔄 Resetting Lab Resource Manager...")
        self.clean()
        print()
        self.start()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage Lab Resource Manager sample application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python lab-resource-manager.py start      # Start the application
    python lab-resource-manager.py logs       # View logs
    python lab-resource-manager.py stop       # Stop the application
        """,
    )

    parser.add_argument("command", choices=["start", "stop", "restart", "status", "logs", "clean", "build", "reset"], help="Command to execute")

    parser.add_argument("--no-follow", action="store_true", help="Don't follow logs (only with 'logs' command)")

    args = parser.parse_args()

    # Get project root (parent of parent of this script, since we're in src/cli/)
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent

    # Create manager
    manager = DockerComposeManager(project_root)

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
        print("\n⚠️  Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
