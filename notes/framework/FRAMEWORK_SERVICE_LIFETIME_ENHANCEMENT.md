# Framework Enhancement Recommendations: Service Lifetime Architecture

**Date**: October 9, 2025
**Priority**: HIGH
**Impact**: Framework Core Architecture
**Breaking Changes**: None (backward compatible)

---

## Executive Summary

The current service lifetime error is a **symptom of an architectural limitation** in the Mediator pattern implementation. While the immediate fix (changing services to transient) resolves the issue, a **proper framework enhancement** would eliminate the root cause and provide better developer experience.

**Current Workaround**: Make pipeline behaviors transient
**Recommended Solution**: Enable mediator to use scoped service resolution
**Impact**: Better resource management, clearer architecture, no workarounds needed

---

## 📊 Problem Analysis

### Current Architecture

```python
┌─────────────────────────────────────────────────────────────┐
│ Application Startup                                          │
│  └─► ServiceProvider.build() → Creates root provider        │
│       └─► Mediator registered as SINGLETON                  │
│            └─► self._service_provider = root_provider       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ HTTP Request → Controller → mediator.execute_async()        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Mediator.execute_async() [Line 513]                         │
│  1. Creates scope for handler ✅                            │
│     scope = self._service_provider.create_scope()           │
│     handler = scope.get_service(handler_class)              │
│                                                              │
│  2. Gets behaviors from ROOT provider ❌                    │
│     behaviors = self._get_pipeline_behaviors(request)       │
│     └─► Line 607: self._service_provider.get_services(...)  │
│                                                              │
│  3. Builds pipeline and executes                            │
└─────────────────────────────────────────────────────────────┘
```

### The Core Issue

**Line 607 in mediator.py**:

```python
all_behaviors = self._service_provider.get_services(PipelineBehavior)
```

This **always** uses the root provider, which:

- ✅ Can resolve `Singleton` services
- ✅ Can resolve `Transient` services
- ❌ **CANNOT** resolve `Scoped` services (by design)

**Why scoped services fail from root provider**:

1. **Memory Leak Prevention**: Scoped services hold per-request state
2. **Disposal Boundaries**: No clear disposal point at root level
3. **Thread Safety**: Root provider is shared across all requests
4. **Resource Management**: Scoped resources need request-level cleanup

---

## 🎯 Recommended Framework Changes

### Change 1: Enhanced Mediator with Scoped Resolution

**File**: `src/neuroglia/mediation/mediator.py`

#### Current Implementation (Lines 513-558)

```python
async def execute_async(self, request: Request) -> OperationResult:
    """Executes the specified request through the pipeline behaviors and handler"""

    # Create scope for handler
    scope = self._service_provider.create_scope()
    try:
        provider: ServiceProviderBase = scope.get_service_provider()
        handler = provider.get_service(handler_class)

        # ❌ Problem: behaviors resolved from root
        behaviors = self._get_pipeline_behaviors(request)

        if not behaviors:
            return await handler.handle_async(request)

        return await self._build_pipeline(request, handler, behaviors)
    finally:
        if hasattr(scope, "dispose"):
            scope.dispose()
```

#### Recommended Enhanced Implementation

```python
async def execute_async(self, request: Request) -> OperationResult:
    """Executes the specified request through the pipeline behaviors and handler"""
    log.info(f"🔍 MEDIATOR: Starting execute_async for request: {type(request).__name__}")

    # Create scope for BOTH handler AND pipeline behaviors
    scope = self._service_provider.create_scope()
    try:
        # Get scoped service provider
        provider: ServiceProviderBase = scope.get_service_provider()

        # Resolve handler from scope
        handler = self._resolve_handler(request, provider)

        # ✅ Enhancement: Resolve behaviors from SCOPED provider
        behaviors = self._get_pipeline_behaviors(request, provider)

        if not behaviors:
            return await handler.handle_async(request)

        return await self._build_pipeline(request, handler, behaviors)
    finally:
        if hasattr(scope, "dispose"):
            scope.dispose()


def _get_pipeline_behaviors(
    self,
    request: Request,
    provider: Optional[ServiceProviderBase] = None
) -> list[PipelineBehavior]:
    """
    Gets all registered pipeline behaviors that can handle the specified request type.

    Args:
        request: The request being processed
        provider: Optional scoped provider to use for resolution.
                  Falls back to root provider for backward compatibility.

    Returns:
        List of pipeline behaviors that can handle this request
    """
    behaviors = []
    try:
        # ✅ Use provided scoped provider if available, otherwise use root
        service_provider = provider if provider is not None else self._service_provider

        # Get all registered pipeline behaviors from appropriate provider
        all_behaviors = service_provider.get_services(PipelineBehavior)

        if all_behaviors:
            # Filter behaviors that can handle this request type
            for behavior in all_behaviors:
                if self._behavior_can_handle(behavior, type(request)):
                    behaviors.append(behavior)

        log.debug(f"Found {len(behaviors)} pipeline behaviors for {type(request).__name__}")

    except Exception as ex:
        log.warning(
            f"Error getting pipeline behaviors: {ex}",
            exc_info=True
        )

    return behaviors
```

**Benefits**:

- ✅ Behaviors can now be `Scoped` or `Transient`
- ✅ Scoped dependencies in behaviors work correctly
- ✅ **Backward compatible** (falls back to root provider if no scope provided)
- ✅ Proper resource disposal within request scope
- ✅ Better alignment with ASP.NET Core Mediator patterns

---

### Change 2: Enhanced ServiceScope for Transient Resolution

**File**: `src/neuroglia/dependency_injection/service_provider.py`

#### Current Implementation (Lines 199-250)

The `ServiceScope` class already handles transient services correctly:

```python
class ServiceScope(ServiceScopeBase, ServiceProviderBase):
    def get_service(self, type: type) -> Optional[any]:
        # ... scoped service handling ...

        # For transient services, build in scope context
        if root_descriptor is not None:
            if root_descriptor.lifetime == ServiceLifetime.TRANSIENT:
                return self._build_service(root_descriptor)  # ✅ Already correct!
```

**No changes needed here** - the ServiceScope already properly resolves transient services in the scope context, which allows transient services to get scoped dependencies.

---

### Change 3: Documentation Updates

#### File: `docs/features/simple-cqrs.md`

Add section on **Pipeline Behavior Lifetimes**:

````markdown
## Pipeline Behavior Service Lifetimes

Pipeline behaviors can use any service lifetime:

### Transient Behaviors (Recommended for Stateless)

```python
# Lightweight, stateless behaviors
services.add_transient(
    PipelineBehavior,
    implementation_factory=lambda sp: LoggingBehavior(
        sp.get_required_service(ILogger)
    )
)
```
````

### Scoped Behaviors (For Per-Request State)

```python
# Behaviors that need per-request dependencies
services.add_scoped(
    PipelineBehavior,
    implementation_factory=lambda sp: TransactionBehavior(
        sp.get_required_service(IUnitOfWork),  # Scoped dependency
        sp.get_required_service(IDbContext)    # Scoped dependency
    )
)
```

**Note**: With the enhanced mediator (v1.x.x+), pipeline behaviors are resolved from the scoped service provider, allowing them to use scoped dependencies correctly.

````

#### File: `docs/guides/dependency-injection-patterns.md` (New)

Create comprehensive guide on service lifetime patterns and best practices.

---

## 📋 Implementation Plan

### Phase 1: Core Framework Enhancement (2-3 hours)

1. **Modify Mediator.execute_async()** ✅
   - Pass scoped provider to `_get_pipeline_behaviors()`
   - Ensure scope disposal happens correctly
   - Add comprehensive logging for debugging

2. **Update _get_pipeline_behaviors()** ✅
   - Accept optional provider parameter
   - Use scoped provider when available
   - Fall back to root provider for backward compatibility

3. **Add Unit Tests** ✅
   - Test scoped behavior resolution
   - Test backward compatibility with transient behaviors
   - Test proper disposal of scoped services
   - Test error handling and logging

### Phase 2: Testing & Validation (1-2 hours)

1. **Create Test Scenarios**:
   ```python
   # Test scoped pipeline behavior
   def test_scoped_pipeline_behavior_resolution():
       services = ServiceCollection()
       services.add_scoped(IUnitOfWork, UnitOfWork)
       services.add_scoped(
           PipelineBehavior,
           implementation_factory=lambda sp: TransactionBehavior(
               sp.get_required_service(IUnitOfWork)
           )
       )
       # Should NOT throw "Failed to resolve scoped service"

   # Test transient still works
   def test_transient_pipeline_behavior_backward_compatibility():
       # Existing transient behaviors should continue working

   # Test mixed lifetimes
   def test_mixed_pipeline_behavior_lifetimes():
       # Can have both scoped and transient behaviors
````

2. **Integration Testing**:
   - Test with mario-pizzeria sample
   - Test with openbank sample
   - Verify all existing tests still pass

### Phase 3: Documentation (1 hour)

1. Update feature documentation
2. Add migration guide for existing applications
3. Update samples to demonstrate both patterns
4. Add troubleshooting section

### Phase 4: Release & Migration (30 minutes)

1. Version bump (1.x.x → 1.y.0 - minor version)
2. Update CHANGELOG.md
3. Release notes with examples
4. Migration guide for existing apps

---

## 🔄 Migration Impact

### For Existing Applications

**No breaking changes** - existing code continues working:

```python
# Old approach (still works)
builder.services.add_transient(
    PipelineBehavior,
    implementation_factory=lambda sp: DomainEventDispatchingMiddleware(
        sp.get_required_service(IUnitOfWork),
        sp.get_required_service(Mediator)
    ),
)
```

**New capability unlocked**:

```python
# New approach (now possible)
builder.services.add_scoped(
    PipelineBehavior,
    implementation_factory=lambda sp: DomainEventDispatchingMiddleware(
        sp.get_required_service(IUnitOfWork),  # Can be scoped!
        sp.get_required_service(Mediator)
    ),
)
```

### For Framework Users

**Benefits**:

- ✅ More flexible service lifetime choices
- ✅ Better resource management
- ✅ Clearer architectural patterns
- ✅ No workarounds needed
- ✅ Matches ASP.NET Core patterns

**No Action Required**:

- Existing transient behaviors continue working
- No code changes needed
- Automatic upgrade path

---

## 💡 Additional Framework Improvements

### Enhancement 1: Scoped Mediator Context

**Concept**: Provide access to current execution context in behaviors

```python
class ExecutionContext:
    """Provides access to current mediator execution state"""
    request: Request
    scope: ServiceScope
    correlation_id: str
    user_context: Optional[UserContext]
    metadata: dict[str, any]

class PipelineBehavior(ABC):
    async def handle_async(
        self,
        request: Request,
        next: RequestHandlerDelegate,
        context: ExecutionContext  # ✅ New parameter
    ) -> OperationResult:
        # Access execution context
        log.info(f"Correlation ID: {context.correlation_id}")
        # ... behavior logic ...
```

**Benefits**:

- Better observability
- Easier testing
- Rich contextual information
- Correlation ID tracking

### Enhancement 2: Behavior Ordering

**Concept**: Explicit control over behavior execution order

```python
@behavior(order=1)
class LoggingBehavior(PipelineBehavior):
    # Executes first
    pass

@behavior(order=2)
class ValidationBehavior(PipelineBehavior):
    # Executes second
    pass

@behavior(order=3)
class TransactionBehavior(PipelineBehavior):
    # Executes third
    pass
```

### Enhancement 3: Conditional Behaviors

**Concept**: Behaviors that apply conditionally

```python
class ConditionalBehavior(PipelineBehavior):
    def should_execute(self, request: Request) -> bool:
        # Only execute for commands, not queries
        return isinstance(request, Command)

    async def handle_async(self, request: Request, next: RequestHandlerDelegate):
        if not self.should_execute(request):
            return await next(request)
        # ... behavior logic ...
```

---

## 📊 Performance Considerations

### Current Workaround (Transient Services)

**Pros**:

- ✅ Works immediately
- ✅ No framework changes needed
- ✅ Simple to understand

**Cons**:

- ❌ New instance per command (allocation overhead)
- ❌ Can't share state across behaviors
- ❌ Workaround, not proper solution

### Recommended Enhancement (Scoped Resolution)

**Pros**:

- ✅ Proper resource management
- ✅ One instance per request (better performance)
- ✅ Natural disposal boundaries
- ✅ Can share state within request
- ✅ Matches industry patterns

**Cons**:

- ❌ Requires framework modification
- ❌ More complex implementation
- ✅ But backward compatible!

**Performance Impact**:

- Minimal (scope already created for handlers)
- Potentially better (fewer allocations with scoped)
- Better memory management

---

## 🧪 Test Coverage Requirements

### Unit Tests (Framework Level)

```python
# Test: Scoped behavior resolution
test_mediator_resolves_scoped_behaviors_from_scope()

# Test: Backward compatibility
test_mediator_transient_behaviors_still_work()

# Test: Mixed lifetimes
test_mediator_handles_mixed_behavior_lifetimes()

# Test: Proper disposal
test_scoped_behaviors_disposed_after_request()

# Test: Error handling
test_mediator_handles_behavior_resolution_errors()

# Test: Dependency injection
test_scoped_behavior_gets_scoped_dependencies()
```

### Integration Tests (Sample Applications)

```python
# Test: mario-pizzeria with scoped behaviors
test_place_order_with_scoped_event_dispatching()

# Test: openbank with scoped behaviors
test_create_account_with_scoped_transaction_behavior()

# Test: Performance
test_scoped_behaviors_performance_acceptable()
```

---

## 🎓 Developer Experience Impact

### Before Enhancement

```python
# Developers must understand this limitation:
# ❌ Can't do this:
builder.services.add_scoped(
    PipelineBehavior,
    implementation_factory=lambda sp: MyBehavior(
        sp.get_required_service(IScopedDependency)  # ERROR!
    )
)

# ✅ Must do this instead:
builder.services.add_transient(IScopedDependency)  # Workaround
builder.services.add_transient(PipelineBehavior, ...)  # Workaround
```

**Developer Confusion**:

- "Why can't I use scoped services?"
- "This works in ASP.NET Core MediatR..."
- "What's the difference between scoped and transient again?"

### After Enhancement

```python
# Developers can use natural patterns:
# ✅ This just works:
builder.services.add_scoped(IUnitOfWork, UnitOfWork)
builder.services.add_scoped(
    PipelineBehavior,
    implementation_factory=lambda sp: MyBehavior(
        sp.get_required_service(IUnitOfWork)  # ✅ Works!
    )
)

# ✅ Or transient still works:
builder.services.add_transient(PipelineBehavior, ...)
```

**Developer Clarity**:

- ✅ Intuitive service lifetime choices
- ✅ Matches patterns from other frameworks
- ✅ No workarounds needed
- ✅ Clear error messages if something goes wrong

---

## 🚀 Rollout Strategy

### Stage 1: Framework Enhancement (Week 1)

- [ ] Implement mediator changes
- [ ] Add comprehensive unit tests
- [ ] Update framework documentation
- [ ] Code review and refinement

### Stage 2: Beta Testing (Week 2)

- [ ] Deploy to beta branch
- [ ] Test with all sample applications
- [ ] Performance benchmarking
- [ ] Community testing and feedback

### Stage 3: Documentation (Week 3)

- [ ] Update all documentation
- [ ] Create migration guide
- [ ] Record video tutorial
- [ ] Update samples to demonstrate both patterns

### Stage 4: Release (Week 4)

- [ ] Merge to main branch
- [ ] Version bump (1.y.0)
- [ ] Release announcement
- [ ] Update package repositories
- [ ] Monitor for issues

---

## 📚 References & Prior Art

### ASP.NET Core MediatR Pattern

```csharp
// In ASP.NET Core, this pattern works naturally:
services.AddScoped<IPipelineBehavior<TRequest, TResponse>, TransactionBehavior>();
services.AddScoped<IUnitOfWork, UnitOfWork>();

// Because MediatR resolves behaviors from scoped container
```

**Neuroglia should match this pattern** for consistency with industry standards.

### Spring Framework Scoping

Spring's `@RequestScope` provides similar scoped lifetime management for web requests.

### Django Request Middleware

Django's middleware pattern shows how request-scoped processing should work.

---

## ✅ Recommendation Summary

### Immediate Action (Application Level) - **DONE**

- ✅ Change `PipelineBehavior` to transient
- ✅ Change `IUnitOfWork` to transient
- ✅ Document the workaround
- ✅ Deploy to production

### Medium-Term Action (Framework Level) - **RECOMMENDED**

**Priority: HIGH**
**Timeline: 1-2 weeks**
**Effort: 4-6 hours development + testing**
**Breaking Changes: NONE**

#### Core Changes:

1. **Modify `Mediator.execute_async()`**
   - Pass scoped provider to behavior resolution
   - Maintain backward compatibility
2. **Update `_get_pipeline_behaviors()`**

   - Accept optional scoped provider parameter
   - Fall back to root provider if not provided

3. **Add comprehensive tests**

   - Scoped behavior resolution
   - Backward compatibility
   - Error handling

4. **Update documentation**
   - Service lifetime best practices
   - Migration guide
   - Enhanced samples

#### Benefits:

- ✅ Eliminates root cause of the issue
- ✅ Better developer experience
- ✅ More flexible architecture
- ✅ Matches industry patterns
- ✅ No breaking changes
- ✅ Better resource management

#### Risks:

- ⚠️ Requires framework testing
- ⚠️ Need to ensure backward compatibility
- ⚠️ Documentation updates needed
- ✅ But overall LOW RISK (well-understood pattern)

---

## 🎯 Final Verdict

### Current Solution (Transient Services)

**Status**: ✅ **ACCEPTABLE** for immediate deployment
**Use Case**: Production hotfix, quick resolution
**Limitations**: Workaround, not architectural solution

### Recommended Solution (Framework Enhancement)

**Status**: 🎯 **RECOMMENDED** for framework improvement
**Use Case**: Long-term proper solution
**Timeline**: Next sprint/release cycle
**Priority**: HIGH (improves developer experience significantly)

---

**The immediate transient fix resolves the production issue, but the framework enhancement eliminates the root cause and provides a better foundation for future development.**

---

_Document created: October 9, 2025_
_Framework version: 1.x.x_
_Status: Recommendation for review and implementation_
