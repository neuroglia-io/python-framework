#!/usr/bin/env python3
"""
Migration script to fix order status case in MongoDB.

This script updates all order documents to use lowercase status values
instead of uppercase enum names.

Before: {"status": "READY"}
After:  {"status": "ready"}
"""

import asyncio
import os

from motor.motor_asyncio import AsyncIOMotorClient

# Mapping from uppercase enum names to lowercase values
STATUS_MAPPING = {
    "PENDING": "pending",
    "CONFIRMED": "confirmed",
    "COOKING": "cooking",
    "READY": "ready",
    "DELIVERING": "delivering",
    "DELIVERED": "delivered",
    "CANCELLED": "cancelled",
}


async def fix_order_status_case():
    """Update all order documents to use lowercase status values."""

    # Get MongoDB connection string from environment or use default
    mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017")

    print(f"Connecting to MongoDB at: {mongo_uri}")
    client = AsyncIOMotorClient(mongo_uri)

    try:
        # Connect to the database and collection
        db = client["mario_pizzeria"]
        orders_collection = db["orders"]

        print("Connected to MongoDB")
        print("=" * 60)

        # Count total orders
        total_orders = await orders_collection.count_documents({})
        print(f"Total orders in collection: {total_orders}")

        # Find orders with uppercase status values
        uppercase_statuses = list(STATUS_MAPPING.keys())
        query = {"status": {"$in": uppercase_statuses}}

        orders_to_fix = await orders_collection.count_documents(query)
        print(f"Orders with uppercase status: {orders_to_fix}")

        if orders_to_fix == 0:
            print("✅ No orders need fixing!")
            return

        print("\nFixing order status values...")
        print("-" * 60)

        # Update each status value
        fixed_count = 0
        for uppercase_status, lowercase_status in STATUS_MAPPING.items():
            result = await orders_collection.update_many({"status": uppercase_status}, {"$set": {"status": lowercase_status}})

            if result.modified_count > 0:
                print(f"  {uppercase_status:12} → {lowercase_status:12} : {result.modified_count} orders")
                fixed_count += result.modified_count

        print("-" * 60)
        print(f"\n✅ Successfully fixed {fixed_count} orders!")

        # Verify the fix
        remaining = await orders_collection.count_documents(query)
        if remaining > 0:
            print(f"⚠️  Warning: {remaining} orders still have uppercase status")
        else:
            print("✅ All orders now have lowercase status values")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        client.close()
        print("\nConnection closed")


if __name__ == "__main__":
    print("🍕 Mario's Pizzeria - Order Status Case Fix")
    print("=" * 60)
    asyncio.run(fix_order_status_case())
