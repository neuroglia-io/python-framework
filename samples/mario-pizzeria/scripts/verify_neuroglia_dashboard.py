#!/usr/bin/env python3
"""
Verify Neuroglia Framework Dashboard is showing data.

This script checks if the dashboard queries return data.
"""

import requests
import sys

TEMPO_URL = "http://localhost:3200"


def check_dashboard_queries():
    """Check all Neuroglia Framework dashboard queries."""

    queries = {"Command Traces": "span.operation.type=command", "Query Traces": "span.operation.type=query", "Repository Traces": "span.operation.type=repository"}

    print("🔍 Neuroglia Framework Dashboard Verification")
    print("=" * 80)
    print()

    all_working = True

    for name, query in queries.items():
        try:
            response = requests.get(f"{TEMPO_URL}/api/search", params={"tags": query, "limit": 5}, timeout=5)
            response.raise_for_status()
            data = response.json()

            traces = data.get("traces", [])
            count = len(traces)

            if count > 0:
                print(f"✅ {name}: {count} traces found")
                # Show first 3 trace names
                for trace in traces[:3]:
                    print(f"     - {trace['rootTraceName']}")
            else:
                print(f"⚠️  {name}: No traces found")
                all_working = False

        except Exception as e:
            print(f"❌ {name}: Error - {e}")
            all_working = False

    print()
    print("=" * 80)

    if all_working:
        print("✅ SUCCESS: All dashboard panels should show data!")
        print()
        print("🎯 Next Steps:")
        print("   1. Open Grafana: http://localhost:3001")
        print("   2. Navigate to: Dashboards > Neuroglia Framework - CQRS & Tracing")
        print("   3. Verify all panels show traces")
        print()
        return 0
    else:
        print("⚠️  WARNING: Some dashboard panels may be empty")
        print()
        print("💡 Troubleshooting:")
        print("   - Generate more test data: python3 scripts/generate_test_data.py")
        print("   - Wait 10-30 seconds for traces to propagate to Tempo")
        print("   - Check application logs for errors")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(check_dashboard_queries())
