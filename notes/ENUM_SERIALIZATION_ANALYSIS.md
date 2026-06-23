# Enum Serialization Analysis

## Current State

### Serialization (Writing to MongoDB)

**Location**: `src/neuroglia/serialization/json.py` - Line 111

```python
def default(self, o: Any) -> Any:
    if issubclass(type(o), Enum):
        return o.name  # Uses enum NAME for serialization
```

**Behavior**: Enums are **always serialized using `.name`** (e.g., `"READY"`, `"PENDING"`, `"COOKING"`)

**Rationale**: As documented in code comments, using `.name` provides "stable storage" - enum names don't change even if values are modified.

### Deserialization (Reading from MongoDB)

The framework has **multiple layers** of enum matching with increasing flexibility:

#### Layer 1: Direct Type Deserialization (Most Specific)

**Location**: `json.py` - Line 724

```python
elif hasattr(expected_type, "__bases__") and expected_type.__bases__ and issubclass(expected_type, Enum):
    for enum_member in expected_type:
        if enum_member.value == value or enum_member.name == value:
            return enum_member
```

**Behavior**: When the expected type is explicitly an Enum, matches **both `.value` AND `.name`**

#### Layer 2: Intelligent Type Inference (Fallback)

**Location**: `json.py` - Line 571 (`_basic_enum_detection`)

```python
for enum_member in attr:
    if enum_member.value == value or enum_member.value == value.lower() or \
       enum_member.name == value or enum_member.name == value.upper():
        return enum_member
```

**Behavior**: Attempts to match enums with **case-insensitive** matching on both `.value` and `.name`

#### Layer 3: TypeRegistry (Most Flexible)

**Location**: `src/neuroglia/core/type_registry.py` - Line 111

```python
def _try_match_enum_value(self, value: str, enum_type: type[Enum]) -> Optional[Enum]:
    for enum_member in enum_type:
        if enum_member.value == value or enum_member.value == value.lower() or \
           enum_member.name == value or enum_member.name == value.upper():
            return enum_member
```

**Behavior**: Global type registry matches with **case-insensitive** logic on both `.value` and `.name`

## The Problem We Encountered

### Root Cause

When we were comparing enums **in application code** (not during deserialization), we were using:

```python
# ❌ WRONG - Comparing enum.value against stored enum.name
order.state.status.value in ["ready", "delivering"]  # Looks for "ready"
# But MongoDB has: "READY" (stored as enum.name)
```

This failed because:

1. **Serialization** used `.name` → stored as `"READY"`
2. **Application queries** used `.value` → compared against `"ready"`
3. String comparison `"READY" != "ready"` → **No match!**

### Why Deserialization Worked But Queries Failed

- **Deserialization from MongoDB → Python objects**: ✅ Works fine!

  - `JsonSerializer` correctly converts `"READY"` string → `OrderStatus.READY` enum
  - Uses the flexible matching logic (checks both `.name` and `.value`)

- **Application queries comparing enum properties**: ❌ Failed!
  - We were doing: `order.state.status.value == "ready"`
  - But the enum was `OrderStatus.READY` (with `.name = "READY"` and `.value = "ready"`)
  - Comparing `.value` ("ready") against stored `.name` ("READY") failed

## Configuration System

### Type Registry Configuration

The `TypeRegistry` is configured to scan specific modules for enum discovery:

```python
# In main.py
JsonSerializer.configure(builder, ["domain.entities.enums", "domain.entities"])
```

**What this does**:

1. Registers modules to scan for Enum types
2. Caches discovered enums for fast lookup
3. Used during intelligent type inference when explicit type hints are missing

**Location of registration**: `json.py` - Lines 765-777

```python
@staticmethod
def configure(builder: "ApplicationBuilderBase", modules: Optional[list[str]] = None):
    # ... service registration ...

    if modules:
        try:
            from neuroglia.core.type_registry import get_type_registry
            type_registry = get_type_registry()
            type_registry.register_modules(modules)
        except ImportError:
            pass
```

## Is It Possible to Make It More Flexible?

### Answer: **It Already Is Flexible!** 🎉

The deserialization **already supports both `.name` and `.value` matching**:

```python
# These all work during deserialization:
'{"status": "READY"}'      # Matches OrderStatus.READY by name
'{"status": "ready"}'      # Matches OrderStatus.READY by value
'{"status": "COOKING"}'    # Matches OrderStatus.COOKING by name
'{"status": "cooking"}'    # Matches OrderStatus.COOKING by value
```

### What Wasn't Flexible

The **application code** wasn't using the deserialized enums correctly:

```python
# ❌ WRONG - Manual string comparison
if order.state.status.value == "ready":  # Fragile, depends on value

# ✅ CORRECT - Use enum directly
if order.state.status == OrderStatus.READY:  # Type-safe, IDE-friendly

# ✅ ALSO CORRECT - Use enum.name for string comparison
if order.state.status.name == "READY":  # Matches serialization format
```

## Historical Context: Did It Use `.value` Before?

Looking at the code history and documentation:

### Evidence for `.name` Being Long-Standing

1. **Line 111 comment**: "Use enum name for consistent serialized representation"
2. **Line 90 documentation**: Explicitly states enums are "Converted to their name"
3. **Example output** (Line 100): Shows `"status": "ACTIVE"` (uppercase name)

### Possible Confusion Sources

1. **Deserialization accepts `.value`** - might have created impression it was primary
2. **Case-insensitive matching** - makes it work with lowercase values too
3. **Different behavior** - serialize with `.name`, accept `.value` during read

## Recommendations

### ✅ Current Approach (What We Fixed)

**Use `.name` consistently in application code to match serialization format**

```python
# MongoDB queries
{"status": OrderStatus.READY.name}  # "READY"

# Application comparisons
if order.state.status.name in ["READY", "DELIVERING"]:
    # Process delivery
```

**Benefits**:

- ✅ Matches serialization format exactly
- ✅ Case-sensitive, predictable
- ✅ Works with MongoDB queries
- ✅ Stable even if enum values change

### ⚠️ Alternative: Change Serialization to Use `.value`

We **could** change Line 111 to use `.value` instead:

```python
def default(self, o: Any) -> Any:
    if issubclass(type(o), Enum):
        return o.value  # Change from o.name to o.value
```

**Drawbacks**:

- ❌ **Breaking change** - all existing data would need migration
- ❌ Less stable - enum values might change in refactoring
- ❌ Lowercase values ("ready", "cooking") less readable in database
- ❌ Would need to update all MongoDB documents

### 🚫 Not Recommended: Mixed Approach

Don't mix `.name` and `.value` in the same application:

```python
# ❌ DON'T DO THIS
if order.state.status.value == "ready":  # Sometimes .value
if order.state.status.name == "READY":   # Sometimes .name
```

This creates confusion and bugs.

## Best Practices Going Forward

### 1. For MongoDB Queries

```python
# ✅ ALWAYS use .name
query = {"status": OrderStatus.READY.name}
query = {"status": {"$nin": [OrderStatus.DELIVERED.name, OrderStatus.CANCELLED.name]}}
```

### 2. For Application Comparisons

```python
# ✅ BEST - Direct enum comparison
if order.state.status == OrderStatus.READY:

# ✅ ACCEPTABLE - Use .name for string comparison
if order.state.status.name == "READY":

# ✅ ACCEPTABLE - Use .name for list checks
if order.state.status.name in ["READY", "DELIVERING"]:

# ❌ AVOID - Don't use .value unless you have a specific reason
if order.state.status.value == "ready":  # Inconsistent with storage
```

### 3. For API Responses (DTOs)

```python
# ✅ Use .value for API output (lowercase, more JSON-friendly)
order_dto = OrderDto(
    status=order.state.status.value  # "ready" in JSON
)
```

**Rationale**:

- Internal storage uses `.name` (uppercase, stable)
- External APIs use `.value` (lowercase, JSON-friendly)
- Clear separation of concerns

### 4. Testing

```python
# ✅ Test both serialization and deserialization
def test_enum_roundtrip():
    order = Order(status=OrderStatus.READY)
    json_text = serializer.serialize_to_text(order)

    # Verify stored as name
    assert '"READY"' in json_text

    # Verify deserialization works with both
    order1 = serializer.deserialize_from_text('{"status": "READY"}', Order)
    order2 = serializer.deserialize_from_text('{"status": "ready"}', Order)

    assert order1.status == OrderStatus.READY
    assert order2.status == OrderStatus.READY
```

## Summary

### Current State ✅

- **Serialization**: Uses `.name` (stable, uppercase)
- **Deserialization**: Accepts both `.name` AND `.value` (flexible, case-insensitive)
- **TypeRegistry**: Configurable module scanning for enum discovery

### The Fix ✅

- Updated **application code** to use `.name` instead of `.value` for consistency
- Fixed 5 query handlers and 5 repository methods
- All enum comparisons now align with serialization format

### No Framework Changes Needed ✅

- The framework **already handles both `.name` and `.value`** during deserialization
- The issue was in application code, not the serialization layer
- TypeRegistry configuration is working as designed

### Going Forward ✅

- Use `.name` for internal storage and queries (uppercase, stable)
- Use `.value` for API responses (lowercase, JSON-friendly)
- Always use enum comparisons (`==`) instead of string comparisons where possible
- Document enum serialization behavior in new samples
