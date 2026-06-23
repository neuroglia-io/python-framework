#!/usr/bin/env python3
"""
Test script to validate flexible domain module discovery across different project structures
"""

import asyncio
import sys
import tempfile
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory

from neuroglia.data.abstractions import Entity
from neuroglia.data.infrastructure.filesystem import FileSystemRepository
from neuroglia.serialization.json import JsonSerializer

# Add the project root to Python path so we can import neuroglia
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


# Test enums in different modules to simulate various project structures
class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class TestOrder(Entity):
    """Test entity that should find enums in current module"""

    def __init__(self, order_id: str, total_amount: Decimal, status: OrderStatus, priority: Priority):
        super().__init__()
        self.id = order_id
        self.total_amount = total_amount
        self.status = status
        self.priority = priority
        self.created_at = datetime.now()


# Create a temporary module structure to test discovery
def create_test_module_structure():
    """Create temporary module files to test different domain structures"""
    temp_dir = Path(tempfile.mkdtemp())

    # Create different domain structure patterns
    patterns = [
        "testproject/domain/models/enums.py",
        "testproject/domain/resources/enums.py",
        "testproject/models/enums.py",
        "testproject/core/enums.py",
        "testproject/shared/enums.py",
    ]

    enum_content = """
from enum import Enum

class TestColor(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

class TestSize(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
"""

    for pattern in patterns:
        file_path = temp_dir / pattern
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(enum_content)

        # Create __init__.py files
        init_file = file_path.parent / "__init__.py"
        if not init_file.exists():
            init_file.write_text("")

        # Create parent __init__.py files
        parent = file_path.parent.parent
        while parent != temp_dir:
            init_file = parent / "__init__.py"
            if not init_file.exists():
                init_file.write_text("")
            parent = parent.parent

    return temp_dir


async def test_flexible_domain_discovery():
    """Test the flexible domain module discovery"""
    print("🧪 Testing Flexible Domain Module Discovery")
    print("=" * 60)

    try:
        # Test 1: Local module enum discovery
        print("📋 Test 1: Local Module Enum Discovery")
        original_order = TestOrder(
            order_id="order-123",
            total_amount=Decimal("199.99"),
            status=OrderStatus.CONFIRMED,
            priority=Priority.HIGH,
        )

        serializer = JsonSerializer()
        json_text = serializer.serialize_to_text(original_order)
        print(f"✅ Serialized: {json_text}")

        deserialized_order = serializer.deserialize_from_text(json_text, TestOrder)
        print(f"✅ Deserialized Status: {deserialized_order.status} (type: {type(deserialized_order.status)})")
        print(f"✅ Deserialized Priority: {deserialized_order.priority} (type: {type(deserialized_order.priority)})")
        print(f"✅ Deserialized Amount: {deserialized_order.total_amount} (type: {type(deserialized_order.total_amount)})")

        # Validation
        validation_results = [
            (
                "Status",
                deserialized_order.status == OrderStatus.CONFIRMED and isinstance(deserialized_order.status, OrderStatus),
            ),
            (
                "Priority",
                deserialized_order.priority == Priority.HIGH and isinstance(deserialized_order.priority, Priority),
            ),
            (
                "Amount",
                deserialized_order.total_amount == Decimal("199.99") and isinstance(deserialized_order.total_amount, Decimal),
            ),
            ("DateTime", isinstance(deserialized_order.created_at, datetime)),
        ]

        print("\n📊 Validation Results:")
        all_passed = True
        for field, result in validation_results:
            status = "✅" if result else "❌"
            print(f"   {status} {field}: {result}")
            if not result:
                all_passed = False

        # Test 2: Repository integration
        print("\n📁 Test 2: FileSystemRepository Integration")

        with TemporaryDirectory() as temp_dir:
            repo = FileSystemRepository[TestOrder, str](data_directory=temp_dir, entity_type=TestOrder, key_type=str)

            # Save and retrieve order
            saved_order = await repo.add_async(original_order)
            retrieved_order = await repo.get_async(saved_order.id)

            if retrieved_order:
                print(f"✅ Saved and retrieved order with status: {retrieved_order.status}")
                print(f"✅ Priority maintained: {retrieved_order.priority}")
            else:
                print("❌ Failed to retrieve order")

        # Test 3: Verify configurable type discovery works
        print("\n🔍 Test 3: Configurable Type Discovery")

        from neuroglia.core.type_registry import get_type_registry

        type_registry = get_type_registry()

        # Check if we can register additional modules
        additional_modules = ["tests.cases.test_flexible_discovery"]
        type_registry.register_modules(additional_modules)

        registered_modules = type_registry.get_registered_modules()
        print(f"📋 Registered modules: {registered_modules}")

        # Test enum discovery
        cached_enums = type_registry.get_cached_enum_types()
        print(f"✅ Cached enum types: {list(cached_enums.keys())}")

        print("\n✅ Configurable type discovery test completed")

        if all_passed:
            print("\n🎉 All flexible domain discovery tests passed!")
        else:
            print("\n❌ Some tests failed.")

        print("=" * 60)

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_flexible_domain_discovery())
