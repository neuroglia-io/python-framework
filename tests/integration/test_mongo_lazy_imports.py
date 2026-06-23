"""
Test lazy import mechanism for MongoDB repositories.

Verifies that:
1. MotorRepository can be imported without pymongo
2. Sync repositories are lazily loaded
3. All exports are in __all__
"""

import sys


def test_motor_import_without_pymongo():
    """Test that MotorRepository can be imported even if pymongo is not available."""
    # Save original pymongo module if it exists
    pymongo_module = sys.modules.get("pymongo")

    try:
        # Temporarily hide pymongo from imports
        if "pymongo" in sys.modules:
            del sys.modules["pymongo"]
        sys.modules["pymongo"] = None  # Block pymongo imports

        # Force reload of mongo package
        if "neuroglia.data.infrastructure.mongo" in sys.modules:
            del sys.modules["neuroglia.data.infrastructure.mongo"]

        # This should work without pymongo
        from neuroglia.data.infrastructure.mongo import MotorRepository

        assert MotorRepository is not None
        print("✅ MotorRepository imported successfully without pymongo")

    finally:
        # Restore pymongo module
        if pymongo_module is not None:
            sys.modules["pymongo"] = pymongo_module
        elif "pymongo" in sys.modules:
            del sys.modules["pymongo"]


def test_sync_repositories_require_pymongo():
    """Test that sync repositories fail gracefully without pymongo."""
    # Save original pymongo module
    pymongo_module = sys.modules.get("pymongo")

    try:
        # Hide pymongo
        if "pymongo" in sys.modules:
            del sys.modules["pymongo"]
        sys.modules["pymongo"] = None

        # Force reload
        if "neuroglia.data.infrastructure.mongo" in sys.modules:
            del sys.modules["neuroglia.data.infrastructure.mongo"]

        # Import package
        import neuroglia.data.infrastructure.mongo as mongo_pkg

        # Try to access sync repository - should fail
        try:
            _ = mongo_pkg.MongoRepository
            print("❌ MongoRepository should have failed without pymongo")
            assert False, "Should have raised ModuleNotFoundError"
        except (ModuleNotFoundError, AttributeError) as e:
            print(f"✅ MongoRepository correctly failed without pymongo: {type(e).__name__}")

    finally:
        # Restore pymongo
        if pymongo_module is not None:
            sys.modules["pymongo"] = pymongo_module
        elif "pymongo" in sys.modules:
            del sys.modules["pymongo"]


def test_all_exports_present():
    """Test that __all__ exports are present after lazy loading."""
    from neuroglia.data.infrastructure.mongo import __all__

    expected_exports = [
        "MotorRepository",
        "MongoRepository",
        "MongoQueryProvider",
        "MongoRepositoryOptions",
        "EnhancedMongoRepository",
        "TypedMongoQuery",
        "with_typed_mongo_query",
        "MongoSerializationHelper",
    ]

    for export in expected_exports:
        assert export in __all__, f"Missing export: {export}"

    print(f"✅ All {len(expected_exports)} exports present in __all__")


def test_sync_imports_work_with_pymongo():
    """Test that sync repositories work when pymongo IS installed."""
    try:
        import pymongo  # noqa: F401 - Checking availability

        # Force reload to get fresh imports
        if "neuroglia.data.infrastructure.mongo" in sys.modules:
            del sys.modules["neuroglia.data.infrastructure.mongo"]

        from neuroglia.data.infrastructure.mongo import (
            EnhancedMongoRepository,
            MongoQueryProvider,
            MongoRepository,
            MongoRepositoryOptions,
        )

        assert MongoRepository is not None
        assert MongoQueryProvider is not None
        assert MongoRepositoryOptions is not None
        assert EnhancedMongoRepository is not None

        print("✅ All sync repositories imported successfully with pymongo")

    except ImportError:
        print("⚠️  Skipping sync repository test (pymongo not installed)")


if __name__ == "__main__":
    print("\n🧪 Testing MongoDB Lazy Import Mechanism\n")
    print("=" * 60)

    test_all_exports_present()
    print()

    test_motor_import_without_pymongo()
    print()

    test_sync_repositories_require_pymongo()
    print()

    test_sync_imports_work_with_pymongo()
    print()

    print("=" * 60)
    print("\n✨ All lazy import tests passed!\n")
