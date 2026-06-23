# Type Variable Substitution Fix (v0.4.3)

## Problem Statement

In v0.4.2, we fixed generic type resolution in the DI container, enabling services to depend on parameterized types like `Repository[User, int]`. However, a critical limitation remained: constructor parameters that used **type variables** were not being substituted with concrete types.

### The Failing Pattern

```python
from typing import Generic, TypeVar

TEntity = TypeVar('TEntity')
TKey = TypeVar('TKey')

class CacheRepositoryOptions(Generic[TEntity, TKey]):
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

class AsyncCacheRepository(Generic[TEntity, TKey]):
    def __init__(
        self,
        options: CacheRepositoryOptions[TEntity, TKey],  # ← Type variables!
        pool: CacheClientPool[TEntity, TKey],            # ← Type variables!
    ):
        self.options = options
        self.pool = pool

# Service registration
services = ServiceCollection()

# Register concrete dependencies
services.add_singleton(
    CacheRepositoryOptions[MozartSession, str],
    implementation_factory=lambda _: CacheRepositoryOptions("localhost", 6379)
)

services.add_transient(
    AsyncCacheRepository[MozartSession, str],
    AsyncCacheRepository[MozartSession, str]
)

# This failed in v0.4.2! ❌
provider = services.build()
repo = provider.get_required_service(AsyncCacheRepository[MozartSession, str])
# Error: Failed to resolve service 'CacheRepositoryOptions'
```

### Why It Failed

When the DI container tried to build `AsyncCacheRepository[MozartSession, str]`, it:

1. Inspected the constructor and found `options: CacheRepositoryOptions[TEntity, TKey]`
2. **Used the annotation as-is** - with `TEntity` and `TKey` still as type variables
3. Tried to resolve `CacheRepositoryOptions[TEntity, TKey]` from the service registry
4. **Failed** because the registry had `CacheRepositoryOptions[MozartSession, str]`, not `CacheRepositoryOptions[TEntity, TKey]`

The problem: `TEntity` and `TKey` are **type variables**, not the concrete types `MozartSession` and `str` that were used in the service registration.

## Root Cause

The code already had the machinery for type variable substitution (`TypeExtensions._substitute_generic_arguments()`), but it wasn't being called at the critical point.

In `ServiceProvider._build_service()` (and similarly in `ServiceScope._build_service()`):

```python
# v0.4.2 code (BROKEN for type variables)
for init_arg in service_init_args:
    origin = get_origin(init_arg.annotation)
    args = get_args(init_arg.annotation)

    if origin is not None and args:
        # It's a parameterized generic type (e.g., Repository[User, int])
        # Use the annotation directly - it's already properly parameterized
        # Note: TypeVar substitution is handled by get_generic_arguments() at service level
        dependency_type = init_arg.annotation  # ← WRONG! This still has TEntity, TKey!
    else:
        dependency_type = init_arg.annotation

    dependency = self.get_service(dependency_type)  # ← Fails!
```

The comment claimed "TypeVar substitution is handled by get_generic_arguments()" but this was **misleading**. The `service_generic_args` mapping was being computed but **never applied** to the constructor parameter annotations.

## Solution

Call `TypeExtensions._substitute_generic_arguments()` to replace type variables with concrete types:

```python
# v0.4.3 code (FIXED)
for init_arg in service_init_args:
    origin = get_origin(init_arg.annotation)
    args = get_args(init_arg.annotation)

    if origin is not None and args:
        # It's a parameterized generic type (e.g., Repository[User, int])
        # Check if it contains type variables that need substitution
        # (e.g., CacheRepositoryOptions[TEntity, TKey] -> CacheRepositoryOptions[MozartSession, str])
        dependency_type = TypeExtensions._substitute_generic_arguments(
            init_arg.annotation,
            service_generic_args  # ← Apply the substitution!
        )
    else:
        dependency_type = init_arg.annotation

    dependency = self.get_service(dependency_type)  # ← Now works!
```

### How Substitution Works

When building `AsyncCacheRepository[MozartSession, str]`:

1. **Extract type mapping**: `service_generic_args = {'TEntity': MozartSession, 'TKey': str}`
2. **Process constructor parameter**: `options: CacheRepositoryOptions[TEntity, TKey]`
3. **Substitute type variables**:
   - Input: `CacheRepositoryOptions[TEntity, TKey]`
   - Mapping: `{'TEntity': MozartSession, 'TKey': str}`
   - Output: `CacheRepositoryOptions[MozartSession, str]`
4. **Resolve from registry**: Now finds the registered `CacheRepositoryOptions[MozartSession, str]` ✅

## Changes Made

### Modified Files

1. **`src/neuroglia/dependency_injection/service_provider.py`**
   - **ServiceProvider.\_build_service()** (lines ~487-490): Added `TypeExtensions._substitute_generic_arguments()` call
   - **ServiceScope.\_build_service()** (lines ~335-338): Added `TypeExtensions._substitute_generic_arguments()` call

### Code Changes

Both methods had the same fix applied:

```diff
  for init_arg in service_init_args:
      origin = get_origin(init_arg.annotation)
      args = get_args(init_arg.annotation)

      if origin is not None and args:
-         # It's a parameterized generic type (e.g., Repository[User, int])
-         # Use the annotation directly - it's already properly parameterized
-         # The DI container will match it against registered types
-         # Note: TypeVar substitution is handled by get_generic_arguments() at service level
-         dependency_type = init_arg.annotation
+         # It's a parameterized generic type (e.g., Repository[User, int])
+         # Check if it contains type variables that need substitution
+         # (e.g., CacheRepositoryOptions[TEntity, TKey] -> CacheRepositoryOptions[MozartSession, str])
+         dependency_type = TypeExtensions._substitute_generic_arguments(init_arg.annotation, service_generic_args)
      else:
          dependency_type = init_arg.annotation
```

## Benefits

1. **Type Variable Substitution**: Constructor parameters with type variables now work correctly
2. **Complex Generic Dependencies**: Services can have dependencies that use the same type parameters
3. **Type Safety**: Full type safety maintained throughout dependency injection
4. **No Breaking Changes**: Enhancement enables previously failing patterns without affecting existing code

## Impact

### Before v0.4.3 (Broken)

```python
class AsyncCacheRepository(Generic[TEntity, TKey]):
    def __init__(
        self,
        options: CacheRepositoryOptions[TEntity, TKey],  # ❌ Fails!
    ):
        ...

# Error: Failed to resolve service 'CacheRepositoryOptions'
```

### After v0.4.3 (Fixed)

```python
class AsyncCacheRepository(Generic[TEntity, TKey]):
    def __init__(
        self,
        options: CacheRepositoryOptions[TEntity, TKey],  # ✅ Works!
    ):
        ...

# Successfully resolves CacheRepositoryOptions[MozartSession, str]
```

## Usage Examples

### Simple Type Variable Substitution

```python
from typing import Generic, TypeVar
from neuroglia.dependency_injection import ServiceCollection

TEntity = TypeVar('TEntity')
TKey = TypeVar('TKey')

class Options(Generic[TEntity, TKey]):
    def __init__(self, name: str):
        self.name = name

class Repository(Generic[TEntity, TKey]):
    def __init__(self, options: Options[TEntity, TKey]):  # ← Type variables!
        self.options = options

class User:
    pass

# Registration
services = ServiceCollection()

services.add_singleton(
    Options[User, int],
    implementation_factory=lambda _: Options("user-options")
)

services.add_transient(
    Repository[User, int],
    Repository[User, int]
)

provider = services.build()

# Resolution - now works! ✅
repo = provider.get_required_service(Repository[User, int])
print(repo.options.name)  # "user-options"
```

### Multiple Type Variables

```python
class ComplexService(Generic[TEntity, TKey]):
    def __init__(
        self,
        options: Options[TEntity, TKey],        # ← Substituted!
        cache: Cache[TEntity, TKey],            # ← Substituted!
        validator: Validator[TEntity, TKey],    # ← Substituted!
    ):
        self.options = options
        self.cache = cache
        self.validator = validator

# All dependencies correctly resolved with MozartSession, str
service = provider.get_required_service(ComplexService[MozartSession, str])
```

### Nested Generic Types

```python
class NestedOptions(Generic[TEntity, TKey]):
    def __init__(self, cache_opts: CacheOptions[TEntity, TKey]):
        self.cache_opts = cache_opts

class Service(Generic[TEntity, TKey]):
    def __init__(self, nested: NestedOptions[TEntity, TKey]):  # ← Deep substitution!
        self.nested = nested

# Type variables substituted at all levels
service = provider.get_required_service(Service[User, int])
```

## Testing

### Test Coverage

Added comprehensive test suite in `tests/cases/test_type_variable_substitution.py`:

1. **test_single_type_variable_substitution**: Basic substitution pattern
2. **test_multiple_different_type_substitutions**: Multiple services with different type arguments
3. **test_scoped_lifetime_with_type_variables**: Scoped services with type variables
4. **test_error_when_substituted_type_not_registered**: Error handling
5. **test_complex_nested_type_variable_substitution**: Nested generic types
6. **test_original_async_cache_repository_with_type_vars**: Regression test for original bug

### Running Tests

```bash
# Run type variable substitution tests
poetry run pytest tests/cases/test_type_variable_substitution.py -v

# Run all generic type tests (14 tests total)
poetry run pytest tests/cases/test_generic_type_resolution.py tests/cases/test_type_variable_substitution.py -v
```

All 14 tests pass ✅ (8 from v0.4.2 + 6 new)

## Migration Guide

### No Code Changes Required

This is a bug fix that enables previously failing patterns. Existing code continues to work unchanged.

### Newly Enabled Patterns

If you previously worked around the limitation by using concrete types in constructor parameters, you can now use type variables for better genericity:

**Before (workaround):**

```python
class MozartSessionRepository:
    def __init__(
        self,
        options: CacheRepositoryOptions[MozartSession, str]  # Concrete types
    ):
        ...
```

**After (type variables):**

```python
class AsyncCacheRepository(Generic[TEntity, TKey]):
    def __init__(
        self,
        options: CacheRepositoryOptions[TEntity, TKey]  # Type variables!
    ):
        ...

# More flexible - can be used with any entity type
provider.get_required_service(AsyncCacheRepository[MozartSession, str])
provider.get_required_service(AsyncCacheRepository[User, int])
```

## Related Documentation

- **v0.4.2 Fix**: Generic type resolution (using `get_origin()` and `get_args()`)
- **TypeExtensions**: `_substitute_generic_arguments()` implementation
- **Generic Type Tests**: `tests/cases/test_generic_type_resolution.py`
- **Type Variable Tests**: `tests/cases/test_type_variable_substitution.py`

## Version Information

- **Fixed in**: v0.4.3
- **Release Date**: 2025-10-19
- **Related Issues**: Type variable substitution in generic dependencies
- **Previous Versions**: v0.4.2 (partial fix), v0.4.1 (controller routing), v0.4.0 (initial)
