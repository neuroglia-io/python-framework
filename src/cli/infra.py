#!/usr/bin/env python3
"""
Shared Infrastructure Management Script

This script provides a portable, cross-platform way to manage the shared
infrastructure services (MongoDB, Keycloak, Observability stack) used by
all Neuroglia sample applications.

Usage:
    python infra.py [command]

Commands:
    start      - Start all shared infrastructure services
    stop       - Stop all shared infrastructure services
    restart    - Restart all shared infrastructure services
    recreate   - Recreate service(s) with fresh containers (optionally delete volumes)
    status     - Check status of infrastructure services
    logs       - View infrastructure logs (all services or specific)
    clean      - Stop and remove volumes (WARNING: destroys all data)
    build      - Rebuild Docker images (if needed)
    reset      - Complete reset (clean + start)
    ps         - List running infrastructure containers
    health     - Check health status of all services
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


class InfrastructureManager:
    """Manages Docker Compose operations for shared infrastructure."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.compose_dir = project_root / "deployment" / "docker-compose"
        self.shared_compose = self.compose_dir / "docker-compose.shared.yml"
        self.env_file = project_root / ".env"

        # Service definitions with their access points
        self.services = {
            "mongodb": {"port": 27017, "name": "MongoDB", "icon": "🗄️"},
            "mongo-express": {"port": 8081, "name": "MongoDB Express", "icon": "📊"},
            "keycloak": {"port": 8090, "name": "Keycloak", "icon": "🔐"},
            "prometheus": {"port": 9090, "name": "Prometheus", "icon": "📈"},
            "grafana": {"port": 3001, "name": "Grafana", "icon": "📊"},
            "loki": {"port": 3100, "name": "Loki", "icon": "📝"},
            "tempo": {"port": 3200, "name": "Tempo", "icon": "🔍"},
            "otel-collector": {"port": 4317, "name": "OpenTelemetry Collector", "icon": "🔌"},
            "event-player": {"port": 8085, "name": "Event Player", "icon": "🎬"},
        }

    def _run_command(self, command: list[str], check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess:
        """Run a shell command."""
        try:
            # Run docker-compose commands from the compose directory to ensure correct relative paths
            cwd = self.compose_dir if command[0] == "docker-compose" else self.project_root
            result = subprocess.run(command, cwd=cwd, check=check, capture_output=capture_output, text=True)
            return result
        except subprocess.CalledProcessError as e:
            print(f"❌ Command failed: {' '.join(command)}")
            if capture_output and e.stderr:
                print(f"Error: {e.stderr}")
            sys.exit(1)

    def _docker_compose(self, args: list[str], capture_output: bool = False) -> subprocess.CompletedProcess:
        """Run docker-compose with the shared infrastructure compose file."""
        cmd = ["docker-compose"]

        # Add env file (use absolute path since we run from compose_dir)
        if self.env_file.exists():
            cmd.extend(["--env-file", str(self.env_file.absolute())])

        # Add compose file (use absolute path to be safe)
        cmd.extend(["-f", str(self.shared_compose.absolute())])

        # Add the actual command
        cmd.extend(args)

        return self._run_command(cmd, capture_output=capture_output)

    def start(self, remove_orphans: bool = True):
        """Start all shared infrastructure services."""
        print("🚀 Starting shared infrastructure services...")
        args = ["up", "-d"]
        if remove_orphans:
            args.append("--remove-orphans")
        self._docker_compose(args)
        print("✅ Shared infrastructure started!")
        print()
        self._print_access_points()

    def stop(self):
        """Stop all shared infrastructure services."""
        print("⏹️  Stopping shared infrastructure services...")
        self._docker_compose(["down"])
        print("✅ Shared infrastructure stopped!")
        print("   Note: Volumes are preserved. Use 'clean' to remove data.")

    def restart(self, service: Optional[str] = None):
        """Restart all or specific infrastructure service."""
        if service:
            print(f"🔄 Restarting {service}...")
            self._docker_compose(["restart", service])
            print(f"✅ {service} restarted!")
        else:
            print("🔄 Restarting all infrastructure services...")
            self._docker_compose(["restart"])
            print("✅ All services restarted!")

    def recreate(
        self,
        service: Optional[str] = None,
        remove_orphans: bool = True,
        delete_volumes: bool = False,
        confirm: bool = False,
    ):
        """Recreate service(s) with fresh containers.

        This forces Docker to create new containers from the images,
        which is needed when environment variables or configurations change.

        Args:
            service: Specific service to recreate (None = all services)
            remove_orphans: Remove containers for services not in compose file
            delete_volumes: Also delete and recreate volumes (WARNING: data loss!)
            confirm: Skip confirmation prompts
        """
        # Build warning message
        target = service if service else "all infrastructure services"
        warning_parts = [f"recreate {target}"]

        if delete_volumes:
            warning_parts.append("DELETE ALL DATA VOLUMES")

        if not confirm and delete_volumes:
            print(f"⚠️  WARNING: This will {' and '.join(warning_parts).upper()}!")
            print("   All persisted data (MongoDB, Keycloak, Grafana, etc.) will be lost!")
            response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
            if response not in ["yes", "y"]:
                print("❌ Operation cancelled.")
                return

        # Stop the service(s) first
        if service:
            print(f"🛑 Stopping {service}...")
            self._docker_compose(["stop", service])
        else:
            print("🛑 Stopping infrastructure services...")
            self._docker_compose(["stop"])

        # Remove containers and optionally volumes
        if delete_volumes:
            if service:
                print(f"🗑️  Removing {service} containers and volumes...")
                # Stop and remove specific service with volumes
                self._docker_compose(["rm", "-f", "-v", service])
                # Also try to remove named volume if it exists
                volume_name = f"pyneuro_{service}_data"
                try:
                    subprocess.run(
                        ["docker", "volume", "rm", volume_name],
                        capture_output=True,
                        check=False,
                    )
                except:
                    pass  # Volume might not exist
            else:
                print("🗑️  Removing all containers and volumes...")
                self._docker_compose(["down", "-v"])
        else:
            if service:
                print(f"🗑️  Removing {service} container...")
                self._docker_compose(["rm", "-f", service])
            else:
                print("🗑️  Removing containers...")
                self._docker_compose(["down"])

        # Recreate with force-recreate flag
        print(f"🔨 Recreating {target}...")
        args = ["up", "-d", "--force-recreate"]

        if remove_orphans:
            args.append("--remove-orphans")

        if service:
            args.append(service)

        self._docker_compose(args)

        print(f"✅ {target.capitalize()} recreated successfully!")

        if service:
            # Show specific service info
            service_info = self.services.get(service, {})
            if service_info:
                port = service_info.get("port")
                name = service_info.get("name")
                icon = service_info.get("icon", "🔧")
                print(f"   {icon} {name} is now available at: http://localhost:{port}")
        else:
            print()
            self._print_access_points()

    def status(self):
        """Check status of infrastructure services."""
        print("📊 Infrastructure Services Status:")
        self._docker_compose(["ps"])

    def logs(self, service: Optional[str] = None, follow: bool = True, tail: int = 100):
        """View infrastructure logs."""
        if service:
            print(f"📝 {service} Logs:")
        else:
            print("📝 Infrastructure Logs (all services):")

        args = ["logs"]
        if follow:
            args.append("-f")
        args.extend(["--tail", str(tail)])

        if service:
            args.append(service)

        self._docker_compose(args, capture_output=False)

    def clean(self, confirm: bool = False):
        """Stop and remove volumes (destroys all data)."""
        if not confirm:
            print("⚠️  WARNING: This will remove all infrastructure data (MongoDB, Grafana, etc.)")
            response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
            if response not in ["yes", "y"]:
                print("❌ Operation cancelled.")
                return

        print("🧹 Cleaning shared infrastructure...")
        self._docker_compose(["down", "-v"])
        print("✅ Shared infrastructure cleaned!")
        print("   All data has been removed.")

    def build(self):
        """Rebuild Docker images if needed."""
        print("🔨 Building shared infrastructure images...")
        self._docker_compose(["build"])
        print("✅ Images built!")

    def reset(self):
        """Complete reset (clean + start)."""
        print("🔄 Resetting shared infrastructure...")
        self.clean(confirm=True)
        print()
        time.sleep(2)  # Give Docker a moment to clean up
        self.start()

    def ps(self):
        """List running infrastructure containers."""
        print("📦 Infrastructure Containers:")
        self._docker_compose(["ps", "-a"])

    def health(self):
        """Check health status of all services."""
        print("🏥 Infrastructure Health Check:")
        print()

        result = self._docker_compose(["ps", "--format", "json"], capture_output=True)

        if result.returncode == 0:
            # Parse container info
            import json

            try:
                containers = []
                # docker-compose ps --format json outputs one JSON object per line
                for line in result.stdout.strip().split("\n"):
                    if line:
                        containers.append(json.loads(line))

                if not containers:
                    print("⚠️  No infrastructure containers running")
                    return

                # Display health status for each container
                for container in containers:
                    service = container.get("Service", "unknown")
                    state = container.get("State", "unknown")
                    status = container.get("Status", "unknown")

                    # Get icon for service
                    service_info = self.services.get(service, {})
                    icon = service_info.get("icon", "🔧")

                    # Determine status emoji
                    if state == "running":
                        if "healthy" in status.lower():
                            status_icon = "✅"
                        elif "unhealthy" in status.lower():
                            status_icon = "❌"
                        else:
                            status_icon = "🟢"
                    else:
                        status_icon = "🔴"

                    print(f"{status_icon} {icon} {service:20s} - {status}")

            except json.JSONDecodeError:
                # Fallback to simple status
                self.status()
        else:
            print("❌ Failed to get health status")
            self.status()

    def _print_access_points(self):
        """Print access points for all services."""
        print("🌐 Service Access Points:")
        for service, info in self.services.items():
            port = info["port"]
            name = info["name"]
            icon = info["icon"]
            print(f"   {icon} {name:30s} http://localhost:{port}")

        print()
        print("💡 Quick Links:")
        print("   📊 Observability Dashboard:  http://localhost:3001 (Grafana)")
        print("   🔐 Identity Management:       http://localhost:8090 (Keycloak)")
        print("   🗄️  Database Management:       http://localhost:8081 (Mongo Express)")
        print("   🎬 Event Testing:             http://localhost:8085 (Event Player)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage shared infrastructure services for Neuroglia samples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python infra.py start                    # Start all infrastructure
    python infra.py status                   # Check service status
    python infra.py logs mongodb             # View MongoDB logs
    python infra.py logs --tail 50           # View last 50 lines of all logs
    python infra.py restart grafana          # Restart Grafana
    python infra.py recreate keycloak        # Recreate Keycloak (preserves data)
    python infra.py recreate keycloak --delete-volumes  # Recreate Keycloak and delete data
    python infra.py recreate --delete-volumes -y        # Recreate all services (skip confirmation)
    python infra.py health                   # Health check
    python infra.py clean                    # Remove all data (with confirmation)
    python infra.py reset                    # Complete reset

Available Services:
    mongodb, mongo-express, keycloak, prometheus, grafana,
    loki, tempo, otel-collector, event-player
        """,
    )

    parser.add_argument(
        "command",
        choices=["start", "stop", "restart", "recreate", "status", "logs", "clean", "build", "reset", "ps", "health"],
        help="Command to execute",
    )

    parser.add_argument("service", nargs="?", help="Specific service name (for restart, logs)")

    parser.add_argument("--no-follow", action="store_true", help="Don't follow logs (only with 'logs' command)")

    parser.add_argument("--tail", type=int, default=100, help="Number of log lines to show (default: 100)")

    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")

    parser.add_argument(
        "--no-remove-orphans",
        action="store_true",
        help="Don't remove orphan containers on start/recreate",
    )

    parser.add_argument(
        "--delete-volumes",
        action="store_true",
        help="Delete volumes when recreating (WARNING: destroys data!)",
    )

    args = parser.parse_args()

    # Get project root (parent of parent of this script, since we're in src/cli/)
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.parent

    # Create manager
    manager = InfrastructureManager(project_root)

    # Execute command
    try:
        if args.command == "start":
            manager.start(remove_orphans=not args.no_remove_orphans)
        elif args.command == "stop":
            manager.stop()
        elif args.command == "restart":
            manager.restart(service=args.service)
        elif args.command == "recreate":
            manager.recreate(
                service=args.service,
                remove_orphans=not args.no_remove_orphans,
                delete_volumes=args.delete_volumes,
                confirm=args.yes,
            )
        elif args.command == "status":
            manager.status()
        elif args.command == "logs":
            manager.logs(service=args.service, follow=not args.no_follow, tail=args.tail)
        elif args.command == "clean":
            manager.clean(confirm=args.yes)
        elif args.command == "build":
            manager.build()
        elif args.command == "reset":
            manager.reset()
        elif args.command == "ps":
            manager.ps()
        elif args.command == "health":
            manager.health()
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
