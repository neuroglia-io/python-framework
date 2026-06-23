# Multi-Aggregate Consistency Analysis

**Date**: November 1, 2025
**Context**: Discussion about handling consistency when multiple aggregates are modified in a single handler
**Question**: "How is consistency handled if one aggregate repository operation fails and the other succeeds?"

## The Fundamental Question

When a command handler modifies multiple aggregates:

```python
class PlaceOrderHandler:
    async def handle_async(self, command: PlaceOrderCommand):
        # Aggregate 1: Order (critical)
        order = Order.create(...)
        await self.order_repository.add_async(order)

        # Aggregate 2: Customer (secondary)
        customer = await self._create_or_get_customer(command)
        await self.customer_repository.update_async(customer)

        # What if customer update fails after order succeeds?
```

**User's concern**: Is UnitOfWork relevant for this scenario? How to revert operations? Should we worry about this?

## DDD Principles: The Foundation

### Aggregate Boundaries ARE Transaction Boundaries

From **Vaughn Vernon** (Implementing Domain-Driven Design):

> "When you request that an Aggregate perform a command, you are requesting that a transaction occur. The transaction may succeed or fail, but one way or another, the consistency rules of the Aggregate must remain satisfied."

Key insight: **One aggregate = one transaction**

### Cross-Aggregate Consistency is EVENTUAL

From **Eric Evans** (Domain-Driven Design):

> "Aggregate boundaries are consistency boundaries. Changes to objects within an aggregate are immediately consistent. Changes across aggregates must be eventually consistent."

Key insight: **Multiple aggregates = eventual consistency, NOT immediate**

## Current UnitOfWork Reality Check

### What UnitOfWork Actually Does

```python
class UnitOfWork:
    def __init__(self):
        self._aggregates: set[AggregateRoot] = set()  # Just a collection!

    def register_aggregate(self, aggregate: AggregateRoot):
        self._aggregates.add(aggregate)  # No transaction coordination!

    def get_domain_events(self) -> list[DomainEvent]:
        events = []
        for aggregate in self._aggregates:
            events.extend(aggregate.get_uncommitted_events())
        return events

    def clear(self):
        for aggregate in self._aggregates:
            aggregate.clear_pending_events()
        self._aggregates.clear()
```

### What UnitOfWork Does NOT Do

❌ **Database Transaction Coordination**: No `begin_transaction()`, `commit()`, `rollback()`
❌ **Rollback on Failure**: If second aggregate fails, first is already persisted
❌ **Two-Phase Commit**: No distributed transaction protocol
❌ **Compensation Logic**: No automatic reversal of operations

**Conclusion**: Current UnitOfWork is just an event collector, NOT a transaction coordinator!

## Real Example: PlaceOrderCommand

### Current Implementation

```python
# File: samples/mario-pizzeria/application/commands/place_order_command.py

class PlaceOrderHandler:
    async def handle_async(self, command: PlaceOrderCommand):
        # 1. Create Order aggregate
        order = Order.create(
            customer_id=customer_id,
            customer_phone=command.customer_phone,
            restaurant_id=command.restaurant_id
        )

        for pizza_request in command.pizzas:
            order_item = OrderItem(...)
            order.add_order_item(order_item)

        order.confirm_order()  # Raises OrderConfirmedEvent

        # 2. Save order to database
        await self.order_repository.add_async(order)
        # ✅ Order is now PERSISTED in database!

        # 3. Get or create customer
        customer = await self._create_or_get_customer(command)

        # 4. Register both with UnitOfWork
        self.unit_of_work.register_aggregate(order)
        self.unit_of_work.register_aggregate(customer)
        # ⚠️ If this line fails, order is ALREADY in database!

        return self.created(order_dto)

    async def _create_or_get_customer(self, command):
        existing = await self.customer_repository.get_by_phone_async(...)
        if existing:
            if command.customer_address and not existing.state.address:
                existing.update_contact_info(address=command.customer_address)
                await self.customer_repository.update_async(existing)
                # ⚠️ If this fails, order is ALREADY saved!
        else:
            customer = Customer(...)
            await self.customer_repository.add_async(customer)
            # ⚠️ If this fails, order is ALREADY saved!
        return customer
```

### The Problem Timeline

```
Time  Action                              State
────  ──────────────────────────────────  ──────────────────────────────────
T1    Order created in memory             Order: memory only
T2    order_repository.add_async()        Order: ✅ IN DATABASE
T3    customer_repository.update_async()
      └─> FAILS! Network error!           Customer: ❌ NOT UPDATED
T4    Exception propagates                Order: ✅ STILL IN DATABASE (orphaned)
```

**Result**: Order exists without proper customer association!

## The DDD Answer: This is Actually OK

### Why It's Acceptable

1. **Different Business Priorities**

   - **Order placement** = Critical business operation (customer wants their pizza!)
   - **Customer profile update** = Nice to have, but not critical
   - Business would rather have order with incomplete customer info than no order at all

2. **Eventual Consistency Pattern**

   ```python
   # When OrderPlacedEvent is published:
   class OrderPlacedEventHandler:
       async def handle_async(self, event: OrderPlacedEvent):
           # Retry customer update asynchronously
           for attempt in range(3):
               try:
                   customer = await self._get_or_create_customer(event)
                   customer.record_order(event.order_id)
                   await self.customer_repository.update_async(customer)
                   break
               except Exception as e:
                   if attempt == 2:
                       log.error(f"Customer update failed: {e}")
                       # Trigger compensating workflow
   ```

3. **Real-World Analogy**
   - Phone order: You take the order (critical), update customer file later (secondary)
   - If customer file is unavailable, you still take the order
   - You fix the customer record when the system is available

### When to Worry About Multi-Aggregate Consistency

**Worry if**: Both operations are equally critical to business outcome

Example: Bank transfer between accounts

```python
# ❌ WRONG: Both aggregates must succeed atomically
async def transfer_money(from_account_id, to_account_id, amount):
    from_account = await self.account_repo.get_async(from_account_id)
    from_account.withdraw(amount)
    await self.account_repo.update_async(from_account)  # Money gone!

    to_account = await self.account_repo.get_async(to_account_id)
    to_account.deposit(amount)
    await self.account_repo.update_async(to_account)  # FAILS = Money lost!
```

**DDD Solution**: This indicates wrong aggregate boundaries!

**Correct Design**:

```python
# ✅ CORRECT: Single aggregate for the transaction
class MoneyTransfer(AggregateRoot):
    """Transfer is the aggregate, not individual accounts"""
    source_account_id: str
    destination_account_id: str
    amount: Decimal
    status: TransferStatus  # Pending, Completed, Failed

    def complete(self):
        # Saga/Process Manager orchestrates account updates
        self.status = TransferStatus.COMPLETED
        self.register_event(TransferCompletedEvent(...))

class TransferCompletedEventHandler:
    async def handle_async(self, event: TransferCompletedEvent):
        # Update accounts separately with compensation
        await self._withdraw_from_source(event)
        await self._deposit_to_destination(event)
```

## Recommended Patterns

### Pattern 1: Prioritize Critical Operations

```python
class PlaceOrderHandler:
    async def handle_async(self, command: PlaceOrderCommand):
        # Critical path: Order must succeed
        order = Order.create(...)
        await self.order_repository.add_async(order)
        # ✅ Events published: OrderPlacedEvent

        # Non-critical path: Log errors but don't fail
        try:
            customer = await self._update_customer_info(command)
        except Exception as e:
            log.warning(f"Customer update failed, order still placed: {e}")
            # Order is successfully placed despite customer failure

        return self.created(order_dto)
```

### Pattern 2: Event-Driven Consistency

```python
class PlaceOrderHandler:
    async def handle_async(self, command: PlaceOrderCommand):
        order = Order.create(
            customer_phone=command.customer_phone,
            customer_address=command.customer_address
        )
        await self.order_repository.add_async(order)
        # ✅ OrderPlacedEvent published automatically
        return self.created(order_dto)

class OrderPlacedEventHandler:
    """Separate event handler for customer updates"""
    async def handle_async(self, event: OrderPlacedEvent):
        # Asynchronous, with retry logic
        customer = await self._get_or_create_customer(event)
        customer.record_order(event.order_id, event.order_total)
        await self.customer_repository.update_async(customer)
        # ✅ If this fails, it can retry without affecting order
```

**Benefits**:

- Order placement succeeds immediately
- Customer update happens asynchronously with retry
- Failures are isolated and recoverable
- Clear separation of concerns

### Pattern 3: Process Manager / Saga

For complex multi-aggregate workflows:

```python
class OrderFulfillmentSaga(AggregateRoot):
    """Orchestrates multi-step process"""
    order_id: str
    customer_updated: bool
    inventory_reserved: bool
    payment_processed: bool

    def handle_order_placed(self, event: OrderPlacedEvent):
        self.order_id = event.order_id
        self.register_event(UpdateCustomerCommand(...))

    def handle_customer_updated(self, event: CustomerUpdatedEvent):
        self.customer_updated = True
        self.register_event(ReserveInventoryCommand(...))

    def handle_step_failed(self, event: StepFailedEvent):
        # Trigger compensating actions
        if self.customer_updated:
            self.register_event(RevertCustomerCommand(...))
```

## Should You Worry?

### No, if

✅ Operations have different business priorities (critical vs. nice-to-have)
✅ You use event-driven eventual consistency
✅ Failures are logged and monitored
✅ System can recover through retries or manual intervention
✅ Business accepts temporary inconsistency

### Yes, if

⚠️ Both operations are equally critical (money transfer, inventory allocation)
⚠️ Partial success creates unrecoverable state
⚠️ Business cannot tolerate any inconsistency
⚠️ No compensation mechanism exists

**But then**: Your aggregate boundaries are probably wrong! Consider:

- Creating a new aggregate that represents the transaction
- Using Process Manager / Saga pattern
- Re-examining domain model

## Is UnitOfWork Relevant for This?

### Short Answer: NO

**UnitOfWork does NOT provide**:

- Database transaction coordination
- Automatic rollback on failure
- Cross-repository consistency guarantees
- Compensation logic

**UnitOfWork ONLY provides**:

- Event collection from multiple aggregates
- Batch event dispatching after command succeeds
- Aggregate tracking for middleware

### What Would Help?

**Option 1: Database Transactions (if using same database)**

```python
class TransactionalRepository:
    async def execute_in_transaction(self, operations: list[Callable]):
        async with await self._client.start_session() as session:
            async with session.start_transaction():
                for operation in operations:
                    await operation(session)
                # All or nothing!
```

**Limitation**: Only works for same database, doesn't scale to distributed systems

**Option 2: Saga / Process Manager (for distributed systems)**

- Orchestrates multi-step processes
- Implements compensation logic
- Handles failures gracefully
- Provides audit trail

**Option 3: Accept Eventual Consistency (DDD recommendation)**

- Use events for cross-aggregate updates
- Implement retry mechanisms
- Monitor failures
- Design compensation workflows

## Conclusion for Mario-Pizzeria

### Current PlaceOrderCommand

**Situation**:

- Order (critical) + Customer (secondary)
- Order must succeed for business
- Customer update is enhancement

**Recommendation**: Event-Driven Pattern

```python
class PlaceOrderHandler:
    async def handle_async(self, command: PlaceOrderCommand):
        # Only focus on order creation
        order = Order.create(
            customer_phone=command.customer_phone,
            delivery_address=command.customer_address
        )

        for pizza in command.pizzas:
            order.add_item(pizza)

        order.confirm()

        await self.order_repository.add_async(order)
        # ✅ OrderPlacedEvent published automatically by Repository

        return self.created(order_dto)

class OrderPlacedEventHandler:
    async def handle_async(self, event: OrderPlacedEvent):
        # Separate concern: update customer profile
        try:
            customer = await self._get_or_create_customer(event)
            customer.record_order(event.order_id)
            await self.customer_repository.update_async(customer)
        except Exception as e:
            log.error(f"Failed to update customer for order {event.order_id}: {e}")
            # Could trigger retry queue, alert monitoring, etc.
```

**Benefits**:

- Simple handler focused on single responsibility
- Order placement always succeeds
- Customer updates are resilient (can retry)
- Clear separation of concerns
- Natural fit for Repository-based event publishing

### Bottom Line

**Don't worry about multi-aggregate consistency in PlaceOrderCommand**:

1. Order is the critical aggregate (must succeed)
2. Customer is secondary (nice to have)
3. Event-driven updates handle failures gracefully
4. This is proper DDD design, not a limitation

**If you need ACID across aggregates**:

- Re-examine aggregate boundaries (probably wrong)
- Consider Saga / Process Manager pattern
- Accept that distributed systems require eventual consistency

**UnitOfWork doesn't help** because it's just an event collector, not a transaction coordinator. Repository-based event publishing is cleaner and achieves the same result.
