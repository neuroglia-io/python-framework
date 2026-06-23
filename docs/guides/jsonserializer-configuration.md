# JsonSerializer and TypeRegistry Configuration Examples

This document provides comprehensive configuration patterns for the JsonSerializer with TypeRegistry to support different project structures and domain discovery requirements.

## Overview

The configurable type discovery system allows you to specify which modules contain your enums and domain types, eliminating the need for hardcoded patterns in the framework.
This provides flexibility for different project architectures while maintaining performance through intelligent caching.

## Configuration Methods

### Method 1: Configure During JsonSerializer Setup

```python
from neuroglia.hosting.enhanced_web_application_builder import EnhancedWebApplicationBuilder
from neuroglia.serialization.json import JsonSerializer

def configure_mario_pizzeria_types():
    """Example: Configure types for Mario Pizzeria application"""
    builder = EnhancedWebApplicationBuilder()

    # Configure during JsonSerializer setup
    JsonSerializer.configure(
        builder,
        type_modules=[
            "domain.entities.enums",    # Main enum module
            "domain.entities",          # Entity module (for embedded enums)
            "domain.value_objects",     # Value objects with enums
            "shared.enums",             # Shared enumeration types
        ]
    )

    return builder
```

### Method 2: Register Types After Configuration

```python
from neuroglia.hosting.enhanced_web_application_builder import EnhancedWebApplicationBuilder
from neuroglia.serialization.json import JsonSerializer

def configure_generic_ddd_application():
    """Example: Configure types for generic DDD application"""
    builder = EnhancedWebApplicationBuilder()

    # Configure JsonSerializer first
    JsonSerializer.configure(builder)

    # Register additional type modules
    JsonSerializer.register_type_modules([
        "myapp.domain.aggregates",
        "myapp.domain.value_objects",
        "myapp.domain.enums",
        "myapp.shared.types",
        "myapp.integration.external_types",
    ])

    return builder
```

### Method 3: Direct TypeRegistry Configuration

```python
from neuroglia.core.type_registry import get_type_registry
from neuroglia.hosting.enhanced_web_application_builder import EnhancedWebApplicationBuilder
from neuroglia.serialization.json import JsonSerializer

def configure_microservice_types():
    """Example: Configure types for microservice with external dependencies"""
    builder = EnhancedWebApplicationBuilder()

    # Get the global TypeRegistry instance
    type_registry = get_type_registry()

    # Register our domain modules
    type_registry.register_modules([
        "orders.domain.entities",
        "orders.domain.enums",
        "orders.shared.types"
    ])

    # Register shared library types
    type_registry.register_modules([
        "shared_lib.common.enums",
        "shared_lib.business.types"
    ])

    # Register external API types that we need to deserialize
    type_registry.register_modules([
        "external_api_client.models",
        "payment_gateway.types"
    ])

    JsonSerializer.configure(builder)

    return builder
```

## Project Structure Examples

### Flat Project Structure

```python
from neuroglia.hosting.enhanced_web_application_builder import EnhancedWebApplicationBuilder
from neuroglia.serialization.json import JsonSerializer

def configure_flat_project_structure():
    """Example: Configure types for flat project structure"""
    builder = EnhancedWebApplicationBuilder()

    # For projects with flat structure like:
    # myproject/
    #   models.py
    #   enums.py
    #   types.py
    JsonSerializer.configure(
        builder,
        type_modules=[
            "models",      # Main model types
            "enums",       # All enumerations
            "types",       # Custom types
            "constants",   # Constants and lookups
        ]
    )

    return builder
```

### Domain-Driven Design Structure

```python
def configure_ddd_structure():
    """Example: Configure types for DDD project structure"""
    # For projects with DDD structure like:
    # myproject/
    #   domain/
    #     aggregates/
    #     entities/
    #     value_objects/
    #     enums/
    #   application/
    #   infrastructure/

    JsonSerializer.configure(
        builder,
        type_modules=[
            "domain.enums",
            "domain.entities",
            "domain.value_objects",
            "domain.aggregates",
            "shared.types"
        ]
    )
```

### Microservice Architecture

```python
def configure_microservice_architecture():
    """Example: Configure types for microservice architecture"""
    # For microservices that need to handle:
    # - Internal domain types
    # - Shared library types
    # - External service types

    type_registry = get_type_registry()

    # Internal domain
    type_registry.register_modules([
        "user_service.domain.enums",
        "user_service.domain.entities"
    ])

    # Shared libraries
    type_registry.register_modules([
        "common_lib.enums",
        "auth_lib.types"
    ])

    # External services
    type_registry.register_modules([
        "notification_service.contracts",
        "payment_service.models"
    ])
```

## Dynamic Type Discovery

For more advanced scenarios, you can dynamically discover and register types:

```python
from enum import Enum
from neuroglia.core.module_loader import ModuleLoader
from neuroglia.core.type_finder import TypeFinder
from neuroglia.core.type_registry import get_type_registry

def dynamic_type_discovery_example():
    """Example: Dynamically discover and register types"""
    type_registry = get_type_registry()

    # Example: Discover all enum types in a base module
    base_modules = ["myapp.domain", "myapp.shared", "myapp.external"]

    for base_module_name in base_modules:
        try:
            base_module = ModuleLoader.load(base_module_name)

            # Find all enum types in this module and submodules
            enum_types = TypeFinder.get_types(
                base_module,
                predicate=lambda t: (
                    isinstance(t, type)
                    and issubclass(t, Enum)
                    and t != Enum
                ),
                include_sub_modules=True,
                include_sub_packages=True
            )

            if enum_types:
                print(f"Found {len(enum_types)} enum types in {base_module_name}")
                # The TypeRegistry will cache these automatically when they're accessed

        except ImportError:
            print(f"Module {base_module_name} not available")

    return type_registry
```

## Performance Considerations

### Module Registration Best Practices

1. **Register Early**: Register type modules during application startup to avoid runtime discovery overhead
2. **Be Specific**: Register only the modules that contain types you need to deserialize
3. **Use Caching**: The TypeRegistry automatically caches discovered types for performance
4. **Group Related Types**: Keep related enums and types in organized module structures

### Example Startup Configuration

```python
from neuroglia.hosting.enhanced_web_application_builder import EnhancedWebApplicationBuilder
from neuroglia.serialization.json import JsonSerializer

def create_optimized_app():
    """Example: Optimized application startup with type registration"""
    builder = EnhancedWebApplicationBuilder()

    # Register all type modules at startup
    type_modules = [
        # Core domain types
        "domain.enums",
        "domain.entities",

        # Application layer types
        "application.commands",
        "application.queries",

        # Integration types
        "integration.external_apis",
        "integration.shared_contracts",

        # Testing types (if needed in production)
        # "tests.fixtures.types",
    ]

    JsonSerializer.configure(builder, type_modules=type_modules)

    # Build application
    app = builder.build()

    return app
```

## Error Handling and Debugging

### Debugging Type Discovery

```python
from neuroglia.core.type_registry import get_type_registry

def debug_type_discovery():
    """Debug helper to inspect registered types"""
    type_registry = get_type_registry()

    # Check registered modules
    modules = type_registry.get_registered_modules()
    print(f"Registered modules: {modules}")

    # Check cached enum types
    cached_enums = type_registry.get_cached_enum_types()
    print(f"Cached enum types: {list(cached_enums.keys())}")

    # Test enum lookup
    test_value = "test_value"
    found_enum = type_registry.find_enum_for_value(test_value)
    print(f"Enum for '{test_value}': {found_enum}")
```

### Common Configuration Issues

1. **Module Not Found**: Ensure module paths are correct and modules are importable
2. **No Enums Discovered**: Check that enum classes are properly defined and accessible
3. **Performance Issues**: Avoid registering too many modules or very large module trees

## Testing Configuration

For testing scenarios, you can configure type discovery specifically for test environments:

```python
def configure_test_types():
    """Example: Configure types for testing environment"""
    from neuroglia.core.type_registry import get_type_registry

    type_registry = get_type_registry()

    # Register test-specific modules
    test_modules = [
        "tests.fixtures.enums",
        "tests.mocks.types",
        "tests.data.models"
    ]

    type_registry.register_modules(test_modules)

    return type_registry
```

## Best Practices Summary

1. **Early Registration**: Register type modules during application startup
2. **Specific Modules**: Only register modules containing types you need to deserialize
3. **Organized Structure**: Keep related types in well-organized module hierarchies
4. **Performance Monitoring**: Monitor type discovery performance in production
5. **Clear Documentation**: Document your type module organization for team members
6. **Environment-Specific**: Use different configurations for development, testing, and production
7. **Error Handling**: Include proper error handling for module loading failures

This configurable approach provides maximum flexibility while maintaining the performance and reliability of the Neuroglia framework's serialization system.
