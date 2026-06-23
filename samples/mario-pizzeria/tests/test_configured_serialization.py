#!/usr/bin/env python3
"""
Test showing how to configure JsonSerializer with TypeRegistry for enum discovery
in Mario Pizzeria domain context
"""

import asyncio
import sys
from pathlib import Path

from neuroglia.core.type_registry import get_type_registry, register_types_modules
from neuroglia.serialization.json import JsonSerializer

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_configured_serialization():
    """Test JsonSerializer with configured type modules"""
    print("🧪 Testing Configured JsonSerializer with TypeRegistry")
    print("=" * 65)

    try:
        # Configure type modules for enum discovery
        print("📋 Step 1: Configuring TypeRegistry with domain modules...")

        # Register the modules where our enums are located
        type_modules = [
            "domain.entities.enums",  # Mario Pizzeria enum location
        ]

        # Register modules globally
        register_types_modules(type_modules)

        # Verify registration
        type_registry = get_type_registry()
        registered_modules = type_registry.get_registered_modules()
        print(f"✅ Registered modules: {registered_modules}")

        # Check what enum types were discovered
        cached_enums = type_registry.get_cached_enum_types()
        print(f"✅ Discovered enum types: {list(cached_enums.keys())}")

        # Test Mario Pizzeria enums
        print("\n📋 Step 2: Testing Mario Pizzeria enum deserialization...")
        from decimal import Decimal

        from domain.entities import Pizza, PizzaSize

        # Create a pizza with enum
        original_pizza = Pizza("Test Pizza", Decimal("19.99"), PizzaSize.LARGE, "Test pizza description")
        original_pizza.id = "test-pizza-123"

        # Serialize
        serializer = JsonSerializer()
        json_text = serializer.serialize_to_text(original_pizza)
        print(f"✅ Serialized Pizza: {json_text}")

        # Deserialize using configured TypeRegistry
        deserialized_pizza = serializer.deserialize_from_text(json_text, Pizza)
        print(f"✅ Deserialized Pizza size: {deserialized_pizza.size} (type: {type(deserialized_pizza.size)})")

        # Validation
        validations = [
            (
                "Pizza Size",
                deserialized_pizza.size == PizzaSize.LARGE and isinstance(deserialized_pizza.size, PizzaSize),
            ),
        ]

        print("\n📊 Validation Results:")
        all_passed = True
        for field, result in validations:
            status = "✅" if result else "❌"
            print(f"   {status} {field}: {result}")
            if not result:
                all_passed = False

        if all_passed:
            print("\n🎉 All configured type discovery tests passed!")
        else:
            print("\n❌ Some tests failed.")

        print("=" * 65)

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_configured_serialization())
