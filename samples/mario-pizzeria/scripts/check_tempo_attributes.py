#!/usr/bin/env python3
"""
Check what span attributes are available in Tempo traces.

This script helps debug dashboard queries by showing what attributes
are actually present in traces.
"""

import requests
import json
import sys

TEMPO_URL = "http://localhost:3200"


def query_tempo_traces(query: str, limit: int = 5):
    """Query Tempo for traces using TraceQL."""
    try:
        response = requests.get(f"{TEMPO_URL}/api/search", params={"q": query, "limit": limit}, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error querying Tempo: {e}")
        return None


def get_trace_details(trace_id: str):
    """Get detailed information about a specific trace."""
    try:
        response = requests.get(f"{TEMPO_URL}/api/traces/{trace_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting trace details: {e}")
        return None


def main():
    print("🔍 Tempo Trace Attribute Checker")
    print("=" * 80)
    print()

    # Check if Tempo is reachable
    try:
        response = requests.get(f"{TEMPO_URL}/api/search?q={{service.name=%22mario-pizzeria%22}}&limit=1", timeout=2)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: Cannot reach Tempo at {TEMPO_URL}")
        print(f"   {e}")
        sys.exit(1)

    # Query for recent traces
    print("📊 Searching for recent Mario's Pizzeria traces...")
    result = query_tempo_traces('{service.name="mario-pizzeria"}', limit=5)

    if not result or not result.get("traces"):
        print("⚠️  No traces found!")
        print("\nTips:")
        print("  - Generate some test data: python3 scripts/generate_test_data.py")
        print("  - Wait a few seconds for traces to propagate")
        sys.exit(0)

    traces = result.get("traces", [])
    print(f"Found {len(traces)} recent traces")
    print()

    # Examine first trace in detail
    first_trace = traces[0]
    trace_id = first_trace.get("traceID")

    print(f"🔬 Examining trace: {trace_id}")
    print("=" * 80)

    trace_data = get_trace_details(trace_id)
    if not trace_data:
        print("❌ Could not get trace details")
        sys.exit(1)

    # Extract spans from the trace
    batches = trace_data.get("batches", [])
    if not batches:
        print("⚠️  No span batches in trace")
        sys.exit(0)

    all_attributes = set()
    operation_types = set()
    cqrs_operations = set()
    repo_operations = set()

    print("\n📋 Spans in trace:")
    print("-" * 80)

    for batch in batches:
        spans = batch.get("scopeSpans", [])
        for scope_span in spans:
            for span in scope_span.get("spans", []):
                span_name = span.get("name", "Unknown")
                attributes = span.get("attributes", [])

                print(f"\nSpan: {span_name}")
                print("  Attributes:")

                for attr in attributes:
                    key = attr.get("key")
                    value = attr.get("value", {})

                    # Get the actual value based on type
                    if "stringValue" in value:
                        val = value["stringValue"]
                    elif "intValue" in value:
                        val = value["intValue"]
                    elif "boolValue" in value:
                        val = value["boolValue"]
                    else:
                        val = str(value)

                    all_attributes.add(key)
                    print(f"    {key}: {val}")

                    # Track specific attributes
                    if key == "span.operation.type":
                        operation_types.add(val)
                    elif key == "cqrs.operation":
                        cqrs_operations.add(val)
                    elif key == "repository.operation":
                        repo_operations.add(val)

    # Summary
    print("\n" + "=" * 80)
    print("📊 Summary:")
    print("-" * 80)
    print(f"Total unique attributes: {len(all_attributes)}")
    print()

    print("🔍 Dashboard Query Attributes:")
    print(f"  span.operation.type values: {operation_types if operation_types else '❌ NOT FOUND'}")
    print(f"  cqrs.operation values: {cqrs_operations if cqrs_operations else '❌ NOT FOUND'}")
    print(f"  repository.operation values: {repo_operations if repo_operations else '❌ NOT FOUND'}")
    print()

    print("💡 Diagnosis:")
    if operation_types:
        print("  ✅ span.operation.type is set - dashboard should work!")
    else:
        print("  ❌ span.operation.type is NOT set - this is why the dashboard is empty!")
        if cqrs_operations:
            print("     Found 'cqrs.operation' instead - need to add 'span.operation.type'")
        if repo_operations:
            print("     Found 'repository.operation' instead - need to add 'span.operation.type'")
    print()

    print("All attributes found:")
    for attr in sorted(all_attributes):
        print(f"  - {attr}")
    print()


if __name__ == "__main__":
    main()
