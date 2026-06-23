#!/usr/bin/env python3
"""
PyNeuroctl - Command Line Interface for Neuroglia Python Framework

This CLI tool helps manage and interact with Neuroglia sample applications,
providing easy commands to start, stop, and monitor different samples.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


class PyNeuroctl:
    """Main CLI controller for Neuroglia framework samples management"""

    def __init__(self):
        self.project_root = self._find_project_root()
        self.samples_dir = self.project_root / "samples"
        self.runtime_dir = self.project_root / ".runtime"
        self.runtime_dir.mkdir(exist_ok=True)
        self.pid_file = self.runtime_dir / "sample_pids.json"
        self.log_dir = self.runtime_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)

        # Sample application configurations
        self.samples = {
            "mario-pizzeria": {
                "name": "Mario's Pizzeria",
                "description": "Pizza ordering and kitchen management system",
                "directory": "mario-pizzeria",
                "main_file": "main.py",
                "port": 8000,
                "features": ["CQRS", "Domain Events", "File Storage", "RESTful API"],
            },
            "openbank": {
                "name": "OpenBank",
                "description": "Banking system with event sourcing",
                "directory": "openbank",
                "main_file": "main.py",
                "port": 8001,
                "features": ["Event Sourcing", "CQRS", "MongoDB", "Banking Domain"],
            },
            "api-gateway": {
                "name": "API Gateway",
                "description": "Microservice API gateway with routing",
                "directory": "api-gateway",
                "main_file": "main.py",
                "port": 8002,
                "features": ["API Gateway", "Service Discovery", "Load Balancing"],
            },
            "desktop-controller": {
                "name": "Desktop Controller",
                "description": "Desktop environment management service",
                "directory": "desktop-controller",
                "main_file": "main.py",
                "port": 8003,
                "features": ["Background Service", "System Integration", "Proctor Lock"],
            },
            "lab-resource-manager": {
                "name": "Lab Resource Manager",
                "description": "Laboratory resource allocation and management",
                "directory": "lab_resource_manager",
                "main_file": "main.py",
                "port": 8004,
                "features": ["Resource Allocation", "Watcher Pattern", "Reconciliation"],
            },
        }

    def _find_project_root(self) -> Path:
        """Find the project root directory"""
        current = Path(__file__).resolve()

        # Look for key files that indicate project root
        for parent in current.parents:
            if (parent / "pyproject.toml").exists() and (parent / "src").exists():
                return parent

        # Fallback to relative path
        return Path(__file__).parent.parent.parent

    def _load_pids(self) -> dict[str, int]:
        """Load running process PIDs from file"""
        if not self.pid_file.exists():
            return {}

        try:
            with open(self.pid_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_pids(self, pids: dict[str, int]) -> None:
        """Save process PIDs to file"""
        try:
            with open(self.pid_file, "w") as f:
                json.dump(pids, f, indent=2)
        except IOError as e:
            print(f"❌ Error saving PID file: {e}")

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is still running"""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _cleanup_stale_pids(self) -> None:
        """Remove PIDs for processes that are no longer running"""
        pids = self._load_pids()
        active_pids = {name: pid for name, pid in pids.items() if self._is_process_running(pid)}

        if len(active_pids) != len(pids):
            self._save_pids(active_pids)

    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return True
            except OSError:
                return False

    def _get_log_file(self, sample_name: str) -> Path:
        """Get the log file path for a sample"""
        return self.log_dir / f"{sample_name}.log"

    def list_samples(self) -> None:
        """List all available sample applications"""
        print("🐍 Neuroglia Python Framework - Sample Applications")
        print("=" * 60)

        if not self.samples:
            print("❌ No sample applications configured")
            return

        for key, config in self.samples.items():
            status = self._get_sample_status(key)
            status_icon = "🟢" if status["running"] else "⚪"

            print(f"\n{status_icon} {config['name']} ({key})")
            print(f"   📖 {config['description']}")
            print(f"   📁 Directory: samples/{config['directory']}")
            print(f"   🌐 Port: {config['port']}")
            print(f"   ⚙️  Features: {', '.join(config['features'])}")

            if status["running"]:
                print(f"   ▶️  Status: Running (PID: {status['pid']})")
                print(f"   🔗 URL: http://localhost:{config['port']}")
            else:
                print(f"   ⏹️  Status: Stopped")

        print()

    def _get_sample_status(self, sample_name: str) -> dict:
        """Get status information for a sample"""
        pids = self._load_pids()
        pid = pids.get(sample_name)

        if pid and self._is_process_running(pid):
            return {"running": True, "pid": pid, "port": self.samples[sample_name]["port"]}
        else:
            return {"running": False, "pid": None, "port": self.samples[sample_name]["port"]}

    def status(self, sample_name: Optional[str] = None) -> None:
        """Show status of sample applications"""
        self._cleanup_stale_pids()

        if sample_name:
            if sample_name not in self.samples:
                print(f"❌ Unknown sample: {sample_name}")
                return

            self._show_single_status(sample_name)
        else:
            self._show_all_status()

    def _show_single_status(self, sample_name: str) -> None:
        """Show status for a single sample"""
        config = self.samples[sample_name]
        status = self._get_sample_status(sample_name)

        print(f"📊 Status: {config['name']}")
        print("=" * 40)

        if status["running"]:
            print(f"Status: 🟢 Running")
            print(f"PID: {status['pid']}")
            print(f"Port: {status['port']}")
            print(f"URL: http://localhost:{status['port']}")
            print(f"Docs: http://localhost:{status['port']}/docs")
        else:
            print(f"Status: ⚪ Stopped")

    def _show_all_status(self) -> None:
        """Show status for all samples"""
        pids = self._load_pids()
        print("📊 Sample Application Status")
        print("=" * 40)

        if not pids:
            print("⚪ No running samples")
            return

        running_count = 0
        for name, pid in pids.items():
            if self._is_process_running(pid):
                config = self.samples.get(name, {})
                sample_name = config.get("name", name)
                port = config.get("port", "Unknown")
                print(f"🟢 {sample_name}: PID {pid}, Port {port}")
                running_count += 1
            else:
                print(f"💀 {name}: Process {pid} (not running)")

        print(f"\n📈 Total running: {running_count}")

    def start(self, sample_name: str, port: Optional[int] = None, background: bool = True) -> None:
        """Start a sample application"""
        if sample_name not in self.samples:
            print(f"❌ Unknown sample: {sample_name}")
            self._suggest_samples()
            return

        # Check if already running
        status = self._get_sample_status(sample_name)
        if status["running"]:
            print(f"⚠️  {self.samples[sample_name]['name']} is already running (PID: {status['pid']})")
            print(f"🔗 URL: http://localhost:{status['port']}")
            return

        config = self.samples[sample_name]
        sample_dir = self.samples_dir / config["directory"]
        main_file = sample_dir / config["main_file"]

        if not main_file.exists():
            print(f"❌ Main file not found: {main_file}")
            return

        # Determine port
        target_port = port or config["port"]

        # Check if port is available
        if not self._is_port_available(target_port):
            print(f"❌ Port {target_port} is already in use")
            print("💡 Try using a different port with --port option")
            return

        # Build command
        cmd = [sys.executable, str(main_file)]
        if port:
            cmd.extend(["--port", str(port)])

        # Get log file for this sample
        log_file = self._get_log_file(sample_name)

        try:
            print(f"🚀 Starting {config['name']}...")
            print(f"📁 Working directory: {sample_dir}")
            print(f"📄 Command: {' '.join(cmd)}")
            print(f"📝 Logs will be written to: {log_file}")

            if background:
                # Start in background with log capture
                with open(log_file, "w") as log_handle:
                    process = subprocess.Popen(
                        cmd,
                        cwd=str(sample_dir),
                        stdout=log_handle,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )

                print(f"📊 Process started with PID: {process.pid}")

                # Wait a moment to check if it started successfully
                time.sleep(3)

                if self._is_process_running(process.pid):
                    # Save PID
                    pids = self._load_pids()
                    pids[sample_name] = process.pid
                    self._save_pids(pids)
                    print(f"✅ {config['name']} started successfully!")
                    print(f"🌐 URL: http://localhost:{target_port}")
                    print(f"📖 API Docs: http://localhost:{target_port}/docs")
                    print(f"📝 View logs: pyneuroctl logs {sample_name}")
                else:
                    print(f"❌ {config['name']} failed to start")
                    print(f"📝 Check logs: pyneuroctl logs {sample_name}")
                    # Show last few lines of log for immediate feedback
                    try:
                        with open(log_file, "r") as f:
                            lines = f.readlines()[-10:]  # Last 10 lines
                            if lines:
                                print("\n📄 Last few log lines:")
                                for line in lines:
                                    print(f"   {line.rstrip()}")
                    except Exception:
                        pass
            else:
                # Start in foreground
                print(f"🌐 URL: http://localhost:{target_port}")
                print("Press Ctrl+C to stop")
                result = subprocess.run(cmd, cwd=str(sample_dir))
                if result.returncode != 0:
                    print(f"❌ {config['name']} exited with code {result.returncode}")

        except KeyboardInterrupt:
            print(f"\n⏹️  {config['name']} stopped by user")
        except Exception as e:
            print(f"❌ Error starting {config['name']}: {e}")
            print(f"💡 Try running in foreground mode: pyneuroctl start {sample_name} --foreground")

    def stop(self, sample_name: Optional[str] = None, all_samples: bool = False) -> None:
        """Stop sample application(s)"""
        if all_samples:
            self._stop_all_samples()
            return

        if not sample_name:
            print("❌ Must specify sample name or use --all")
            return

        if sample_name not in self.samples:
            print(f"❌ Unknown sample: {sample_name}")
            return

        self._stop_single_sample(sample_name)

    def _stop_single_sample(self, sample_name: str) -> None:
        """Stop a single sample application"""
        config = self.samples[sample_name]
        pids = self._load_pids()

        if sample_name not in pids:
            print(f"⚪ {config['name']} is not running")
            return

        pid = pids[sample_name]

        if not self._is_process_running(pid):
            print(f"💀 {config['name']} process {pid} is not running")
            # Clean up PID
            del pids[sample_name]
            self._save_pids(pids)
            return

        try:
            print(f"⏹️  Stopping {config['name']} (PID: {pid})...")
            os.kill(pid, signal.SIGTERM)

            # Wait for graceful shutdown
            for i in range(5):
                if not self._is_process_running(pid):
                    break
                time.sleep(1)

            if self._is_process_running(pid):
                print("⚠️  Graceful shutdown failed, forcing...")
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)

            if not self._is_process_running(pid):
                print(f"✅ {config['name']} stopped successfully")
            else:
                print(f"❌ Failed to stop {config['name']}")
                return

            # Remove from PIDs
            del pids[sample_name]
            self._save_pids(pids)

        except Exception as e:
            print(f"❌ Error stopping {config['name']}: {e}")

    def _stop_all_samples(self) -> None:
        """Stop all running sample applications"""
        pids = self._load_pids()

        if not pids:
            print("⚪ No running samples to stop")
            return

        print("⏹️  Stopping all sample applications...")

        stopped_count = 0
        for sample_name in list(pids.keys()):
            self._stop_single_sample(sample_name)
            stopped_count += 1

        print(f"✅ Stopped {stopped_count} sample(s)")

    def _suggest_samples(self) -> None:
        """Show available samples when user enters invalid name"""
        print("\n💡 Available samples:")
        for key, config in self.samples.items():
            print(f"   • {key}: {config['name']}")

    def logs(self, sample_name: str, lines: int = 50, follow: bool = False) -> None:
        """Show logs for a sample application"""
        if sample_name not in self.samples:
            print(f"❌ Unknown sample: {sample_name}")
            return

        log_file = self._get_log_file(sample_name)

        if not log_file.exists():
            print(f"❌ No log file found for {self.samples[sample_name]['name']}")
            print(f"💡 Expected log file: {log_file}")
            return

        try:
            print(f"📝 Logs for {self.samples[sample_name]['name']}")
            print("=" * 60)

            if follow:
                # Follow mode - similar to 'tail -f'
                print("Following logs (Ctrl+C to stop)...")
                try:
                    subprocess.run(["tail", "-f", str(log_file)])
                except KeyboardInterrupt:
                    print("\n⏹️  Stopped following logs")
                except FileNotFoundError:
                    # Fallback if tail command not available
                    self._show_log_lines(log_file, lines)
            else:
                # Show last N lines
                self._show_log_lines(log_file, lines)

        except Exception as e:
            print(f"❌ Error reading logs: {e}")

    def _show_log_lines(self, log_file: Path, lines: int) -> None:
        """Show the last N lines of a log file"""
        try:
            with open(log_file, "r") as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

                if not last_lines:
                    print("📄 Log file is empty")
                    return

                for line in last_lines:
                    print(line.rstrip())

                print(f"\n📊 Showing last {len(last_lines)} lines of {len(all_lines)} total")
        except Exception as e:
            print(f"❌ Error reading log file: {e}")

    def validate(self) -> None:
        """Validate that all sample applications are properly configured"""
        print("🔍 Validating sample applications...")
        print("=" * 50)

        issues_found = 0
        for key, config in self.samples.items():
            print(f"\n📦 Validating {config['name']} ({key})")

            sample_dir = self.samples_dir / config["directory"]
            main_file = sample_dir / config["main_file"]

            # Check if directory exists
            if not sample_dir.exists():
                print(f"   ❌ Directory not found: {sample_dir}")
                issues_found += 1
                continue
            else:
                print(f"   ✅ Directory exists: {sample_dir}")

            # Check if main file exists
            if not main_file.exists():
                print(f"   ❌ Main file not found: {main_file}")
                issues_found += 1
            else:
                print(f"   ✅ Main file exists: {main_file}")

            # Check if port is available
            if self._is_port_available(config["port"]):
                print(f"   ✅ Port {config['port']} is available")
            else:
                print(f"   ⚠️  Port {config['port']} is currently in use")

        print("\n📊 Validation Summary:")
        if issues_found == 0:
            print("✅ All sample applications are properly configured!")
        else:
            print(f"❌ Found {issues_found} configuration issue(s)")
            print("💡 Fix the issues above before running samples")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="PyNeuroctl - Neuroglia Python Framework CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pyneuroctl list                    # List all samples
  pyneuroctl validate                # Validate sample configurations
  pyneuroctl start mario-pizzeria    # Start Mario's Pizzeria
  pyneuroctl status                  # Show status of all samples
  pyneuroctl logs mario-pizzeria     # View logs for Mario's Pizzeria
  pyneuroctl logs mario-pizzeria -f  # Follow logs in real-time
  pyneuroctl stop mario-pizzeria     # Stop Mario's Pizzeria
  pyneuroctl stop --all             # Stop all running samples
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    subparsers.add_parser("list", help="List available sample applications")

    # Validate command
    subparsers.add_parser("validate", help="Validate sample application configurations")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show sample application status")
    status_parser.add_argument("sample", nargs="?", help="Specific sample to check")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start a sample application")
    start_parser.add_argument("sample", help="Sample application to start")
    start_parser.add_argument("--port", "-p", type=int, help="Custom port number")
    start_parser.add_argument("--foreground", "-f", action="store_true", help="Run in foreground (default: background)")

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop sample application(s)")
    stop_parser.add_argument("sample", nargs="?", help="Sample application to stop")
    stop_parser.add_argument("--all", "-a", action="store_true", help="Stop all running samples")

    # Logs command (for future implementation)
    logs_parser = subparsers.add_parser("logs", help="Show sample application logs")
    logs_parser.add_argument("sample", help="Sample application name")
    logs_parser.add_argument("--lines", "-n", type=int, default=50, help="Number of lines to show")
    logs_parser.add_argument("--follow", "-f", action="store_true", help="Follow logs (like tail -f)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = PyNeuroctl()

    try:
        if args.command == "list":
            cli.list_samples()
        elif args.command == "validate":
            cli.validate()
        elif args.command == "status":
            cli.status(getattr(args, "sample", None))
        elif args.command == "start":
            cli.start(args.sample, args.port, not args.foreground)
        elif args.command == "stop":
            cli.stop(getattr(args, "sample", None), args.all)
        elif args.command == "logs":
            cli.logs(args.sample, args.lines, getattr(args, "follow", False))
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
