# Application Builder Unification Plan

## Executive Summary

This document provides a comprehensive analysis and recommendation for unifying the `WebApplicationBuilder` and `EnhancedWebApplicationBuilder` implementations while maintaining backward compatibility and preserving all advanced features.

## Current State Analysis

### 1. Core Implementation: `WebApplicationBuilder` (web.py)

**Location**: `src/neuroglia/hosting/web.py`

**Key Features**:

- ✅ Basic FastAPI integration via `WebHost` and `WebHostBase`
- ✅ Automatic controller discovery and registration
- ✅ Simple DI container integration
- ✅ `HostedService` lifecycle management via `Host`
- ✅ Exception handling middleware
- ✅ Clean, minimal API surface
- ✅ Auto-mount controllers option in `build()`

**Limitations**:

- ❌ No multi-app support
- ❌ No flexible prefix management per app
- ❌ No observability integration
- ❌ No lifespan builder method
- ❌ No app_settings management
- ❌ Cannot mount controllers to different FastAPI apps
- ❌ No controller deduplication tracking

**Usage Pattern**:

```python
builder = WebApplicationBuilder()
builder.add_controllers(["api.controllers"])
app = builder.build()  # Auto-mounts controllers
app.use_controllers()  # Optional explicit call
app.run()
```

**Used By**:

- `samples/openbank`
- `samples/desktop-controller`
- `samples/lab_resource_manager`
- `samples/api-gateway`
- Most test cases

### 2. Enhanced Implementation: `EnhancedWebApplicationBuilder`

**Location**: `src/neuroglia/hosting/enhanced_web_application_builder.py`

**Key Features**:

- ✅ All core features from `WebApplicationBuilder`
- ✅ Multi-app support (main app + UI app + API app)
- ✅ Flexible controller registration with custom prefixes per app
- ✅ Controller deduplication tracking by app
- ✅ `build_app_with_lifespan()` method for advanced lifecycle control
- ✅ Integrated observability configuration
- ✅ App settings management and DI registration
- ✅ Pending controller registration queue
- ✅ Enhanced exception handling
- ✅ OpenTelemetry instrumentation integration

**Limitations**:

- ⚠️ More complex API surface
- ⚠️ Requires app_settings parameter
- ⚠️ Separate file creates maintenance burden

**Usage Pattern**:

```python
builder = EnhancedWebApplicationBuilder(app_settings)
builder.add_controllers(["api.controllers"], app=api_app, prefix="/api/v1")
app = builder.build_app_with_lifespan(title="My App", version="1.0.0")
# Or for advanced scenarios
host = builder.build()  # Returns WebHost
```

**Used By**:

- `samples/mario-pizzeria` (complex multi-app scenario)

### 3. Base Abstractions: `ApplicationBuilderBase` (abstractions.py)

**Location**: `src/neuroglia/hosting/abstractions.py`

**Key Features**:

- ✅ Defines fundamental builder interface
- ✅ Manages `ServiceCollection` and `ApplicationSettings`
- ✅ Provides `build()` abstract method
- ✅ Integrates `HostApplicationLifetime`

**Issues**:

- ⚠️ `ApplicationSettings` and observability settings are disconnected
- ⚠️ No built-in support for advanced features

## Comparison Matrix

| Feature                       | WebApplicationBuilder | EnhancedWebApplicationBuilder | Required?    |
| ----------------------------- | --------------------- | ----------------------------- | ------------ |
| Basic controller registration | ✅                    | ✅                            | ✅ Essential |
| Auto-mount controllers        | ✅                    | ✅                            | ✅ Essential |
| Simple build() method         | ✅                    | ✅                            | ✅ Essential |
| HostedService support         | ✅                    | ✅                            | ✅ Essential |
| Exception handling            | ✅                    | ✅                            | ✅ Essential |
| Multi-app support             | ❌                    | ✅                            | 🔶 Advanced  |
| Custom prefix per app         | ❌                    | ✅                            | 🔶 Advanced  |
| App settings integration      | ❌                    | ✅                            | 🔶 Advanced  |
| build_app_with_lifespan()     | ❌                    | ✅                            | 🔶 Advanced  |
| Observability integration     | ❌                    | ✅                            | 🔶 Advanced  |
| Controller deduplication      | ❌                    | ✅                            | 🔶 Advanced  |
| Pending registration queue    | ❌                    | ✅                            | 🔶 Advanced  |

## Recommended Unified Architecture

### Design Principles

1. **Backward Compatibility First**: All existing code using `WebApplicationBuilder` must work without changes
2. **Progressive Enhancement**: Advanced features are opt-in, not required
3. **Single Source of Truth**: One builder class with smart defaults
4. **Clean API Surface**: Simple for basic use cases, powerful for advanced scenarios
5. **No Breaking Changes**: Maintain all existing method signatures

### Proposed Unified Class Hierarchy

```
ApplicationBuilderBase (abstractions.py)
    ├── ApplicationBuilder (abstractions.py) - For non-web apps
    └── WebApplicationBuilderBase (web.py) - Abstract base for web apps
            └── WebApplicationBuilder (web.py) - Unified implementation
```

### Implementation Strategy: Merge Enhanced Features into Core

**File to Modify**: `src/neuroglia/hosting/web.py`

**File to Deprecate**: `src/neuroglia/hosting/enhanced_web_application_builder.py`

### Unified WebApplicationBuilder API

```python
class WebApplicationBuilder(WebApplicationBuilderBase):
    """
    Unified web application builder supporting both simple and advanced scenarios.

    Simple Usage (backward compatible):
        builder = WebApplicationBuilder()
        builder.add_controllers(["api.controllers"])
        app = builder.build()
        app.run()

    Advanced Usage (multi-app, observability):
        builder = WebApplicationBuilder(app_settings)
        builder.add_controllers(["api.controllers"], app=custom_app, prefix="/api/v1")
        app = builder.build_app_with_lifespan(title="My App")
    """

    def __init__(self, app_settings: Optional[ApplicationSettings] = None):
        """
        Initialize builder with optional settings.

        Args:
            app_settings: Optional application settings. If provided, enables
                         advanced features like observability and multi-app support.
        """
        super().__init__()

        # Advanced features (only if app_settings provided)
        self._app_settings = app_settings or ApplicationSettings()
        self._main_app = None
        self._registered_controllers: dict[str, set[str]] = {}
        self._pending_controller_modules: list[dict] = []
        self._observability_config = None

        # Auto-register app_settings in DI container
        if app_settings:
            self.services.add_singleton(type(app_settings), lambda: app_settings)

    @property
    def app(self) -> Optional[FastAPI]:
        """Get the main FastAPI app, if built."""
        return self._main_app

    def build(self, auto_mount_controllers: bool = True) -> WebHostBase:
        """
        Build web host with configured services (backward compatible).

        Args:
            auto_mount_controllers: Auto-mount registered controllers (default: True)

        Returns:
            WebHostBase with FastAPI integration
        """
        # Use EnhancedWebHost if advanced features are used
        if self._registered_controllers or self._pending_controller_modules:
            host = EnhancedWebHost(self.services.build())
        else:
            host = WebHost(self.services.build())

        self._main_app = host

        # Process pending controller registrations
        self._process_pending_controllers()

        if auto_mount_controllers:
            host.use_controllers()

        return host

    def build_app_with_lifespan(
        self,
        title: str = None,
        description: str = "",
        version: str = None,
        debug: bool = None
    ) -> FastAPI:
        """
        Build FastAPI app with integrated Host lifespan and observability.

        This advanced method provides:
        - Automatic HostedService lifecycle management
        - Integrated observability endpoints
        - OpenTelemetry instrumentation
        - Smart defaults from app_settings

        Args:
            title: App title (defaults to app_settings.service_name)
            description: App description
            version: App version (defaults to app_settings.service_version)
            debug: Debug mode (defaults to app_settings.debug)

        Returns:
            FastAPI app with full lifecycle support
        """
        # Implementation from EnhancedWebApplicationBuilder
        # (Full code omitted for brevity - see detailed implementation below)
        pass

    def add_controllers(
        self,
        modules: list[str],
        app: Optional[FastAPI] = None,
        prefix: Optional[str] = None
    ) -> ServiceCollection:
        """
        Register controllers from modules.

        Simple Usage (backward compatible):
            builder.add_controllers(["api.controllers"])

        Advanced Usage (multi-app):
            builder.add_controllers(["api.controllers"], app=custom_app, prefix="/api/v1")

        Args:
            modules: Module names containing controllers
            app: Optional FastAPI app (uses main app if None)
            prefix: Optional URL prefix for controllers

        Returns:
            ServiceCollection for chaining
        """
        # Register with DI container
        self._register_controller_types(modules)

        # If app provided, register immediately (advanced mode)
        if app is not None:
            self._register_controllers_to_app(modules, app, prefix)
        elif prefix is not None:
            # Prefix without app means pending registration (advanced mode)
            self._pending_controller_modules.append({
                "modules": modules,
                "app": None,
                "prefix": prefix
            })
        # else: simple mode - controllers registered via build() -> use_controllers()

        return self.services

    def add_exception_handling(self, app: Optional[FastAPI] = None):
        """Add exception handling middleware to app."""
        # Implementation from EnhancedWebApplicationBuilder
        pass

    # Private helper methods
    def _register_controller_types(self, modules: list[str]) -> None:
        """Register controller types with DI container."""
        # Implementation from parent class and EnhancedWebApplicationBuilder
        pass

    def _register_controllers_to_app(
        self,
        modules: list[str],
        app: FastAPI,
        prefix: Optional[str] = None
    ) -> None:
        """Register controllers to specific app with deduplication."""
        # Implementation from EnhancedWebApplicationBuilder
        pass

    def _process_pending_controllers(self) -> None:
        """Process pending controller registrations."""
        if not self._main_app or not self._pending_controller_modules:
            return

        for registration in self._pending_controller_modules:
            if registration.get("app") is None:  # Main app registrations
                self._register_controllers_to_app(
                    registration["modules"],
                    self._main_app,
                    registration.get("prefix")
                )

        self._pending_controller_modules.clear()

    def _setup_observability_endpoints(self, app: FastAPI) -> None:
        """Add observability endpoints if configured."""
        # Implementation from EnhancedWebApplicationBuilder
        pass

    def _setup_observability_instrumentation(self, app: FastAPI) -> None:
        """Apply OpenTelemetry instrumentation."""
        # Implementation from EnhancedWebApplicationBuilder
        pass
```

## Migration Path

### Phase 1: Unification (Immediate)

1. ✅ **Copy enhanced features into `web.py`**

   - Move all methods from `EnhancedWebApplicationBuilder` into `WebApplicationBuilder`
   - Make `app_settings` parameter optional in `__init__()`
   - Maintain all existing method signatures

2. ✅ **Update `EnhancedWebHost` in `web.py`**

   - Move `EnhancedWebHost` class to `web.py`
   - Keep as internal implementation detail

3. ✅ **Add backward compatibility mode detection**
   - If `app_settings` is None: simple mode (existing behavior)
   - If `app_settings` provided: advanced mode (enhanced features)
   - If controllers registered without app/prefix: simple mode
   - If controllers registered with app/prefix: advanced mode

### Phase 2: Deprecation (Next Release)

1. ✅ **Mark `enhanced_web_application_builder.py` as deprecated**

   ```python
   # enhanced_web_application_builder.py
   import warnings
   from neuroglia.hosting.web import WebApplicationBuilder as UnifiedWebApplicationBuilder

   warnings.warn(
       "EnhancedWebApplicationBuilder is deprecated. Use WebApplicationBuilder instead.",
       DeprecationWarning,
       stacklevel=2
   )

   # Alias for backward compatibility
   EnhancedWebApplicationBuilder = UnifiedWebApplicationBuilder
   ```

2. ✅ **Update documentation**

   - Mark `EnhancedWebApplicationBuilder` as deprecated
   - Update all docs to use unified `WebApplicationBuilder`

3. ✅ **Update samples to use unified builder**
   - Mario's Pizzeria: Change to `WebApplicationBuilder(app_settings)`
   - Keep existing samples unchanged (they already use `WebApplicationBuilder`)

### Phase 3: Removal (Future Release)

1. ✅ **Remove deprecated file**
   - Delete `enhanced_web_application_builder.py` after 2-3 releases
   - Ensure no imports remain

## Testing Strategy

### Unit Tests Required

1. **Backward Compatibility Tests** (highest priority)

   ```python
   def test_simple_mode_without_settings():
       """Test that existing code works without changes"""
       builder = WebApplicationBuilder()
       builder.add_controllers(["test.controllers"])
       app = builder.build()
       assert app is not None

   def test_auto_mount_default_behavior():
       """Test auto-mount is enabled by default"""
       builder = WebApplicationBuilder()
       builder.add_controllers(["test.controllers"])
       app = builder.build()  # Should auto-mount
       # Verify controllers are mounted
   ```

2. **Advanced Features Tests**

   ```python
   def test_multi_app_registration():
       """Test registering controllers to different apps"""
       builder = WebApplicationBuilder(app_settings)
       api_app = FastAPI()
       builder.add_controllers(["test.api"], app=api_app, prefix="/api/v1")
       # Verify controllers registered to correct app

   def test_build_with_lifespan():
       """Test advanced lifespan builder"""
       builder = WebApplicationBuilder(app_settings)
       app = builder.build_app_with_lifespan(title="Test App")
       assert app.title == "Test App"
   ```

3. **Deduplication Tests**

   ```python
   def test_controller_deduplication():
       """Test controllers aren't registered twice"""
       builder = WebApplicationBuilder(app_settings)
       app = FastAPI()
       builder.add_controllers(["test.controllers"], app=app)
       builder.add_controllers(["test.controllers"], app=app)
       # Verify controllers only registered once
   ```

### Integration Tests Required

1. **Mario's Pizzeria compatibility**
2. **OpenBank compatibility**
3. **Desktop Controller compatibility**
4. **Observability integration**

## Benefits of Unification

### For Users

✅ **Simpler Mental Model**

- One builder class for all scenarios
- Progressive disclosure of complexity
- No confusion about which builder to use

✅ **Backward Compatibility**

- Existing code works without changes
- No migration required for simple use cases

✅ **Easier Onboarding**

- Single builder to learn
- Advanced features discoverable through IDE

### For Maintainers

✅ **Reduced Code Duplication**

- Single implementation to maintain
- Consistent behavior across scenarios

✅ **Easier Testing**

- Test one class instead of two
- Reduced test surface area

✅ **Better Documentation**

- Single source of truth for docs
- Clearer examples

### For Framework

✅ **Cleaner Architecture**

- Follows Single Responsibility Principle
- Better separation of concerns

✅ **Extensibility**

- Easier to add new features
- Clear extension points

## Risks and Mitigation

### Risk 1: Breaking Existing Code

**Likelihood**: Low
**Impact**: High

**Mitigation**:

- Extensive backward compatibility tests
- Deprecation warnings before removal
- Multiple release cycle for migration

### Risk 2: Increased Complexity in Core Class

**Likelihood**: Medium
**Impact**: Medium

**Mitigation**:

- Use optional parameters with smart defaults
- Keep simple mode truly simple
- Clear separation of simple vs advanced code paths
- Comprehensive inline documentation

### Risk 3: Test Coverage Gaps

**Likelihood**: Medium
**Impact**: Medium

**Mitigation**:

- Achieve 90%+ test coverage for unified class
- Test both simple and advanced modes
- Integration tests for all samples

## Implementation Checklist

### Phase 1: Unification

- [ ] Copy enhanced methods to `WebApplicationBuilder` in `web.py`
- [ ] Add optional `app_settings` parameter to `__init__()`
- [ ] Implement mode detection logic
- [ ] Move `EnhancedWebHost` to `web.py`
- [ ] Add private helper methods for advanced features
- [ ] Update `__all__` exports
- [ ] Run existing tests - ensure nothing breaks

### Phase 2: Testing

- [ ] Create backward compatibility test suite
- [ ] Create advanced features test suite
- [ ] Test all sample applications
- [ ] Test with and without observability
- [ ] Test multi-app scenarios
- [ ] Achieve 90%+ coverage

### Phase 3: Documentation

- [ ] Update `docs/getting-started.md`
- [ ] Update framework documentation
- [ ] Add migration guide
- [ ] Update sample documentation
- [ ] Add docstrings with examples

### Phase 4: Deprecation

- [ ] Add deprecation warnings to `enhanced_web_application_builder.py`
- [ ] Create alias for backward compatibility
- [ ] Update CHANGELOG.md
- [ ] Announce deprecation in release notes

### Phase 5: Cleanup (Future)

- [ ] Remove deprecated file (2-3 releases later)
- [ ] Remove deprecation warnings
- [ ] Final documentation cleanup

## Conclusion

The unification of `WebApplicationBuilder` and `EnhancedWebApplicationBuilder` is **highly recommended** and **feasible** with minimal risk. The proposed approach:

1. ✅ Maintains full backward compatibility
2. ✅ Preserves all advanced features
3. ✅ Simplifies the framework architecture
4. ✅ Reduces maintenance burden
5. ✅ Improves developer experience

The key insight is that **optional parameters and smart defaults** allow a single class to serve both simple and advanced use cases without forcing complexity on basic users.

## Next Steps

1. **Review this plan** with the team
2. **Approve the approach**
3. **Begin Phase 1 implementation**
4. **Create comprehensive test suite**
5. **Update documentation**
6. **Release with deprecation warnings**
7. **Monitor feedback**
8. **Complete removal in future release**
