#!/usr/bin/env python3
"""
Mario's Pizzeria Docker Compose Management Script

This script provides a portable, cross-platform way to manage Mario's Pizzeria
sample application and its dependencies using Docker Compose.

Usage:
    python mario-pizzeria.py [command]

Commands:
    start      - Start Mario's Pizzeria with shared infrastructure
    stop       - Stop Mario's Pizzeria (keeps infrastructure running)
    restart    - Restart Mario's Pizzeria
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
    """Manages Docker Compose operations for Mario's Pizzeria."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.compose_dir = project_root / "deployment" / "docker-compose"
        self.shared_compose = self.compose_dir / "docker-compose.shared.yml"
        self.mario_compose = self.compose_dir / "docker-compose.mario.yml"
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
        cmd.extend(["-f", str(self.mario_compose.absolute())])

        # Add the actual command
        cmd.extend(args)

        return self._run_command(cmd, capture_output=capture_output)

    def start(self):
        """Start Mario's Pizzeria with shared infrastructure."""
        print("🍕 Starting Mario's Pizzeria...")
        self._docker_compose(["up", "-d"])
        print("✅ Mario's Pizzeria started!")
        print()
        print("📊 Access Points:")
        print("   🍕 Application: http://localhost:8080")
        print("   📖 API Docs: http://localhost:8080/api/docs")
        print("   🎬 Event Player: http://localhost:8085")
        print("   📊 Grafana: http://localhost:3001")
        print("   🗄️  MongoDB Express: http://localhost:8081")
        print("   🔐 Keycloak: http://localhost:8090")

    def stop(self):
        """Stop Mario's Pizzeria and all running services."""
        print("⏹️  Stopping Mario's Pizzeria...")
        # Note: use_shared=True is required to resolve network references
        self._docker_compose(["down"], use_shared=True)
        print("✅ Mario's Pizzeria stopped!")

    def restart(self):
        """Restart Mario's Pizzeria."""
        print("🔄 Restarting Mario's Pizzeria...")
        self._docker_compose(["restart", "mario-pizzeria-app"], use_shared=False)
        print("✅ Mario's Pizzeria restarted!")

    def status(self):
        """Check status of services."""
        print("📊 Mario's Pizzeria Status:")
        self._docker_compose(["ps"])

    def logs(self, follow: bool = True):
        """View application logs."""
        print("📝 Mario's Pizzeria Logs:")
        args = ["logs"]
        if follow:
            args.append("-f")
        args.append("mario-pizzeria-app")
        self._docker_compose(args, use_shared=False, capture_output=False)

    def clean(self):
        """Stop and remove volumes."""
        print("🧹 Cleaning Mario's Pizzeria...")
        # Note: use_shared=True is required to resolve network references
        # The 'down -v' command only removes services/volumes defined in mario.yml
        self._docker_compose(["down", "-v"], use_shared=True)
        print("✅ Mario's Pizzeria cleaned!")

    def build(self):
        """Rebuild Docker images."""
        print("🔨 Building Mario's Pizzeria...")
        self._docker_compose(["build"], use_shared=False)
        print("✅ Mario's Pizzeria built!")

    def reset(self):
        """Complete reset (clean + start)."""
        print("🔄 Resetting Mario's Pizzeria...")
        self.clean()
        print()
        self.start()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage Mario's Pizzeria sample application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python mario-pizzeria.py start      # Start the application
    python mario-pizzeria.py logs       # View logs
    python mario-pizzeria.py stop       # Stop the application
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
