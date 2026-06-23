#!/usr/bin/env python3
"""
Run the Watcher and Reconciliation Loop Demonstration

This script demonstrates how the Resource Watcher and Reconciliation Loop
patterns work together in the Resource Oriented Architecture.

Usage:
    python run_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path so we can import neuroglia
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))  # For neuroglia imports
sys.path.insert(0, str(Path(__file__).parent))  # For local imports from lab_resource_manager

from demo_watcher_reconciliation import main

if __name__ == "__main__":
    print("🚀 Starting Watcher and Reconciliation Loop Demonstration")
    print("=" * 60)
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚡ Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\n👋 Demo finished")
