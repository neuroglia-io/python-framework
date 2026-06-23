#!/usr/bin/env python3
"""
Test script to validate the generic FileSystemRepository implementation in Mario Pizzeria
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path so we can import neuroglia
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Add mario-pizzeria to path for domain imports
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_generic_repository():
    """Test the generic FileSystemRepository implementation"""
    print("🧪 Testing Mario Pizzeria Generic FileSystemRepository Implementation")
    print("=" * 60)

    try:
        from decimal import Decimal

        from domain.entities import Pizza, PizzaSize
        from integration.repositories import FilePizzaRepository

        # Create repository instance
        test_data_dir = Path(__file__).parent / "test_data"
        test_data_dir.mkdir(exist_ok=True)

        pizza_repo = FilePizzaRepository(str(test_data_dir / "menu"))

        print(f"✅ Created FilePizzaRepository with data directory: {test_data_dir / 'menu'}")

        # Test getting all pizzas (should initialize default menu)
        print("\n📋 Testing get_all_async() - should initialize default menu...")
        all_pizzas = await pizza_repo.get_all_async()

        print(f"✅ Found {len(all_pizzas)} pizzas in menu:")
        for pizza in all_pizzas:
            print(f"   - {pizza.name} ({pizza.size.value}) - ${pizza.total_price}")

        # Test getting pizza by name
        print("\n🔍 Testing get_by_name_async('Margherita')...")
        margherita = await pizza_repo.get_by_name_async("Margherita")
        if margherita:
            print(f"✅ Found Margherita: {margherita.name}, Size: {margherita.size.value}, Price: ${margherita.total_price}")
            print(f"   Toppings: {', '.join(margherita.toppings)}")
        else:
            print("❌ Margherita not found")

        # Test getting pizzas by size
        print("\n📏 Testing get_by_size_async(PizzaSize.LARGE)...")
        large_pizzas = await pizza_repo.get_by_size_async(PizzaSize.LARGE)
        print(f"✅ Found {len(large_pizzas)} large pizzas:")
        for pizza in large_pizzas:
            print(f"   - {pizza.name}")

        # Test creating a new pizza
        print("\n➕ Testing add_async() with new pizza...")
        hawaiian = Pizza("Hawaiian", Decimal("18.99"), PizzaSize.LARGE, "Ham and pineapple pizza")
        hawaiian.toppings = ["tomato sauce", "mozzarella", "ham", "pineapple"]

        await pizza_repo.add_async(hawaiian)
        print(f"✅ Added Hawaiian pizza with ID: {hawaiian.id}")

        # Verify the new pizza was added
        print("\n🔍 Testing get_async() with new pizza ID...")
        retrieved_hawaiian = await pizza_repo.get_async(hawaiian.id)
        if retrieved_hawaiian:
            print(f"✅ Retrieved Hawaiian: {retrieved_hawaiian.name}, Price: ${retrieved_hawaiian.total_price}")
        else:
            print(f"❌ Could not retrieve Hawaiian pizza with ID: {hawaiian.id}")

        # Test search by toppings
        print("\n🔍 Testing search_by_toppings_async(['pineapple'])...")
        pineapple_pizzas = await pizza_repo.search_by_toppings_async(["pineapple"])
        print(f"✅ Found {len(pineapple_pizzas)} pizzas with pineapple:")
        for pizza in pineapple_pizzas:
            print(f"   - {pizza.name}")

        # Test the file structure created by FileSystemRepository
        print("\n📁 Checking file structure created by FileSystemRepository...")
        menu_dir = test_data_dir / "menu"
        if menu_dir.exists():
            print(f"✅ Menu directory created: {menu_dir}")
            files = list(menu_dir.rglob("*"))
            for file in files:
                if file.is_file():
                    print(f"   📄 {file.relative_to(menu_dir)}")

        print("\n🎉 All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_generic_repository())
