#!/usr/bin/env python3
"""Check if span.operation.type attribute exists in recent traces."""

import requests
import json

# Get a recent trace
response = requests.get("http://localhost:3200/api/search?tags=service.name%3Dmario-pizzeria&limit=1")
traces = response.json().get("traces", [])

if not traces:
    print("No traces found!")
    exit(1)

trace_id = traces[0]["traceID"]
print(f"Examining trace: {trace_id}")
print("=" * 80)

# Get trace details
response = requests.get(f"http://localhost:3200/api/traces/{trace_id}")
trace = response.json()

found_span_operation_type = False

for batch in trace.get("batches", []):
    scope_spans = batch.get("scopeSpans", [])
    for scope_span in scope_spans:
        spans = scope_span.get("spans", [])
        for span in spans[:5]:  # Check first 5 spans
            name = span.get("name")
            print(f"\nSpan: {name}")

            attrs = {attr["key"]: attr["value"] for attr in span.get("attributes", [])}

            if "span.operation.type" in attrs:
                val = list(attrs["span.operation.type"].values())[0]
                print(f"  ✅ span.operation.type = {val}")
                found_span_operation_type = True
            else:
                print(f"  ❌ span.operation.type NOT FOUND")

            if "cqrs.operation" in attrs:
                val = list(attrs["cqrs.operation"].values())[0]
                print(f"  ℹ️  cqrs.operation = {val}")

            if "repository.operation" in attrs:
                val = list(attrs["repository.operation"].values())[0]
                print(f"  ℹ️  repository.operation = {val}")

print("\n" + "=" * 80)
if found_span_operation_type:
    print("✅ span.operation.type IS being set in traces")
else:
    print("❌ span.operation.type is NOT in traces - container may need restart")
