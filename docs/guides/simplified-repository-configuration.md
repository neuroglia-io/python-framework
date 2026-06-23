# Simplified Repository Configuration

## Overview

The Neuroglia framework supports a simplified API for configuring repositories for both Write and Read Models, eliminating the need for verbose custom factory functions.

This guide covers:

- **WriteModel (v0.6.21+)**: Simplified `EventSourcingRepository` configuration with options
- **ReadModel (v0.6.22+)**: Simplified `MongoRepository` configuration with database name
- **ReadModel (v0.6.23+)**: Support for async `MotorRepository` (Motor driver for FastAPI)

## Write Model Simplification (v0.6.21+)

### The Problem (Before v0.6.21)

Previously, configuring `EventSourcingRepository` with custom options (e.g., `DeleteMode.HARD` for GDPR compliance) required writing a **37-line custom factory function**:

```python
# Old approach: 37 lines of boilerplate
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.data.infrastructure.event_sourcing.abstractions import (
    Aggregator, DeleteMode, EventStore
)
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepository, EventSourcingRepositoryOptions
)
from neuroglia.dependency_injection import ServiceProvider
from neuroglia.mediation import Mediator

def configure_eventsourcing_repository(
    builder_: "WebApplicationBuilder",
    entity_type: type,
    key_type: type
) -> "WebApplicationBuilder":
    """Configure EventSourcingRepository with HARD delete mode enabled."""

    # Create options with HARD delete mode
    options = EventSourcingRepositoryOptions[entity_type, key_type](
        delete_mode=DeleteMode.HARD
    )

    # Factory function to create repository with explicit options
    def repository_factory(sp: ServiceProvider) -> EventSourcingRepository[entity_type, key_type]:
        eventstore = sp.get_required_service(EventStore)
        aggregator = sp.get_required_service(Aggregator)
        mediator = sp.get_service(Mediator)
        return EventSourcingRepository[entity_type, key_type](
            eventstore=eventstore,
            aggregator=aggregator,
            mediator=mediator,
            options=options,
        )

    # Register the repository with factory
    builder_.services.add_singleton(
        Repository[entity_type, key_type],
        implementation_factory=repository_factory,
    )
    return builder_

# Usage
DataAccessLayer.WriteModel().configure(
    builder,
    ["domain.entities"],
    configure_eventsourcing_repository,  # Custom factory required
)
```

### Issues with Old Approach

1. **Boilerplate Heavy**: 37 lines for a one-line configuration change
2. **Error Prone**: Manual service resolution from `ServiceProvider`
3. **Inconsistent**: Other components use simpler `.configure(builder, ...)` patterns
4. **Undiscoverable**: Required reading framework source code
5. **Repetitive**: Same boilerplate copied across projects

## The Solution (v0.6.21+)

### Simple Configuration with Default Options

```python
from neuroglia.hosting.configuration.data_access_layer import DataAccessLayer

# Default options (deletion disabled)
DataAccessLayer.WriteModel().configure(
    builder,
    ["domain.entities"]
)
```

### Configuration with Custom Delete Mode

```python
from neuroglia.data.infrastructure.event_sourcing.abstractions import DeleteMode
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepositoryOptions
)
from neuroglia.hosting.configuration.data_access_layer import DataAccessLayer

# Enable HARD delete for GDPR compliance
DataAccessLayer.WriteModel(
    options=EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
).configure(builder, ["domain.entities"])
```

**Reduction: 37 lines → 5 lines (86% less boilerplate)**

### Configuration with Soft Delete

```python
from neuroglia.data.infrastructure.event_sourcing.abstractions import DeleteMode
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepositoryOptions
)

# Enable soft delete with custom method name
DataAccessLayer.WriteModel(
    options=EventSourcingRepositoryOptions(
        delete_mode=DeleteMode.SOFT,
        soft_delete_method_name="mark_as_deleted"
    )
).configure(builder, ["domain.entities"])
```

## Read Model Simplification (v0.6.22+)

### The Problem (Before v0.6.22)

Configuring `MongoRepository` for read models required verbose lambda functions:

```python
# Old approach: Verbose lambda function
DataAccessLayer.ReadModel().configure(
    builder,
    ["integration.models"],
    lambda b, et, kt: MongoRepository.configure(b, et, kt, "database_name")
)
```

### The Solution (v0.6.22+)

#### Synchronous MongoRepository (Default)

```python
from neuroglia.hosting.configuration.data_access_layer import DataAccessLayer

# Simple - just pass database name (uses PyMongo - synchronous)
DataAccessLayer.ReadModel(database_name="myapp").configure(
    builder,
    ["integration.models"]
)
```

#### Async MotorRepository for FastAPI (v0.6.23+)

For async applications using FastAPI, you can use the Motor driver:

```python
from neuroglia.hosting.configuration.data_access_layer import DataAccessLayer

# Async configuration with MotorRepository (uses Motor - async driver)
DataAccessLayer.ReadModel(
    database_name="myapp",
    repository_type='motor'
).configure(
    builder,
    ["integration.models", "application.events.domain"]
)
```

**Repository Type Options:**

| `repository_type` | Driver          | Use Case                   | Lifetime  |
| ----------------- | --------------- | -------------------------- | --------- |
| `'mongo'`         | PyMongo         | Synchronous apps (default) | Singleton |
| `'motor'`         | Motor (AsyncIO) | Async apps (FastAPI, ASGI) | Scoped    |

**Note**: MotorRepository uses `MotorRepository.configure()` under the hood, which:

- Registers `AsyncIOMotorClient` as a singleton (shared connection pool)
- Registers repositories with **SCOPED** lifetime (one per request)
- Supports injection as `Repository[T, K]` in handlers
- Requires `motor` package: `pip install motor`

#### Backwards Compatible Custom Factory

```python
# Custom factory still supported for advanced scenarios
def custom_setup(builder_, entity_type, key_type):
    # Custom configuration logic
    MongoRepository.configure(builder_, entity_type, key_type, "myapp")

DataAccessLayer.ReadModel().configure(
    builder,
    ["integration.models"],
    custom_setup
)
```

## Backwards Compatibility

Both enhancements maintain **full backwards compatibility**. Existing code continues to work without modification:

### WriteModel Backwards Compatibility

```python
# Old custom factory pattern still supported
def custom_setup(builder_, entity_type, key_type):
    # Your custom configuration logic
    EventSourcingRepository.configure(builder_, entity_type, key_type)

DataAccessLayer.WriteModel().configure(
    builder,
    ["domain.entities"],
    custom_setup  # Custom factory still works
)
```

### ReadModel Backwards Compatibility

```python
# Old lambda pattern still supported
DataAccessLayer.ReadModel().configure(
    builder,
    ["integration.models"],
    lambda b, et, kt: MongoRepository.configure(b, et, kt, "myapp")
)
```

## Complete Example

```python
from neuroglia.data.infrastructure.event_sourcing.abstractions import DeleteMode, EventStoreOptions
from neuroglia.data.infrastructure.event_sourcing.event_store.event_store import ESEventStore
from neuroglia.data.infrastructure.event_sourcing.event_sourcing_repository import (
    EventSourcingRepositoryOptions
)
from neuroglia.hosting.configuration.data_access_layer import DataAccessLayer
from neuroglia.hosting.web import WebApplicationBuilder
from neuroglia.mediation.mediator import Mediator
from neuroglia.mapping.mapper import Mapper

def create_app():
    builder = WebApplicationBuilder()

    # Configure core services
    Mapper.configure(builder, ["application"])
    Mediator.configure(builder, ["application"])
    ESEventStore.configure(builder, EventStoreOptions("myapp", "myapp-group"))

    # Configure Write Model with HARD delete enabled (v0.6.21+)
    DataAccessLayer.WriteModel(
        options=EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
    ).configure(builder, ["domain.entities"])

    # Configure Read Model - Synchronous (v0.6.22+)
    DataAccessLayer.ReadModel(database_name="myapp").configure(
        builder,
        ["integration.models"]
    )

    # OR Configure Read Model - Async with Motor (v0.6.23+)
    DataAccessLayer.ReadModel(
        database_name="myapp",
        repository_type='motor'
    ).configure(
        builder,
        ["integration.models"]
    )

    # Add controllers
    builder.add_controllers(["api.controllers"])

    return builder.build()

if __name__ == "__main__":
    app = create_app()
    app.run()
```

## When to Use Custom Factory Pattern

The custom factory pattern is still useful for advanced scenarios:

1. **Per-Entity Configuration**: Different options for different entities
2. **Custom Repository Implementations**: Using your own repository classes
3. **Complex Initialization Logic**: Advanced setup requirements
4. **Migration from Legacy Code**: Gradual refactoring

### WriteModel Advanced Example

```python
def advanced_setup(builder_, entity_type, key_type):
    if entity_type.__name__ == "SensitiveData":
        # Use HARD delete only for sensitive data
        options = EventSourcingRepositoryOptions[entity_type, key_type](
            delete_mode=DeleteMode.HARD
        )
    else:
        # Use SOFT delete for everything else
        options = EventSourcingRepositoryOptions[entity_type, key_type](
            delete_mode=DeleteMode.SOFT
        )

    # Custom registration logic
    # ...

DataAccessLayer.WriteModel().configure(
    builder,
    ["domain.entities"],
    advanced_setup
)
```

### ReadModel Advanced Example

```python
def advanced_setup(builder_, entity_type, key_type):
    # Use different databases based on entity type
    if entity_type.__name__ == "AuditLog":
        database_name = "audit_db"
    else:
        database_name = "main_db"

    MongoRepository.configure(builder_, entity_type, key_type, database_name)

DataAccessLayer.ReadModel().configure(
    builder,
    ["integration.models"],
    advanced_setup
)
```

## API Reference

### `DataAccessLayer.WriteModel`

```python
class WriteModel:
    def __init__(
        self,
        options: Optional[EventSourcingRepositoryOptions] = None
    ):
        """Initialize WriteModel configuration

        Args:
            options: Optional repository options (e.g., delete_mode).
                    If not provided, default options will be used.
        """

    def configure(
        self,
        builder: ApplicationBuilderBase,
        modules: list[str],
        repository_setup: Optional[Callable[[ApplicationBuilderBase, type, type], None]] = None
    ) -> ApplicationBuilderBase:
        """Configure the Write Model DAL

        Args:
            builder: The application builder to configure
            modules: List of module names to scan for aggregate root types
            repository_setup: Optional custom configuration function.
                             If provided, takes precedence over options.
                             If not provided, uses simplified configuration.

        Returns:
            The configured builder
        """
```

### `DataAccessLayer.ReadModel`

```python
class ReadModel:
    def __init__(
        self,
        database_name: Optional[str] = None,
        repository_type: str = 'mongo'
    ):
        """Initialize ReadModel configuration

        Args:
            database_name: Optional database name for MongoDB repositories.
                          If not provided, custom repository_setup must be used.
            repository_type: Type of repository to use ('mongo' or 'motor').
                           - 'mongo': MongoRepository with PyMongo (sync, default)
                           - 'motor': MotorRepository with Motor (async)
        """

    def configure(
        self,
        builder: ApplicationBuilderBase,
        modules: list[str],
        repository_setup: Optional[Callable[[ApplicationBuilderBase, type, type], None]] = None
    ) -> ApplicationBuilderBase:
        """Configure the Read Model DAL

        Args:
            builder: The application builder to configure
            modules: List of module names to scan for queryable types
            repository_setup: Optional custom configuration function.
                             If provided, takes precedence over database_name.
                             If not provided, uses simplified configuration.

        Returns:
            The configured builder

        Raises:
            ValueError: If consumer_group not specified in settings
            ValueError: If neither repository_setup nor database_name is provided
            ValueError: If mongo connection string not found in settings
            ValueError: If invalid repository_type provided (not 'mongo' or 'motor')
        """
```

## Benefits

### WriteModel

| Aspect                    | Before | After                         |
| ------------------------- | ------ | ----------------------------- |
| Lines of code             | 37     | 5                             |
| Custom factory required   | Yes    | No                            |
| Type-safe options         | Manual | Built-in                      |
| Error-prone DI resolution | Yes    | Handled by framework          |
| Discoverable API          | No     | Yes (IDE autocomplete)        |
| Consistency               | No     | Aligned with other components |

### ReadModel

| Aspect                   | Before           | After (v0.6.22+)          | After (v0.6.23+)                   |
| ------------------------ | ---------------- | ------------------------- | ---------------------------------- |
| Configuration style      | Lambda function  | Constructor parameter     | Constructor parameter              |
| Database name visibility | Hidden in lambda | Explicit in constructor   | Explicit in constructor            |
| Async support            | Manual setup     | Manual setup              | Built-in (repository_type='motor') |
| Type safety              | No autocomplete  | Full IDE support          | Full IDE support                   |
| Error handling           | Runtime failures | Early validation          | Early validation                   |
| Consistency              | Unique pattern   | Aligned with WriteModel   | Aligned with WriteModel            |
| Backwards compatibility  | N/A              | Full (lambda still works) | Full (lambda still works)          |

## Related Documentation

- [Event Sourcing Pattern](../patterns/event-sourcing.md)
- [Delete Mode Enhancement](../patterns/event-sourcing.md#deletion-strategies)
- [Repository Pattern](../patterns/repository.md)
- [Getting Started](../getting-started.md)
