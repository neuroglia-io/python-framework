#!/usr/bin/env python3
"""
Generate test data for Mario's Pizzeria to populate metrics and dashboards.

This script creates diverse orders with different:
- Pizza sizes (small, medium, large)
- Payment methods (cash, credit_card)
- Pizza types (Margherita, Pepperoni, Hawaiian, Vegetarian)

Usage:
    python scripts/generate_test_data.py [--count COUNT] [--base-url URL]
"""

import argparse
import requests
import time
import sys
from typing import List, Dict, Any
from datetime import datetime

# Default configuration
DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_COUNT = 10

# Test data configurations
PIZZA_TYPES = ["Margherita", "Pepperoni", "Hawaiian", "Vegetarian", "Supreme"]
SIZES = ["small", "medium", "large"]
PAYMENT_METHODS = ["cash", "credit_card"]
TOPPINGS_MAP = {"Margherita": [], "Pepperoni": ["pepperoni"], "Hawaiian": ["ham", "pineapple"], "Vegetarian": ["mushrooms", "peppers", "onions"], "Supreme": ["pepperoni", "sausage", "mushrooms", "peppers", "onions"]}


def create_order(base_url: str, customer_name: str, pizza_type: str, size: str, payment_method: str) -> Dict[str, Any]:
    """Create a single order via the API."""
    order_data = {"customer_name": customer_name, "customer_phone": f"+1555{hash(customer_name) % 10000000:07d}", "customer_address": f"{hash(customer_name) % 999 + 1} Main Street", "pizzas": [{"name": pizza_type, "size": size, "toppings": TOPPINGS_MAP.get(pizza_type, [])}], "payment_method": payment_method}

    try:
        response = requests.post(f"{base_url}/api/orders/", json=order_data, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create order: {e}")
        return None


def cook_order(base_url: str, order_id: str) -> bool:
    """Start cooking an order."""
    try:
        response = requests.put(f"{base_url}/api/orders/{order_id}/cook", timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to cook order {order_id}: {e}")
        return False


def complete_order(base_url: str, order_id: str) -> bool:
    """Mark an order as ready."""
    try:
        response = requests.put(f"{base_url}/api/orders/{order_id}/ready", timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to complete order {order_id}: {e}")
        return False


def generate_test_data(base_url: str, count: int, complete_workflow: bool = True):
    """Generate test orders with variety."""
    print(f"🍕 Mario's Pizzeria - Test Data Generator")
    print(f"=" * 60)
    print(f"Target: {base_url}")
    print(f"Orders to create: {count}")
    print(f"Complete workflow: {complete_workflow}")
    print(f"=" * 60)
    print()

    created_orders = []
    cooked_orders = []
    completed_orders = []

    # Create orders
    for i in range(count):
        pizza_type = PIZZA_TYPES[i % len(PIZZA_TYPES)]
        size = SIZES[i % len(SIZES)]
        payment_method = PAYMENT_METHODS[i % len(PAYMENT_METHODS)]
        customer_name = f"TestCustomer{i+1}"

        print(f"Creating order {i+1}/{count}: {pizza_type} ({size}) - {payment_method}...", end=" ")

        order = create_order(base_url, customer_name, pizza_type, size, payment_method)

        if order:
            order_id = order.get("id")
            created_orders.append(order_id)
            print(f"✅ {order_id[:8]}")

            # Optionally complete the workflow
            if complete_workflow:
                time.sleep(0.5)

                # Cook the order
                if cook_order(base_url, order_id):
                    cooked_orders.append(order_id)
                    print(f"  🍳 Cooking started")

                    time.sleep(0.5)

                    # Complete the order
                    if complete_order(base_url, order_id):
                        completed_orders.append(order_id)
                        print(f"  ✅ Order ready")
        else:
            print("❌ Failed")

        # Small delay between orders
        time.sleep(0.3)

    # Summary
    print()
    print(f"=" * 60)
    print(f"📊 Summary:")
    print(f"  Orders created: {len(created_orders)}/{count}")

    if complete_workflow:
        print(f"  Orders cooked: {len(cooked_orders)}/{len(created_orders)}")
        print(f"  Orders completed: {len(completed_orders)}/{len(cooked_orders)}")

    print(f"=" * 60)
    print()
    print(f"🎯 Next Steps:")
    print(f"  1. Check Grafana dashboards: http://localhost:3001")
    print(f"  2. View Prometheus metrics: http://localhost:9090")
    print(f"  3. Query Tempo traces: http://localhost:3200")
    print()

    return len(created_orders)


def main():
    parser = argparse.ArgumentParser(description="Generate test data for Mario's Pizzeria")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help=f"Number of orders to create (default: {DEFAULT_COUNT})")
    parser.add_argument("--base-url", type=str, default=DEFAULT_BASE_URL, help=f"Base URL of the API (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--no-complete", action="store_true", help="Only create orders without cooking/completing them")

    args = parser.parse_args()

    # Check if API is reachable
    try:
        response = requests.get(f"{args.base_url}/api/orders/", timeout=2)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        print(f"❌ Error: Cannot reach API at {args.base_url}")
        print(f"   Make sure Mario's Pizzeria is running.")
        sys.exit(1)

    # Generate test data
    try:
        count = generate_test_data(args.base_url, args.count, complete_workflow=not args.no_complete)

        if count > 0:
            print(f"✅ Successfully generated {count} orders!")
            sys.exit(0)
        else:
            print(f"❌ Failed to generate any orders")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
