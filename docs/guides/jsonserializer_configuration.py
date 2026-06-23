"""
JsonSerializer and TypeRegistry Configuration Examples

This module provides reusable configuration functions for different project structures.
Import and use these functions in your application setup.
"""

from enum import Enum

from neuroglia.core.module_loader import ModuleLoader
from neuroglia.core.type_finder import TypeFinder
from neuroglia.core.type_registry import get_type_registry
from neuroglia.hosting.enhanced_web_application_builder import (
    EnhancedWebApplicationBuilder,
)
from neuroglia.serialization.json import JsonSerializer


def configure_ddd_application(
    domain_module_prefix: str = "domain",
) -> EnhancedWebApplicationBuilder:
    """
    Configure JsonSerializer for Domain-Driven Design project structure.

    Args:
        domain_module_prefix: The prefix for your domain modules (e.g., "domain", "myapp.domain")

    Returns:
        Configured WebApplicationBuilder
    """
    builder = EnhancedWebApplicationBuilder()

    type_modules = [
        f"{domain_module_prefix}.enums",
        f"{domain_module_prefix}.entities",
        f"{domain_module_prefix}.value_objects",
        f"{domain_module_prefix}.aggregates",
    ]

    JsonSerializer.configure(builder, modules=type_modules)
    return builder


def configure_flat_structure(module_names: list[str] = None) -> EnhancedWebApplicationBuilder:
    """
    Configure JsonSerializer for flat project structure.

    Args:
        module_names: List of module names containing types. Defaults to common names.

    Returns:
        Configured WebApplicationBuilder
    """
    builder = EnhancedWebApplicationBuilder()

    if module_names is None:
        module_names = ["models", "enums", "types", "constants"]

    JsonSerializer.configure(builder, modules=module_names)
    return builder


def configure_microservice(internal_modules: list[str], external_modules: list[str] = None) -> EnhancedWebApplicationBuilder:
    """
    Configure JsonSerializer for microservice architecture.

    Args:
        internal_modules: List of internal domain modules
        external_modules: List of external service/library modules

    Returns:
        Configured WebApplicationBuilder
    """
    builder = EnhancedWebApplicationBuilder()

    type_registry = get_type_registry()

    # Register internal modules
    type_registry.register_modules(internal_modules)

    # Register external modules if provided
    if external_modules:
        type_registry.register_modules(external_modules)

    JsonSerializer.configure(builder)
    return builder


def register_additional_modules(module_names: list[str]) -> None:
    """
    Register additional type modules with the global TypeRegistry.

    Args:
        module_names: List of module names to register
    """
    type_registry = get_type_registry()
    type_registry.register_modules(module_names)


def discover_enum_types_in_modules(base_module_names: list[str]) -> dict[str, type]:
    """
    Dynamically discover all Enum types in the specified base modules.

    Args:
        base_module_names: List of base module names to search

    Returns:
        Dictionary mapping enum value strings to enum types
    """
    discovered_enums = {}
    type_registry = get_type_registry()

    for base_module_name in base_module_names:
        try:
            base_module = ModuleLoader.load(base_module_name)

            # Find all enum types in this module and submodules
            enum_types = TypeFinder.get_types(
                base_module,
                predicate=lambda t: (isinstance(t, type) and issubclass(t, Enum) and t != Enum),
                include_sub_modules=True,
                include_sub_packages=True,
            )

            # Cache enum values for quick lookup
            for enum_type in enum_types:
                for enum_value in enum_type:
                    discovered_enums[str(enum_value.value)] = enum_type

        except ImportError as e:
            print(f"Warning: Could not import module {base_module_name}: {e}")

    return discovered_enums


def get_type_registry_status() -> dict:
    """
    Get the current status of the TypeRegistry for debugging.

    Returns:
        Dictionary with registry status information
    """
    type_registry = get_type_registry()

    return {
        "registered_modules": type_registry.get_registered_modules(),
        "cached_enum_types": list(type_registry.get_cached_enum_types().keys()),
        "total_cached_enums": len(type_registry.get_cached_enum_types()),
    }


# Pre-configured setups for common scenarios
CONFIGURATION_PRESETS = {
    "ddd_standard": lambda: configure_ddd_application("domain"),
    "ddd_prefixed": lambda prefix: configure_ddd_application(f"{prefix}.domain"),
    "flat_basic": lambda: configure_flat_structure(),
    "flat_custom": lambda modules: configure_flat_structure(modules),
}


def create_app_with_preset(preset_name: str, **kwargs) -> EnhancedWebApplicationBuilder:
    """
    Create an application using a predefined configuration preset.

    Args:
        preset_name: Name of the preset to use
        **kwargs: Additional arguments for the preset function

    Returns:
        Configured WebApplicationBuilder
    """
    if preset_name not in CONFIGURATION_PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(CONFIGURATION_PRESETS.keys())}")

    preset_func = CONFIGURATION_PRESETS[preset_name]

    if kwargs:
        return preset_func(**kwargs)
    else:
        return preset_func()


# Example usage patterns
if __name__ == "__main__":
    print("🧪 JsonSerializer Configuration Examples")
    print("=" * 50)

    # Example 1: DDD Structure
    print("\n📋 DDD Structure Configuration:")
    try:
        ddd_builder = configure_ddd_application("myapp.domain")
        print("✅ DDD configuration successful")
    except Exception as e:
        print(f"❌ DDD configuration failed: {e}")

    # Example 2: Flat Structure
    print("\n📋 Flat Structure Configuration:")
    try:
        flat_builder = configure_flat_structure(["models", "enums"])
        print("✅ Flat configuration successful")
    except Exception as e:
        print(f"❌ Flat configuration failed: {e}")

    # Example 3: Registry Status
    print("\n📋 TypeRegistry Status:")
    try:
        status = get_type_registry_status()
        print(f"✅ Status: {status}")
    except Exception as e:
        print(f"❌ Status check failed: {e}")

    print("\n🎉 All configuration examples completed!")
    print("=" * 50)
