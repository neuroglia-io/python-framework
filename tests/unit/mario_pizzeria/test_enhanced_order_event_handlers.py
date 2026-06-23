"""
Unit tests for enhanced order event handlers
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock

# Add samples to path
samples_root = Path(__file__).parent.parent.parent.parent.parent / "samples" / "mario-pizzeria"
sys.path.insert(0, str(samples_root))

from application.events.order_event_handlers import (
    CookingStartedEventHandler,
    OrderCancelledEventHandler,
    OrderCreatedEventHandler,
    OrderDeliveredEventHandler,
)
from domain.entities import Customer
from domain.events import (
    CookingStartedEvent,
    OrderCancelledEvent,
    OrderCreatedEvent,
    OrderDeliveredEvent,
)


class TestEnhancedOrderEventHandlers:
    """Test cases for enhanced order event handlers"""

    def setup_method(self):
        """Set up test dependencies"""
        self.mediator = Mock()
        self.cloud_event_bus = Mock()
        self.cloud_event_publishing_options = Mock()
        self.customer_repository = AsyncMock()
        self.order_repository = AsyncMock()

    async def test_order_created_handler_adds_active_order(self):
        """Test OrderCreatedEventHandler adds order to customer's active orders"""
        # Setup
        handler = OrderCreatedEventHandler(
            mediator=self.mediator,
            cloud_event_bus=self.cloud_event_bus,
            cloud_event_publishing_options=self.cloud_event_publishing_options,
            customer_repository=self.customer_repository,
        )

        # Create mock customer
        customer = Mock(spec=Customer)
        customer.add_active_order = Mock()
        self.customer_repository.get_async.return_value = customer

        # Create event
        event = OrderCreatedEvent(
            aggregate_id="order-123",
            customer_id="customer-456",
            order_time=datetime.now(),
        )

        # Execute
        await handler.handle_async(event)

        # Verify
        self.customer_repository.get_async.assert_called_once_with("customer-456")
        customer.add_active_order.assert_called_once_with("order-123")
        self.customer_repository.update_async.assert_called_once_with(customer)

    async def test_order_created_handler_handles_customer_not_found(self):
        """Test OrderCreatedEventHandler handles missing customer gracefully"""
        # Setup
        handler = OrderCreatedEventHandler(
            mediator=self.mediator,
            cloud_event_bus=self.cloud_event_bus,
            cloud_event_publishing_options=self.cloud_event_publishing_options,
            customer_repository=self.customer_repository,
        )

        # Customer not found
        self.customer_repository.get_async.return_value = None

        # Create event
        event = OrderCreatedEvent(
            aggregate_id="order-123",
            customer_id="nonexistent-customer",
            order_time=datetime.now(),
        )

        # Execute - should not raise exception
        await handler.handle_async(event)

        # Verify customer lookup was attempted but update was not called
        self.customer_repository.get_async.assert_called_once_with("nonexistent-customer")
        self.customer_repository.update_async.assert_not_called()

    async def test_cooking_started_handler_creates_notification(self):
        """Test CookingStartedEventHandler attempts to create notification"""
        # Setup
        handler = CookingStartedEventHandler(
            mediator=self.mediator,
            cloud_event_bus=self.cloud_event_bus,
            cloud_event_publishing_options=self.cloud_event_publishing_options,
            order_repository=self.order_repository,
            customer_repository=self.customer_repository,
        )

        # Create mock order with customer_id
        order = Mock()
        order.state.customer_id = "customer-456"
        self.order_repository.get_async.return_value = order

        # Create event
        event = CookingStartedEvent(
            aggregate_id="order-123",
            cooking_started_time=datetime.now(),
            user_id="chef-789",
            user_name="Chef Mario",
        )

        # Execute
        await handler.handle_async(event)

        # Verify order lookup was called
        self.order_repository.get_async.assert_called_once_with("order-123")

    async def test_order_delivered_handler_removes_active_order(self):
        """Test OrderDeliveredEventHandler removes order from customer's active orders"""
        # Setup
        handler = OrderDeliveredEventHandler(
            mediator=self.mediator,
            cloud_event_bus=self.cloud_event_bus,
            cloud_event_publishing_options=self.cloud_event_publishing_options,
            order_repository=self.order_repository,
            customer_repository=self.customer_repository,
        )

        # Create mocks
        order = Mock()
        order.state.customer_id = "customer-456"
        self.order_repository.get_async.return_value = order

        customer = Mock(spec=Customer)
        customer.remove_active_order = Mock()
        self.customer_repository.get_async.return_value = customer

        # Create event
        event = OrderDeliveredEvent(
            aggregate_id="order-123",
            delivered_time=datetime.now(),
        )

        # Execute
        await handler.handle_async(event)

        # Verify
        self.order_repository.get_async.assert_called_once_with("order-123")
        self.customer_repository.get_async.assert_called_once_with("customer-456")
        customer.remove_active_order.assert_called_once_with("order-123")
        self.customer_repository.update_async.assert_called_once_with(customer)

    async def test_order_cancelled_handler_removes_active_order(self):
        """Test OrderCancelledEventHandler removes order from customer's active orders"""
        # Setup
        handler = OrderCancelledEventHandler(
            mediator=self.mediator,
            cloud_event_bus=self.cloud_event_bus,
            cloud_event_publishing_options=self.cloud_event_publishing_options,
            order_repository=self.order_repository,
            customer_repository=self.customer_repository,
        )

        # Create mocks
        order = Mock()
        order.state.customer_id = "customer-456"
        self.order_repository.get_async.return_value = order

        customer = Mock(spec=Customer)
        customer.remove_active_order = Mock()
        self.customer_repository.get_async.return_value = customer

        # Create event
        event = OrderCancelledEvent(
            aggregate_id="order-123",
            cancelled_time=datetime.now(),
            reason="Customer request",
        )

        # Execute
        await handler.handle_async(event)

        # Verify
        self.order_repository.get_async.assert_called_once_with("order-123")
        self.customer_repository.get_async.assert_called_once_with("customer-456")
        customer.remove_active_order.assert_called_once_with("order-123")
        self.customer_repository.update_async.assert_called_once_with(customer)
