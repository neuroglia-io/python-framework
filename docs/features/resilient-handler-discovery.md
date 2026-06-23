# 🛡️ Resilient Handler Discovery

The Neuroglia framework now includes **Resilient Handler Discovery** in the Mediator, designed to handle real-world scenarios where packages may have complex dependencies or mixed architectural patterns.

## 🎯 Problem Solved

Previously, `Mediator.configure()` would fail completely if a package's `__init__.py` had any import errors, even when the package contained valid handlers that could be imported individually. This blocked automatic discovery in:

- **Legacy migrations** from UseCase patterns to CQRS handlers
- **Mixed codebases** with varying dependency graphs
- **Optional dependencies** that may not be available in all environments
- **Modular monoliths** with packages containing both new and legacy patterns

## 🏗️ How It Works

The resilient discovery implements a two-stage fallback strategy:

### Stage 1: Package Import (Original Behavior)

```python
# Attempts to import the entire package
Mediator.configure(builder, ['application.runtime_agent.queries'])
```

If successful, handlers are discovered and registered normally.

### Stage 2: Individual Module Fallback

```python
# If package import fails, falls back to:
# 1. Discover individual .py files in the package directory
# 2. Attempt to import each module individually
# 3. Register handlers from successful imports
# 4. Skip modules with import failures

# Example fallback discovery:
# application.runtime_agent.queries.get_worker_query     ✅ SUCCESS
# application.runtime_agent.queries.list_workers_query   ✅ SUCCESS
# application.runtime_agent.queries.broken_module        ❌ SKIPPED
```

## 🚀 Usage Examples

### Basic Usage (Unchanged)

```python
from neuroglia.mediation import Mediator
from neuroglia.hosting import WebApplicationBuilder

builder = WebApplicationBuilder()

# This now works even if some packages have dependency issues
Mediator.configure(builder, [
    'application.commands',           # May have legacy UseCase imports
    'application.queries',            # Clean CQRS handlers
    'application.event_handlers'      # Mixed dependencies
])

app = builder.build()
```

### Mixed Legacy/Modern Codebase

```python
# Your package structure:
# application/
# ├── __init__.py                    # ❌ Imports missing UseCase class
# ├── legacy_use_cases.py           # ❌ Uses old patterns
# └── queries/
#     ├── __init__.py               # ✅ Clean file
#     ├── get_user_query.py         # ✅ Valid QueryHandler
#     └── list_users_query.py       # ✅ Valid QueryHandler

# This now works! Handlers are discovered from individual modules
Mediator.configure(builder, ['application.queries'])
```

### Debugging Discovery Issues

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed logging to see what's discovered vs skipped
Mediator.configure(builder, ['your.package.name'])

# Sample output:
# WARNING: Package import failed for 'application.queries': UseCase not found
# INFO: Attempting fallback: scanning individual modules
# DEBUG: Discovered submodule: application.queries.get_user_query
# DEBUG: Discovered submodule: application.queries.list_users_query
# INFO: Successfully registered 2 handlers from submodule: application.queries.get_user_query
# INFO: Fallback succeeded: registered 4 handlers from individual modules
```

## 🔍 Logging and Diagnostics

The resilient discovery provides comprehensive logging at different levels:

### INFO Level - Summary Information

```
INFO: Successfully registered 3 handlers from package: application.commands
INFO: Fallback succeeded: registered 2 handlers from individual modules in 'application.queries'
INFO: Handler discovery completed: 5 total handlers registered from 2 module specifications
```

### WARNING Level - Import Issues

```
WARNING: Package import failed for 'application.queries': cannot import name 'UseCase'
WARNING: No submodules discovered for package: broken.package
WARNING: Error registering handlers from module application.legacy: circular import
```

### DEBUG Level - Detailed Discovery

```
DEBUG: Attempting to load package: application.queries
DEBUG: Found 3 potential submodules in application.queries
DEBUG: Discovered submodule: application.queries.get_user_query
DEBUG: Successfully registered QueryHandler: GetUserQueryHandler from application.queries.get_user_query
DEBUG: Skipping submodule 'application.queries.broken_module': ImportError
```

## 🧪 Best Practices

### 1. Incremental Migration Strategy

```python
# Start with clean packages, gradually add legacy ones
modules = [
    'application.commands.user',      # ✅ Clean CQRS handlers
    'application.queries.user',       # ✅ Clean CQRS handlers
    'application.legacy.commands',    # ⚠️  Mixed patterns - will use fallback
]

Mediator.configure(builder, modules)
```

### 2. Package Organization

```python
# Recommended: Separate clean handlers from legacy code
application/
├── handlers/              # ✅ Clean CQRS handlers only
│   ├── commands/
│   └── queries/
└── legacy/               # ⚠️  Old patterns with complex dependencies
    ├── use_cases/
    └── services/
```

### 3. Gradual Cleanup

```python
# As you migrate legacy code, packages will automatically
# switch from fallback discovery to normal discovery
# No changes needed in configuration!

# Before migration (uses fallback):
# WARNING: Package import failed, using fallback discovery

# After migration (normal discovery):
# INFO: Successfully registered 5 handlers from package: application.commands
```

## 🔧 Advanced Configuration

### Individual Module Specification

You can also specify individual modules instead of packages:

```python
Mediator.configure(builder, [
    'application.commands.create_user_command',
    'application.commands.update_user_command',
    'application.queries.get_user_query'
])
```

### Error Handling

```python
try:
    Mediator.configure(builder, ['your.package'])
except Exception as e:
    # Resilient discovery should prevent most exceptions,
    # but you can still catch unexpected errors
    logger.error(f"Handler discovery failed: {e}")
```

## 🚨 Migration from Manual Registration

### Before (Manual Workaround)

```python
# Old approach - manual registration due to import failures
try:
    from application.queries.get_user_query import GetUserQueryHandler
    from application.queries.list_users_query import ListUsersQueryHandler

    builder.services.add_scoped(GetUserQueryHandler)
    builder.services.add_scoped(ListUsersQueryHandler)
    log.debug("Manually registered query handlers")
except ImportError as e:
    log.warning(f"Could not register handlers: {e}")
```

### After (Automatic Discovery)

```python
# New approach - automatic resilient discovery
Mediator.configure(builder, ['application.queries'])
# That's it! No manual registration needed
```

## ⚠️ Important Notes

### Backward Compatibility

- **100% backward compatible** - existing code continues to work unchanged
- **No breaking changes** - all existing `Mediator.configure()` calls work as before
- **Enhanced behavior** - only adds fallback capability when needed

### Performance Considerations

- **Package discovery first** - normal path is unchanged and just as fast
- **Fallback only when needed** - individual module discovery only triggers on import failures
- **Directory scanning** - minimal filesystem operations, cached results
- **Logging overhead** - debug logging can be disabled in production

### Limitations

- **Directory structure dependent** - requires standard Python package layout
- **Search paths** - looks in `src/`, `./`, and `app/` directories
- **File system access** - requires read permissions to package directories

## 🎉 Benefits

### For Developers

- **Reduced friction** during legacy code migration
- **Automatic discovery** without manual registration
- **Clear diagnostics** about what was discovered vs skipped
- **Incremental adoption** of CQRS patterns

### For Projects

- **Mixed architectural patterns** supported
- **Gradual modernization** without breaking changes
- **Complex dependency graphs** handled gracefully
- **Better development experience** with detailed logging

### For Teams

- **Parallel development** - teams can work on different parts without breaking discovery
- **Easier onboarding** - less manual configuration needed
- **Reduced support burden** - fewer "handler not found" issues

The resilient discovery makes the Neuroglia framework significantly more robust for real-world codebases with complex dependencies and mixed architectural patterns! 🎯
