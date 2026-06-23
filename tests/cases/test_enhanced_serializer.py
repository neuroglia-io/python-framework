#!/usr/bin/env python3
"""
Test script to validate the enhanced JsonSerializer's generic type inference capabilities
"""

import asyncio
import sys
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory

# Add the project root to Python path so we can import neuroglia
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from neuroglia.data.abstractions import Entity
from neuroglia.data.infrastructure.filesystem import FileSystemRepository
from neuroglia.serialization.json import JsonSerializer


class TestStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class TestProduct(Entity):
    """Test entity with various complex types - no type annotations to test inference"""

    def __init__(self, name: str, price: Decimal, status: TestStatus):
        super().__init__()
        self.name = name
        self.price = price
        self.status = status
        self.created_at = datetime.now()
        self.tags = ["test", "product"]
        self.metadata = {"category": "testing", "priority": 1}


async def test_generic_serialization():
    """Test the enhanced JsonSerializer with generic type inference"""
    print("🧪 Testing Enhanced JsonSerializer Generic Type Inference")
    print("=" * 65)

    try:
        # Create a test product with complex types
        original_product = TestProduct(name="Test Product", price=Decimal("99.99"), status=TestStatus.ACTIVE)

        print("📦 Original Product:")
        print(f"   - Name: {original_product.name}")
        print(f"   - Price: {original_product.price} (type: {type(original_product.price)})")
        print(f"   - Status: {original_product.status} (type: {type(original_product.status)})")
        print(f"   - Created: {original_product.created_at} (type: {type(original_product.created_at)})")
        print(f"   - Tags: {original_product.tags}")
        print(f"   - Metadata: {original_product.metadata}")

        # Test direct serialization/deserialization
        serializer = JsonSerializer()

        print("\n🔧 Testing JsonSerializer direct usage...")
        json_text = serializer.serialize_to_text(original_product)
        print(f"✅ Serialized to JSON: {json_text}")

        # Deserialize using the enhanced type inference
        deserialized_product = serializer.deserialize_from_text(json_text, TestProduct)

        print("\n📥 Deserialized Product:")
        print(f"   - Name: {deserialized_product.name}")
        print(f"   - Price: {deserialized_product.price} (type: {type(deserialized_product.price)})")
        print(f"   - Status: {deserialized_product.status} (type: {type(deserialized_product.status)})")
        print(f"   - Created: {deserialized_product.created_at} (type: {type(deserialized_product.created_at)})")
        print(f"   - Tags: {deserialized_product.tags}")
        print(f"   - Metadata: {deserialized_product.metadata}")

        # Test with FileSystemRepository using the generic implementation
        print("\n📁 Testing with Generic FileSystemRepository...")

        with TemporaryDirectory() as temp_dir:
            repo = FileSystemRepository[TestProduct, str](data_directory=temp_dir, entity_type=TestProduct, key_type=str)

            # Add product to repository
            saved_product = await repo.add_async(original_product)
            print(f"✅ Saved product with ID: {saved_product.id}")

            # Retrieve product from repository
            retrieved_product = await repo.get_async(saved_product.id)

            if retrieved_product is None:
                print("❌ Failed to retrieve product from repository")
                return

            print("\n📤 Retrieved Product from FileSystemRepository:")
            print(f"   - Name: {retrieved_product.name}")
            print(f"   - Price: {retrieved_product.price} (type: {type(retrieved_product.price)})")
            print(f"   - Status: {retrieved_product.status} (type: {type(retrieved_product.status)})")
            print(f"   - Created: {retrieved_product.created_at} (type: {type(retrieved_product.created_at)})")
            print(f"   - Tags: {retrieved_product.tags}")
            print(f"   - Metadata: {retrieved_product.metadata}")

            # Validation
            success = True
            validations = [
                ("Name", retrieved_product.name == original_product.name),
                (
                    "Price",
                    retrieved_product.price == original_product.price and isinstance(retrieved_product.price, Decimal),
                ),
                (
                    "Status",
                    retrieved_product.status == original_product.status and isinstance(retrieved_product.status, TestStatus),
                ),
                ("DateTime", isinstance(retrieved_product.created_at, datetime)),
                ("Tags", retrieved_product.tags == original_product.tags),
                ("Metadata", retrieved_product.metadata == original_product.metadata),
            ]

            print("\n✅ Validation Results:")
            for field, result in validations:
                status = "✅" if result else "❌"
                print(f"   {status} {field}: {result}")
                if not result:
                    success = False

            if success:
                print("\n🎉 All validations passed! Enhanced JsonSerializer works generically!")
            else:
                print("\n❌ Some validations failed.")

        print("=" * 65)

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_generic_serialization())
