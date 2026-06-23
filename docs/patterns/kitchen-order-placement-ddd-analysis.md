# DDD Analysis: Where Should Kitchen Orders Be Added?

> **🚧 Work in Progress**: This documentation is being updated to include beginner-friendly explanations with What & Why sections, Common Mistakes, and When NOT to Use guidance. The content below is accurate but will be enhanced soon.

## Question

In the Mario Pizzeria sample app, where should an order be added to the Kitchen's pending orders list:

1. **In the Command Handler** (PlaceOrderCommandHandler) - as part of the transaction?
2. **In the Domain Event Handler** (OrderConfirmedEventHandler) - as a side effect?

## Current State Analysis

### What Happens Now

**PlaceOrderCommandHandler Flow:**

```python
async def handle_async(self, request: PlaceOrderCommand):
    # 1. Create or get customer
    customer = await self._create_or_get_customer(request)

    # 2. Create order with items
    order = Order(customer_id=customer.id())
    order.add_order_item(...)

    # 3. Confirm order (raises OrderConfirmedEvent)
    order.confirm_order()

    # 4. Save order - repository publishes events automatically
    await self.order_repository.add_async(order)
    # Repository handles:
    # - Saves order state
    # - Publishes OrderConfirmedEvent
    # - Event handlers process asynchronously

    # ❌ Kitchen is NOT updated here

    return self.created(order_dto)
```

**StartCookingCommandHandler Flow:**

```python
async def handle_async(self, request: StartCookingCommand):
    # 1. Get order and kitchen
    order = await self.order_repository.get_async(request.order_id)
    kitchen = await self.kitchen_repository.get_kitchen_state_async()

    # 2. Check capacity
    if kitchen.is_at_capacity:
        return self.bad_request("Kitchen is at capacity")

    # 3. Start cooking
    order.start_cooking()  # Raises CookingStartedEvent
    kitchen.start_order(order.id())  # ✅ Kitchen updated in command handler

    # 4. Save both aggregates - events published automatically
    await self.order_repository.update_async(order)
    await self.kitchen_repository.update_kitchen_state_async(kitchen)
    # Both repositories publish their respective events

    return self.ok(order_dto)
```

**Key Observation:** The `StartCookingCommandHandler` updates the Kitchen **in the command handler**, not in an event handler.

---

## DDD Principles Analysis

### 1. Aggregate Boundaries

**Order Aggregate:**

- Root: `Order`
- Owns: `OrderItems` (value objects)
- Responsible for: Order lifecycle, business rules about items, pricing

**Kitchen Aggregate:**

- Root: `Kitchen`
- Owns: `active_orders` list (order IDs)
- Responsible for: Capacity management, tracking orders in preparation

**Customer Aggregate:**

- Root: `Customer`
- Responsible for: Customer information, contact details

**These are SEPARATE aggregates** - they should maintain their own consistency boundaries.

### 2. Transaction Boundaries

**DDD Rule:** A transaction should modify **at most ONE aggregate root**.

**Why?**

- Ensures clear consistency boundaries
- Prevents distributed transaction complexity
- Makes concurrency control manageable
- Maintains aggregate autonomy

**Application to Pizza Domain:**

#### Scenario A: Update Kitchen in Command Handler

```python
async def handle_async(self, request: PlaceOrderCommand):
    # Transaction modifies TWO aggregates:
    order = Order(...)
    order.confirm_order()
    await self.order_repository.add_async(order)  # Aggregate 1

    kitchen = await self.kitchen_repository.get_kitchen_state_async()
    kitchen.add_pending_order(order.id())
    await self.kitchen_repository.update_kitchen_state_async(kitchen)  # Aggregate 2

    # ❌ VIOLATES: One transaction, two aggregates
```

**Problems:**

- ❌ Violates single aggregate per transaction rule
- ❌ Tight coupling between Order and Kitchen
- ❌ If Kitchen update fails, what happens to Order?
- ❌ Concurrency issues if multiple orders placed simultaneously
- ❌ Kitchen becomes a bottleneck for order placement

#### Scenario B: Update Kitchen in Event Handler (Eventually Consistent)

```python
# Command Handler - modifies ONE aggregate
async def handle_async(self, request: PlaceOrderCommand):
    order = Order(...)
    order.confirm_order()  # Raises OrderConfirmedEvent
    await self.order_repository.add_async(order)
    # Repository automatically publishes events
    # ✅ Transaction complete, only modified Order
    return self.created(order_dto)

# Event Handler - separate transaction, different aggregate
class OrderConfirmedEventHandler:
    async def handle_async(self, event: OrderConfirmedEvent):
        kitchen = await self.kitchen_repository.get_kitchen_state_async()
        kitchen.add_pending_order(event.aggregate_id)
        await self.kitchen_repository.update_kitchen_state_async(kitchen)
        # ✅ Separate transaction, only modified Kitchen
```

**Benefits:**

- ✅ Each transaction modifies ONE aggregate
- ✅ Loose coupling via events
- ✅ Order placement succeeds independently
- ✅ Better scalability and concurrency
- ✅ Clearer failure boundaries

### 3. Domain Event Semantics

**What is OrderConfirmedEvent?**

- **Past tense** - something that ALREADY happened
- **Immutable fact** - the order WAS confirmed
- **Publishing contract** - "I'm telling you this happened, do what you need to do"

**Event Handler Responsibilities:**

- React to domain events from other aggregates
- Implement **inter-aggregate workflows**
- Maintain **eventual consistency** between aggregates
- Handle **side effects** and **projections**

### 4. Consistency Models

**Strong Consistency (Single Aggregate):**

```
Order.confirm_order() → Order.state.status = CONFIRMED
                      → Order.state.confirmed_time = now()
✅ Immediate consistency within Order aggregate
```

**Eventual Consistency (Cross-Aggregate):**

```
Order confirms → OrderConfirmedEvent published
              ↓
              → Event dispatched (after transaction commits)
              ↓
              → OrderConfirmedEventHandler invoked
              ↓
              → Kitchen updated with new pending order

✅ Eventually consistent between Order and Kitchen
```

### 5. Business Rules Analysis

**Question:** Is "Kitchen must know about confirmed orders" a business invariant or a side effect?

**Business Invariant** (must be enforced in transaction):

- "Order must have at least one pizza"
- "Order total must be >= 0"
- "Kitchen cannot exceed max capacity when starting cooking"
- **These must be checked BEFORE committing**

**Side Effect / Eventual Consistency** (can happen after transaction):

- "Kitchen should track pending orders for dashboard"
- "Customer should receive confirmation email"
- "Analytics should update order metrics"
- **These can happen asynchronously**

**Analysis for Pizzeria:**

The Kitchen tracking pending orders is **NOT a business invariant for order placement**. Here's why:

1. **Order can be placed even if Kitchen is busy** - the order goes into "confirmed" state, waiting for kitchen capacity
2. **Kitchen tracking is for operational visibility** - showing what orders are waiting
3. **Failure to update Kitchen doesn't invalidate the Order** - the order is still valid
4. **Kitchen state is a projection/read model** - derived from order events

**Counterpoint:** When **starting cooking** (StartCookingCommand), Kitchen capacity IS a business rule:

```python
if kitchen.is_at_capacity:
    return self.bad_request("Kitchen is at capacity")
```

This must be checked in the transaction because it affects whether the order can transition to "Cooking" state.

---

## Recommendation: Use Event Handler (Eventually Consistent)

### ✅ Recommended Approach

**Update the Kitchen via OrderConfirmedEventHandler:**

```python
# domain/entities/kitchen.py
class Kitchen(Entity[str]):
    def __init__(self, max_concurrent_orders: int = 3):
        super().__init__()
        self.id = "kitchen"
        self.active_orders: list[str] = []  # Orders being cooked
        self.pending_orders: list[str] = []  # Orders confirmed, waiting to cook
        self.max_concurrent_orders = max_concurrent_orders
        self.total_orders_processed = 0

    def add_pending_order(self, order_id: str) -> None:
        """Add a confirmed order to the pending queue"""
        if order_id not in self.pending_orders:
            self.pending_orders.append(order_id)

    def start_order(self, order_id: str) -> bool:
        """Move order from pending to active (if capacity allows)"""
        if self.is_at_capacity:
            return False

        # Remove from pending if present
        if order_id in self.pending_orders:
            self.pending_orders.remove(order_id)

        # Add to active
        if order_id not in self.active_orders:
            self.active_orders.append(order_id)

        return True
```

```python
# application/event_handlers.py
class OrderConfirmedEventHandler(DomainEventHandler[OrderConfirmedEvent]):
    """Handles order confirmation - adds to kitchen pending queue"""

    def __init__(self, kitchen_repository: IKitchenRepository):
        self.kitchen_repository = kitchen_repository

    async def handle_async(self, event: OrderConfirmedEvent) -> Any:
        """Process order confirmed event"""
        logger.info(
            f"🍕 Order {event.aggregate_id} confirmed! "
            f"Total: ${event.total_amount}, Pizzas: {event.pizza_count}"
        )

        # Update kitchen with pending order
        kitchen = await self.kitchen_repository.get_kitchen_state_async()
        kitchen.add_pending_order(event.aggregate_id)
        await self.kitchen_repository.update_kitchen_state_async(kitchen)

        # Other side effects:
        # - Send SMS notification to customer
        # - Send email receipt
        # - Update kitchen display system
        # - Create kitchen ticket

        return None
```

```python
# application/commands/place_order_command.py
class PlaceOrderCommandHandler(CommandHandler[PlaceOrderCommand, OperationResult[OrderDto]]):
    async def handle_async(self, request: PlaceOrderCommand) -> OperationResult[OrderDto]:
        try:
            # Create customer and order (ONE aggregate modified)
            customer = await self._create_or_get_customer(request)
            order = Order(customer_id=customer.id())

            # Add items
            for pizza_item in request.pizzas:
                order_item = OrderItem(...)
                order.add_order_item(order_item)

            # Confirm order (raises OrderConfirmedEvent)
            order.confirm_order()

            # Save order - repository publishes events automatically
            await self.order_repository.add_async(order)
            # Repository handles:
            # - Saves order state
            # - Publishes OrderConfirmedEvent
            # - Event handlers process asynchronously

            # ✅ Kitchen will be updated by OrderConfirmedEventHandler
            # ✅ Happens AFTER this transaction commits
            # ✅ Eventually consistent

            return self.created(order_dto)

        except Exception as e:
            return self.bad_request(f"Failed to place order: {str(e)}")
```

### Why This is Better

#### 1. **Respects Aggregate Boundaries**

- PlaceOrderCommand modifies only Order aggregate ✅
- OrderConfirmedEventHandler modifies only Kitchen aggregate ✅
- Each transaction touches ONE aggregate root ✅

#### 2. **Follows Event-Driven Architecture**

- Domain events communicate between aggregates ✅
- Loose coupling between Order and Kitchen ✅
- Easy to add new event handlers (email, SMS, analytics) ✅

#### 3. **Better Scalability**

```
Without Event Handler (Synchronous):
PlaceOrder → Update Order → Update Kitchen → Commit
             |______________|______________|
                 Single Transaction
                 Kitchen is bottleneck

With Event Handler (Asynchronous):
PlaceOrder → Update Order → Commit ✅ (fast)
                          ↓
                          Event Published
                          ↓
                          → Update Kitchen ✅ (separate transaction)
                          → Send Email ✅
                          → Update Analytics ✅
```

#### 4. **Clearer Failure Handling**

- Order placement **succeeds** even if Kitchen update temporarily fails
- Event handler can **retry** Kitchen update independently
- Kitchen update failure doesn't rollback the order (order is still valid)
- Eventual consistency is acceptable for this use case

#### 5. **Business Semantics Match Reality**

Real pizza shop flow:

1. Customer places order → **Order confirmed** ✅
2. Order ticket goes to kitchen → **Kitchen gets notification** ✅
3. Kitchen starts when ready → **Order moves to cooking** ✅

The kitchen getting the ticket is a **consequence** of order confirmation, not a prerequisite.

#### 6. **Consistency with StartCookingCommand**

Notice that `StartCookingCommand` DOES update Kitchen in the handler:

```python
kitchen.start_order(order.id())  # Check capacity + update kitchen
order.start_cooking()  # Update order status
```

**Why is this different?**

- **Kitchen capacity is a business rule** for starting cooking
- Must be checked atomically to prevent race conditions
- If capacity check fails, order cannot start cooking
- **Strong consistency required** between Kitchen and Order for this operation

**But for PlaceOrder:**

- Kitchen tracking confirmed orders is just **visibility/monitoring**
- Order can be confirmed regardless of kitchen state
- **Eventual consistency is acceptable**

---

## Common Objections Addressed

### Objection 1: "But kitchen update might fail!"

**Response:**

- That's OK - the Order is still valid and confirmed
- Event handlers can **retry** on failure
- Use outbox pattern or reliable event bus for guaranteed delivery
- Kitchen can poll for confirmed orders as backup
- This is **eventual consistency** - the system will become consistent

### Objection 2: "What if we need to know kitchen state before confirming?"

**Response:**

- Then that's a different requirement: "Order placement should check kitchen capacity"
- In that case, add a **query before the command**:

```python
# In controller or application service
kitchen = await query_handler.execute(GetKitchenStatusQuery())
if kitchen.pending_orders_count >= MAX_PENDING:
    return self.bad_request("Too many pending orders")

# Proceed with PlaceOrderCommand
result = await mediator.execute(PlaceOrderCommand(...))
```

- Still don't couple Order and Kitchen aggregates in the same transaction
- Pre-check is for **user experience**, not **transactional consistency**

### Objection 3: "Eventual consistency is complex!"

**Response:**

- It's actually **simpler** than distributed transactions
- The framework handles event dispatching automatically
- No distributed locks or 2-phase commits needed
- Better scalability and resilience
- This is how most successful systems work (Amazon, Netflix, Uber)

---

## Implementation Checklist

To implement this recommendation:

1. ✅ **Add `pending_orders` to Kitchen entity**

   ```python
   self.pending_orders: list[str] = []
   ```

2. ✅ **Add `add_pending_order()` method to Kitchen**

   ```python
   def add_pending_order(self, order_id: str) -> None
   ```

3. ✅ **Update `start_order()` to move from pending to active**

   ```python
   def start_order(self, order_id: str) -> bool:
       if order_id in self.pending_orders:
           self.pending_orders.remove(order_id)
       self.active_orders.append(order_id)
   ```

4. ✅ **Update OrderConfirmedEventHandler**

   ```python
   kitchen = await self.kitchen_repository.get_kitchen_state_async()
   kitchen.add_pending_order(event.aggregate_id)
   await self.kitchen_repository.update_kitchen_state_async(kitchen)
   ```

5. ✅ **Keep PlaceOrderCommandHandler as-is**

   - No kitchen updates in command handler
   - Only modifies Order aggregate

6. ✅ **Update KitchenStatusDto to show pending orders**

   ```python
   pending_orders: list[str]
   ```

---

## Conclusion

**Recommendation: Add orders to Kitchen in the OrderConfirmedEventHandler** ✅

This approach:

- ✅ Follows DDD aggregate boundary rules (one aggregate per transaction)
- ✅ Uses domain events correctly (inter-aggregate communication)
- ✅ Provides eventual consistency (acceptable for this use case)
- ✅ Maintains loose coupling (easy to extend)
- ✅ Scales better (no transaction bottleneck)
- ✅ Matches real-world semantics (order confirmed → kitchen notified)
- ✅ Handles failures gracefully (order valid even if kitchen update fails)

**The current StartCookingCommand is correct** because kitchen capacity is a **business invariant** that must be checked atomically when transitioning to cooking state.

**Your intuition about transactions was correct**, but the key insight is: **Not everything needs strong consistency**. Kitchen tracking confirmed orders is a **projection/read model** that can be eventually consistent, while kitchen capacity for cooking is a **business rule** that requires strong consistency.

This is a fundamental DDD pattern: **Strong consistency within aggregates, eventual consistency between aggregates.**

---

## Further Reading

- **Domain-Driven Design** by Eric Evans - Chapter on Aggregates
- **Implementing Domain-Driven Design** by Vaughn Vernon - Chapter on Aggregates and Event-Driven Architecture
- **Patterns, Principles, and Practices of Domain-Driven Design** by Scott Millett - Chapter on Eventual Consistency
