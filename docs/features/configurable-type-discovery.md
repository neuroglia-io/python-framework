# 🎯 Configurable Type Discovery

The Neuroglia framework provides a flexible TypeRegistry system that allows applications to configure which modules should be scanned for domain types (enums, value objects, etc.) without hardcoding patterns in the framework itself.

## 🎯 Overview

The TypeRegistry replaces hardcoded domain structure assumptions with a clean, configurable approach:

- **Framework Agnostic**: No domain-specific knowledge in framework code
- **Configurable**: Applications specify their exact module structure
- **Performance Optimized**: Only scans registered modules instead of trying dozens of patterns
- **Extensible**: Supports dynamic type discovery and multiple configuration methods

## 🏗️ Core Components

### TypeRegistry

The `TypeRegistry` provides centralized type discovery using the framework's existing utilities:

```python
from neuroglia.core.type_registry import TypeRegistry, get_type_registry
from neuroglia.core.type_finder import TypeFinder
from neuroglia.core.module_loader import ModuleLoader

# Get the global type registry instance
registry = get_type_registry()

# Register modules for type discovery
registry.register_modules([
    "domain.entities.enums",
    "domain.value_objects",
    "shared.types"
])

# Find enum for a value
pizza_size_enum = registry.find_enum_for_value("LARGE")
```

### Enhanced JsonSerializer

The `JsonSerializer` now accepts configurable type modules:

```python
from neuroglia.serialization.json import JsonSerializer
from neuroglia.hosting.enhanced_web_application_builder import EnhancedWebApplicationBuilder

builder = EnhancedWebApplicationBuilder()

# Configure with specific type modules
JsonSerializer.configure(builder, type_modules=[
    "domain.entities.enums",      # Main enum module
    "domain.entities",            # Entity module (for embedded enums)
    "domain.value_objects",       # Value objects with enums
])
```

## 🚀 Configuration Methods

### Method 1: Direct Configuration

Configure type modules during JsonSerializer setup:

```python
def configure_application():
    builder = EnhancedWebApplicationBuilder()

    # Configure JsonSerializer with your domain modules
    JsonSerializer.configure(builder, type_modules=[
        "myapp.domain.enums",         # Primary enumerations
        "myapp.domain.entities",      # Domain entities
        "myapp.domain.value_objects", # Value objects
        "myapp.shared.types",         # Shared types
        "myapp.integration.external"  # External API types
    ])

    return builder
```

### Method 2: Post-Configuration Registration

Register modules after initial configuration:

```python
def configure_with_registration():
    builder = EnhancedWebApplicationBuilder()

    # Basic configuration
    JsonSerializer.configure(builder)

    # Register additional type modules
    JsonSerializer.register_type_modules([
        "myapp.domain.aggregates",
        "myapp.domain.value_objects",
        "myapp.shared.enums"
    ])

    return builder
```

### Method 3: Direct TypeRegistry Access

Configure the TypeRegistry directly for advanced scenarios:

```python
def configure_advanced():
    from neuroglia.core.type_registry import get_type_registry

    # Get the global registry
    registry = get_type_registry()

    # Register core domain modules
    registry.register_modules([
        "orders.domain.entities",
        "orders.domain.enums"
    ])

    # Register shared library types
    registry.register_modules([
        "shared_lib.common.enums",
        "payment_gateway.types"
    ])

    # Standard JsonSerializer configuration
    builder = EnhancedWebApplicationBuilder()
    JsonSerializer.configure(builder)

    return builder
```

## 🧪 Usage Examples

### Mario Pizzeria Configuration

```python
from neuroglia.serialization.json import JsonSerializer
from neuroglia.hosting.enhanced_web_application_builder import EnhancedWebApplicationBuilder

def configure_mario_pizzeria():
    builder = EnhancedWebApplicationBuilder()

    # Configure with Mario Pizzeria's domain structure
    JsonSerializer.configure(builder, type_modules=[
        "domain.entities.enums",      # PizzaSize, OrderStatus, Priority
        "domain.entities",            # Pizza, Order entities
        "domain.value_objects",       # Money, Address value objects
    ])

    return builder
```

### Microservice Configuration

```python
def configure_microservice():
    from neuroglia.core.type_registry import get_type_registry

    registry = get_type_registry()

    # Register internal domain types
    registry.register_modules([
        "orders.domain.entities",
        "orders.domain.enums"
    ])

    # Register external service types we need to deserialize
    registry.register_modules([
        "payment_service.models",
        "inventory_service.types",
        "shared_contracts.events"
    ])

    builder = EnhancedWebApplicationBuilder()
    JsonSerializer.configure(builder)
    return builder
```

### Flat Project Structure

For projects with simple, flat module structure:

```python
def configure_flat_structure():
    builder = EnhancedWebApplicationBuilder()

    # Simple flat structure: models.py, enums.py, types.py
    JsonSerializer.configure(builder, type_modules=[
        "models",        # Main model types
        "enums",         # All enumerations
        "types",         # Custom types
        "constants"      # Constants and lookups
    ])

    return builder
```

## 🔧 Dynamic Type Discovery

For advanced scenarios, you can dynamically discover and register types:

```python
def dynamic_type_discovery():
    from neuroglia.core.type_registry import get_type_registry
    from neuroglia.core.type_finder import TypeFinder
    from neuroglia.core.module_loader import ModuleLoader
    from enum import Enum

    registry = get_type_registry()

    # Discover all enum types in base modules
    base_modules = ["myapp.domain", "myapp.shared"]

    for base_module_name in base_modules:
        try:
            base_module = ModuleLoader.load(base_module_name)

            # Find all enum types
            enum_types = TypeFinder.get_types(
                base_module,
                predicate=lambda t: isinstance(t, type) and issubclass(t, Enum) and t != Enum,
                include_sub_modules=True,
                include_sub_packages=True
            )

            if enum_types:
                print(f"Discovered {len(enum_types)} enum types in {base_module_name}")
                # Types are automatically cached when accessed

        except ImportError:
            print(f"Module {base_module_name} not available")

    return registry
```

## 💡 Best Practices

### 1. Specific Module Registration

Register only the modules that contain types you need:

```python
# Good: Specific modules
JsonSerializer.configure(builder, type_modules=[
    "domain.entities.enums",      # Specific enum module
    "domain.value_objects"        # Specific value object module
])

# Avoid: Too broad
JsonSerializer.configure(builder, type_modules=[
    "domain",                     # Too broad, includes everything
    "application"                 # Application layer shouldn't have enums
])
```

### 2. Layer-Appropriate Registration

Only register modules from appropriate architectural layers:

```python
# Good: Domain and integration layers
JsonSerializer.configure(builder, type_modules=[
    "domain.entities.enums",         # Domain layer
    "domain.value_objects",          # Domain layer
    "integration.external_types"     # Integration layer for external APIs
])

# Avoid: Application layer
JsonSerializer.configure(builder, type_modules=[
    "application.commands",          # Commands shouldn't have enums
    "application.handlers"           # Handlers shouldn't have enums
])
```

### 3. Performance Optimization

Register modules in order of frequency of use:

```python
# Most frequently used enums first
JsonSerializer.configure(builder, type_modules=[
    "domain.entities.enums",      # Most common: PizzaSize, OrderStatus
    "domain.value_objects",       # Less common: specialized enums
    "shared.constants"            # Least common: system constants
])
```

### 4. Modular Configuration

For large applications, organize configuration by feature:

```python
def configure_order_types():
    return [
        "orders.domain.enums",
        "orders.domain.entities",
        "orders.integration.payment_types"
    ]

def configure_inventory_types():
    return [
        "inventory.domain.enums",
        "inventory.domain.entities",
        "inventory.integration.supplier_types"
    ]

def configure_application():
    builder = EnhancedWebApplicationBuilder()

    all_type_modules = (
        configure_order_types() +
        configure_inventory_types() +
        ["shared.common.enums"]
    )

    JsonSerializer.configure(builder, type_modules=all_type_modules)
    return builder
```

## 🔗 Related Documentation

- [Data Access](data-access.md) - Repository patterns and serialization
- [Domain-Driven Design](../getting-started.md#domain-driven-design) - Domain layer organization
- [Dependency Injection](../patterns/dependency-injection.md) - Service configuration patterns

## 🧪 Testing Configuration

Test your type configuration with different scenarios:

```python
def test_configured_serialization():
    """Test that configured types are discovered correctly"""
    from neuroglia.core.type_registry import get_type_registry

    registry = get_type_registry()
    registry.register_modules(["domain.entities.enums"])

    # Test enum discovery
    pizza_size_enum = registry.find_enum_for_value("LARGE")
    assert pizza_size_enum is not None
    assert pizza_size_enum.__name__ == "PizzaSize"

    print("✅ Configured type discovery working correctly")
```

The configurable TypeRegistry approach ensures your application can specify exactly which modules contain domain types, making the framework truly generic while maintaining intelligent type inference capabilities.
