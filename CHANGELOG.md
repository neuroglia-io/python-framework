# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.3] - 2026-05-29

### Fixed

- **CloudEventPublisher**: Replace blocking `httpx.Client()` with `httpx.AsyncClient()` in `on_publish_cloud_event_async` to avoid blocking the event loop during HTTP POST calls

## [0.9.0] - 2026-01-19

### Added

- **Observability Module Enhancements**: Comprehensive observability improvements (CR-1 through CR-4)

  - **Structlog Integration (`neuroglia.observability.structlog_integration`)**: Optional structured logging with OpenTelemetry trace correlation

    - `configure_structlog()`: Set up structured logging with JSON/console output and OTel trace context injection
    - `get_structlog_logger()`: Get logger with fallback to standard logging when structlog unavailable
    - `bind_contextvars()` / `clear_contextvars()`: Request-scoped context management
    - Feature detection: graceful fallback when `structlog` package not installed

  - **Pluggable Health Check Providers (`neuroglia.observability.health_checks`)**: Abstract provider pattern for dependency health monitoring

    - `HealthCheckProvider`: Abstract base class for custom health checks
    - `HealthCheckResult`: Dataclass with status (healthy/unhealthy/degraded), message, and latency
    - Built-in providers: `MongoDBHealthCheck`, `RedisHealthCheck`, `Neo4jHealthCheck`, `QdrantHealthCheck`, `HttpServiceHealthCheck`
    - All providers use lazy imports to avoid hard dependencies
    - Integration with `/health` and `/ready` endpoints via `Observability.configure(health_check_providers=[...])`

  - **Metrics Helper Decorators (`neuroglia.observability.decorators`)**: Convenience decorators for automatic metrics recording

    - `@track_operation(metric_name)`: Count operations with success/error status labels
    - `@track_latency(metric_name)`: Record operation duration to histogram
    - `@track_operation_and_latency()`: Combined decorator for both count and latency
    - Supports both sync and async functions

  - **Service Info Gauge**: Automatic service metadata export at startup
    - Creates `service.info` gauge with labels: `service.name`, `service.version`, `deployment.environment`
    - Enabled by default via `otel_service_info_gauge` setting
    - Common Prometheus pattern for service discovery

### Changed

- **Observability.configure()**: Added `health_check_providers` parameter for pluggable dependency monitoring
- **ObservabilitySettingsMixin**: Added `otel_service_info_gauge` setting for service info gauge control
- **StandardEndpoints**: Health and readiness endpoints now use registered health check providers

## [0.8.0] - 2026-01-18

### Added

- **Agent Module (`neuroglia.data.agent`)**: Base classes and value objects for Agent aggregates

  - `BaseAgentState`: Base state class for all agent aggregates with identity, ownership, team membership, knowledge scopes, capabilities, and delegation tracking
  - `TeamMembership`: Value object for team membership with role and granted capabilities
  - `KnowledgeScope`: Value object for knowledge namespace access with access levels
  - `AgentCapability`: Value object for agent capabilities with tool mappings

- **Agent Domain Events**: Comprehensive event coverage for agent lifecycle

  - Lifecycle events: `AgentCreatedDomainEvent`, `AgentStatusChangedDomainEvent`
  - Team events: `AgentJoinedTeamDomainEvent`, `AgentLeftTeamDomainEvent`, `AgentTeamRoleChangedDomainEvent`
  - Knowledge events: `KnowledgeScopeGrantedDomainEvent`, `KnowledgeScopeRevokedDomainEvent`, `PrimaryNamespaceSetDomainEvent`
  - Capability events: `CapabilityAddedDomainEvent`, `CapabilityRemovedDomainEvent`
  - Delegation events: `DelegationRequestedDomainEvent`, `DelegationCompletedDomainEvent`
  - Session events: `SessionStartedDomainEvent`, `SessionEndedDomainEvent`
  - Focus events: `FocusSetDomainEvent`, `FocusClearedDomainEvent`

- **A2A Protocol Module (`neuroglia.a2a`)**: Agent-to-Agent communication types

  - `AgentIdentity`: Identity for A2A routing with agent_id, agent_type, owner_id, team_id
  - `TaskRequest`: Delegation request with capability-based routing, context sharing, priority, timeout
  - `TaskResponse`: Response with execution metadata (iterations, tools_called, duration_ms)
  - `TaskPriority`: Priority enum (LOW, NORMAL, HIGH, CRITICAL)
  - `TaskStatus`: Status enum (PENDING, QUEUED, RUNNING, WAITING_DELEGATION, COMPLETED, FAILED, CANCELLED)

- **Conversation Building Blocks (`neuroglia.data.conversation`)**: Universal value objects for LLM conversations
  - `Message`: Universal message with factory methods and multi-provider format converters (OpenAI, Anthropic, Gemini, Ollama)
  - `MessageRole`: Role enum (SYSTEM, USER, ASSISTANT, TOOL)
  - `MessageStatus`: Status enum (PENDING, STREAMING, COMPLETED, ERROR)
  - `ToolCall`: Tool invocation request with multi-provider format converters
  - `ToolResult`: Tool execution result with success/failure state
  - `ExecutionContext`: ReAct loop state for suspend/resume with message snapshots
  - `LlmMessageSnapshot`: Lightweight message snapshot for execution state preservation
  - `Session`: Session lifecycle value object with duration tracking

### Changed

- Version bump from 0.7.10 to 0.8.0 to reflect new Agent module feature addition

## [0.7.10] - 2025-01-03

### Changed

- **Dependency Upgrades for MCP SDK Compatibility**:
  - Upgraded `uvicorn` from 0.32.1 to 0.35.0
  - Upgraded `pydantic[email]` from 2.10.3 to 2.11.0 (includes pydantic-core 2.33.0)

## [0.7.9] - 2025-12-28

### Fixed

- **JSON Serializer Nested Dataclass Deserialization**: Fixed critical bug where `dict[str, Any]` fields in nested dataclasses lost their deeply nested values during deserialization

  - **Issue**: When deserializing lists of dataclasses (e.g., `list[ConversationItem]`) where items contain `dict[str, Any]` fields (e.g., `widget_config`), the nested dict values were dropped or partially populated
  - **Root Cause**: `_deserialize_nested()` list-of-dataclasses code path (lines 769-786) used `field.type` directly instead of `get_type_hints()` to resolve type annotations
  - **Impact**: Types like `dict[str, Any]` were not properly resolved, causing the serializer to skip proper deserialization of nested structures
  - **Fix**:
    - Added `get_type_hints()` call to properly resolve type annotations in list deserialization
    - Added handling for missing optional fields and default values (matching existing direct dataclass path)
    - Fallback to `field.type` if `get_type_hints()` fails (backward compatible)
  - **Affected Use Cases**:
    - MongoDB `MotorRepository` with aggregates containing lists of nested dataclasses with `dict[str, Any]` fields
    - Any JSON serialization/deserialization of nested dataclass structures with arbitrary dict fields
  - **Tests**: `tests/cases/test_nested_dict_in_dataclass_list.py` (6 comprehensive tests)
  - **Backward Compatible**: 100% - existing code paths unaffected, fix only improves handling of previously broken cases

- **Pydantic BaseModel Deserialization**: Fixed issue where Pydantic v2 models were deserialized without proper initialization
  - **Issue**: Deserializer created Pydantic model instances using `object.__new__()` and direct dictionary assignment, bypassing Pydantic's initialization logic
  - **Impact**: Models were missing internal attributes (e.g., `__pydantic_private__`, `__pydantic_fields_set__`), causing runtime errors when accessing them
  - **Fix**:
    - Added `_is_pydantic_model()` detection using duck typing (no hard dependency)
    - Updated deserializer to use `model.model_validate()` for Pydantic models, ensuring full initialization
  - **Tests**: `tests/cases/test_pydantic_model_deserialization.py`

## [0.7.8] - 2025-12-07

### Improved

- **JSON Serializer Hardening**: Preventive improvements to type inference heuristics

  - **DateTime Detection (`_is_datetime_string`)**:

    - Now requires 'T' or space separator to distinguish datetime from date-only strings
    - Date-only strings like '2025-12-15' are NO LONGER automatically converted to datetime
    - Prevents unexpected type conversions when the intended type is a plain date string
    - Added `TypeError` to exception handling for non-string inputs
    - Added comprehensive docstring explaining behavior and rationale

  - **Enum Case-Insensitive Matching**:

    - Unified matching logic across `_basic_enum_detection` and typed enum deserialization
    - Implemented priority-based matching:
      1. Exact match on enum member value (highest priority)
      2. Exact match on enum member name
      3. Case-insensitive match on value (lowercase comparison)
      4. Case-insensitive match on name (uppercase comparison for CONSTANT_CASE convention)
    - Consistent behavior whether using TypeRegistry or fallback detection
    - Added comprehensive docstrings with matching priority documentation

  - **Tests**: `tests/cases/test_json_serializer_hardening.py` (46 comprehensive tests)

    - DateTime heuristic validation (18 tests)
    - Enum case-insensitive matching (9 tests)
    - Basic enum detection (6 tests)
    - Edge cases and regressions (8 tests)
    - Backward compatibility (5 tests)

  - **Impact**: More predictable and consistent type inference behavior across serialization/deserialization

## [0.7.7] - 2025-12-07

### Fixed

- **JSON Serializer Decimal Heuristic Bug**: Fixed `decimal.InvalidOperation` errors when deserializing nested dictionaries
  - **Issue**: The `_infer_and_deserialize` method's decimal heuristic caused `InvalidOperation` errors when field paths contained monetary keywords (e.g., `input_schema_properties_price_type`)
  - **Root Cause 1**: The heuristic used substring matching (`"price" in field_name`) which triggered on nested paths like `input_schema_properties_price_type`
  - **Root Cause 2**: Missing `InvalidOperation` in exception handler - only `ValueError` and `TypeError` were caught
  - **Root Cause 3**: When `expected_type` was `typing.Any`, `_deserialize_nested` incorrectly called `_deserialize_object` which created a corrupted `Any` instance
  - **Solution**:
    - Changed to terminal-only matching: only fields ENDING with monetary patterns trigger decimal conversion
    - Added `_is_monetary_field()` helper that checks if the last underscore-separated part is a monetary pattern
    - Added `_looks_like_decimal()` regex validation to pre-check if string is a valid decimal format
    - Added `InvalidOperation` to exception handler
    - Added special handling for `typing.Any` in `_deserialize_nested` to properly recurse through containers
  - **Monetary Patterns**: `price`, `cost`, `amount`, `total`, `fee`, `balance`, `rate`, `tax`
  - **Tests**: `tests/cases/test_json_serializer_decimal_heuristic.py` (42 comprehensive tests)
  - **Impact**: OpenAPI schemas, JSON Schema definitions, and other nested structures with monetary keywords now deserialize correctly

## [0.7.6] - 2025-12-06

### Fixed

- **ReadModelReconciliator Race Condition**: Fixed critical race condition in domain event projection

  - **Issue**: When an aggregate emits multiple domain events (e.g., `ToolGroupCreatedEvent` followed by `SelectorAddedEvent`), projection handlers could run concurrently, causing the second handler to fail with "document not found" errors
  - **Root Cause**: Events were dispatched via `asyncio.create_task()` without awaiting completion, allowing subsequent events to be processed before prior events finished
  - **Solution**: Added `AggregateEventQueue` that ensures events from the same aggregate are processed sequentially while maintaining parallelism across different aggregates
  - **New Options**:
    - `ReadModelConciliationOptions.sequential_processing` (default: `True`) - Enable/disable sequential event processing per aggregate
    - Sequential mode groups events by aggregate ID and processes them in order
    - Parallel mode (legacy behavior) available via `sequential_processing=False`
  - **Tests**: `tests/cases/test_read_model_reconciliator_sequential_processing.py` (15 comprehensive tests)
  - **Impact**: Read model projections now correctly handle aggregates that emit multiple events in a single operation

- **Aggregator.\_pending_events Initialization**: Fixed critical bug in aggregate reconstitution
  - `Aggregator.aggregate()` uses `object.__new__()` which bypasses `__init__`
  - This left `_pending_events` attribute uninitialized, causing `AttributeError` when reconstituted aggregates tried to register new domain events
  - Added explicit `aggregate._pending_events = list()` initialization in `Aggregator.aggregate()` after `object.__new__()` call
  - Added comprehensive docstring explaining the `__new__()` bypass pattern and rationale
  - Tests: `tests/cases/test_aggregator_pending_events_initialization.py` (7 comprehensive tests)
  - Impact: Event-sourced aggregates can now properly register new domain events after reconstitution from event streams

## [0.7.5] - 2025-12-04

### Added

- **MotorRepository Enhanced Query Methods**: Added comprehensive querying capabilities to `MotorRepository`
  - **`find_async` enhancements**: Added optional parameters for `sort`, `limit`, `skip`, and `projection`
    - Enables sorting: `sort=[("name", 1), ("created_at", -1)]`
    - Enables pagination: `skip=20, limit=10`
    - Enables field projection: `projection={"name": 1, "email": 1}`
    - Maintains full backward compatibility (all parameters optional)
  - **`count_async` method**: Count documents matching filter (useful for pagination metadata)
    - `count_async({"is_active": True})` - count with filter
    - `count_async()` - count all documents
  - **`exists_async` method**: Efficient existence check using `limit=1`
    - `exists_async({"email": "user@example.com"})` - check if any document matches
  - **Impact**: Eliminates need to access internal `collection` directly for common query patterns

### Fixed

- **EventSourcingRepository.get_async**: Fixed handling of non-existent streams

  - Previously raised exceptions when attempting to read from non-existent streams
  - Now correctly returns `None` following repository pattern contract
  - Added proper exception handling and empty event list checks
  - Tests: `tests/cases/test_event_sourcing_repository_get_async.py`

- **Queryable Type Propagation**: Fixed type information loss during queryable chaining operations
  - **Issue**: `AttributeError: 'MotorQuery' object has no attribute '__orig_class__'` when chaining operations like `.where().order_by()`
  - **Root Cause**: `__orig_class__` is only set at initial instantiation; intermediate queries created by chaining lost type information
  - **Solution**: Store `element_type` explicitly in `Queryable`, propagate through `create_query()`, check `_element_type` before `__orig_class__`
  - **Impact**: Fluent query chaining now works correctly across all operations

## [0.7.4] - 2025-12-04

### Fixed

- **Queryable Lambda Extraction**: Fixed lambda extraction failure in multi-line method chains

  - **Issue**: `_get_lambda_source_code()` failed when lambdas were used in multi-line method chains (backslash continuation or implicit continuation)
  - **Root Cause**: `inspect.getsourcelines()` returns multiple lines for continuation patterns, and lines starting with `.` are invalid Python syntax
  - **Solution**:
    - Use only the first line containing the lambda (sufficient for extraction)
    - Strip trailing backslashes from continuation lines
    - Prepend dummy identifier `_` to lines starting with `.` to make them parseable
    - Adjust column offsets accordingly
  - **Impact**: Common repository patterns now work correctly:

    ```python
    queryable = await self.query_async()
    return await queryable \
        .where(lambda x: x.is_enabled == True) \
        .order_by(lambda x: x.name) \
        .to_list_async()
    ```

  - **Scope**: Fixed in `where()`, `order_by()`, `order_by_descending()`, `select()`, `first_or_default()`, and `last_or_default()` methods
  - **Backward Compatibility**: Fully backward compatible - all single-line lambda usage continues to work unchanged

### Changed

- **DataAccessLayer.WriteModel**: Simplified API with automatic event store configuration

  - New simplified parameters: `database_name`, `consumer_group`, `delete_mode`
  - Internally calls `ESEventStore.configure()` when `database_name` is provided
  - Eliminates need for separate `ESEventStore.configure()` call in application startup
  - Backwards compatible: legacy `options` parameter still supported
  - Example:

    ```python
    # Before (required separate ESEventStore.configure call):
    ESEventStore.configure(builder, EventStoreOptions("myapp", "myapp_group"))
    DataAccessLayer.WriteModel(
        options=EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)
    ).configure(builder, ["domain.entities"])

    # After (simplified, single call):
    DataAccessLayer.WriteModel(
        database_name="myapp",
        consumer_group="myapp_group",
        delete_mode=DeleteMode.HARD
    ).configure(builder, ["domain.entities"])
    ```

## [0.7.3] - 2025-12-04

### Changed

- **DataAccessLayer.ReadModel**: Refactored configuration for improved maintainability
  - Decomposed large `configure()` method into 7 focused, single-responsibility methods
  - Extracted reconciliation setup, mongo/motor configuration, and custom repository mappings
  - Improved code readability and testability
  - No behavior changes - fully backward compatible

### Fixed

- **MotorQuery**: Added missing async query execution methods

  - Implemented `to_list_async()` for executing queries and returning list of entities
  - Implemented `first_or_default_async()` for retrieving first element or None
  - Both methods properly deserialize MongoDB documents to entity instances using JsonSerializer
  - Fixes critical API gap where documentation referenced methods that didn't exist
  - Prevents AttributeError when following documentation examples

- **DataAccessLayer.ReadModel**: Custom repository mappings now use factory functions
  - Prevents DI container from trying to auto-resolve generic type parameters as services
  - Fixes "Failed to resolve service 'str'" error when registering custom repositories
  - Factory functions properly instantiate repositories with all required dependencies
  - Extracts entity type dynamically from implementation's base classes

## [0.7.2] - 2025-12-04

### Added

- **MotorRepository**: Queryable support with LINQ-style fluent API

  - `MotorRepository` now extends `QueryableRepository[TEntity, TKey]`
  - New `query_async()` method returns `Queryable[TEntity]` for fluent queries
  - `MotorQuery`, `MotorQueryProvider`, `MotorQueryBuilder` for async query execution
  - Python lambda expressions translated to MongoDB `$where` JavaScript queries
  - Support for: `where()`, `order_by()`, `order_by_descending()`, `skip()`, `take()`, `select()`
  - Documentation: `docs/guides/motor-queryable-repositories.md`

- **DataAccessLayer.ReadModel**: Custom repository mappings
  - New `repository_mappings` parameter for registering domain repository implementations
  - Maps abstract repository interfaces to concrete implementations (e.g., `TaskRepository` → `MotorTaskRepository`)
  - Eliminates manual DI registration boilerplate
  - Works seamlessly with both `repository_type='mongo'` and `repository_type='motor'`
  - Example: `repository_mappings={TaskRepository: MotorTaskRepository}`
  - Documentation: `docs/guides/custom-repository-mappings.md`

### Changed

- **DataAccessLayer**: Motor configuration now registers `QueryableRepository[T, K]` interface
  - Enables dependency injection of `QueryableRepository` for repositories with queryable support
  - Registers both `Repository[T, K]` and `QueryableRepository[T, K]` for motor repositories
  - Backward compatible - existing `Repository[T, K]` injections continue to work

## [0.7.1] - 2025-12-02

### Fixed

- **CRITICAL**: Fixed `ESEventStore._ensure_client()` kurrentdbclient compatibility
  - `AsyncKurrentDBClient` constructor is not awaitable (returns client directly)
  - Added required `await client.connect()` call to establish connection
  - Fixed `TypeError: object AsyncKurrentDBClient can't be used in 'await' expression`
  - Fixed `AttributeError: 'AsyncKurrentDBClient' object has no attribute '_connection'`
  - **Impact**: v0.7.0 was completely broken for event sourcing - this patch fixes it

## [0.7.0] - 2025-12-02

### Changed

- **BREAKING**: Migrated from `esdbclient` to `kurrentdbclient` 1.1.2

  - EventStoreDB/KurrentDB official Python client replacement
  - Updated all imports: `esdbclient` → `kurrentdbclient`
  - `AsyncioEventStoreDBClient` → `AsyncKurrentDBClient`
  - `AlreadyExists` → `AlreadyExistsError` (aliased for compatibility)
  - Bug fix: `AsyncPersistentSubscription.init()` now propagates `subscription_id` correctly
  - ACK/NACK operations now work reliably without redelivery loops

- **Dependencies**: Pinned all dependency versions for production stability
  - All core dependencies now use exact versions (removed `^` ranges)
  - `grpcio`: 1.76.0 (upgraded from 1.68.x, required by kurrentdbclient)
  - `protobuf`: 6.33.1 (upgraded from 5.x, kurrentdbclient/OpenTelemetry compatibility)
  - OpenTelemetry stack: 1.38.0/0.59b0 (upgraded for protobuf 6.x support)
  - `pymongo`: 4.15.4 (CVE-2024-5629 security fix)
  - `motor`: 3.7.0 (async MongoDB driver update)
  - `h11`: 0.16.0 (CVE-2025-43859 security fix, CVSS 9.3 Critical)

### Removed

- **Runtime Patches**: Removed `patches.py` module (no longer needed)
  - kurrentdbclient 1.1.2 includes upstream fix for subscription_id propagation
  - Eliminated monkey-patching of `AsyncPersistentSubscription.init()`
  - Cleaner codebase with no runtime modifications to third-party libraries

### Fixed

- **Event Sourcing**: Persistent subscription ACK delivery now reliable
  - Fixed 30-second event redelivery loop issue
  - Checkpoints now advance correctly in EventStoreDB/KurrentDB
  - Events no longer parked incorrectly after maxRetryCount attempts
  - Read models process events exactly once (idempotency restored)

### Security

- **Critical**: Fixed CVE-2025-43859 in h11 (CVSS 9.3)
- **Medium**: Fixed CVE-2024-5629 in pymongo (CVSS 4.7)
- **Medium**: Fixed CVE-2024-5569 in zipp (CVSS 6.9) - transitive dependency
- **Medium**: Fixed CVE-2024-39689 in certifi (CVSS 6.1) - transitive dependency
- **Medium**: Fixed CVE-2024-3651 in idna (CVSS 6.2) - transitive dependency
- **Medium**: Fixed CVE-2023-29483 in dnspython (CVSS 5.9) - transitive dependency

### Added

- **Testing**: Comprehensive test suite for kurrentdbclient subscription_id bug
  - Portable test demonstrating the historical bug and its fix
  - Source code inspection tests comparing sync vs async implementations
  - Documentation in `tests/cases/KURRENTDB_BUG_REPORT.md`

## [0.6.23] - 2025-12-02

### Added

- **DataAccessLayer.ReadModel**: Async MotorRepository support

  - **Enhancement**: Support `repository_type='motor'` parameter for async Motor driver in `ReadModel()` constructor
  - **New Parameter**: `repository_type: str = 'mongo'` (options: `'mongo'` or `'motor'`)
  - **Motor Configuration**: Uses `MotorRepository.configure()` static method for proper async setup
  - **Before**: Manual MotorRepository configuration required lambda function

    ```python
    DataAccessLayer.ReadModel().configure(
        builder,
        ["integration.models"],
        lambda b, et, kt: MotorRepository.configure(b, et, kt, "database_name")
    )
    ```

  - **After**: Simple configuration with `repository_type='motor'`

    ```python
    DataAccessLayer.ReadModel(
        database_name="myapp",
        repository_type='motor'
    ).configure(builder, ["integration.models"])
    ```

  - **Repository Types**:
    - `'mongo'` (default): MongoRepository with PyMongo (synchronous, singleton lifetime)
    - `'motor'`: MotorRepository with Motor/AsyncIOMotorClient (async, scoped lifetime)
  - **Benefits**:
    - Native async support for FastAPI and ASGI applications
    - Proper connection pooling with AsyncIOMotorClient
    - Scoped repository lifetime (one per request for async context)
    - Consistent simplified API across sync and async scenarios
  - **Backwards Compatible**: Lambda pattern and MongoRepository (default) still supported
  - **Use Cases**:
    - Sync apps: `DataAccessLayer.ReadModel(database_name="myapp").configure(...)`
    - Async apps: `DataAccessLayer.ReadModel(database_name="myapp", repository_type='motor').configure(...)`
    - Custom: `DataAccessLayer.ReadModel().configure(..., custom_setup)`
  - **Testing**: 3 new tests for Motor configuration (total 31 DataAccessLayer tests)
  - **Documentation**: Updated `docs/guides/simplified-repository-configuration.md` with Motor examples

## [0.6.22] - 2025-12-02

### Added

- **DataAccessLayer.ReadModel**: Simplified repository configuration API
  - **Enhancement**: Support `database_name` directly in `ReadModel()` constructor for MongoDB repositories
  - **Before**: Required lambda function: `lambda b, et, kt: MongoRepository.configure(b, et, kt, "database_name")`
  - **After**: Simple configuration: `DataAccessLayer.ReadModel(database_name="myapp").configure(builder, ["integration.models"])`
  - **Benefits**:
    - Eliminates verbose lambda functions for simple configurations
    - Type-safe database name configuration
    - Framework handles MongoDB connection and repository setup automatically
    - Consistent with WriteModel simplified API
    - IDE autocomplete support
  - **Backwards Compatible**: Custom factory pattern still supported via optional `repository_setup` parameter
  - **Use Cases**:
    - Simple: `DataAccessLayer.ReadModel(database_name="myapp").configure(builder, ["integration.models"])`
    - Custom: `DataAccessLayer.ReadModel().configure(builder, ["integration.models"], custom_setup)`
  - **Testing**: 10 comprehensive tests added (all passing)
  - **Total Tests**: Now 28 tests for DataAccessLayer (18 WriteModel + 10 ReadModel)

## [0.6.21] - 2025-12-02

### Added

- **DataAccessLayer.WriteModel**: Simplified repository configuration API
  - **Enhancement**: Support `EventSourcingRepositoryOptions` directly in `WriteModel()` constructor
  - **Before**: Required 37-line custom factory function to configure delete mode
  - **After**: Single-line configuration: `DataAccessLayer.WriteModel(options=EventSourcingRepositoryOptions(delete_mode=DeleteMode.HARD)).configure(builder, ["domain.entities"])`
  - **Benefits**:
    - 86% reduction in boilerplate code (37 lines → 5 lines)
    - Type-safe options configuration
    - Framework handles service resolution automatically
    - Consistent with other Neuroglia component patterns
    - IDE autocomplete support
  - **Backwards Compatible**: Custom factory pattern still supported via optional `repository_setup` parameter
  - **Use Cases**:
    - Default configuration: `DataAccessLayer.WriteModel().configure(builder, ["domain"])`
    - With delete mode: `DataAccessLayer.WriteModel(options=...).configure(builder, ["domain"])`
    - Custom factory: `DataAccessLayer.WriteModel().configure(builder, ["domain"], custom_setup)`
  - **Documentation**: See `docs/guides/simplified-repository-configuration.md`
  - **Type Safety**: Added `type: ignore` comments for runtime generic type parameters

## [0.6.20] - 2025-12-02

### Fixed

- **CRITICAL**: ESEventStore now uses `ack_id` instead of `id` for persistent subscription ACKs with resolved links
  - **Bug**: When `resolveLinktos=true` (e.g., category streams `$ce-*`), ACKs were sent with resolved event ID instead of link event ID
  - **Impact**: EventStoreDB ignored ACKs, causing events to be redelivered after `messageTimeout`
  - **Root Cause**: Code used `e.id` (resolved event ID) instead of `e.ack_id` (link event ID required for ACK)
  - **Fix**: Now uses `getattr(e, 'ack_id', e.id)` for all ACK/NACK operations in `_consume_events_async()`
  - **Affected**: All persistent subscriptions with `resolveLinktos=true` (category streams, projections)
  - **Lines Fixed**: 256 (tombstone ACK), 266 (system event ACK), 277 (decode failure ACK), 284 (normal event ACK/NACK delegates)
  - **Tests**: Updated all test mocks to include `ack_id` attribute
  - **Verification**: All 18 EventStore tests passing

## [0.6.19] - 2025-12-02

### Fixed

- **CRITICAL**: Workaround for esdbclient AsyncPersistentSubscription bug causing silent ACK failures
  - **Bug**: esdbclient v1.1.7 `AsyncPersistentSubscription.init()` doesn't propagate `subscription_id` to `_read_reqs`
  - **Impact**: Persistent subscription ACKs fail silently, causing events to be redelivered every `message_timeout`
  - **Symptoms**:
    - Events redelivered despite successful processing
    - Checkpoint never advances in EventStoreDB
    - Events eventually parked after `maxRetryCount` attempts
    - Read models may process same event multiple times
  - **Root Cause**: Async version missing `self._read_reqs.subscription_id = subscription_id.encode()` (present in sync version)
  - **Workaround**: Added runtime monkey-patch in `src/neuroglia/data/infrastructure/event_sourcing/patches.py`
  - **Patch Function**: `patch_esdbclient_async_subscription_id()` - must be called before EventStore initialization
  - **Integration**: Patch auto-applied when importing `neuroglia.data.infrastructure.event_sourcing.event_store`
  - **Upstream**: Bug report to be filed with esdbclient/kurrentdbclient maintainers
  - **Affected Versions**: esdbclient 1.1.7 (and likely all versions with async support)
  - **Documentation**: See `notes/ESDBCLIENT_ASYNC_SUBSCRIPTION_BUG.md` for detailed analysis
  - **Verification**: Check EventStoreDB admin UI - `lastCheckpointedEventPosition` should now advance

## [0.6.18] - 2025-12-01

### Fixed

- **ESEventStore**: Added missing `await` statements for read_stream methods
  - Fixed `client.read_stream()` call in `get_async()` (line 104) - first read for stream metadata
  - Fixed `client.read_stream()` call in `get_async()` (line 112) - second read for stream metadata
  - Fixed `client.read_stream()` call in `read_async()` (line 135) - main stream read operation
  - **Impact**: `read_stream()` is an async coroutine that must be awaited
  - **Symptoms Fixed**: Prevents potential runtime issues with unawaited coroutines
  - **Root Cause**: Oversight in v0.6.16 async migration - read operations were called without await
  - **Files**: `neuroglia/data/infrastructure/event_sourcing/event_store/event_store.py`
  - **Verification**: All 18 EventStore tests passing

## [0.6.17] - 2025-12-01

### Fixed

- **ESEventStore**: Added missing `await` statements for subscription methods
  - Fixed `client.subscribe_to_stream()` call in `observe_async()` (line 158) - was not awaited
  - Fixed `client.read_subscription_to_stream()` call in `observe_async()` (line 173) - was not awaited
  - **Impact**: Both methods are async coroutines in `AsyncioEventStoreDBClient` that must be awaited
  - **Symptoms Fixed**: Eliminates "coroutine was never awaited" runtime warnings
  - **Root Cause**: Oversight in v0.6.16 async migration - subscription creation methods were called without await
  - **Files**: `neuroglia/data/infrastructure/event_sourcing/event_store/event_store.py`
  - **Tests**: Updated mock in `test_persistent_subscription_ack_delivery.py` to use `AsyncMock`
  - **Verification**: All 18 EventStore tests passing

## [0.6.16] - 2025-12-01

### Changed

- **MAJOR**: Migrated ESEventStore to AsyncioEventStoreDBClient for proper async/await support

  - **Motivation**: Eliminates threading workaround and ACK delivery issues by using native async API
  - **Breaking Change**: EventStoreDBClient → AsyncioEventStoreDBClient (only affects direct instantiation)
  - **Impact on Client Code**:
    - ✅ **NO BREAKING CHANGES** for code using `ESEventStore.configure()` (recommended pattern)
    - ⚠️ **Breaking only** for direct `ESEventStore()` instantiation (uncommon pattern)
  - **Benefits**:
    - Native async iteration with `async for` over subscriptions
    - Immediate ACK/NACK delivery through async gRPC streams (no more queuing delays)
    - Removes threading complexity - uses `asyncio.create_task()` instead of `threading.Thread()`
    - Proper async/await throughout: append, read, observe, delete operations
  - **Impact**:
    - `ESEventStore.configure()` method signature **unchanged** - NO client code changes needed
    - `ESEventStore.__init__()` now accepts connection string (or pre-initialized client for testing)
    - Internal implementation uses lazy async client initialization
    - `AckableEventRecord.ack_async()`/`nack_async()` now properly await async delegates
    - All test mocks updated to use `AsyncMock` and `AsyncIteratorMock`
  - **Files**:
    - `neuroglia/data/infrastructure/event_sourcing/event_store/event_store.py` - Full async migration
    - `neuroglia/data/infrastructure/event_sourcing/abstractions.py` - Fixed ack/nack delegates to await
    - `tests/cases/test_event_store_tombstone_handling.py` - Converted to async tests (18 tests passing)
    - `tests/cases/test_persistent_subscription_ack_delivery.py` - Converted to async tests (18 tests passing)
  - **Migration Guide** (only needed if directly instantiating ESEventStore):

    ```python
    # Old (direct instantiation - uncommon)
    from esdbclient import EventStoreDBClient
    client = EventStoreDBClient(uri=connection_string)
    store = ESEventStore(options, client, serializer)

    # New (pass connection string instead)
    store = ESEventStore(options, connection_string, serializer)

    # Recommended (no changes needed)
    ESEventStore.configure(builder, EventStoreOptions(database_name, consumer_group))
    ```

  - **Note**: This change supersedes the previous ACK delivery workaround - async API handles ACKs correctly without checkpoint tuning

### Fixed

- **CRITICAL**: Improved EventStoreDB persistent subscription ACK delivery (SUPERSEDED by async migration above)

  - **Root Cause**: esdbclient uses gRPC bidirectional streaming where ACKs are queued but the request stream must be actively iterated to send them
  - **Impact**: ACKs accumulated in queue without being sent, causing event redelivery every messageTimeout (30s) until events got parked after maxRetryCount
  - **Fix**: Optimized subscription configuration with immediate checkpoint delivery (min/max checkpoint count = 1, messageTimeout = 60s)
  - **Behavior**:
    - Persistent subscriptions created with min_checkpoint_count=1 and max_checkpoint_count=1 for immediate ACK delivery
    - Increased messageTimeout to 60s to give more processing time
    - Added detailed ACK/NACK logging at DEBUG level
    - Added periodic ACK queue metrics logging (every 10 seconds)
  - **Files**: `neuroglia/data/infrastructure/event_sourcing/event_store/event_store.py`
  - **Tests**: `tests/cases/test_persistent_subscription_ack_delivery.py` - 7 comprehensive tests covering ACK/NACK delivery
  - **Note**: This improves ACK delivery but esdbclient's threading model may still cause delays. For production, consider using idempotent handlers or switching to catchup subscriptions with manual checkpointing

- **CRITICAL**: Fixed ReadModelReconciliator crash on EventStoreDB tombstone events
  - **Root Cause**: Hard-deleted streams create tombstone markers ($$-prefixed streams) that appear in category projections with invalid JSON
  - **Impact**: ReadModelReconciliator subscription stopped when encountering tombstones, causing read/write model desync
  - **Fix**: Added graceful handling for tombstone events, system events, and invalid JSON in EventStore.\_consume_events_async()
  - **Behavior**:
    - Tombstone events (streams prefixed with `$$`) are skipped and acknowledged at DEBUG level
    - System events (types prefixed with `$`) are skipped and acknowledged at DEBUG level
    - Invalid JSON events are skipped and acknowledged at WARNING level (prevents subscription stop)
  - **Files**: `neuroglia/data/infrastructure/event_sourcing/event_store/event_store.py`
  - **Tests**: `tests/cases/test_event_store_tombstone_handling.py` - 11 comprehensive tests covering all scenarios
  - **Related**: Works with DeleteMode.HARD from v0.6.15 - hard deletes no longer crash ReadModelReconciliator

## [0.6.15] - 2025-12-01

### Added

- **Flexible Deletion Strategies for Event-Sourced Aggregates**
  - **DeleteMode Enum**: Three deletion strategies (DISABLED, SOFT, HARD) for event-sourced repositories
    - **DISABLED**: Default behavior, raises NotImplementedError (preserves immutable event history)
    - **SOFT**: Delegates to aggregate's deletion method (e.g., `mark_as_deleted()`), preserves event stream with deletion event
    - **HARD**: Physical stream deletion via EventStore.delete_async() for GDPR compliance and data privacy
  - **EventSourcingRepositoryOptions**: Configuration dataclass with `delete_mode` and `soft_delete_method_name` fields
  - **"Delegate to Aggregate" Pattern**: Soft delete calls convention-based methods (default: `mark_as_deleted()`, configurable)
  - **EventStore Interface Enhancement**: Added `delete_async()` abstract method for stream deletion
  - **ESEventStore Implementation**: Implemented `delete_async()` using EventStoreDB's `delete_stream()`
  - **Architecture**: Follows DDD principles - aggregate controls deletion semantics, repository orchestrates persistence
  - **Files**:
    - `neuroglia/data/infrastructure/event_sourcing/abstractions.py` - DeleteMode enum and EventStore.delete_async()
    - `neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py` - Deletion mode implementation
    - `neuroglia/data/infrastructure/event_sourcing/event_store/event_store.py` - ESEventStore.delete_async()
  - **Tests**: `tests/cases/test_event_sourcing_repository_delete.py` - 12 comprehensive tests covering all modes

### Fixed

- **CRITICAL**: Fixed event acknowledgment timing to prevent duplicate event delivery
  - **Root Cause**: `ESEventStore._consume_events_async()` was acknowledging events **immediately** after pushing to observable (via `subject.on_next()`), **before** `ReadModelReconciliator` completed processing
  - **Impact**: Events were ACKed before processing → events lost on crash, events redelivered on restart, failed events never retried, duplicate CloudEvents on service restart
  - **Fix**: Return `AckableEventRecord` with ack/nack delegates from EventStore, allowing `ReadModelReconciliator` to control acknowledgment **after** processing completes
  - **Architecture**: Consumer (ReadModelReconciliator) now controls acknowledgment timing, not producer (EventStore) - follows proper producer-consumer pattern
  - **Backward Compatibility**: 100% backward compatible - non-persistent subscriptions still use regular `EventRecord`, persistent subscriptions use `AckableEventRecord`
  - **Files**:
    - `neuroglia/data/infrastructure/event_sourcing/event_store/event_store.py` - Returns AckableEventRecord with delegates
    - `neuroglia/data/infrastructure/event_sourcing/read_model_reconciliator.py` - Calls ack/nack after processing
  - **See**: `notes/fixes/EVENT_ACKNOWLEDGMENT_FIX.md` for complete technical analysis
  - **Related**: Fixes EVENT_SOURCING_DOUBLE_PUBLISH_FIX (v0.6.14) - this completes the event delivery correctness work

### Added

- **Comprehensive Test Suite**: `tests/cases/test_event_acknowledgment_fix.py`
  - Validates events acknowledged AFTER successful processing
  - Validates events nacked on processing failure
  - Validates acknowledgment timing (mediator.publish_async before ack)
  - Validates multiple events acknowledged independently
  - Validates timeout handling with nack
  - 6 tests, all passing ✅

## [0.6.14] - 2025-12-01

### Fixed

- **CRITICAL**: Fixed double CloudEvent emission with EventSourcingRepository
  - **Root Cause**: Base `Repository._publish_domain_events()` was publishing events, then `ReadModelReconciliator` was also publishing the same events from EventStore subscription, resulting in 2 CloudEvents per domain event
  - **Impact**: Every domain event produced duplicate CloudEvents, causing double processing in event handlers and external systems
  - **Fix**: Override `_publish_domain_events()` in `EventSourcingRepository` to do nothing - ReadModelReconciliator handles all event publishing from EventStore (source of truth)
  - **Architecture**: Event sourcing uses asynchronous publishing from EventStore subscription (at-least-once delivery), while state-based repositories use synchronous publishing (best-effort)
  - **Backward Compatibility**: 100% backward compatible - state-based repositories (MotorRepository, MongoRepository) continue to publish events synchronously as before
  - **File**: `neuroglia/data/infrastructure/event_sourcing/event_sourcing_repository.py`
  - **See**: `notes/fixes/EVENT_SOURCING_DOUBLE_PUBLISH_FIX.md` for complete technical analysis

### Added

- **Comprehensive Test Suite**: `tests/cases/test_event_sourcing_double_publish_fix.py`
  - Validates EventSourcingRepository does not call mediator.publish_async()
  - Validates multiple events do not cause multiple publishes
  - Validates method override is correctly implemented
  - Validates backward compatibility with state-based repositories
  - 7 tests, all passing ✅

## [0.6.13] - 2025-12-01

### Fixed

- **CRITICAL**: Fixed repository instantiation failures due to missing abstract method implementations

  - **EventSourcingRepository**: Implemented `_do_add_async`, `_do_update_async`, `_do_remove_async` to follow Template Method Pattern
  - **MongoRepository**: Implemented `_do_add_async`, `_do_update_async`, `_do_remove_async` to follow Template Method Pattern
  - Added optional `mediator` parameter to repository constructors for automatic domain event publishing
  - Both repositories now properly call `super().__init__(mediator)` to initialize base `Repository` class
  - Added `TYPE_CHECKING` imports for `Mediator` type hints in both implementations
  - **Root Cause**: Base `Repository` class defines abstract methods for Template Method Pattern, but concrete implementations were not updated
  - **Impact**: Without this fix, attempting to instantiate `EventSourcingRepository` or `MongoRepository` raises `TypeError: Can't instantiate abstract class`
  - **See**: `notes/fixes/REPOSITORY_ABSTRACT_METHODS_FIX.md` for detailed analysis

- **Missing Type Imports**: Fixed `NameError: name 'List' is not defined` in query execution

  - Added `List` import to `neuroglia.data.queryable` (line 230 usage in `to_list()`)
  - Added `List` import to `neuroglia.data.infrastructure.mongo.mongo_repository` (lines 118-119 usage in `MongoQueryProvider.execute()`)

- **CRITICAL**: Fixed ReadModelReconciliator breaking Motor's event loop
  - **Root Cause**: `subscribe_async()` used `asyncio.run()` inside RxPY callback, which creates and **closes** a temporary event loop
  - **Impact**: Motor's MongoDB client becomes corrupted when event loop closes, causing `RuntimeError: Event loop is closed` on subsequent queries
  - **Fix**: Replaced `asyncio.run()` with `loop.call_soon_threadsafe()` and `asyncio.create_task()` to schedule async handlers on main event loop
  - **File**: `neuroglia/data/infrastructure/event_sourcing/read_model_reconciliator.py`
  - This fix is **critical** for any application using ReadModelReconciliator with Motor-based repositories

### Added

- **Validation Script**: `scripts/validate_repository_fixes.py` to verify all repository fixes

  - Validates EventSourcingRepository instantiation
  - Validates MongoRepository instantiation
  - Validates List imports in queryable and mongo_repository modules
  - Validates Template Method Pattern implementation in base Repository class
  - Run with: `poetry run python scripts/validate_repository_fixes.py`

- **Comprehensive Test Suite**: `tests/cases/test_repository_abstract_methods_fix.py`
  - Tests repository instantiation with and without mediator
  - Tests abstract method implementations
  - Tests List import availability
  - Tests Template Method Pattern behavior
  - Validates that no runtime patches are needed

### Changed

- **Breaking Change (Minor)**: Repository constructor signatures now include optional `mediator` parameter
  - `EventSourcingRepository.__init__(eventstore, aggregator, mediator=None)` (was: no mediator param)
  - `MongoRepository.__init__(options, mongo_client, serializer, mediator=None)` (was: no mediator param)
  - **Impact**: Existing code continues to work (parameter is optional and defaults to None)
  - **Benefit**: Enables automatic domain event publishing after successful persistence operations
  - **Migration**: No changes required for existing code; add `mediator=mediator` to enable event publishing

## [0.6.12] - 2025-12-01

### Fixed

- **CRITICAL**: Fixed EventStore persistent subscription acknowledgement loop
  - Added explicit event acknowledgement (`subscription.ack(e.id)`) after successful processing
  - Added negative acknowledgement (`subscription.nack(e.id, action="retry")`) on processing failures
  - Added negative acknowledgement with park action on decoding failures
  - Resolves infinite event redelivery loop (events redelivered every 30 seconds)
  - Without acknowledgement, EventStoreDB assumes processing failed and redelivers indefinitely
  - Fix prevents duplicate event processing and excessive system load
  - Uses `hasattr()` checks for backward compatibility with non-persistent subscriptions

## [0.6.11] - 2025-11-30

### Fixed

- **CRITICAL**: Fixed persistent subscription connection in `observe_async` for esdbclient >= 1.0
  - Added explicit `read_subscription_to_stream` call after `create_subscription_to_stream`
  - Resolves `TypeError: 'NoneType' object is not iterable` when using consumer groups
  - `create_subscription_to_stream` only creates subscription group (returns None)
  - `read_subscription_to_stream` connects to subscription and returns iterable object
  - Fixes event consumption in persistent subscription scenarios

## [0.6.10] - 2025-11-30

### Fixed

- **Event Sourcing: EventStore Type Safety and Compatibility**
  - Fixed parameter name mismatch in `EventStore.append_async` base class (streamId → stream_id, expectedVersion → expected_version)
  - Fixed `bytearray | None` to `bytes` conversion in NewEvent data serialization
  - Added runtime validation for None event data with descriptive error messages
  - Fixed all None comparisons to use Python idioms (`is not None` instead of `!= None`)
  - Added proper null safety checks for stream_id and offset parameters in `observe_async`
  - Fixed method signature in `_decode_recorded_event` (removed incorrect subscription parameter)
  - Added null checks for `inspect.getmodule()` result with descriptive error
  - Fixed timestamp handling with fallback to current UTC time when None
  - Fixed position handling with fallback to 0 when commit_position is None
  - Fixed subscription null check before calling stop()
  - Converted UUID to string for EventRecord id field
  - Removed duplicate incomplete `create_subscription_to_stream` call
  - Removed unused `first_event` variable
  - Fixed RxPY imports to use explicit module paths
  - Changed `configure` method to `@staticmethod` decorator
  - All 32 event sourcing integration tests passing
  - 100% type safety compliance with zero type errors

## [0.6.9] - 2025-11-22

### Added

- **Documentation: Enhanced Framework Discoverability**

  - Enhanced `RequestHandler` docstring with comprehensive visual reference table of 12 helper methods
  - Added module-level documentation to `neuroglia.mediation` with quick start guide and API examples
  - Added explicit `__all__` exports (28 items) for improved IDE autocomplete and discoverability
  - Enhanced `Command` and `Query` classes with 15+ type hint patterns covering all common scenarios
  - Added prominent warnings to `OperationResult` and `ProblemDetails` discouraging manual construction
  - Updated `docs/features/simple-cqrs.md` with comprehensive helper methods reference section
  - Updated `.github/copilot-instructions.md` with enhanced CQRS patterns and error handling guidance
  - Improved discoverability from ~20% to ~95% through documentation-only changes
  - Zero breaking changes, 100% backward compatible

- **Documentation: Starter App Repository Integration**

  - Added prominent references to the [Starter App Repository](https://bvandewe.github.io/starter-app/) across documentation
  - Positioned starter-app as production-ready template alternative to blank setup
  - Updated `docs/index.md` with "Quick Start Options" section featuring three paths:
    - Option 1: Production Template (starter-app with OAuth2/OIDC, RBAC, SubApp, OTEL, frontend)
    - Option 2: Learn from Samples (existing Mario's Pizzeria, OpenBank, Simple UI)
    - Option 3: Build from Scratch (traditional getting started guide)
  - Updated `docs/getting-started.md` with "Choose Your Starting Point" section
  - Added starter-app tip to `docs/guides/3-min-bootstrap.md`
  - Added starter-app to `docs/documentation-philosophy.md` learning options
  - Starter app includes: SubApp architecture, OAuth2/OIDC with RBAC, clean architecture (DDD+CQRS), modular frontend (Vanilla JS/SASS/ES6), OpenTelemetry instrumentation, Docker Compose setup

- **Documentation: Philosophy & Critical Disclaimer**
  - Added prominent "⚠️ Eventual Accuracy Disclaimer" to `docs/index.md`
  - Created comprehensive `docs/documentation-philosophy.md` page
  - Positioned documentation as entry point for both human developers and AI agents
  - Emphasized critical mindset approach and toolbox metaphor (no one-size-fits-all)
  - Highlighted business modeling and ecosystem perspectives as starting points
  - Documented clean architecture starting with domain understanding, not code
  - Added guidance on microservices interaction via persisted queryable CloudEvents streams
  - Cross-referenced AI agent guide with documentation philosophy

### Changed

- **Development: Markdown linting configuration**
  - Disabled MD046 rule in `.markdownlint.json` to allow MkDocs admonition syntax
  - Allows consistent use of indented code blocks within admonitions (warning, tip, info boxes)

## [0.6.8] - 2025-11-16

### Fixed

- **WebApplicationBuilder: Settings registration no longer breaks DI resolution**

  - Fixed critical bug where `lambda: app_settings` registration caused `AttributeError` when resolving services depending on settings
  - Root cause: Lambda functions registered as `implementation_type` don't have `__origin__` attribute, breaking generic type inspection
  - Solution: Changed `WebApplicationBuilder.__init__` to use `singleton=app_settings` instead of `lambda: app_settings` (line 371 in `web.py`)
  - Added defensive check in `ServiceProvider._build_service` to prevent crashes from non-class implementation types (line 600 in `service_provider.py`)
  - Benefits:
    - Semantically correct: settings are already singleton instances, no need for lambda wrapper
    - Performance improvement: eliminates lambda invocation overhead on every settings resolution
    - Type safety: DI container can properly inspect service types
    - 100% backward compatible: behavior from consumer perspective is identical
  - Comprehensive test coverage added in `test_web_application_builder_settings_registration.py`
  - This fix enables command/query handlers to declare settings dependencies without manual workarounds

- **Mario's Pizzeria: Enum serialization and query mismatch**
  - Fixed critical bug where ready orders weren't appearing in delivery dashboard
  - Root cause: Enums stored in MongoDB using `.name` (e.g., "READY") but queries using `.value` (e.g., "ready")
  - Updated all status comparisons in query handlers to use `.name` instead of `.value`:
    - `get_delivery_orders_query.py` - READY/DELIVERING comparisons
    - `get_active_kitchen_orders_query.py` - PENDING/CONFIRMED/COOKING comparisons
    - `get_orders_timeseries_query.py` - DELIVERED/CANCELLED comparisons
    - `get_orders_by_driver_query.py` - DELIVERED comparison
    - `in_memory_customer_notification_repository.py` - UNREAD comparison
  - Updated all MongoDB queries in `mongo_order_repository.py` to use `.name`:
    - `get_by_status_async()` - Status query filter
    - `get_active_orders_async()` - DELIVERED/CANCELLED exclusion
    - `get_orders_by_delivery_person_async()` - DELIVERING filter
    - `get_orders_for_kitchen_stats_async()` - PENDING/CANCELLED exclusion
    - `get_orders_for_pizza_analytics_async()` - CANCELLED exclusion
  - This aligns with the `JsonEncoder` behavior (line 111 in `json.py`) which serializes enums using `.name` for stable storage

## [0.6.7] - 2025-11-12

### Added

- **CQRS/Mediation: Expanded OperationResult helper methods**

  - Added `accepted(data)` for async operations (HTTP 202 Accepted)
  - Added `no_content()` for successful operations with no response body (HTTP 204 No Content)
  - Added `unauthorized(detail)` for authentication failures (HTTP 401 Unauthorized)
  - Added `forbidden(detail)` for authorization failures (HTTP 403 Forbidden)
  - Added `unprocessable_entity(detail)` for semantic validation errors (HTTP 422 Unprocessable Entity)
  - Added `service_unavailable(detail)` for temporary service outages (HTTP 503 Service Unavailable)
  - All helper methods available in both `RequestHandler` and `SimpleCommandHandler`
  - Comprehensive test coverage with 26 unit tests validating all response types

- **Data Access: Optimistic Concurrency Control (OCC) for MotorRepository**

  - Automatic version-based conflict detection for `AggregateRoot` state-based persistence
  - `state_version` field in `AggregateState` automatically increments on each save operation
  - Atomic MongoDB operations prevent race conditions using `replace_one` with version filter
  - New `OptimisticConcurrencyException` raised when concurrent updates are detected
  - New `EntityNotFoundException` raised when attempting to update non-existent entities
  - `last_modified` timestamp automatically updated on each save
  - Comprehensive test coverage with 9 unit tests validating all OCC scenarios

- **Keycloak: Management scripts and commands**
  - Added `deployment/keycloak/create-test-users.sh` for automated test user creation
  - Added `scripts/keycloak-reset.sh` for interactive Keycloak data reset
  - Added Makefile commands: `keycloak-reset`, `keycloak-configure`, `keycloak-create-users`, `keycloak-logs`, `keycloak-restart`, `keycloak-export`
  - Test users (manager, chef, customer, driver, john.doe, jane.smith) with password "test"

### Changed

- **Observability: Transparent CloudEvent environment variable reading**

  - Removed `NEUROGLIA_` prefix requirement from `ObservabilitySettingsMixin`
  - Applications now read `CLOUD_EVENT_SINK`, `CLOUD_EVENT_SOURCE`, `CLOUD_EVENT_TYPE_PREFIX` directly
  - `ApplicationSettingsWithObservability` now inherits from `BaseSettings` for proper Pydantic settings behavior
  - Simplified settings configuration in Mario's Pizzeria sample

- **Keycloak: Persistent H2 file-based storage**
  - Changed from `KC_DB: dev-mem` (in-memory) to `KC_DB: dev-file` for data persistence
  - Keycloak configurations now survive container restarts
  - Realm configurations persist in `pyneuro_keycloak_data` Docker volume

### Fixed

- **Data Access: MotorRepository legacy document compatibility**

  - Fixed `OptimisticConcurrencyException` on documents without `state_version` field
  - Added `$or` query to match documents with `state_version: 0` or missing `state_version` field
  - Legacy documents (created before OCC implementation) now update successfully
  - Handles migration from non-versioned to versioned documents transparently

- **Events: Duplicate CloudEvent publishing in Mario's Pizzeria**
  - Fixed duplicate CloudEvents for order and pizza domain events
  - Removed manual `publish_cloud_event_async()` calls from event handlers
  - `DomainEventCloudEventBehavior` pipeline behavior now exclusively handles CloudEvent conversion
  - Event handlers focus on side effects (notifications, state updates) while framework handles publishing
  - Customer profile events were working correctly (never manually published)

### Documentation

- Added comprehensive Optimistic Concurrency Control documentation:
  - `docs/features/data-access.md`: Detailed OCC guide with pizzeria examples, retry patterns, and best practices
  - `docs/patterns/persistence-patterns.md`: OCC implementation patterns for state-based persistence
  - Complete usage examples including exception handling and MongoDB atomic operations
- Updated `deployment/keycloak/README.md` with persistent storage documentation and management commands
- Updated `deployment/keycloak/configure-master-realm.sh` to automatically import realm and create test users

## [0.6.6] - 2025-11-10

### Added

- **Data Access: MotorRepository custom implementation registration**
  - `MotorRepository.configure` now accepts an optional `implementation_type` parameter for registering custom repository implementations that extend `MotorRepository`
  - Enables single-line registration of custom repositories with domain-specific query methods
  - Validates that implementation types properly extend `MotorRepository` at configuration time
  - When provided with `domain_repository_type`, the custom implementation is automatically bound to the domain interface

### Documentation

- Updated `docs/tutorials/mario-pizzeria-06-persistence.md` with examples of custom repository implementation registration

## [0.6.5] - 2025-11-10

### Added

- **Data Access: MotorRepository domain interface registration**
  - `MotorRepository.configure` can now bind a domain-layer repository interface directly to the scoped Motor repository via the optional `domain_repository_type` argument
- **Tests: CloudEvent publishing regression coverage**
  - Added `tests/cases/test_cloud_event_publisher.py` to verify CloudEvents are emitted with JSON payloads

### Fixed

- **CloudEvents: HTTP publishing with httpx**
  - `CloudEventPublisher` now submits JSON payloads as UTF-8 text, preventing `httpx` from treating the body as a streaming request when the serializer produced a `bytearray`
- **Data Access: MotorRepository mediator resolution**
  - `MotorRepository.configure` now requires a Mediator from the service provider when available so aggregate domain events continue to flow without manual wiring

### Documentation

- Updated `docs/tutorials/mario-pizzeria-06-persistence.md` to show how to bind domain repository interfaces with `MotorRepository.configure`

## [0.6.4] - 2025-11-10

### Added

- **Eventing: Automatic CloudEvent emission from domain events**
  - New `DomainEventCloudEventBehavior` pipeline behavior transforms domain events decorated with `@cloudevent` into CloudEvents and publishes them on the internal bus
  - `CloudEventPublisher.configure` now wires the CloudEvent bus, publishing options, and behavior in one call for consistent setup
  - Payload sanitizer ensures datetimes, decimals, enums, and nested events are CloudEvent-friendly and always include the aggregate id when available
- **Serialization: Optional field hydration for missing payload members**
  - `JsonSerializer` now populates omitted `Optional[...]` fields with `None`
  - Dataclass defaults are preserved when source JSON omits optional attributes
  - Non-dataclass objects also receive automatic optional backfilling via type hints
- **Tests: Optional hydration regression coverage**
  - Added `tests/cases/test_json_serializer_optional_fields.py` covering dataclass and plain-class scenarios

### Changed

- **Domain Model: AggregateRoot initialization is now generic-safe**
  - Aggregate roots resolve their state type through a dedicated `_get_state_type` helper, preventing `__orig_bases__` access errors and ensuring custom constructors still receive an initialized state instance
- **Mediator: Notification pipeline now honors behaviors**
  - Notification publishing reuses the same pipeline behavior infrastructure, enabling CloudEvent emission and other cross-cutting behaviors for domain events without additional wiring

### Deprecated

- **DomainEventDispatchingMiddleware**
  - Middleware is now a no-op wrapper kept for backward compatibility; use `DomainEventCloudEventBehavior.configure()` for CloudEvent publishing instead

### Documentation

- Updated `docs/features/serialization.md` to document optional field hydration behaviour and defaults preservation
- Refreshed `docs/patterns/persistence-patterns.md` and `docs/patterns/unit-of-work.md` with guidance on replacing `DomainEventDispatchingMiddleware` with `DomainEventCloudEventBehavior`

## [0.6.3] - 2025-11-07

### Added

- **Infrastructure CLI: `recreate` command** for service recreation with fresh containers

  - Forces Docker to create new containers (picks up environment variable changes)
  - `--delete-volumes` option to also delete and recreate volumes (data loss warning)
  - `--no-remove-orphans` option to skip orphan container removal
  - `-y, --yes` flag to skip confirmation prompts
  - Makefile targets: `infra-recreate` and `infra-recreate-clean`
  - Comprehensive documentation in `RECREATE_COMMAND_GUIDE.md`

- **Tests: MongoDB Lazy Import Tests** (`tests/integration/test_mongo_lazy_imports.py`)
  - Comprehensive test suite verifying lazy import mechanism
  - Tests MotorRepository imports without pymongo dependency
  - Tests sync repositories fail gracefully without pymongo
  - Tests sync repositories work correctly when pymongo is installed
  - Tests all exports present in `__all__`

### Fixed

- **Packaging: Ensure `rx` installs with base distribution**

  - Removed `rx` from extras list so it's treated as a core dependency
  - Downstream consumers no longer need to install `rx` manually

- **Observability: Re-enabled Prometheus /metrics endpoint**

  - Added `opentelemetry-exporter-prometheus ^0.49b2` dependency (now compatible with protobuf 5.x)
  - Prometheus metrics endpoint now works correctly at `/metrics`
  - PrometheusMetricReader properly configured in OpenTelemetry SDK
  - Applications can now expose metrics for Prometheus scraping
  - Note: Was previously removed due to protobuf incompatibility, now resolved

- **Docker Compose: Fixed network and port configuration**

  - Changed network from `external: true` to `driver: bridge` in `docker-compose.shared.yml`
  - Removed duplicate network declarations from sample compose files
  - Updated OTEL collector ports in `.env` to avoid conflicts (4317→4417, 4318→4418, etc.)
  - Updated debug ports in `.env` to avoid conflicts (5678→5778, 5679→5779)
  - Added port configuration documentation in `notes/infrastructure/DOCKER_COMPOSE_PORT_CONFIGURATION.md`
  - Multiple stacks can now run concurrently without port conflicts

- **Keycloak: Fixed admin CLI configuration script**
  - Auto-detects Keycloak container name instead of hardcoding
  - Auto-detects `kcadm.sh` location (supports multiple Keycloak versions)
  - Fixed script to target correct container (was incorrectly targeting mario-pizzeria-app)
  - Improved error handling with validation checks

### Changed

- **Framework: MongoDB Package Lazy Imports (Breaking Dependency Fix)**

  - Implemented PEP 562 lazy imports in `neuroglia.data.infrastructure.mongo.__init__`
  - **MotorRepository** now imports without requiring pymongo (async-only applications)
  - **Sync repositories** (MongoRepository, EnhancedMongoRepository) lazy-loaded on access
  - Added `TYPE_CHECKING` imports for type checker compatibility
  - Added comprehensive `__getattr__` implementation for lazy loading
  - Maintains **full backward compatibility** - all import paths unchanged
  - Removes unnecessary pymongo dependency for Motor-only users
  - Updated package docstring with lazy import notes

- **Documentation: Removed deprecated Unit of Work pattern references**

  - Updated all Mario's Pizzeria documentation to use repository-based event publishing
  - Replaced Unit of Work references with Persistence Patterns documentation
  - Updated `docs/mario-pizzeria.md` pattern table
  - Updated `docs/mario-pizzeria/domain-design.md` event publishing guidance
  - Updated `docs/mario-pizzeria/implementation-guide.md` code examples and patterns
  - Updated `docs/mario-pizzeria/testing-deployment.md` testing patterns

- **Documentation: Unified getting started guides**
  - Removed duplicate `guides/3-min-bootstrap.md` from navigation
  - Consolidated quick start content into comprehensive `getting-started.md`
  - Streamlined learning path: Welcome → Getting Started → Local Dev Setup → Tutorials

### Fixed

- **Infrastructure: Event Player OAuth configuration**
  - Updated `oauth_client_id` from `pyneuro-public-app` to `pyneuro-public` (matches Keycloak realm)
  - Fixed OAuth redirect URL using `oauth_server_url` (browser) and `oauth_server_url_backend` (container)
  - Added `oauth_legacy_keycloak: "false"` for Event Player v0.4.4+ compatibility

## [0.6.2] - 2025-11-02

### Added

- **Sample Application: Mario's Pizzeria - Customer Notifications Feature**
  - Added complete customer notification system with order status updates
  - Domain: `CustomerNotification` entity with notification types (order_cooking_started, order_ready, order_delivered, order_cancelled, general)
  - Domain: Notification status management (unread, read, dismissed) with event sourcing
  - Domain events: `CustomerNotificationCreatedEvent`, `CustomerNotificationReadEvent`, `CustomerNotificationDismissedEvent`
  - Repository: `ICustomerNotificationRepository` interface and `InMemoryCustomerNotificationRepository` implementation
  - Application: `GetCustomerNotificationsQuery` with pagination support
  - Application: `DismissCustomerNotificationCommand` for dismissing notifications
  - Application: `NotificationService` for in-memory notification tracking
  - API: `/api/notifications` endpoints for retrieving and dismissing notifications
  - UI: Notifications page (`/notifications`) with Bootstrap 5 styling
  - UI: Notifications dropdown in navigation bar with unread count badge
  - UI: Profile page integration showing active orders and notifications
  - Enhanced order event handlers to create notifications on order status changes
  - Customer entity: Active orders tracking (`add_active_order`, `remove_active_order`, `has_active_orders`)
  - UI: Smooth animations for notification dismissal and unread badges
  - Unit tests: Comprehensive test coverage for notification entity and repositories

### Changed

- **Dependencies: Updated all dependencies to latest versions**
  - Core: fastapi 0.115.5, pydantic-settings 2.6.1, typing-extensions 4.12.2, uvicorn 0.32.1, httpx 0.27.2, grpcio 1.68.1
  - Auth: pyjwt 2.10.1, python-multipart 0.0.17, itsdangerous 2.2.0, jinja2 3.1.4
  - Optional: pymongo 4.10.1, motor 3.6.0, esdbclient 1.1.1, redis 5.2.0, pydantic 2.10.3, email-validator 2.2.0
  - Dev: pytest 8.3.3, pytest-asyncio 0.24.0, mypy 1.13.0, autopep8 2.3.1, coverage 7.6.9, flake8 7.1.1, isort 5.13.2, pre-commit 4.0.1
  - Docs: mkdocs-material 9.5.48

## [0.6.1] - 2025-11-02

### Changed

- **Documentation: Source Code Docstring Updates**: Updated docstrings to reflect v0.6.0 patterns and deprecations

  - Updated `src/neuroglia/extensions/mediator_extensions.py` to recommend `Mediator.configure()` pattern
  - Updated `src/neuroglia/extensions/cqrs_metrics_extensions.py` with modern WebApplicationBuilder examples
  - Updated `src/neuroglia/extensions/state_persistence_extensions.py` marking UnitOfWork as deprecated
  - Updated `src/neuroglia/mediation/mediator.py` showing `Mediator.configure()` as primary pattern
  - Added deprecation notices for UnitOfWork pattern with repository-based event publishing alternative
  - Updated all examples to use `Mediator.configure()` instead of `services.add_mediator()`
  - Added legacy pattern notes for backward compatibility
  - Created `DOCSTRING_UPDATE_PLAN.md` with comprehensive audit and enhancement roadmap
  - Created `DOCSTRING_UPDATES_SUMMARY.md` documenting all changes made

- **Documentation: Observability Guide Enhancements**: Massively expanded observability documentation with comprehensive beginner-to-advanced content

  - Expanded `docs/features/observability.md` from 838 to 2,079 lines (148% increase)
  - Added Architecture Overview for Beginners section with complete stack visualization using Mermaid diagrams
  - Added Infrastructure Setup guide covering Docker Compose and Kubernetes deployment
  - Added layer-by-layer Developer Implementation Guide (API, Application, Domain, Integration layers)
  - Added Understanding Metric Types section with Counter vs Gauge vs Histogram comparison
  - Added Data Flow Explained section with sequence diagrams showing app → OTEL Collector → backends → Grafana
  - Enhanced `docs/guides/opentelemetry-integration.md` with documentation map and clear scope definition
  - Reorganized MkDocs navigation: added 3-tier Guides structure (Getting Started/Development/Operations)
  - Integrated OpenTelemetry Integration guide into navigation under Operations section
  - Established cross-references between all observability documentation files

- **Documentation: AI Agent Guide Updates**: Updated AI agent documentation to reflect recent framework improvements

  - Added observability patterns with OpenTelemetry integration examples
  - Added RBAC implementation patterns with JWT authentication
  - Updated sample applications section with OpenBank event sourcing details and Simple UI SubApp pattern
  - Enhanced key takeaways with observability, security, and event sourcing guidance
  - Added comprehensive documentation navigation reference

- **Documentation: Copilot Instructions Alignment**: Aligned GitHub Copilot instructions with AI agent guide
  - Added comprehensive observability section with OpenTelemetry patterns
  - Added RBAC best practices and implementation examples
  - Added SubApp pattern documentation for UI/API separation
  - Updated IDE-specific instructions to reference new samples and patterns
  - Added documentation navigation map with 3-tier structure
  - Documented recent framework improvements (v0.6.0+)
  - Added sample application reference guide (Mario's Pizzeria, OpenBank, Simple UI)

## [0.6.0] - 2025-11-01

### Added

- **Repository-Based Domain Event Publishing**: Repositories now automatically publish domain events after successful persistence
  - Extended `Repository` base class with automatic event publishing via optional mediator parameter
  - Implemented template method pattern: `add_async`/`update_async` call `_do_add_async`/`_do_update_async`
  - Events published AFTER successful persistence, then cleared from aggregates (best-effort logging on failure)
  - Updated `MotorRepository` and `MemoryRepository` to support mediator injection
  - Updated all mario-pizzeria repositories to accept mediator parameter
  - Benefits: Automatic event publishing (impossible to forget), works everywhere, simplifies handler code
  - **BREAKING**: Repository constructors now require optional `mediator` parameter (defaults to `None` for backward compatibility)

### Changed

- **Documentation: Repository-Based Event Publishing Pattern**: Comprehensive documentation update to reflect current framework architecture

  - Replaced all UnitOfWork references with repository-based event publishing pattern
  - Emphasized that **Command Handler IS the transaction boundary**
  - Updated `persistence-patterns.md` with detailed transaction boundary explanation and component role comparison
  - Marked `unit-of-work.md` as DEPRECATED with clear migration guidance
  - Updated all Mario's Pizzeria tutorial files (mario-pizzeria-03-cqrs.md, mario-pizzeria-05-events.md, mario-pizzeria-06-persistence.md)
  - Updated pattern analysis files (kitchen-order-placement-ddd-analysis.md)
  - Removed UnitOfWork from all code examples throughout documentation
  - Added comprehensive explanation of domain event lifecycle (raised vs published)
  - Clarified repository responsibilities: persistence + automatic event publishing
  - Documentation now 100% aligned with actual framework implementation

- **Documentation: Deployment Architecture**: Updated README and sample documentation for new docker-compose architecture

  - Restructured README.md Quick Start section with comprehensive Docker setup
  - Added service ports reference table for all samples and infrastructure
  - Documented CLI tools: `mario-pizzeria`, `openbank`, `simple-ui`
  - Updated OpenBank guide with correct ports (8899) and CLI commands
  - Added authentication section documenting shared `pyneuro` realm configuration
  - Replaced legacy docker-compose instructions with CLI-based workflow
  - All ports, commands, and configurations verified against actual implementation

- **Simplified Mario-Pizzeria Command Handlers**: Removed UnitOfWork pattern in favor of repository-based event publishing

  - Removed `IUnitOfWork` dependency from all 10 command handlers
  - Handlers no longer need to manually register aggregates for event publishing
  - Simplified handler constructors by removing `unit_of_work` parameter
  - Events are now published automatically by repositories after successful persistence
  - Affected handlers: PlaceOrderCommand, AddPizzaCommand, UpdateCustomerProfileCommand, StartCookingCommand, UpdatePizzaCommand, CreateCustomerProfileCommand, AssignOrderToDeliveryCommand, RemovePizzaCommand, CompleteOrderCommand, UpdateOrderStatusCommand
  - Reduced boilerplate code and eliminated possibility of forgetting to register aggregates

- **Simple UI Authentication**: Migrated to pure JWT-only authentication (stateless)
  - Removed redundant server-side session cookies and SessionMiddleware
  - All authentication now handled via JWT tokens in Authorization header
  - JWT tokens stored client-side in localStorage only
  - Updated `ui_auth_controller.py` to remove session storage logic
  - Updated `main.py` to remove SessionMiddleware from UI sub-app
  - Removed `session_secret_key` from `application/settings.py`
  - Fixed JWT token parsing to use `username` field instead of `sub` (UUID)
  - Benefits: Stateless, scalable, microservices-ready, no CSRF concerns
  - Updated documentation in `docs/guides/simple-ui-app.md` with JWT-only architecture details

## [0.5.1] - 2025-10-29

### Changed

- **Python Version Requirement**: Lowered minimum Python version from 3.11+ to 3.9+
  - Framework analysis revealed only Python 3.9+ features are actually used (built-in generic types like `dict[str, int]`)
  - Pattern matching (`match/case`) syntax only appears in documentation/docstrings, not runtime code
  - Makes the framework accessible to a much wider audience while maintaining all functionality
  - Updated in `pyproject.toml`, README badges, and documentation

### Added

- **CQRS Metrics Auto-Enablement**: Intelligent automatic registration of CQRS metrics collection

  - `Observability.configure()` now auto-detects Mediator configuration and enables CQRS metrics by default
  - New `auto_enable_cqrs_metrics` parameter (default: `True`) for opt-out capability
  - Hybrid approach: convention over configuration with explicit control when needed
  - Consistent with tracing behavior auto-enablement pattern
  - Usage: `Observability.configure(builder)` automatically enables metrics when Mediator is present
  - Opt-out: `Observability.configure(builder, auto_enable_cqrs_metrics=False)` for manual control

- **Request Handler Helpers**: Added `conflict()` method to `RequestHandler` base class
  - Returns HTTP 409 Conflict status with error message
  - Available to all `CommandHandler` and `QueryHandler` instances
  - Matches existing helper methods: `ok()`, `created()`, `bad_request()`, `not_found()`
  - Usage: `return self.conflict("User with this email already exists")`

### Fixed

- **CQRS Metrics Middleware**: Fixed duplicate metric instrument creation warnings

  - Changed to class-level (static) meter initialization to prevent re-creating instruments on each request
  - Meters now initialized once and shared across all `MetricsPipelineBehavior` instances
  - Eliminates OpenTelemetry warnings: "An instrument with name X has been created already"
  - Fixed registration pattern: now registers as `PipelineBehavior` interface only (not dual registration)
  - Matches the pattern used by `DomainEventDispatchingMiddleware` for consistency

- **Minimal Samples**: Fixed handler registration issues across multiple samples

  - **simplest.py**: Fixed to properly start uvicorn server

    - Changed from `app.run()` to `uvicorn.run(app, host="0.0.0.0", port=8000)`
    - Ensures the sample actually serves HTTP requests instead of exiting immediately
    - Aligns with Docker deployment pattern
    - Updated `docs/getting-started.md` to reflect the correct usage pattern

  - **minimal-cqrs.py**: Fixed mediator handler registration

    - Replaced `add_simple_mediator()` with manual `Mediator` singleton registration
    - Added explicit `_handler_registry` population for command/query handlers
    - Added required `super().__init__()` calls to handler constructors
    - Now successfully creates and retrieves tasks

  - **ultra-simple-cqrs.py**: Fixed mediator handler registration

    - Replaced `create_simple_app()` with manual `ServiceCollection` setup
    - Applied same registry pattern as minimal-cqrs.py
    - Now successfully adds and retrieves notes

  - **simple-cqrs-example.py**: Fixed handler type mismatches and registration

    - Converted from `SimpleCommandHandler` to `CommandHandler` for all 6 handlers
    - Fixed generic type parameters: `CommandHandler[TCommand, TResult]`
    - Applied manual mediator registry pattern
    - Now demonstrates complete CRUD workflow: create, read, update, deactivate users

  - **state-based-persistence-demo.py**: Complete fix for advanced features demo
    - Fixed `build_provider()` to `build()` method call
    - Applied manual mediator registry for 4 handlers
    - **Fixed query handlers to use `OperationResult`**: Changed from raw return types to `OperationResult[T]`
    - Updated query result handling to extract data from `OperationResult`
    - ✅ All scenarios now work: create products, query all, update prices, query individual
    - Demonstrates full integration with domain event dispatching middleware

## [0.5.0] - 2025-10-27

### Added

#### **Mario's Pizzeria Sample - Event Handler Enhancements**

- **Pizza Event Handlers**: Complete CloudEvent publishing for pizza lifecycle

  - `PizzaCreatedEventHandler`: Publishes CloudEvents when pizzas are created with comprehensive logging and emoji indicators (🍕)
  - `ToppingsUpdatedEventHandler`: Tracks and publishes topping modifications with logging (🧀)
  - Integration with event-player for real-time event visualization
  - Comprehensive test suite `test_pizza_event_handlers.py` with CloudEvent validation
  - Auto-discovery via mediator pattern from `application.events` module

- **Order Event Handlers**: Enhanced order lifecycle tracking

  - `OrderCreatedEventHandler`: CloudEvent publishing for order creation events
  - Full integration with `BaseDomainEventHandler` pattern for consistent event processing
  - Comprehensive logging for order lifecycle tracking

- **Event-Player Integration**: External event visualization support

  - Keycloak auth client configuration for event-player service (mario-public-app)
  - Docker Compose integration with event-player v0.3.4
  - Support for admin, viewer, and event-publisher roles
  - Redirect URIs configured for http://localhost:8085/\*

- **Development Workflow Improvements**: Enhanced debugging and hot reload
  - Debugpy configuration with proper PYTHONPATH for module resolution
  - Automatic code reload on changes without authentication blocking
  - Watch directories configured for both application and framework code
  - VS Code debugger attachment on port 5678

### Changed

- **Documentation**: Repository presentation improvements
  - Added comprehensive repository badges to README.md:
    - PyPI version badge
    - Python 3.11+ requirement badge
    - Apache 2.0 license badge
    - Documentation link badge
    - Changelog badge with Keep a Changelog style
    - Poetry dependency management badge
    - Docker ready badge
    - Pre-commit enabled badge
    - Black code style badge
    - FastAPI framework badge
    - GitHub stars social badge
  - Enhanced project visibility and quality indicators
  - Added changelog badge linking to version history

### Fixed

- **Docker Compose Configuration**: Mario's Pizzeria app startup
  - Fixed debugpy module import error by adding /tmp to PYTHONPATH
  - Resolved "No module named debugpy" issue when using `python -m debugpy`
  - Container now starts reliably with hot reload enabled
  - Improved developer experience with immediate feedback loop

#### **Framework Enhancements**

- **CloudEvent Decorator System**: Enhanced `@cloudevent` decorator for event handler registration

  - **Type-based Handler Discovery**: Automatic registration of event handlers based on CloudEvent types
  - **Metadata Attachment**: `__cloudevent__type__` attribute for handler identification
  - **Integration with Event Bus**: Seamless integration with CloudEventIngestor and event routing
  - **Documentation**: Comprehensive examples for event-driven architecture patterns

- **Integration Event Base Class**: New `IntegrationEvent[TKey]` generic base class for domain events

  - **Generic Type Support**: Parameterized by aggregate ID type (`str`, `int`, etc.)
  - **Standard Metadata**: `created_at` timestamp and `aggregate_id` fields
  - **Abstract Base**: Enforces consistent integration event structure across applications

- **OpenTelemetry Observability Module**: Complete `neuroglia.observability` package for distributed tracing, metrics, and logging

  - **Configuration Management**: `OpenTelemetryConfig` dataclass with environment variable defaults and one-line initialization
  - **Automatic Instrumentation**: FastAPI, HTTPX, logging, and system metrics instrumentation out-of-the-box
  - **TracerProvider Setup**: Configurable OTLP gRPC exporters with batch processing and console debugging
  - **MeterProvider Integration**: Prometheus metrics endpoint with periodic export and custom metric creation
  - **Graceful Shutdown**: Proper resource cleanup with `shutdown_opentelemetry()` function

- **CQRS Tracing Middleware**: `TracingPipelineBehavior` for automatic command and query instrumentation

  - **Automatic Span Creation**: All commands and queries automatically traced with operation metadata
  - **Performance Metrics**: Built-in duration histograms for `command.duration` and `query.duration`
  - **Error Tracking**: Exception handling with span status and error attributes
  - **Zero-Code Instrumentation**: Add `services.add_pipeline_behavior(TracingPipelineBehavior)` for full CQRS tracing

- **Event Handler Tracing**: `TracedEventHandler` wrapper for domain event processing instrumentation

  - **Event Processing Spans**: Automatic tracing for all domain event handlers with event metadata
  - **Handler Performance**: Duration metrics and error tracking for event processing operations
  - **Context Propagation**: Trace context carried through event-driven workflows

- **Repository Tracing Mixin**: `TracedRepositoryMixin` for data access layer observability
  - **Database Operation Tracing**: Automatic spans for repository methods (get, save, delete, query)
  - **Query Performance**: Duration metrics for database operations with entity type metadata
  - **Error Handling**: Database exception tracking with proper span status codes

#### **Detailed Framework Component Enhancements**

- **Data Abstractions**: Enhanced Entity and VersionedState with timezone-aware UTC timestamps and comprehensive documentation
- **Infrastructure Module**: Added optional dependency handling with graceful imports for MongoDB, EventSourcing, FileSystem, and TracingMixin
- **Repository Abstractions**: Enhanced Repository and QueryableRepository base classes with improved async method signatures
- **MongoDB Integration**: Expanded MongoDB exports including EnhancedMongoRepository, MotorRepository, and query utilities
- **Enhanced MongoDB Repository**: Advanced repository with bulk operations, aggregation support, and comprehensive type handling
- **Unit of Work**: Enhanced IUnitOfWork with comprehensive documentation and automatic domain event collection patterns
- **Service Provider**: Enhanced ServiceLifetime with improved documentation and comprehensive service registration examples
- **CloudEvent Ingestor**: Added CloudEventIngestor hosted service with automatic type mapping and reactive stream processing
- **CloudEvent Publisher**: Enhanced CloudEventPublisher with HTTP publishing, retry logic, and comprehensive configuration options
- **Hosting Abstractions**: Enhanced HostBase and HostedService with improved lifecycle management and documentation
- **Enhanced Web Application Builder**: Multi-app support, advanced controller management, and intelligent registration capabilities
- **Mediation Module**: Enhanced exports including metrics middleware, simple mediator patterns, and comprehensive extension support
- **Domain Event Dispatching**: Enhanced middleware with outbox pattern implementation and comprehensive transactional consistency
- **JSON Serialization**: Enterprise-grade JSON serialization with intelligent type handling, enum support, and configurable type discovery

#### **Sample Application - Mario's Pizzeria Complete Rewrite**

- **UI/API Separation Architecture**: Comprehensive hybrid authentication and modern frontend

  - **IMPLEMENTATION_PLAN.md**: Complete roadmap for separating UI (session cookies) and API (JWT) authentication
  - **Parcel Build Pipeline**: Modern frontend build system with tree-shaking and asset optimization
  - **Hybrid Authentication Strategy**: Session-based auth for web UI, JWT for programmatic API access
  - **Multi-App Architecture**: Clear separation between customer-facing UI and external API integrations
  - **Security Best Practices**: HttpOnly cookies, CSRF protection, JWT with proper expiration
  - **Phase-by-Phase Implementation**: Detailed steps from build setup to production deployment

- **Complete Frontend UI Implementation**: Modern web interface for all user roles

  - **Customer Interface**: Menu browsing, cart management, order placement, order history
  - **Kitchen Dashboard**: Real-time order management with status updates and cooking workflow
  - **Delivery Dashboard**: Ready orders, delivery tour management, address handling
  - **Management Dashboard**: Operations monitoring, analytics, menu management, staff performance
  - **Role-Based Navigation**: Conditional menus and features based on user roles

- **Advanced Styling System**: Comprehensive SCSS architecture

  - **Component-Based Styles**: Separate stylesheets for management, kitchen, delivery, and menu components
  - **Bootstrap Integration**: Custom Bootstrap overrides with brand colors and animations
  - **Responsive Design**: Mobile-first approach with adaptive layouts
  - **Interactive Elements**: Hover effects, animations, and state-based styling

- **Authentication & Authorization**: Multi-role user system with demo accounts

  - **Role-Based Access Control**: Customer, chef, delivery driver, and manager roles
  - **Demo Credentials**: Pre-configured test accounts for each role type
  - **Session Management**: Secure session handling with role persistence
  - **Access Protection**: Route-level authorization with 403 error pages

- **Real-Time Features**: WebSocket integration for live updates

  - **Kitchen Order Updates**: Real-time order status changes for kitchen staff
  - **Delivery Notifications**: Live updates for ready orders and delivery assignments
  - **Management Dashboards**: Real-time metrics and operational monitoring
  - **Connection Status Indicators**: Visual feedback for WebSocket connectivity

- **Advanced Analytics**: Comprehensive business intelligence features
  - **Sales Analytics**: Revenue trends, order volumes, and performance metrics
  - **Pizza Popularity**: Ranking and analysis of menu item performance
  - **Staff Performance**: Kitchen and delivery team productivity tracking
  - **Customer Insights**: Order history, preferences, and VIP customer identification

### Fixed

- **Observability Stack - Grafana Traces Panel Issue Resolution**:
  - **Root Cause**: Discovered Grafana traces panels only support single trace IDs, not TraceQL search queries
  - **Solution**: Converted all traces panels to table view for multiple trace display
  - **Performance**: Disabled OTEL logging auto-instrumentation (was causing workstation slowdown)
  - **Documentation**: Added comprehensive TraceQL/PromQL cheat sheets and usage guides
  - **Files Updated**: All Grafana dashboard JSONs, Tempo configuration, observability documentation
  - **Impact**: Full distributed tracing operational with proper table views and Explore interface integration

## [0.4.8] - 2025-10-19

### Fixed

- **CRITICAL**: Fixed `AsyncCacheRepository.get_async()` deserialization error introduced in v0.4.7

  - **Problem**: `get_async()` was decoding bytes to str before passing to `JsonSerializer.deserialize()`

    - `JsonSerializer.deserialize()` expects `bytes` (or `bytearray`) and calls `.decode()` internally
    - When passed `str`, it crashes with `AttributeError: 'str' object has no attribute 'decode'`
    - This bug was introduced in v0.4.7 when trying to fix the pattern search bug
    - Affected ALL single-entity retrievals from cache (critical production bug)

  - **Solution**: Remove premature decode from cache repository methods

    - Removed `data.decode("utf-8")` from `get_async()`
    - Removed decode from `get_all_by_pattern_async()`
    - Pass bytes directly to serializer - it handles decoding internally
    - Serializer's `deserialize()` method is designed to accept bytes

  - **Impact**:

    - Single-entity cache retrieval now works correctly
    - Pattern-based queries continue to work (from v0.4.7 fix)
    - Session lifecycle and event processing fully functional
    - No more cascade failures in event handlers

  - **Files Changed**: `neuroglia/integration/cache_repository.py` lines 157-170, 211-220

  - **Root Cause Analysis**:
    - v0.4.6: Pattern search had decode issues
    - v0.4.7: Fixed pattern search but introduced decode in `get_async()` (wrong layer)
    - v0.4.8: Proper fix - let serializer handle all decoding

### Technical Details

- **Correct Data Flow**:

  1. Redis client returns `bytes` (with `decode_responses=False`)
  2. `_search_by_key_pattern_async()` normalizes str to bytes if needed
  3. Cache repository methods pass bytes directly to serializer
  4. `JsonSerializer.deserialize()` calls `.decode()` on bytes
  5. Deserialization completes successfully

- **Why Previous Fixes Failed**:
  - Attempted to decode at wrong layer (repository instead of serializer)
  - Created incompatibility between repository output and serializer input
  - Serializer already has robust decode logic

## [0.4.7] - 2025-10-19

### Fixed

- **CRITICAL**: Fixed `AsyncCacheRepository.get_all_by_pattern_async()` deserialization error

  - **Problem**: Pattern-based queries failed with `AttributeError: 'str' object has no attribute 'decode'`

    - Redis client may return strings (when `decode_responses=True`) or bytes (when `decode_responses=False`)
    - `_search_by_key_pattern_async()` was returning data as-is from Redis without normalizing the type
    - When Redis returned strings, the code expected bytes and failed during deserialization
    - Caused cascade failures in event-driven workflows relying on pattern searches

  - **Solution**: Normalize entity data to bytes in `_search_by_key_pattern_async()`

    - Added type check: if `entity_data` is `str`, encode to bytes (`entity_data.encode("utf-8")`)
    - Ensures consistent data type returned regardless of Redis client configuration
    - Existing decode logic in `get_all_by_pattern_async()` handles bytes correctly

  - **Impact**:

    - Pattern searches now work with both `decode_responses=True` and `decode_responses=False`
    - Prevents production failures in event processing that relies on cache pattern queries
    - Maintains backward compatibility with existing code expecting bytes

  - **Files Changed**: `neuroglia/integration/cache_repository.py` line 263-267

  - **Testing**: Added comprehensive test suite `test_cache_repository_pattern_search_fix.py`
    - Tests both string and bytes responses from Redis
    - Validates handling of mixed responses
    - Tests complex real-world patterns from production
    - Verifies error handling and filtering

### Technical Details

- **Root Cause**: Modern `redis-py` (v5.x) defaults to `decode_responses=True` for Python 3 compatibility
- **Compatibility**: Fix works with both old (`decode_responses=False`) and new (`decode_responses=True`) Redis client configurations
- **Data Flow**:
  1. Redis client returns data (str or bytes depending on configuration)
  2. `_search_by_key_pattern_async()` normalizes to bytes (NEW)
  3. `get_all_by_pattern_async()` decodes bytes to string
  4. Serializer receives consistent string input

## [0.4.6] - 2025-10-19

### Fixed

- **CRITICAL**: Fixed transient service resolution in scoped contexts

  - **Problem**: Transient services (like notification handlers) were built from root provider, preventing them from accessing scoped dependencies
  - **Solution**: Modified `ServiceScope.get_services()` to build transient services within scope context using `self._build_service(descriptor)`
  - **Impact**: Enables event-driven architecture where transient handlers can depend on scoped repositories
  - Resolves issue: "Scoped Services Cannot Be Resolved in Event Handlers"

- **Async Scope Disposal**: Added proper async disposal support for scoped services
  - Added `ServiceScope.dispose_async()` method for async resource cleanup
  - Calls `__aexit__()` for async context managers
  - Falls back to `__exit__()` for sync context managers
  - Also invokes `dispose()` method if present for explicit cleanup
  - Ensures proper resource cleanup after event processing, even in error scenarios

### Added

- `ServiceProviderBase.create_async_scope()` - Async context manager for scoped service resolution

  - Creates isolated scope per event/operation (similar to HTTP request scopes)
  - Automatic resource disposal on scope exit
  - Essential for event-driven architectures with scoped dependencies

- `Mediator.publish_async()` now creates async scope per notification

  - All notification handlers execute within same isolated scope
  - Handlers can depend on scoped services (repositories, UnitOfWork, DbContext)
  - Automatic scope disposal after all handlers complete

- Comprehensive test suite: `test_mediator_scoped_notification_handlers.py`
  - 10 tests covering scoped service resolution in event handlers
  - Tests for service isolation, sharing, disposal, and error handling
  - Validates backward compatibility with non-scoped handlers

### Technical Details

- **Service Lifetime Handling in Scopes**:

  - Singleton services: Retrieved from root provider (cached globally)
  - Scoped services: Built and cached within scope
  - Transient services: Built fresh in scope context (can access scoped dependencies)

- **Event-Driven Pattern Support**:
  - Each `CloudEvent` processed in isolated async scope
  - Scoped repositories shared across handlers for same event
  - Automatic cleanup prevents resource leaks

## [0.4.5] - 2025-10-19

### Fixed

- **CacheRepository Parameterization**: `AsyncCacheRepository.configure()` now registers parameterized singleton services
  - **BREAKING CHANGE**: Changed from non-parameterized to parameterized service registration
  - **Problem**: All entity types shared the same `CacheRepositoryOptions` and `CacheClientPool` instances
    - DI container couldn't distinguish between `CacheRepositoryOptions[User, str]` and `CacheRepositoryOptions[Order, int]`
    - Potential cache collisions between different entity types
    - Lost type safety benefits of generic repository pattern
  - **Solution**: Register type-specific singleton instances
    - `CacheRepositoryOptions[entity_type, key_type]` for each entity type
    - `CacheClientPool[entity_type, key_type]` for each entity type
    - DI container now resolves cache services independently per entity type
  - **Benefits**:
    - Type-safe cache resolution per entity type
    - Prevents cache collisions between different entity types
    - Full generic type support in DI container
    - Each entity gets dedicated cache configuration
  - **Requires**: neuroglia v0.4.3+ with type variable substitution support

### Added

- Comprehensive documentation: `notes/STRING_ANNOTATIONS_EXPLAINED.md`
  - Explains string annotations (forward references) in Python type hints
  - Details circular import prevention strategy
  - Shows impact of PEP 563 and `get_type_hints()` usage
  - Real-world Neuroglia framework examples
  - Best practices for using string annotations

### Changed

- Enhanced logging in `CacheRepository.configure()` to show entity and key types
  - Now logs: `"Redis cache repository configured for User[str] at localhost:6379"`
  - Helps debug multi-entity cache configurations

## [0.4.4] - 2025-10-19

### Fixed

- **CRITICAL**: Fixed string annotation (forward reference) resolution in DI container

  - DI container now properly resolves `"ClassName"` annotations to actual classes
  - Fixed crash with `AttributeError: 'str' object has no attribute '__name__'`
  - Affects AsyncCacheRepository and services using `from __future__ import annotations`
  - Comprehensive test coverage with 6 new tests

- Enhanced error message generation to handle all annotation types safely

  - String annotations (forward references)
  - Types without **name** attribute (typing constructs)
  - Regular types

- Updated CacheRepository to use parameterized types (v0.4.3)
  - CacheRepositoryOptions[TEntity, TKey]
  - CacheClientPool[TEntity, TKey]
  - Full type safety with type variable substitution

### Added

- Comprehensive test suite for string annotation handling
- Documentation for string annotation bug fix

## [0.4.3] - 2025-10-19

### Fixed

- **Type Variable Substitution in Generic Dependencies**: Enhanced DI container to properly substitute type variables in constructor parameters
  - **Problem**: Constructor parameters with type variables (e.g., `options: CacheRepositoryOptions[TEntity, TKey]`) were not being substituted with concrete types
    - When building `AsyncCacheRepository[MozartSession, str]`, parameters with `TEntity` and `TKey` were used as-is
    - DI container looked for `CacheRepositoryOptions[TEntity, TKey]` instead of `CacheRepositoryOptions[MozartSession, str]`
    - Service resolution failed with "cannot resolve service 'CacheRepositoryOptions'"
  - **Root Cause**: v0.4.2 fixed parameter resolution but didn't call `TypeExtensions._substitute_generic_arguments()`
    - Comment claimed "TypeVar substitution is handled by get_generic_arguments()" but wasn't actually performed
    - The substitution logic existed but wasn't being used at the critical point
  - **Solution**: Added type variable substitution in `_build_service()` methods
    - Both `ServiceScope._build_service()` and `ServiceProvider._build_service()` now call `TypeExtensions._substitute_generic_arguments()`
    - Type variables in constructor parameters are replaced with concrete types from service registration
    - Example: `CacheRepositoryOptions[TEntity, TKey]` → `CacheRepositoryOptions[MozartSession, str]`
  - **Impact**: Constructor parameters can now use type variables that match the service's generic parameters
    - Repositories with parameterized dependencies work correctly
    - Complex generic dependency graphs resolve properly
    - Type safety maintained throughout dependency injection
  - **Affected Scenarios**: Services with constructor parameters using type variables
    - `AsyncCacheRepository(options: CacheRepositoryOptions[TEntity, TKey])` pattern now works
    - Multiple parameterized dependencies in single constructor
    - Nested generic types with type variable substitution
  - **Migration**: No code changes required - enhancement enables previously failing patterns
  - **Testing**: Added 6 comprehensive test cases in `tests/cases/test_type_variable_substitution.py`

## [0.4.2] - 2025-10-19

### Fixed

- **Generic Type Resolution in Dependency Injection**: Fixed critical bug preventing resolution of parameterized generic types
  - **Root Cause**: `ServiceScope._build_service()` and `ServiceProvider._build_service()` attempted to reconstruct generic types by calling `__getitem__()` on origin class:
    - Tried `init_arg.annotation.__origin__.__getitem__(args)` which failed
    - `__origin__` returns the base class, not a generic alias
    - Classes don't have `__getitem__` unless explicitly defined
    - Manual reconstruction was unnecessary - annotation already properly parameterized
  - **Error**: `AttributeError: type object 'AsyncStringCacheRepository' has no attribute '__getitem__'`
  - **Solution**: Replaced manual reconstruction with Python's official typing utilities
    - Imported `get_origin()` and `get_args()` from typing module
    - Use annotation directly when it's a parameterized generic type
    - Simpler, more robust, standards-compliant approach
  - **Impact**: Generic types now resolve correctly in DI container
    - Services can depend on `Repository[User, int]` style types
    - Event handlers with multiple generic repositories work
    - Query handlers can access generic data access layers
    - Full CQRS pattern support with generic infrastructure
  - **Affected Scenarios**: All services depending on parameterized generic classes
    - Event handlers depending on generic repositories
    - Query handlers depending on generic data access layers
    - Any CQRS pattern implementation using generic infrastructure
  - **Migration**: No code changes required - bug fix makes existing patterns work
  - **Documentation**: Added comprehensive fix guide in `docs/fixes/GENERIC_TYPE_RESOLUTION_FIX.md`
  - **Testing**: Added 8 comprehensive test cases covering all scenarios

## [0.4.1] - 2025-10-19

### Fixed

- **Controller Routing Fix**: Fixed critical bug preventing controllers from mounting to FastAPI application
  - **Root Cause**: `WebHostBase.use_controllers()` had multiple bugs:
    - Instantiated controllers without dependency injection (`controller_type()` instead of retrieving from DI)
    - Called non-existent `get_route_prefix()` method on controller instances
    - Used incorrect `self.mount()` method instead of `self.include_router()`
  - **Solution - use_controllers() Rewrite**: Complete rewrite of controller mounting logic
    - Retrieves properly initialized controller instances from DI container via `services.get_services(ControllerBase)`
    - Accesses existing `controller.router` attribute (from Routable base class)
    - Uses correct FastAPI `include_router()` API with `/api` prefix
  - **Solution - Auto-Mounting Feature**: Enhanced `WebApplicationBuilder.build()` method
    - Added `auto_mount_controllers=True` parameter (default enabled)
    - Automatically calls `host.use_controllers()` during build process
    - 99% of use cases now work without manual mounting step
    - Optional manual control available by setting parameter to False
  - **Impact**: Controllers now properly mount to FastAPI application with all routes accessible
    - Swagger UI at `/api/docs` now shows all controller endpoints
    - OpenAPI spec at `/openapi.json` properly populated
    - API endpoints return 200 responses instead of 404 errors
  - **Migration**: No breaking changes - existing code continues to work, but explicit `use_controllers()` calls are now optional
  - **Documentation**: Added comprehensive fix guide and troubleshooting documentation in `docs/fixes/`
  - **Testing**: Added test suite validating DI registration, route mounting, and HTTP endpoint accessibility

### Documentation

- **Mario's Pizzeria Documentation Alignment**: Comprehensive update to align all documentation with actual codebase implementation
  - **Tutorial Updates**: Updated `mario-pizzeria-tutorial.md` with real project structure, actual application setup code, and multi-app architecture examples
  - **Domain Design Alignment**: Updated `domain-design.md` with actual Pizza entity implementation including real pricing logic (size multipliers: Small 1.0x, Medium 1.3x, Large 1.6x) and topping pricing ($2.50 each)
  - **Code Sample Accuracy**: Replaced all placeholder/conceptual code with actual implementation from `samples/mario-pizzeria/` codebase
  - **GitHub Repository Links**: Added direct GitHub repository links with line number references for easy navigation to source code
  - **Enhanced Code Formatting**: Improved MkDocs code presentation with `title` and `linenums` attributes for better readability
  - **Fixed Run Commands**: Corrected directory paths and execution instructions to match actual project structure
  - **Enum Documentation**: Added real `PizzaSize` and `OrderStatus` enumerations with proper GitHub source links
  - **Architecture Examples**: Updated with sophisticated multi-app setup, interface-based dependency injection, and auto-discovery configuration patterns

## [0.4.0] - 2025-09-26

### Added

- **Configurable Type Discovery**: Enhanced serialization with flexible domain module scanning

  - **TypeRegistry**: Centralized type discovery using framework's TypeFinder and ModuleLoader utilities
  - **Configurable JsonSerializer**: Applications can specify which modules to scan for enums and value types
  - **Multiple Configuration Methods**: Direct configuration, post-configuration registration, and TypeRegistry access
  - **Dynamic Type Discovery**: Runtime module scanning for advanced scenarios and microservice architectures
  - **Performance Optimized**: Type caching and efficient module scanning with fallback strategies
  - **Framework Agnostic**: No hardcoded domain patterns, fully configurable for any project structure
  - **Generic FileSystemRepository**: Complete repository pattern using framework's JsonSerializer for persistence
  - **Enhanced Mario Pizzeria**: Updated sample application demonstrating configurable type discovery patterns

- **Framework Configuration Examples**: Comprehensive JsonSerializer and TypeRegistry configuration patterns

  - **Documentation Examples**: Complete markdown guide with configuration patterns for different project structures
  - **Reusable Configuration Functions**: Python module with preset configurations for DDD, flat, and microservice architectures
  - **Project Structure Support**: Examples for domain-driven design, flat structure, and microservice patterns
  - **Dynamic Discovery Patterns**: Advanced configuration examples for runtime type discovery
  - **Performance Best Practices**: Guidance on efficient type registration and caching strategies

- **Reference Documentation**: Comprehensive Python language and framework reference guides

  - **Source Code Naming Conventions**: Complete guide to consistent naming across all architectural layers
    - **Layer-Specific Patterns**: API controllers, application handlers, domain entities, integration repositories
    - **Python Convention Adherence**: snake_case, PascalCase, UPPER_CASE usage patterns with framework examples
    - **Testing Conventions**: Test file, class, and method naming patterns for maintainable test suites
    - **File Organization**: Directory structure and file naming patterns for clean architecture
    - **Anti-Pattern Guidance**: Common naming mistakes and how to avoid them
    - **Mario's Pizzeria Examples**: Complete feature implementation showing all naming conventions
  - **12-Factor App Compliance**: Detailed guide showing how Neuroglia supports cloud-native architecture principles
    - **Comprehensive Coverage**: All 12 factors with practical Neuroglia implementation examples
    - **Codebase Management**: Single codebase, multiple deployment patterns with Docker and Kubernetes
    - **Dependency Management**: Poetry integration, dependency injection, and environment isolation
    - **Configuration Management**: Environment-based settings with Pydantic validation
    - **Backing Services**: Repository pattern abstraction for databases, caches, and external APIs
    - **Process Architecture**: Stateless design, horizontal scaling, and process type definitions
    - **Cloud-Native Deployment**: Production deployment patterns with container orchestration
  - **Python Modular Code**: In-depth guide to organizing Python code into maintainable modules
    - **Module Organization**: Package structure, import strategies, and dependency management
    - **Design Patterns**: Factory, plugin architecture, and configuration module patterns
    - **Testing Organization**: Test structure mirroring module organization with comprehensive fixtures
    - **Best Practices**: Single responsibility, high cohesion, low coupling principles
    - **Advanced Patterns**: Lazy loading, dynamic module discovery, and namespace management
  - **Python Object-Oriented Programming**: Complete OOP reference for framework development
    - **Core Concepts**: Classes, objects, encapsulation, inheritance, and composition with pizza examples
    - **Framework Patterns**: Entity base classes, repository inheritance, command/query handlers
    - **Advanced Patterns**: Abstract factories, strategy pattern, and polymorphism in practice
    - **Testing OOP**: Mocking inheritance hierarchies, testing composition, and object lifecycle management
    - **SOLID Principles**: Practical application of object-oriented design principles
  - **Cross-Reference Integration**: All reference documentation integrated throughout existing framework documentation
    - **Main Documentation**: Reference section added to index.md with comprehensive links
    - **Getting Started**: Framework standards section with naming conventions integration
    - **Feature Documentation**: Contextual links to relevant reference materials
    - **Sample Applications**: Reference links showing patterns used in OpenBank and Lab Resource Manager

- **Background Task Scheduling**: Comprehensive background job processing with APScheduler integration

  - **Scheduled Jobs**: Execute tasks at specific dates and times with `ScheduledBackgroundJob`
  - **Recurrent Jobs**: Execute tasks at regular intervals with `RecurrentBackgroundJob`
  - **Task Management**: Complete task lifecycle management with start, stop, and monitoring
  - **Background Task Bus**: Reactive streams for task coordination and event handling
  - **Redis Persistence**: Persistent task storage and distributed task coordination
  - **APScheduler Integration**: Full AsyncIOScheduler support with circuit breaker patterns
  - **Type Safety**: Strongly typed task descriptors and job configurations
  - **Framework Integration**: Seamless dependency injection and service provider integration

- **Redis Cache Repository**: High-performance distributed caching with advanced data structures

  - **Async Operations**: Full async/await support for non-blocking cache operations
  - **Hash Storage**: Redis hash-based storage for efficient field-level operations
  - **Distributed Locks**: `set_if_not_exists()` for distributed locking patterns
  - **Pattern Matching**: `get_all_by_pattern_async()` for bulk key retrieval
  - **Connection Pooling**: Redis connection pool management with circuit breaker
  - **Raw Operations**: Direct Redis access for advanced use cases
  - **Lua Script Support**: Execute Redis Lua scripts for atomic operations
  - **Type Safety**: Generic type support for compile-time type checking

- **HTTP Service Client**: Production-ready HTTP client with resilience patterns

  - **Circuit Breaker**: Automatic failure detection and service protection
  - **Retry Policies**: Exponential backoff, linear delay, and fixed delay strategies
  - **Request/Response Interceptors**: Middleware pattern for cross-cutting concerns
  - **Bearer Token Authentication**: Built-in OAuth/JWT token handling
  - **Request Logging**: Comprehensive HTTP request/response logging
  - **Timeout Management**: Configurable timeouts with proper error handling
  - **JSON Convenience Methods**: `get_json()`, `post_json()` for API interactions
  - **SSL Configuration**: Flexible SSL verification and certificate handling

- **Case Conversion Utilities**: Comprehensive string and object transformation utilities

  - **String Transformations**: snake_case, camelCase, PascalCase, kebab-case, Title Case
  - **Dictionary Transformations**: Recursive key conversion for nested data structures
  - **List Processing**: Handle arrays of objects with nested dictionary conversion
  - **Performance Optimized**: Efficient regex-based conversions with caching
  - **API Boundary Integration**: Seamless frontend/backend data format compatibility
  - **Pydantic Integration**: Optional CamelModel for automatic case conversion

- **Enhanced Model Validation**: Advanced business rule validation with fluent API

  - **Business Rules**: Fluent API for complex domain validation logic
  - **Conditional Validation**: Rules that apply only when specific conditions are met
  - **Property Validators**: Built-in validators for common scenarios (required, length, email, etc.)
  - **Entity Validators**: Complete object validation with cross-field rules
  - **Composite Validators**: Combine multiple validators with AND/OR logic
  - **Custom Validators**: Easy creation of domain-specific validation rules
  - **Validation Results**: Detailed error reporting with field-level error aggregation
  - **Exception Handling**: Rich exception hierarchy for different validation scenarios

- **Comprehensive Documentation**: New feature documentation with Mario's Pizzeria examples

  - **Background Task Scheduling**: Pizza order processing, kitchen automation, delivery coordination
  - **Redis Cache Repository**: Menu caching, order session management, inventory coordination
  - **HTTP Service Client**: Payment gateway integration, delivery service APIs, notification services
  - **Case Conversion Utilities**: API compatibility patterns for frontend/backend integration
  - **Enhanced Model Validation**: Pizza order validation, customer eligibility, inventory checks
  - **Architecture Diagrams**: Mermaid diagrams showing framework component interactions
  - **Testing Patterns**: Comprehensive test examples for all new framework features

- **Development Environment Configuration**: Enhanced development tooling and configuration

  - **VS Code Extensions**: Configured recommended extensions for Python development (`extensions.json`)
  - **Code Quality Tools**: Integrated Markdown linting (`.markdownlint.json`) and Prettier formatting (`.prettierrc`)
  - **Development Scripts**: Added comprehensive build and utility scripts in `scripts/` directory
  - **Makefile**: Standardized build commands and development workflow automation

- **Mario's Pizzeria Enhanced Sample**: Expanded the sample application with additional features
  - **Complete Sample Implementation**: Full working example in `samples/mario-pizzeria/`
  - **Comprehensive Test Suite**: Dedicated integration and unit tests in `tests/mario_pizzeria/`
  - **Test Configuration**: Mario's Pizzeria specific test configuration in `tests/mario_pizzeria_conftest.py`

### Enhanced

- **Framework Infrastructure**: Major framework capabilities expansion with production-ready components

  - **Optional Dependencies**: All new features properly handle missing dependencies with graceful fallbacks
  - **Error Handling**: Comprehensive exception hierarchy with detailed error messages
  - **Performance Optimization**: Async/await patterns throughout with connection pooling and caching
  - **Type Safety**: Full generic type support with proper type annotations
  - **Testing Coverage**: 71+ comprehensive tests covering all success and failure scenarios

- **Documentation Quality**: Professional documentation standards with consistent examples

  - **Mario's Pizzeria Context**: All new features documented with realistic restaurant scenarios
  - **Architecture Diagrams**: Mermaid diagrams showing framework integration patterns
  - **Code Examples**: Complete, runnable examples with proper error handling
  - **Cross-References**: Consistent linking between related framework features
  - **Testing Patterns**: Test-driven development examples for all new components

- **Framework Core Improvements**: Enhanced core framework capabilities

  - **Enhanced Web Application Builder**: Improved `src/neuroglia/hosting/enhanced_web_application_builder.py` with additional features
  - **Mediator Enhancements**: Updated `src/neuroglia/mediation/mediator.py` with improved functionality
  - **Dependency Management**: Updated `pyproject.toml` and `poetry.lock` with latest dependencies

- **Development Environment**: Improved developer experience and tooling

  - **VS Code Configuration**: Enhanced debugging configuration in `.vscode/launch.json`
  - **Settings Optimization**: Improved development settings in `.vscode/settings.json`
  - **Git Configuration**: Updated `.gitignore` for better file exclusion patterns

- **Documentation Architecture Reorganization**: Improved conceptual organization and navigation structure
  - **New Feature Documentation**: Added comprehensive documentation for previously undocumented features
    - **Serialization**: Complete guide to JsonSerializer with automatic type handling, custom encoders, and Mario's Pizzeria examples
    - **Object Mapping**: Advanced object-to-object mapping with Mapper class, custom transformations, and mapping profiles
    - **Reactive Programming**: Observable patterns with AsyncRx integration for event-driven architectures
  - **Pattern Organization**: Reorganized architectural patterns for better conceptual coherence
    - **Moved to Patterns Section**: Resource-Oriented Architecture, Watcher & Reconciliation Patterns, and Watcher & Reconciliation Execution
    - **Enhanced Pattern Integration**: Updated implementation flow showing Clean Architecture → CQRS → Event-Driven → Repository → Resource-Oriented → Watcher Patterns
    - **Improved Navigation**: Logical grouping of architectural patterns separate from framework-specific features
  - **Updated Navigation Structure**: Comprehensive mkdocs.yml updates reflecting new organization
    - Clear separation between architectural patterns and framework features
    - Enhanced pattern discovery and learning path guidance
    - Consistent Mario's Pizzeria examples throughout all new documentation

### Removed

- **Deprecated Validation Script**: Removed outdated `validate_mermaid.py` script in favor of improved documentation tooling

## [0.3.1] - 2025-09-25

### Added

- **PyNeuroctl CLI Tool**: Complete command-line interface for managing Neuroglia sample applications

  - **Process Management**: Start, stop, and monitor sample applications with proper PID tracking
  - **Log Management**: Capture and view application logs with real-time following capabilities
  - **Port Validation**: Automatic port availability checking and conflict detection
  - **Status Monitoring**: Real-time status reporting for all running sample applications
  - **Sample Validation**: Pre-flight configuration validation for sample applications
  - **Global Access**: Shell wrapper enabling pyneuroctl usage from any directory
  - **Environment Detection**: Intelligent Python environment detection (venv, Poetry, pyenv, system)
  - **Automated Setup**: Comprehensive installation scripts with PATH integration

- **Mario's Pizzeria Sample Application**: Complete production-ready CQRS sample demonstrating clean architecture
  - **Full CQRS Implementation**: Commands, queries, and handlers for pizza ordering workflow
  - **Domain-Driven Design**: Rich domain entities with business logic and validation
  - **Clean Architecture**: Proper layer separation with dependency inversion
  - **FastAPI Integration**: RESTful API with Swagger documentation and validation
  - **Event-Driven Patterns**: Domain events and handlers for order lifecycle management
  - **Repository Pattern**: File-based persistence with proper abstraction
  - **Comprehensive Testing**: Unit and integration tests with fixtures and mocks

### Enhanced

- **Code Organization**: Improved maintainability through proper file structure

  - **Domain Entity Separation**: Split monolithic domain entities into individual files
    - `enums.py`: PizzaSize and OrderStatus enumerations
    - `pizza.py`: Pizza entity with pricing logic and topping management
    - `customer.py`: Customer entity with contact information and validation
    - `order.py`: Order entity with business logic and status management
    - `kitchen.py`: Kitchen entity with capacity management and order processing
  - **Clean Import Structure**: Maintained backward compatibility with clean `__init__.py` exports
  - **Type Safety**: Enhanced type annotations and proper generic type usage
  - **Code Quality**: Consistent formatting, documentation, and error handling

- **Developer Experience**: Streamlined development workflow with powerful tooling
  - **One-Command Management**: Simple CLI commands for all sample application lifecycle operations
  - **Enhanced Logging**: Detailed debug information and structured log output
  - **Setup Automation**: Zero-configuration installation with automatic PATH management
  - **Cross-Platform Support**: Shell detection and environment compatibility across systems

### Technical Details

- **CLI Implementation**: `src/cli/pyneuroctl.py` with comprehensive process management

  - Socket-based port checking with proper resource cleanup
  - PID persistence with automatic cleanup of stale process files
  - Log file rotation and structured output formatting
  - Background process management with proper signal handling
  - Comprehensive error handling with user-friendly messages

- **Shell Integration**: Global pyneuroctl wrapper with environment detection

  - Bash script with intelligent Python interpreter discovery
  - PYTHONPATH configuration for proper module resolution
  - Symlink management for global CLI access
  - Installation validation with automated testing

- **Sample Application Structure**: Production-ready clean architecture implementation
  - API layer with FastAPI controllers and dependency injection
  - Application layer with CQRS handlers and service orchestration
  - Domain layer with entities, value objects, and business rules
  - Integration layer with repository implementations and external services

## [0.3.0] - 2025-09-22

### Added

- **Comprehensive Documentation Transformation**: Complete overhaul of all framework documentation using unified Mario's Pizzeria domain model
  - **Mario's Pizzeria Domain**: Unified business domain used consistently across all documentation sections
    - Complete pizza ordering system with Orders, Menu, Kitchen, Customer entities
    - Rich business scenarios: order placement, kitchen workflow, payment processing, status updates
    - Production-ready patterns demonstrated through realistic restaurant operations
    - OAuth authentication, file-based persistence, MongoDB integration, event sourcing examples
  - **Enhanced Getting Started Guide**: Complete rewrite with 7-step pizzeria application tutorial
    - Step-by-step construction of full pizzeria management system
    - Enhanced web builder configuration with OAuth authentication
    - File-based repository implementation with persistent data storage
    - Complete application lifecycle from startup to production deployment
  - **Unified Architecture Documentation**: Clean architecture demonstrated through pizzeria layers
    - API Layer: OrdersController, MenuController, KitchenController with OAuth security
    - Application Layer: PlaceOrderHandler, GetMenuHandler with complete CQRS workflows
    - Domain Layer: Order, Pizza, Customer entities with business rule validation
    - Integration Layer: FileOrderRepository, PaymentService, SMS notifications
  - **Comprehensive Feature Documentation**: All framework features illustrated through pizzeria examples
    - **CQRS & Mediation**: Complete pizza ordering workflow with commands, queries, events
    - **Dependency Injection**: Service registration patterns for pizzeria repositories and services
    - **Data Access**: File-based persistence, MongoDB integration, event sourcing for kitchen workflow
    - **MVC Controllers**: RESTful API design with authentication, validation, error handling
    - **Event Sourcing**: Kitchen workflow tracking with order state transitions and notifications
  - **Main Documentation Index**: Framework introduction with pizzeria quick start example
    - Comprehensive framework overview with practical pizzeria API demonstration
    - Progressive learning path from basic concepts to advanced clean architecture
    - Feature showcase with pizzeria examples for each major framework component
    - Installation guide with optional dependencies and development setup instructions

### Enhanced

- **Developer Experience**: Dramatically improved documentation quality and consistency

  - **Unified Examples**: Single coherent business domain replaces scattered abstract examples
  - **Practical Learning Path**: Real-world pizzeria scenarios demonstrate production patterns
  - **Consistent Cross-References**: All documentation sections reference the same domain model
  - **Maintainable Structure**: Standardized pizzeria examples reduce documentation maintenance burden
  - **Enhanced Readability**: Business-focused examples are more engaging and understandable

- **Framework Documentation Structure**: Complete reorganization for better developer onboarding
  - **Pizzeria Domain Model**: Central domain specification used across all documentation
  - **Progressive Complexity**: Learning path from simple API to complete clean architecture
  - **Production Examples**: OAuth authentication, data persistence, event handling through pizzeria
  - **Testing Patterns**: Comprehensive testing strategies demonstrated through business scenarios

### Technical Details

- **Documentation Files Transformed**: Complete rewrite of all major documentation sections

  - `docs/index.md`: Framework introduction with pizzeria quick start and feature showcase
  - `docs/getting-started.md`: 7-step pizzeria tutorial with enhanced web builder
  - `docs/architecture.md`: Clean architecture layers demonstrated through pizzeria workflow
  - `docs/features/cqrs-mediation.md`: Pizza ordering CQRS patterns with event handling
  - `docs/features/dependency-injection.md`: Service registration for pizzeria infrastructure
  - `docs/features/data-access.md`: File repositories, MongoDB, event sourcing for pizzeria data
  - `docs/features/mvc-controllers.md`: Pizzeria API controllers with OAuth and validation
  - `docs/mario-pizzeria.md`: Complete bounded context specification with detailed domain model

- **Quality Improvements**: Professional documentation standards throughout

  - **Consistent Business Domain**: Mario's Pizzeria used in 100+ examples across all documentation
  - **Cross-Reference Validation**: All internal links verified and working properly
  - **Code Example Quality**: Complete, runnable examples with proper error handling
  - **Progressive Learning**: Documentation structured for step-by-step skill building

- **Navigation and Structure**: Improved documentation organization
  - Updated `mkdocs.yml` with enhanced navigation structure
  - Removed outdated sample application documentation
  - Added Resilient Handler Discovery feature documentation
  - Streamlined feature organization for better discoverability

## [0.2.0] - 2025-09-22

### Added

- **Resilient Handler Discovery**: Enhanced Mediator with fallback discovery for mixed codebases

  - **Automatic Fallback**: When package imports fail, automatically discovers individual modules
  - **Legacy Migration Support**: Handles packages with broken dependencies while still discovering valid handlers
  - **Comprehensive Logging**: Debug, info, and warning levels show what was discovered vs skipped
  - **Zero Breaking Changes**: 100% backward compatible with existing `Mediator.configure()` calls
  - **Real-world Scenarios**: Supports incremental CQRS migration, optional dependencies, mixed architectures
  - **Individual Module Discovery**: Scans package directories for .py files without importing the package
  - **Graceful Error Handling**: Continues discovery even when some modules fail to import
  - **Production Ready**: Minimal performance impact, detailed diagnostics, and robust error recovery

- **MongoDB Infrastructure Extensions**: Complete type-safe MongoDB data access layer

  - **TypedMongoQuery**: Type-safe MongoDB querying with automatic dictionary-to-entity conversion
    - Direct MongoDB cursor optimization for improved performance
    - Complex type handling for enums, dates, and nested objects
    - Seamless integration with existing MongoQuery decorator patterns
    - Query chaining methods with automatic type inference
  - **MongoSerializationHelper**: Production-ready complex type serialization/deserialization
    - Full Decimal type support with precision preservation for financial applications
    - Safe enum type checking with proper class validation using `inspect.isclass()`
    - Comprehensive datetime and date object handling
    - Nested object serialization with constructor parameter analysis
    - Value object and entity serialization support with automatic type resolution
  - **Enhanced module exports**: Clean import paths via updated `__init__.py` files
    - `from neuroglia.data.infrastructure.mongo import TypedMongoQuery, MongoSerializationHelper`

- **Enhanced MongoDB Repository**: Advanced MongoDB operations for production applications

  - **Bulk Operations**: High-performance bulk insert, update, and delete operations
    - `bulk_insert_async()`: Efficient batch document insertion with validation
    - `update_many_async()`: Bulk document updates with MongoDB native filtering
    - `delete_many_async()`: Batch deletion operations with query support
  - **Advanced Querying**: MongoDB aggregation pipelines and native query support
    - `aggregate_async()`: Full MongoDB aggregation framework integration
    - `find_async()`: Advanced querying with pagination, sorting, and projections
    - Native MongoDB filter support alongside repository pattern abstraction
  - **Upsert Operations**: `upsert_async()` for insert-or-update scenarios
  - **Production Features**: Comprehensive error handling, logging, and async/await patterns
  - **Type Safety**: Full integration with MongoSerializationHelper for complex type handling

- **Enhanced Web Application Builder**: Multi-application hosting with advanced controller management
  - **Multi-FastAPI Application Support**: Host multiple FastAPI applications within single framework instance
    - Independent application lifecycles and configurations
    - Shared service provider and dependency injection across applications
    - Application-specific middleware and routing configurations
  - **Advanced Controller Registration**: Flexible controller management with prefix support
    - `add_controllers_with_prefix()`: Register controllers with custom URL prefixes
    - Controller deduplication tracking to prevent double-registration
    - Automatic controller discovery from multiple module paths
  - **Exception Handling Middleware**: Production-ready error handling with RFC 7807 compliance
    - `ExceptionHandlingMiddleware`: Converts exceptions to Problem Details format
    - Comprehensive error logging with request context information
    - HTTP status code mapping for different exception types
  - **Enhanced Web Host**: `EnhancedWebHost` for multi-application serving
    - Unified hosting model for complex microservice architectures
    - Service provider integration across application boundaries

### Enhanced

- **Framework Architecture**: Production-ready infrastructure capabilities

  - MongoDB data access layer now supports enterprise-grade applications
  - Type-safe operations throughout the data access stack
  - Comprehensive error handling and logging across all infrastructure components
  - Async/await patterns implemented consistently for optimal performance

- **Developer Experience**: Improved tooling and type safety
  - IntelliSense support for all new infrastructure components
  - Comprehensive docstrings with usage examples and best practices
  - Type hints throughout for better IDE integration and compile-time error detection
  - Clear separation of concerns between data access, serialization, and web hosting layers

### Technical Details

- **Test Coverage**: Comprehensive test suites for all new infrastructure components

  - **MongoDB Serialization**: 12 comprehensive tests covering complex type scenarios
    - Decimal serialization/deserialization with precision validation
    - Enum type safety with proper class validation
    - Datetime and nested object round-trip serialization integrity
    - Error handling for invalid type conversions and edge cases
  - **Enhanced Repository**: 21 comprehensive tests covering all advanced operations
    - Complete CRUD operation validation with type safety
    - Bulk operations testing with large datasets and error scenarios
    - Aggregation pipeline integration and complex query validation
    - Pagination, sorting, and advanced filtering capabilities
  - **Enhanced Web Builder**: 16 comprehensive tests for multi-application hosting
    - Multi-app controller registration and deduplication validation
    - Exception handling middleware with proper Problem Details formatting
    - Service provider integration across application boundaries
    - Build process validation and application lifecycle management

- **Performance Optimizations**: Infrastructure tuned for production workloads

  - Direct MongoDB cursor integration bypasses unnecessary data transformations
  - Bulk operations reduce database round-trips for large-scale operations
  - Type-safe serialization optimized for complex business domain objects
  - Multi-application hosting with shared resource optimization

- **Standards Compliance**: Enterprise integration ready
  - RFC 7807 Problem Details implementation for standardized API error responses
  - MongoDB best practices implemented throughout data access layer
  - FastAPI integration patterns following framework conventions
  - Proper async/await implementation for high-concurrency scenarios

## [0.1.10] - 2025-09-21

### Fixed

- **Critical Infrastructure**: Resolved circular import between core framework modules

  - Fixed circular dependency chain: `serialization.json` → `hosting.web` → `mvc.controller_base` → `serialization.json`
  - Implemented TYPE_CHECKING import pattern to break dependency cycle while preserving type hints
  - Added late imports in runtime methods to maintain functionality without circular dependencies
  - Converted direct imports to quoted type annotations for forward references
  - Fixed TypeFinder.get_types method with proper @staticmethod decorator
  - Framework modules (JsonSerializer, ControllerBase, WebApplicationBuilder) can now be imported without errors
  - Critical infrastructure issue that prevented proper module loading has been resolved

- **Eventing Module**: Added missing DomainEvent export
  - Re-exported DomainEvent from data.abstractions in eventing module for convenient access
  - Both `neuroglia.data` and `neuroglia.eventing` import paths now work for DomainEvent
  - Maintains backward compatibility with existing data module imports
  - Eventing module now provides complete event functionality (CloudEvent + DomainEvent)
  - Converted direct imports to quoted type annotations for forward references
  - Fixed TypeFinder.get_types method with proper @staticmethod decorator
  - Framework modules (JsonSerializer, ControllerBase, WebApplicationBuilder) can now be imported without errors
  - Critical infrastructure issue that prevented proper module loading has been resolved

## [0.1.9] - 2025-09-21

### Enhanced

- **Documentation**: Comprehensive documentation enhancement for core framework classes

  - Added extensive docstrings to `OperationResult` class with usage patterns and best practices
  - Enhanced `ProblemDetails` class documentation with RFC 7807 compliance details
  - Included practical code examples for CQRS handlers, controllers, and manual construction
  - Added property documentation for computed properties (`is_success`, `error_message`, `status_code`)
  - Documented framework integration patterns with RequestHandler, ControllerBase, and Mediator
  - Provided type safety guidance and TypeScript-like usage examples
  - Added cross-references to related framework components and standards

- **Dependencies**: Optimized dependency organization for better modularity and lighter installs
  - **Core Dependencies**: Reduced to essential framework requirements only
    - `fastapi`, `classy-fastapi`, `pydantic-settings`, `python-dotenv`, `typing-extensions`, `annotated-types`
  - **Optional Dependencies**: Organized into logical groups with extras
    - `web` extra: `uvicorn`, `httpx` for web hosting and HTTP client features
    - `mongodb` extra: `pymongo` for MongoDB repository implementations
    - `eventstore` extra: `esdbclient`, `rx` for event sourcing capabilities
    - `grpc` extra: `grpcio` for gRPC communication support
    - `all` extra: includes all optional dependencies
  - **Documentation Dependencies**: Moved to optional `docs` group
    - `mkdocs`, `mkdocs-material`, `mkdocs-mermaid2-plugin` for documentation generation
  - **Removed Unused**: Eliminated `multipledispatch` (not used in framework)

### Fixed

- **Code Quality**: Resolved trailing whitespace and formatting issues

  - Fixed whitespace consistency across core modules
  - Improved code formatting in `__init__.py` files
  - Maintained strict linting compliance for better code quality

- **Version Management**: Updated package version to 0.1.9 throughout project files

### Technical Details

- **Developer Experience**: Enhanced IntelliSense and documentation generation
  - Comprehensive docstrings now provide rich IDE tooltips and autocomplete information
  - Usage examples demonstrate real-world patterns for command handlers and queries
  - Best practices section guides proper error handling and type safety
- **Standards Compliance**: Maintained RFC 7807 adherence while extending for framework needs
  - ProblemDetails follows HTTP API error reporting standards
  - OperationResult provides functional error handling patterns
  - Thread safety and performance considerations documented
- **Dependency Management**: Improved install flexibility and reduced bloat
  - Default installation ~70% lighter (only core dependencies)
  - Feature-specific installs via extras: `pip install neuroglia-python[web,mongodb]`
  - Clear separation between framework core and optional integrations
  - Streamlined version constraints for better compatibility

## [0.1.8] - 2025-09-20

### Fixed

- **Critical**: Resolved circular import issue preventing `neuroglia.mediation.Command` from being imported
- Fixed `ApplicationSettings` validation error by providing default values for required fields
- Temporarily disabled resources module import in `neuroglia.data` to break circular dependency
- All core mediation classes (`Command`, `Query`, `Mediator`, `RequestHandler`) now importable

### Technical Details

- Addressed circular import chain: mediation → data.abstractions → data.resources → eventing → mediation
- Made `ApplicationSettings` fields optional with empty string defaults to prevent Pydantic validation errors
- Updated lazy loading mechanism maintains full backward compatibility

## [0.1.7] - 2025-09-20log

All notable changes to the Neuroglia Python framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.7] - 2025-09-20

### Added

- **Type Stub Infrastructure**: Complete type stub implementation for external package usage

  - Added `py.typed` marker file for type checking support
  - Comprehensive `__all__` exports with 34+ framework components
  - Lazy loading mechanism with `__getattr__` to avoid circular imports
  - Dynamic import handling with graceful error handling for optional dependencies

- **Module Organization**: Improved module structure and initialization

  - Added missing `__init__.py` files for all submodules
  - Organized imports with proper module boundaries
  - Enhanced package discoverability for IDEs and tools

- **Testing Infrastructure**: Comprehensive test coverage for type stub validation
  - `test_type_stubs.py` - Full framework component testing
  - `test_type_stubs_simple.py` - Core functionality validation
  - `test_documentation_report.py` - Coverage analysis and documentation

### Changed

- **Sample Code Organization**: Reorganized test files and examples for better maintainability

  - **Mario Pizzeria Tests**: Moved domain-specific tests to `samples/mario-pizzeria/tests/` directory
  - **Framework Tests**: Relocated generic tests to `tests/cases/` for proper framework testing
  - **Configuration Examples**: Moved configuration patterns to `docs/examples/` for reusability
  - **Import Path Updates**: Fixed all import statements for relocated test files
  - **Directory Cleanup**: Removed temporary test data and organized file structure
  - **Documentation Integration**: Added examples section to MkDocs navigation

- **Import Resolution**: Fixed circular import issues throughout the framework

  - Updated relative imports in `core/operation_result.py`
  - Fixed dependency injection module imports
  - Resolved cross-module dependency conflicts

- **Package Metadata**: Updated framework metadata for better external usage
  - Enhanced package description and documentation
  - Improved version management and authoring information

### Fixed

- **Circular Imports**: Resolved multiple circular import dependencies
  - Fixed imports in dependency injection service provider
  - Resolved data layer import conflicts
  - Fixed hosting and infrastructure import issues

### Technical Details

- **Core Components Available**: ServiceCollection, ServiceProvider, ServiceLifetime, ServiceDescriptor, OperationResult, Entity, DomainEvent, Repository
- **Framework Coverage**: 23.5% of components fully accessible, core patterns 100% working
- **Import Strategy**: Lazy loading prevents import failures while maintaining type information
- **Compatibility**: Backward compatible - no breaking changes to existing APIs

### Developer Experience

- **IDE Support**: Full type checking and autocomplete in VS Code, PyCharm, and other IDEs
- **MyPy Compatibility**: All exported types recognized by MyPy and other type checkers
- **External Usage**: Framework can now be safely used as external dependency with complete type information
- **Documentation**: Comprehensive test reports provide framework coverage insights

---

## [0.1.6] - Previous Release

### Features

- Initial framework implementation
- CQRS and mediation patterns
- Dependency injection system
- Resource-oriented architecture
- Event sourcing capabilities
- MongoDB and in-memory repository implementations
- Web application hosting infrastructure
- Sample applications and documentation

### Infrastructure

- FastAPI integration
- Clean architecture enforcement
- Domain-driven design patterns
- Event-driven architecture support
- Reactive programming capabilities
