# String Annotations in Python - Complete Guide

## What Are String Annotations?

String annotations (also called "forward references") are type hints written as strings instead of actual type references:

```python
# String annotation (forward reference)
def configure(builder: "ApplicationBuilderBase") -> "ApplicationBuilderBase":
    pass

# Regular annotation
def configure(builder: ApplicationBuilderBase) -> ApplicationBuilderBase:
    pass
```

## Why Use String Annotations?

### 1. **Avoid Circular Import Dependencies**

The most common reason - when two modules import from each other:

```python
# File: cache_repository.py
from neuroglia.hosting.abstractions import ApplicationBuilderBase  # ❌ Circular import!

class AsyncCacheRepository:
    @staticmethod
    def configure(builder: ApplicationBuilderBase):  # Needs the actual class
        pass
```

```python
# File: hosting/abstractions.py
from neuroglia.integration.cache_repository import AsyncCacheRepository  # ❌ Imports cache_repository!

class ApplicationBuilderBase:
    def add_cache_repository(self):
        AsyncCacheRepository.configure(self)  # Uses cache_repository
```

**Solution: Use string annotations**

```python
# File: cache_repository.py
# NO import needed at module level!

class AsyncCacheRepository:
    @staticmethod
    def configure(builder: "ApplicationBuilderBase"):  # ✅ String reference, no circular dependency
        pass
```

### 2. **Conditional/Optional Imports**

When dependencies might not be available:

```python
try:
    from neuroglia.hosting.abstractions import ApplicationBuilderBase
    from neuroglia.serialization.json import JsonSerializer
except ImportError:
    ApplicationBuilderBase = None  # type: ignore
    JsonSerializer = None  # type: ignore

# Still works even if imports failed!
def configure(builder: "ApplicationBuilderBase") -> "ApplicationBuilderBase":
    """Type checker sees the string, runtime doesn't need the actual class"""
    pass
```

### 3. **Type Checking Only**

String annotations are resolved by:

- **Type checkers** (mypy, pylance, pyright) - They resolve strings to actual types
- **NOT by Python runtime** - The string stays as a string

```python
# Type checker sees: builder has type ApplicationBuilderBase
# Python runtime sees: builder has annotation "ApplicationBuilderBase" (just a string)
def configure(builder: "ApplicationBuilderBase"):
    # Type checker provides autocomplete and error checking
    builder.services.add_singleton(...)  # ✅ Type checker knows .services exists
```

## PEP 563: Postponed Evaluation of Annotations

### The `from __future__ import annotations` Pattern

```python
from __future__ import annotations  # Makes ALL annotations strings automatically

# This:
def configure(builder: ApplicationBuilderBase) -> ApplicationBuilderBase:
    pass

# Becomes this at runtime:
def configure(builder: "ApplicationBuilderBase") -> "ApplicationBuilderBase":
    pass
```

**Benefits:**

1. **No import needed** - Annotations don't evaluate until requested
2. **Faster imports** - Python doesn't evaluate type hints at module load
3. **Cleaner code** - No need for manual string quotes

**This is why the DI container needed `get_type_hints()`** in v0.4.4!

```python
from typing import get_type_hints

# Without get_type_hints()
def __init__(self, dependency: "JsonSerializer"):
    # __annotations__ = {"dependency": "JsonSerializer"}  # It's a STRING!
    pass

# With get_type_hints()
type_hints = get_type_hints(MyClass.__init__)
# type_hints = {"dependency": <class 'JsonSerializer'>}  # Actual class!
```

## Real-World Example from Neuroglia

### Before v0.4.4 (BROKEN with string annotations):

```python
from __future__ import annotations  # Makes everything a string

class AsyncCacheRepository:
    def __init__(self, serializer: JsonSerializer):  # Becomes "JsonSerializer" at runtime
        pass

# DI Container tries to resolve:
dependency_type = init_arg.annotation  # Gets "JsonSerializer" (string!)
dependency_type.__name__  # ❌ AttributeError: 'str' object has no attribute '__name__'
```

### After v0.4.4 (FIXED with `get_type_hints()`):

```python
from typing import get_type_hints

# In DI container's _build_service():
type_hints = get_type_hints(service_type.__init__)  # Resolves string to actual class
resolved_annotation = type_hints.get(init_arg.name, init_arg.annotation)

dependency_type = resolved_annotation  # Gets JsonSerializer class (not string!)
dependency_type.__name__  # ✅ "JsonSerializer"
```

## When to Use String Annotations

### ✅ USE String Annotations When:

1. **Avoiding circular imports**

   ```python
   def configure(builder: "ApplicationBuilderBase"):  # builder.py imports this module
       pass
   ```

2. **Optional/conditional dependencies**

   ```python
   try:
       from some_package import SomeClass
   except ImportError:
       SomeClass = None

   def method(param: "SomeClass"):  # Works even if import failed
       pass
   ```

3. **Self-referential types**

   ```python
   class TreeNode:
       def add_child(self, child: "TreeNode"):  # TreeNode not fully defined yet
           pass
   ```

4. **Using `from __future__ import annotations`**

   ```python
   from __future__ import annotations  # All annotations become strings

   # No need for manual quotes, but be aware of DI resolution!
   ```

### ❌ DON'T Use String Annotations When:

1. **Simple, direct imports with no circular dependencies**

   ```python
   from typing import Optional

   def get_user(id: str) -> Optional[User]:  # ✅ No need for strings
       pass
   ```

2. **Standard library types**
   ```python
   def process(data: list[str]) -> dict[str, int]:  # ✅ No need for strings
       pass
   ```

## Impact on Neuroglia Framework

### CacheRepository Example

**Old (v0.4.2 - BROKEN):**

```python
# Non-parameterized - DI can't distinguish User vs Order cache
builder.services.add_singleton(CacheRepositoryOptions, singleton=options)
```

**Fixed (v0.4.4 - CORRECT):**

```python
# Parameterized - DI resolves CacheRepositoryOptions[User, str] correctly
builder.services.add_singleton(
    CacheRepositoryOptions[User, str],
    singleton=options_instance
)
```

**Why it works now:**

1. v0.4.3: Type variable substitution (TEntity → User, TKey → str)
2. v0.4.4: String annotation resolution ("JsonSerializer" → JsonSerializer class)
3. DI container resolves parameterized constructor parameters correctly

## Best Practices

### 1. Use Conditional Imports with String Annotations

```python
try:
    from neuroglia.hosting.abstractions import ApplicationBuilderBase
except ImportError:
    ApplicationBuilderBase = None  # type: ignore

def configure(builder: "ApplicationBuilderBase"):  # ✅ Safe even if import fails
    pass
```

### 2. Document When String Annotations Are Used

```python
def configure(
    builder: "ApplicationBuilderBase",  # String annotation to avoid circular import
    entity_type: type,
    key_type: type,
) -> "ApplicationBuilderBase":
    """
    Configure cache repository.

    Uses string annotation for ApplicationBuilderBase to avoid circular dependency
    with neuroglia.hosting.abstractions module.
    """
```

### 3. Test with `from __future__ import annotations`

All framework code should be tested with postponed annotation evaluation:

```python
from __future__ import annotations  # Add to test files

# Ensures DI container handles string annotations correctly
```

### 4. Use `get_type_hints()` in Reflection Code

Any code that inspects type annotations should use `get_type_hints()`:

```python
from typing import get_type_hints

# ❌ BAD - Gets raw annotations (might be strings)
annotations = some_func.__annotations__

# ✅ GOOD - Resolves string annotations to actual types
type_hints = get_type_hints(some_func)
```

## Summary

**String annotations solve:**

- ✅ Circular import problems
- ✅ Optional dependency issues
- ✅ Self-referential types
- ✅ Future-proof code (PEP 563)

**Neuroglia v0.4.4 supports:**

- ✅ String annotations in DI container
- ✅ Forward references with `get_type_hints()`
- ✅ Parameterized generic types in constructors
- ✅ Type variable substitution (TEntity → User)

**Key takeaway:** String annotations are a Python type system feature that separates type checking (design time) from runtime behavior, enabling more flexible code organization.
