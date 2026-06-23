# User Tracking Implementation Summary

## 📋 Overview

Implemented comprehensive user tracking for Mario's Pizzeria to record WHO performed cooking, ready marking, and delivery operations. This enhancement provides accountability, supports analytics dashboards, and enables customer transparency.

## 🎯 Business Requirements

### Core Functionality

- Track which chef/manager started cooking each order
- Track who marked order as ready
- Track who delivered the order
- Record both user_id and user_name for each operation
- Support manager override scenarios (manager gets credit when performing operations assigned to others)

### Use Cases

1. **Accountability**: Know which staff member handled each order stage
2. **Analytics**: Compute per-chef and per-driver performance metrics
3. **Customer Transparency**: Show customers who cooked and delivered their order
4. **Manager Override**: Properly attribute operations when manager steps in

## 🏗️ Implementation Details

### 1. Domain Model Updates ✅

#### OrderState (`domain/entities/order.py`)

Added 6 new tracking fields to `OrderState`:

```python
class OrderState(AggregateState[str]):
    # Existing fields...

    # NEW: User tracking fields
    chef_user_id: Optional[str]  # User who started cooking
    chef_name: Optional[str]  # Name of chef who started cooking
    ready_by_user_id: Optional[str]  # User who marked order as ready
    ready_by_name: Optional[str]  # Name of user who marked as ready
    delivery_user_id: Optional[str]  # User who delivered the order
    delivery_name: Optional[str]  # Name of delivery person

    def __init__(self):
        # ... existing initialization ...
        self.chef_user_id = None
        self.chef_name = None
        self.ready_by_user_id = None
        self.ready_by_name = None
        self.delivery_user_id = None
        self.delivery_name = None
```

**Impact**:

- All orders now persist user attribution for each operation
- Fields are optional to maintain backward compatibility
- Supports both assigned user and actual performer tracking

### 2. Domain Events Updates ✅

#### CookingStartedEvent (`domain/events.py`)

```python
@dataclass
class CookingStartedEvent(DomainEvent):
    """Event raised when cooking starts for an order."""

    def __init__(
        self,
        aggregate_id: str,
        cooking_started_time: datetime,
        user_id: str,  # NEW
        user_name: str,  # NEW
    ):
        super().__init__(aggregate_id)
        self.cooking_started_time = cooking_started_time
        self.user_id = user_id
        self.user_name = user_name

    cooking_started_time: datetime
    user_id: str
    user_name: str
```

#### OrderReadyEvent (`domain/events.py`)

```python
@dataclass
class OrderReadyEvent(DomainEvent):
    """Event raised when an order is ready for pickup/delivery."""

    def __init__(
        self,
        aggregate_id: str,
        ready_time: datetime,
        estimated_ready_time: Optional[datetime],
        user_id: str,  # NEW
        user_name: str,  # NEW
    ):
        super().__init__(aggregate_id)
        self.ready_time = ready_time
        self.estimated_ready_time = estimated_ready_time
        self.user_id = user_id
        self.user_name = user_name

    ready_time: datetime
    estimated_ready_time: Optional[datetime]
    user_id: str
    user_name: str
```

#### OrderDeliveredEvent (`domain/events.py`)

```python
@dataclass
class OrderDeliveredEvent(DomainEvent):
    """Event raised when an order is delivered."""

    def __init__(
        self,
        aggregate_id: str,
        delivered_time: datetime,
        user_id: str,  # NEW
        user_name: str,  # NEW
    ):
        super().__init__(aggregate_id)
        self.delivered_time = delivered_time
        self.user_id = user_id
        self.user_name = user_name

    delivered_time: datetime
    user_id: str
    user_name: str
```

**Impact**:

- Events now carry complete user context
- Enables event sourcing with full audit trail
- Supports event handlers that need user information

### 3. Order Aggregate Updates ✅

#### Order Methods (`domain/entities/order.py`)

**start_cooking() - Now accepts user context:**

```python
def start_cooking(self, user_id: str, user_name: str) -> None:
    """Start cooking the order"""
    if self.state.status != OrderStatus.CONFIRMED:
        raise ValueError("Only confirmed orders can start cooking")

    cooking_time = datetime.now(timezone.utc)

    # Register event with user context
    self.state.on(
        self.register_event(
            CookingStartedEvent(
                aggregate_id=self.id(),
                cooking_started_time=cooking_time,
                user_id=user_id,  # NEW
                user_name=user_name,  # NEW
            )
        )
    )
```

**mark_ready() - Now accepts user context:**

```python
def mark_ready(self, user_id: str, user_name: str) -> None:
    """Mark order as ready for pickup/delivery"""
    if self.state.status != OrderStatus.COOKING:
        raise ValueError("Only cooking orders can be marked ready")

    ready_time = datetime.now(timezone.utc)

    # Register event with user context
    self.state.on(
        self.register_event(
            OrderReadyEvent(
                aggregate_id=self.id(),
                ready_time=ready_time,
                estimated_ready_time=getattr(self.state, "estimated_ready_time", None),
                user_id=user_id,  # NEW
                user_name=user_name,  # NEW
            )
        )
    )
```

**deliver_order() - Now accepts user context:**

```python
def deliver_order(self, user_id: str, user_name: str) -> None:
    """Mark order as delivered"""
    if self.state.status != OrderStatus.DELIVERING:
        raise ValueError("Only orders out for delivery can be marked as delivered")

    delivered_time = datetime.now(timezone.utc)

    # Register event with user context
    self.state.on(
        self.register_event(
            OrderDeliveredEvent(
                aggregate_id=self.id(),
                delivered_time=delivered_time,
                user_id=user_id,  # NEW
                user_name=user_name,  # NEW
            )
        )
    )
```

#### Event Handlers in OrderState

**CookingStartedEvent Handler:**

```python
@dispatch(CookingStartedEvent)
def on(self, event: CookingStartedEvent) -> None:
    """Handle cooking started event"""
    self.status = OrderStatus.COOKING
    self.cooking_started_time = event.cooking_started_time
    self.chef_user_id = event.user_id  # NEW
    self.chef_name = event.user_name  # NEW
```

**OrderReadyEvent Handler:**

```python
@dispatch(OrderReadyEvent)
def on(self, event: OrderReadyEvent) -> None:
    """Handle order ready event"""
    self.status = OrderStatus.READY
    self.actual_ready_time = event.ready_time
    self.ready_by_user_id = event.user_id  # NEW
    self.ready_by_name = event.user_name  # NEW
```

**OrderDeliveredEvent Handler:**

```python
@dispatch(OrderDeliveredEvent)
def on(self, event: OrderDeliveredEvent) -> None:
    """Handle order delivered event"""
    self.status = OrderStatus.DELIVERED
    self.delivered_time = event.delivered_time
    self.delivery_user_id = event.user_id  # NEW
    self.delivery_name = event.user_name  # NEW
```

**Impact**:

- Domain model enforces user tracking at the core
- Event sourcing properly captures user attribution
- State transitions automatically record performer information

### 4. Application Layer Updates ✅

#### Command Signatures

**StartCookingCommand:**

```python
@dataclass
class StartCookingCommand(Command[OperationResult[OrderDto]]):
    """Command to start cooking an order"""

    order_id: str
    user_id: Optional[str] = None  # NEW
    user_name: Optional[str] = None  # NEW
```

**CompleteOrderCommand:**

```python
@dataclass
class CompleteOrderCommand(Command[OperationResult[OrderDto]]):
    """Command to mark an order as ready"""

    order_id: str
    user_id: Optional[str] = None  # NEW
    user_name: Optional[str] = None  # NEW
```

**UpdateOrderStatusCommand:**

```python
@dataclass
class UpdateOrderStatusCommand(Command[OperationResult[OrderDto]]):
    """Command to update order status (kitchen operations)"""

    order_id: str
    new_status: str
    notes: Optional[str] = None
    user_id: Optional[str] = None  # NEW
    user_name: Optional[str] = None  # NEW
```

#### Command Handlers

All handlers now extract user info and pass to domain methods:

```python
# In StartCookingCommandHandler.handle_async()
user_id = request.user_id or "system"
user_name = request.user_name or "System"
order.start_cooking(user_id, user_name)

# In CompleteOrderCommandHandler.handle_async()
user_id = request.user_id or "system"
user_name = request.user_name or "System"
order.mark_ready(user_id, user_name)

# In UpdateOrderStatusHandler.handle_async()
user_id = request.user_id or "system"
user_name = request.user_name or "System"
# Then passed to order.start_cooking(), order.mark_ready(), or order.deliver_order()
```

**Impact**:

- Commands optionally accept user context
- Defaults to "system"/"System" for automated/API operations
- UI controllers can pass actual session user information

### 5. Files Modified ✅

| File                                                  | Changes                                                                              | Purpose                                           |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------- |
| `domain/entities/order.py`                            | Added 6 fields to OrderState, updated 3 event handlers, modified 3 aggregate methods | Track user information in state and handle events |
| `domain/events.py`                                    | Added user_id and user_name to 3 events                                              | Carry user context in domain events               |
| `application/commands/start_cooking_command.py`       | Added optional user fields to command, updated handler                               | Accept and pass user context                      |
| `application/commands/complete_order_command.py`      | Added optional user fields to command, updated handler                               | Accept and pass user context                      |
| `application/commands/update_order_status_command.py` | Added optional user fields to command, updated handler                               | Accept and pass user context                      |

## 🔄 Remaining Work

### 5. UI Controllers Update (IN PROGRESS)

**Location**: `ui/controllers/kitchen_controller.py`, `delivery_controller.py`, `management_controller.py`

**Required Changes**:

```python
# In kitchen controller - start cooking endpoint
@post("/orders/{order_id}/start-cooking")
async def start_cooking(self, request: Request, order_id: str):
    # Extract user from session
    user_id = request.session.get("user_id")
    user_name = request.session.get("name")

    # Pass to command
    command = StartCookingCommand(
        order_id=order_id,
        user_id=user_id,
        user_name=user_name
    )
    result = await self.mediator.execute_async(command)
    return self.process(result)
```

**Pattern to Apply**:

1. Extract `user_id = request.session.get("user_id")`
2. Extract `user_name = request.session.get("name")`
3. Pass both to command constructor

**Files to Update**:

- `kitchen_controller.py`: Update cooking and ready endpoints
- `delivery_controller.py`: Update delivery completion endpoints
- `management_controller.py`: Update manager override operations

### 6. OrderDto Update (NOT STARTED)

**Location**: `api/dtos/order_dto.py`

**Required Changes**:

```python
@dataclass
class OrderDto:
    # ... existing fields ...

    # NEW: User attribution fields for UI display
    chef_name: Optional[str] = None
    ready_by_name: Optional[str] = None
    delivery_name: Optional[str] = None
```

**Purpose**:

- Display chef and driver names in UI
- Customer transparency
- Order history attribution

### 7. UI Templates Update (NOT STARTED)

**Locations**:

- `ui/templates/kitchen/index.html`
- `ui/templates/delivery/ready_orders.html`
- `ui/templates/orders/history.html`

**Required Changes**:

```html
<!-- Kitchen view -->
<div class="order-info">
  <p>Chef: {{ order.chef_name }}</p>
  <p>Ready by: {{ order.ready_by_name }}</p>
</div>

<!-- Delivery view -->
<div class="order-info">
  <p>Prepared by: {{ order.chef_name }}</p>
  <p>Driver: {{ order.delivery_name }}</p>
</div>

<!-- Order history -->
<div class="order-details">
  <p>Cooked by: {{ order.chef_name }}</p>
  <p>Delivered by: {{ order.delivery_name }}</p>
</div>
```

**Purpose**:

- Show customers who prepared their food
- Display delivery driver information
- Enhance transparency and trust

### 8. Analytics Queries Update (NOT STARTED)

**Locations**:

- `application/queries/get_staff_performance_query.py`
- `application/queries/get_kitchen_performance_query.py`
- `application/queries/get_delivery_performance_query.py`

**Required Changes**:

```python
# Group by actual performer instead of assigned user
pipeline = [
    {
        "$group": {
            "_id": "$chef_user_id",  # Changed from assigned_chef_id
            "chef_name": {"$first": "$chef_name"},
            "total_orders": {"$sum": 1},
            "avg_cooking_time": {"$avg": "$cooking_time"}
        }
    }
]
```

**Purpose**:

- Accurate performance metrics per actual performer
- Manager override properly attributed
- Fair performance evaluation

## 📊 Data Flow

### Cooking Operation Flow

```
1. User clicks "Start Cooking" in Kitchen UI
2. kitchen_controller extracts user_id and user_name from session
3. Creates StartCookingCommand(order_id, user_id, user_name)
4. StartCookingCommandHandler receives command
5. Handler calls order.start_cooking(user_id, user_name)
6. Order aggregate creates CookingStartedEvent with user context
7. Event handler updates OrderState with chef_user_id and chef_name
8. Repository persists updated order
9. Domain events dispatched via UnitOfWork
10. UI displays order with chef attribution
```

### Manager Override Scenario

```
1. Order assigned to chef_A
2. Manager (chef_role + manager_role) performs "Start Cooking"
3. System records manager's user_id and name in chef_user_id/chef_name
4. Analytics show manager as performer (not chef_A)
5. Manager gets credit for operation
```

## 🧪 Testing Considerations

### Unit Tests Required

- [x] OrderState captures user info from events
- [x] Order aggregate methods require user parameters
- [ ] Command handlers default to "system" when user not provided
- [ ] Event handlers properly update state with user info

### Integration Tests Required

- [ ] Kitchen controller passes session user to command
- [ ] Delivery controller passes session user to command
- [ ] Manager override properly attributes to manager
- [ ] Analytics queries group by actual performer

### E2E Tests Required

- [ ] Full cooking workflow with user tracking
- [ ] Order history shows chef and driver names
- [ ] Analytics dashboard shows per-chef metrics
- [ ] Manager override correctly updates attribution

## 🎓 Key Design Decisions

### 1. Optional Command Parameters

**Decision**: Made user_id and user_name optional in commands with defaults to "system"/"System"

**Rationale**:

- API endpoints can work without session context
- Background jobs can execute commands
- Maintains backward compatibility
- UI controllers provide actual user info when available

### 2. Separate Fields for Assignment vs Performance

**Decision**: Keep delivery_person_id (assignment) separate from delivery_user_id (performer)

**Rationale**:

- Assignment !== Performance (manager override scenario)
- Analytics need actual performer
- Audit trail shows both who should have done it and who actually did it

### 3. Store Both User ID and Name

**Decision**: Persist both user_id and user_name in OrderState

**Rationale**:

- user_id: Unique identifier for analytics and queries
- user_name: Human-readable for UI display without additional lookups
- Denormalization acceptable for read-optimized order history

### 4. Event Sourcing with User Context

**Decision**: Add user information to domain events

**Rationale**:

- Events represent complete business occurrences
- Event replay can reconstruct user attribution
- Event handlers can react to user-specific actions
- Audit trail is comprehensive

## 📈 Benefits

### Accountability

- ✅ Every operation attributed to specific user
- ✅ Manager overrides properly tracked
- ✅ Complete audit trail in event store

### Analytics

- ✅ Per-chef performance metrics
- ✅ Per-driver performance metrics
- ✅ Accurate attribution for manager operations
- ✅ Performance evaluation data

### Customer Transparency

- ✅ Customers know who cooked their food
- ✅ Customers know who delivered their order
- ✅ Builds trust and connection
- ✅ Enables specific feedback/reviews

### Operational Insights

- ✅ Identify high-performing staff
- ✅ Track manager intervention frequency
- ✅ Analyze cooking time by chef
- ✅ Analyze delivery time by driver

## 🚀 Next Steps

1. **Complete UI Controller Updates** (Task 5)

   - Update kitchen_controller.py to pass user context
   - Update delivery_controller.py to pass user context
   - Update management_controller.py to pass user context

2. **Update OrderDto** (Task 6)

   - Add chef_name, ready_by_name, delivery_name fields
   - Test DTO mapping from OrderState

3. **Update UI Templates** (Task 7)

   - Kitchen view: Display chef names
   - Delivery view: Display driver names
   - Order history: Display complete attribution

4. **Update Analytics** (Task 8)

   - Modify queries to group by chef_user_id/delivery_user_id
   - Create dashboard with per-user metrics
   - Test manager override scenarios

5. **Testing**
   - Write comprehensive unit tests
   - Create integration tests for user tracking
   - Add E2E tests for complete workflows

## 📝 Migration Considerations

### Backward Compatibility

- ✅ New fields are optional (None by default)
- ✅ Existing orders without user tracking remain valid
- ✅ Commands accept optional user parameters
- ✅ Defaults to "system" for automated operations

### Data Migration

**Not Required** - New fields default to None:

- Existing orders show "Unknown" or blank for chef/driver
- New orders capture full user attribution
- No breaking changes to existing data

### Deployment Strategy

1. Deploy domain and application layer changes
2. Deploy UI controller changes
3. Deploy DTO changes
4. Deploy UI template changes
5. Deploy analytics changes
6. Monitor for issues

**Rollback**: All changes are additive and backward compatible

## 🔗 Related Documentation

- [Inline Imports Cleanup](./INLINE_IMPORTS_CLEANUP.md)
- [Domain-Driven Design Patterns](./DDD.md)
- [Event Sourcing Guide](../docs/patterns/event-sourcing.md)
- [CQRS Implementation](../docs/patterns/cqrs.md)

---

**Status**: Domain and Application layers complete ✅
**Next**: UI Controllers, DTOs, Templates, and Analytics
**Last Updated**: 2024 (after domain/application implementation)
**Implementation Time**: ~2 hours for core domain changes
