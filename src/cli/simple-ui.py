#!/usr/bin/env python3
"""
Simple UI Docker Compose Management Script

This script provides a portable, cross-platform way to manage the Simple UI
sample application and its dependencies using Docker Compose.

Usage:
    python simple-ui.py [command]

Commands:
    start      - Start Simple UI with shared infrastructure
    stop       - Stop Simple UI (keeps infrastructure running)
    restart    - Restart Simple UI
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
    """Manages Docker Compose operations for Simple UI."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.compose_dir = project_root / "deployment" / "docker-compose"
        self.shared_compose = self.compose_dir / "docker-compose.shared.yml"
        self.simple_ui_compose = self.compose_dir / "docker-compose.simple-ui.yml"
        self.env_file = project_root / ".env"

    def _run_command(self, command: list[str], check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess:
        """Run a shell command."""
        try:
            result = subprocess.run(command, cwd=self.project_root, check=check, capture_output=capture_output, text=True)
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {' '.join(command)}")
            print(f"Error: {e.stderr if capture_output else e}")
            sys.exit(1)

    def _docker_compose(self, args: list[str], use_shared: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess:
        """Run docker-compose with the appropriate compose files."""
        cmd = ["docker-compose"]

        # Add env file
        if self.env_file.exists():
            cmd.extend(["--env-file", str(self.env_file)])

        # Add compose files
        if use_shared:
            cmd.extend(["-f", str(self.shared_compose)])
        cmd.extend(["-f", str(self.simple_ui_compose)])

        # Add the actual command
        cmd.extend(args)

        return self._run_command(cmd, capture_output=capture_output)

    def start(self):
        """Start Simple UI with shared infrastructure."""
        print("📱 Starting Simple UI...")
        self._docker_compose(["up", "-d"])
        print("✅ Simple UI started!")
        print()
        print("📊 Access Points:")
        print("   📱 Application: http://localhost:8082")
        print("   📊 Grafana: http://localhost:3001")
        print("   🗄️  MongoDB Express: http://localhost:8081")
        print("   🔐 Keycloak: http://localhost:8090")
        print()
        print("👤 Demo Users:")
        print("   admin / admin123 (can see all tasks, can create)")
        print("   manager / manager123 (can see non-admin tasks)")
        print("   john.doe / user123 (can see own tasks)")
        print("   jane.smith / user123 (can see own tasks)")

    def stop(self):
        """Stop Simple UI and all running services."""
        print("⏹️  Stopping Simple UI...")
        # Note: use_shared=True is required to resolve network references
        self._docker_compose(["down"], use_shared=True)
        print("✅ Simple UI stopped!")

    def restart(self):
        """Restart Simple UI."""
        print("🔄 Restarting Simple UI...")
        self._docker_compose(["restart", "simple-ui-app"], use_shared=False)
        print("✅ Simple UI restarted!")

    def status(self):
        """Check status of services."""
        print("📊 Simple UI Status:")
        self._docker_compose(["ps"])

    def logs(self, follow: bool = True):
        """View application logs."""
        print("📝 Simple UI Logs:")
        args = ["logs"]
        if follow:
            args.append("-f")
        args.append("simple-ui-app")
        self._docker_compose(args, use_shared=False, capture_output=False)

    def clean(self):
        """Stop and remove volumes."""
        print("🧹 Cleaning Simple UI...")
        # Note: use_shared=True is required to resolve network references
        # The 'down -v' command only removes services/volumes defined in simple-ui.yml
        self._docker_compose(["down", "-v"], use_shared=True)
        print("✅ Simple UI cleaned!")

    def build(self):
        """Rebuild Docker images."""
        print("🔨 Building Simple UI...")
        self._docker_compose(["build"], use_shared=False)
        print("✅ Simple UI built!")

    def reset(self):
        """Complete reset (clean + start)."""
        print("🔄 Resetting Simple UI...")
        self.clean()
        print()
        self.start()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage Simple UI sample application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python simple-ui.py start      # Start the application
    python simple-ui.py logs       # View logs
    python simple-ui.py stop       # Stop the application
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
