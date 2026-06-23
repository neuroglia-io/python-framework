#!/usr/bin/env python3
"""
Check if dashboard metrics are available in Prometheus.

This script tests the exact queries used in Grafana dashboards to help
troubleshoot why panels might be showing no data.
"""

import requests
import json
from typing import Dict, Any, List
import sys

PROMETHEUS_URL = "http://localhost:9090"

# Dashboard queries to test
DASHBOARD_QUERIES = {
    "Order Rate (5m)": "rate(mario_orders_created_total[5m])",
    "Orders In Progress": "mario_orders_in_progress",
    "Average Order Value (1h)": "sum(rate(mario_orders_value_USD_sum[1h])) / sum(rate(mario_orders_value_USD_count[1h]))",
    "Pizzas by Size (5m)": "sum by (size) (rate(mario_pizzas_by_size_total[5m]))",
    "Cooking Duration p50": "histogram_quantile(0.50, rate(mario_kitchen_cooking_duration_seconds_bucket[5m]))",
    "Cooking Duration p95": "histogram_quantile(0.95, rate(mario_kitchen_cooking_duration_seconds_bucket[5m]))",
    "Total Orders Created": "sum(mario_orders_created_total)",
    "Total Orders Completed": "sum(mario_orders_completed_total)",
    "Total Pizzas Ordered": "sum(mario_pizzas_ordered_total)",
}


def query_prometheus(query: str) -> Dict[str, Any]:
    """Execute a PromQL query."""
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": str(e)}


def format_result(result: Dict[str, Any]) -> str:
    """Format query result for display."""
    if result.get("status") == "error":
        return f"❌ Error: {result.get('error', 'Unknown error')}"

    data = result.get("data", {})
    result_list = data.get("result", [])

    if not result_list:
        return "⚠️  No data (0 series)"

    # For instant queries
    if len(result_list) == 1 and not result_list[0].get("metric"):
        value = result_list[0].get("value", [None, "N/A"])[1]
        return f"✅ Value: {value}"

    # For queries with labels
    output = f"✅ {len(result_list)} series:\n"
    for i, series in enumerate(result_list[:5]):  # Show max 5 series
        metric = series.get("metric", {})
        value = series.get("value", [None, "N/A"])[1]

        # Format metric labels
        labels = ", ".join([f"{k}={v}" for k, v in metric.items() if k not in ["__name__", "job", "instance", "collector", "exported_instance", "exported_job"]])
        if labels:
            output += f"      [{labels}] = {value}\n"
        else:
            output += f"      {value}\n"

    if len(result_list) > 5:
        output += f"      ... and {len(result_list) - 5} more series\n"

    return output.rstrip()


def check_raw_metrics():
    """Check if raw metrics exist (without rate/aggregation)."""
    print("📊 Raw Metrics Check")
    print("=" * 80)

    raw_metrics = [
        "mario_orders_created_total",
        "mario_orders_completed_total",
        "mario_orders_value_USD_sum",
        "mario_orders_value_USD_count",
        "mario_pizzas_by_size_total",
        "mario_pizzas_ordered_total",
        "mario_kitchen_cooking_duration_seconds_count",
    ]

    for metric in raw_metrics:
        result = query_prometheus(metric)
        data = result.get("data", {}).get("result", [])
        status = "✅" if data else "⚠️ "
        print(f"{status} {metric:50} {len(data)} series")

    print()


def check_dashboard_queries():
    """Check all dashboard queries."""
    print("🎯 Dashboard Query Results")
    print("=" * 80)

    for name, query in DASHBOARD_QUERIES.items():
        print(f"\n{name}")
        print(f"  Query: {query}")

        result = query_prometheus(query)
        formatted = format_result(result)

        # Indent the output
        for line in formatted.split("\n"):
            print(f"  {line}")


def check_time_ranges():
    """Check if we have enough data for time-based queries."""
    print("\n⏱️  Time Range Analysis")
    print("=" * 80)

    # Check how old is our oldest data point
    result = query_prometheus("mario_orders_created_total")
    if result.get("status") == "success":
        data = result.get("data", {}).get("result", [])
        if data:
            # Get first series
            series = data[0]
            timestamp = series.get("value", [0, None])[0]

            import time
            from datetime import datetime, timedelta

            age_seconds = time.time() - timestamp
            age_minutes = age_seconds / 60

            print(f"Oldest data point: {age_minutes:.1f} minutes ago")
            print(f"  - Timestamp: {datetime.fromtimestamp(timestamp)}")

            if age_minutes < 5:
                print(f"\n⚠️  WARNING: Data is less than 5 minutes old!")
                print(f"  Rate queries with [5m] window may not have enough data yet.")
                print(f"  Wait a few more minutes and metrics should appear.")


def main():
    print("🔍 Mario's Pizzeria - Dashboard Metrics Checker")
    print("=" * 80)
    print()

    # Check if Prometheus is reachable
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query?query=up", timeout=2)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: Cannot reach Prometheus at {PROMETHEUS_URL}")
        print(f"   {e}")
        sys.exit(1)

    # Run checks
    check_raw_metrics()
    check_time_ranges()
    check_dashboard_queries()

    print("\n" + "=" * 80)
    print("✅ Check complete!")
    print("\nTips:")
    print("  - If raw metrics show 0 series: Generate more test data")
    print("  - If rate() queries show no data: Wait 5+ minutes after generating data")
    print("  - If specific panels empty: Check query syntax in Grafana")
    print()


if __name__ == "__main__":
    main()
