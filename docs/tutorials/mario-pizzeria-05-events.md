# Part 5: Events & Integration

**Time: 45 minutes** | **Prerequisites: [Part 4](mario-pizzeria-04-api.md)**

In this tutorial, you'll learn how to use domain events to build reactive, loosely-coupled systems. Events enable different parts of your application to react to business occurrences without direct dependencies.

## 🎯 What You'll Learn

- What domain events are and when to use them
- How to publish and handle events
- Event-driven architecture patterns
- CloudEvents for external integration
- Asynchronous event processing

## 💡 Understanding Events

### The Problem

Without events, components are tightly coupled:

```python
# ❌ Tight coupling - Order knows about Kitchen and Notifications
class OrderService:
    def confirm_order(self, order_id):
        order = self.repo.get(order_id)
        order.confirm()

        # Direct dependencies on other systems
        self.kitchen_service.add_to_queue(order)  # 😟
        self.notification_service.send_sms(order)  # 😟
        self.analytics_service.track_order(order)  # 😟

        self.repo.save(order)
```

**Problems:**

- Order service knows about Kitchen, Notifications, Analytics
- Can't add new reactions without modifying OrderService
- Difficult to test (must mock 3+ services)
- Changes ripple across services

### The Solution: Domain Events

Events **decouple the "what happened" from "what to do about it"**:

```
┌─────────────┐
│   Order     │  Order confirmed!
│  (raises    │──────┐
│   event)    │      │
└─────────────┘      │
                     ▼
              ┌──────────────┐
              │  Event Bus   │
              └──────┬───────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
  ┌─────────┐  ┌─────────┐  ┌─────────┐
  │ Kitchen │  │  Notify │  │Analytics│
  │ Handler │  │ Handler │  │ Handler │
  └─────────┘  └─────────┘  └─────────┘
```

**Benefits:**

- **Loose Coupling**: Order doesn't know who listens
- **Extensibility**: Add handlers without changing domain
- **Testability**: Test handlers independently
- **Scalability**: Process events asynchronously

## 📣 Publishing Domain Events

Domain events are **automatically published** when you use `AggregateRoot`.

### How It Works

In your domain entity (from Part 2):

```python
from neuroglia.data.abstractions import AggregateRoot, AggregateState
from domain.events import OrderConfirmedEvent

class Order(AggregateRoot[OrderState, str]):

    def confirm_order(self) -> None:
        """Confirm the order"""
        if self.state.status != OrderStatus.PENDING:
            raise ValueError("Only pending orders can be confirmed")

        # 1️⃣ Create event
        event = OrderConfirmedEvent(
            aggregate_id=self.id(),
            confirmed_time=datetime.now(timezone.utc),
            total_amount=self.total_amount,
            pizza_count=self.pizza_count
        )

        # 2️⃣ Register event (stored in aggregate)
        self.register_event(event)

        # 3️⃣ Apply to state
        self.state.on(event)
```

**When are events published?**

Events are **automatically published by the repository** when you save an aggregate:

```python
# In handler
order.confirm_order()  # Raises event internally
await self.order_repository.add_async(order)

# Repository does:
# 1. Save aggregate state to database
# 2. Get uncommitted events from aggregate
# 3. Publish each event to event bus
# 4. Clear uncommitted events from aggregate
```

This ensures **transactional consistency**:

- ✅ Events only published if database save succeeds
- ✅ No manual event management needed
- ✅ Command handler IS the transaction boundary
- ✅ Repository coordinates persistence + event publishing

## 🎧 Handling Domain Events

Event handlers react to domain events.

### Step 1: Create Event Handler

Create `application/events/order_event_handlers.py`:

```python
"""Order event handlers"""
import logging

from domain.events import OrderConfirmedEvent
from neuroglia.mediation import DomainEventHandler

logger = logging.getLogger(__name__)


class OrderConfirmedEventHandler(DomainEventHandler[OrderConfirmedEvent]):
    """
    Handles OrderConfirmedEvent.

    DomainEventHandler:
    - Processes events after they're published
    - Can have side effects (send email, update systems)
    - Runs asynchronously
    - Multiple handlers can listen to same event
    """

    async def handle_async(self, event: OrderConfirmedEvent) -> None:
        """
        Process order confirmed event.

        This runs AFTER the order is saved to the database.
        """
        logger.info(
            f"🍕 Order {event.aggregate_id} confirmed! "
            f"Total: ${event.total_amount}, Pizzas: {event.pizza_count}"
        )

        # Send confirmation SMS
        await self._send_customer_sms(event)

        # Add to kitchen queue
        await self._notify_kitchen(event)

        # Track in analytics
        await self._track_analytics(event)

    async def _send_customer_sms(self, event: OrderConfirmedEvent):
        """Send SMS notification to customer"""
        # In real app: integrate with Twilio, SNS, etc.
        logger.info(f"📱 SMS sent: Order {event.aggregate_id} confirmed")

    async def _notify_kitchen(self, event: OrderConfirmedEvent):
        """Add order to kitchen queue"""
        # In real app: update kitchen display system
        logger.info(f"👨‍🍳 Kitchen notified of order {event.aggregate_id}")

    async def _track_analytics(self, event: OrderConfirmedEvent):
        """Track order in analytics"""
        # In real app: send to analytics service
        logger.info(f"📊 Analytics tracked for order {event.aggregate_id}")
```

**Handler characteristics:**

- **Async**: All handlers are async for non-blocking execution
- **Side Effects Only**: Don't modify domain state (that happened already)
- **Idempotent**: Should be safe to run multiple times
- **Independent**: One handler failure shouldn't affect others

### Step 2: Create Multiple Handlers for Same Event

You can have **multiple handlers** for the same event:

```python
class OrderConfirmedEmailHandler(DomainEventHandler[OrderConfirmedEvent]):
    """Sends email receipt when order is confirmed"""

    def __init__(self, email_service: EmailService):
        self.email_service = email_service

    async def handle_async(self, event: OrderConfirmedEvent) -> None:
        """Send email receipt"""
        logger.info(f"📧 Sending email receipt for order {event.aggregate_id}")

        await self.email_service.send_receipt(
            order_id=event.aggregate_id,
            total=event.total_amount
        )


class OrderConfirmedMetricsHandler(DomainEventHandler[OrderConfirmedEvent]):
    """Records metrics when order is confirmed"""

    async def handle_async(self, event: OrderConfirmedEvent) -> None:
        """Record order metrics"""
        logger.info(f"📈 Recording metrics for order {event.aggregate_id}")

        # Record metrics (e.g., Prometheus, CloudWatch)
        # metrics.order_total.observe(event.total_amount)
        # metrics.pizza_count.observe(event.pizza_count)
```

**All three handlers** will execute when `OrderConfirmedEvent` is published!

### Step 3: Handler for Order Lifecycle

Create handlers for other events:

```python
class CookingStartedEventHandler(DomainEventHandler[CookingStartedEvent]):
    """Handles cooking started events"""

    async def handle_async(self, event: CookingStartedEvent) -> None:
        """Process cooking started"""
        logger.info(
            f"👨‍🍳 Cooking started for order {event.aggregate_id} "
            f"by {event.user_name} at {event.cooking_started_time}"
        )

        # Update customer app with cooking status
        # Send estimated ready time notification
        # Update kitchen display


class OrderReadyEventHandler(DomainEventHandler[OrderReadyEvent]):
    """Handles order ready events"""

    async def handle_async(self, event: OrderReadyEvent) -> None:
        """Process order ready"""
        logger.info(
            f"✅ Order {event.aggregate_id} is ready! "
            f"Completed by {event.user_name}"
        )

        # Send "order ready" SMS/push notification
        # Update pickup queue display
        # Print pickup receipt

        # Calculate if order was on time
        if event.estimated_ready_time:
            delta = (event.ready_time - event.estimated_ready_time).total_seconds()
            if delta > 300:  # 5 minutes late
                logger.warning(f"⏰ Order was {delta/60:.1f} minutes late")
```

## 🌐 CloudEvents for External Integration

CloudEvents is a **standard format** for event interoperability.

### What are CloudEvents?

CloudEvents provide a common event format:

```json
{
  "specversion": "1.0",
  "type": "com.mario-pizzeria.order.confirmed",
  "source": "/orders/service",
  "id": "A234-1234-1234",
  "time": "2025-10-25T14:30:00Z",
  "datacontenttype": "application/json",
  "data": {
    "orderId": "order-123",
    "totalAmount": 29.98,
    "pizzaCount": 2
  }
}
```

**Benefits:**

- **Interoperability**: Works across languages and platforms
- **Routing**: Type-based routing in event brokers
- **Metadata**: Standardized headers (source, time, type)
- **Tools**: Compatible with Knative, Azure Event Grid, etc.

### Publishing CloudEvents

Create `application/events/base_domain_event_handler.py`:

```python
"""Base handler for publishing CloudEvents"""
from typing import Generic, TypeVar

from neuroglia.eventing.cloud_events.infrastructure import CloudEventBus
from neuroglia.eventing.cloud_events.infrastructure.cloud_event_publisher import (
    CloudEventPublishingOptions
)
from neuroglia.eventing.domain_event import DomainEvent
from neuroglia.mediation import Mediator

TEvent = TypeVar("TEvent", bound=DomainEvent)


class BaseDomainEventHandler(Generic[TEvent]):
    """
    Base class for event handlers that publish CloudEvents.

    Provides helper to convert domain events to CloudEvents.
    """

    def __init__(
        self,
        mediator: Mediator,
        cloud_event_bus: CloudEventBus,
        cloud_event_publishing_options: CloudEventPublishingOptions,
    ):
        self.mediator = mediator
        self.cloud_event_bus = cloud_event_bus
        self.publishing_options = cloud_event_publishing_options

    async def publish_cloud_event_async(self, event: TEvent) -> None:
        """
        Publish domain event as CloudEvent.

        The framework automatically:
        - Converts domain event to CloudEvent format
        - Adds metadata (type, source, time, id)
        - Publishes to configured event bus
        """
        if self.cloud_event_bus and self.publishing_options:
            await self.cloud_event_bus.publish_async(
                event,
                self.publishing_options
            )
```

Use in handlers:

```python
class OrderConfirmedEventHandler(
    BaseDomainEventHandler[OrderConfirmedEvent],
    DomainEventHandler[OrderConfirmedEvent]
):

    async def handle_async(self, event: OrderConfirmedEvent) -> None:
        """Process and publish event"""
        logger.info(f"Order {event.aggregate_id} confirmed")

        # Handle internally
        await self._send_notifications(event)

        # Publish to external systems via CloudEvents
        await self.publish_cloud_event_async(event)
```

### Configure CloudEvents in main.py

```python
from neuroglia.eventing.cloud_events.infrastructure import (
    CloudEventPublisher,
    CloudEventIngestor
)

# Configure CloudEvent publishing
CloudEventPublisher.configure(builder)

# Configure CloudEvent consumption (optional)
CloudEventIngestor.configure(
    builder,
    ["application.events.integration"]  # External event handlers
)
```

## 🧪 Testing Event Handlers

Create `tests/application/events/test_order_event_handlers.py`:

```python
"""Tests for order event handlers"""
import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone
from decimal import Decimal

from application.events.order_event_handlers import (
    OrderConfirmedEventHandler
)
from domain.events import OrderConfirmedEvent


@pytest.fixture
def handler():
    """Create handler with mocked dependencies"""
    mediator = AsyncMock()
    cloud_event_bus = AsyncMock()
    publishing_options = Mock()

    return OrderConfirmedEventHandler(
        mediator=mediator,
        cloud_event_bus=cloud_event_bus,
        cloud_event_publishing_options=publishing_options
    )


@pytest.mark.asyncio
async def test_order_confirmed_handler(handler):
    """Test OrderConfirmedEventHandler processes event"""
    # Create event
    event = OrderConfirmedEvent(
        aggregate_id="order-123",
        confirmed_time=datetime.now(timezone.utc),
        total_amount=Decimal("29.98"),
        pizza_count=2
    )

    # Handle event
    await handler.handle_async(event)

    # Verify CloudEvent published
    handler.cloud_event_bus.publish_async.assert_called_once()


@pytest.mark.asyncio
async def test_multiple_handlers_same_event():
    """Test multiple handlers can process same event"""
    event = OrderConfirmedEvent(
        aggregate_id="order-123",
        confirmed_time=datetime.now(timezone.utc),
        total_amount=Decimal("29.98"),
        pizza_count=2
    )

    # Create multiple handlers
    handler1 = OrderConfirmedEventHandler(Mock(), AsyncMock(), Mock())
    handler2 = OrderConfirmedEmailHandler(Mock())

    # Both should handle event
    await handler1.handle_async(event)
    await handler2.handle_async(event)

    # Each handler processes independently
    assert True  # Both completed without error
```

## 📝 Key Takeaways

1. **Domain Events**: Represent business occurrences, raised by aggregates
2. **Loose Coupling**: Events decouple publishers from subscribers
3. **Multiple Handlers**: Many handlers can react to one event
4. **Automatic Publishing**: Repository handles event dispatch when saving aggregates
5. **CloudEvents**: Standard format for external integration
6. **Async Processing**: Handlers run asynchronously for performance

## 🚀 What's Next?

In [Part 6: Persistence & Repositories](mario-pizzeria-06-persistence.md), you'll learn:

- Implementing the repository pattern
- MongoDB integration with Motor
- Repository pattern for persistence and event publishing
- Data persistence strategies

---

**Previous:** [← Part 4: API Controllers](mario-pizzeria-04-api.md) | **Next:** [Part 6: Persistence & Repositories →](mario-pizzeria-06-persistence.md)
