"""
Unit tests for CustomerNotification entity
"""

import sys
from pathlib import Path

# Add samples to path
samples_root = Path(__file__).parent.parent.parent.parent.parent / "samples" / "mario-pizzeria"
sys.path.insert(0, str(samples_root))

from domain.entities import CustomerNotification, NotificationStatus, NotificationType


class TestCustomerNotification:
    """Test cases for CustomerNotification entity"""

    def test_notification_creation(self):
        """Test creating a customer notification"""
        notification = CustomerNotification(
            customer_id="customer-123",
            notification_type=NotificationType.ORDER_COOKING_STARTED,
            title="Cooking Started",
            message="Your order is being prepared!",
            order_id="order-123",
        )

        assert notification.state.customer_id == "customer-123"
        assert notification.state.notification_type == NotificationType.ORDER_COOKING_STARTED
        assert notification.state.title == "Cooking Started"
        assert notification.state.message == "Your order is being prepared!"
        assert notification.state.order_id == "order-123"
        assert notification.state.status == NotificationStatus.UNREAD
        assert notification.state.created_at is not None
        assert notification.state.read_at is None
        assert notification.state.dismissed_at is None

    def test_notification_without_order_id(self):
        """Test creating a general notification without order ID"""
        notification = CustomerNotification(
            customer_id="customer-123",
            notification_type=NotificationType.GENERAL,
            title="Welcome!",
            message="Welcome to Mario's Pizzeria!",
        )

        assert notification.state.order_id is None
        assert not notification.is_order_related()

    def test_mark_as_read(self):
        """Test marking notification as read"""
        notification = CustomerNotification(
            customer_id="customer-123",
            notification_type=NotificationType.ORDER_READY,
            title="Order Ready",
            message="Your order is ready!",
            order_id="order-123",
        )

        assert notification.state.status == NotificationStatus.UNREAD

        notification.mark_as_read()

        assert notification.state.status == NotificationStatus.READ
        assert notification.state.read_at is not None

    def test_mark_already_read_notification(self):
        """Test marking an already read notification as read again"""
        notification = CustomerNotification(
            customer_id="customer-123",
            notification_type=NotificationType.ORDER_READY,
            title="Order Ready",
            message="Your order is ready!",
        )

        # Mark as read first time
        notification.mark_as_read()
        first_read_time = notification.state.read_at

        # Mark as read second time (should not change read_at)
        notification.mark_as_read()

        assert notification.state.read_at == first_read_time

    def test_dismiss_notification(self):
        """Test dismissing a notification"""
        notification = CustomerNotification(
            customer_id="customer-123",
            notification_type=NotificationType.ORDER_DELIVERED,
            title="Order Delivered",
            message="Your order has been delivered!",
        )

        notification.dismiss()

        assert notification.state.status == NotificationStatus.DISMISSED
        assert notification.state.dismissed_at is not None

    def test_dismiss_read_notification(self):
        """Test dismissing a notification that was already read"""
        notification = CustomerNotification(
            customer_id="customer-123",
            notification_type=NotificationType.ORDER_READY,
            title="Order Ready",
            message="Your order is ready!",
        )

        notification.mark_as_read()
        notification.dismiss()

        assert notification.state.status == NotificationStatus.DISMISSED
        assert notification.state.dismissed_at is not None

    def test_is_dismissible(self):
        """Test notification dismissibility logic"""
        notification = CustomerNotification(
            customer_id="customer-123",
            notification_type=NotificationType.ORDER_READY,
            title="Order Ready",
            message="Your order is ready!",
        )

        # Unread notification should be dismissible
        assert notification.is_dismissible()

        # Read notification should be dismissible
        notification.mark_as_read()
        assert notification.is_dismissible()

        # Dismissed notification should not be dismissible
        notification.dismiss()
        assert not notification.is_dismissible()

    def test_is_order_related(self):
        """Test order relation detection"""
        # Order-related notification
        order_notification = CustomerNotification(
            customer_id="customer-123",
            notification_type=NotificationType.ORDER_COOKING_STARTED,
            title="Cooking Started",
            message="Your order is being prepared!",
            order_id="order-123",
        )
        assert order_notification.is_order_related()

        # General notification (not order-related)
        general_notification = CustomerNotification(
            customer_id="customer-123",
            notification_type=NotificationType.GENERAL,
            title="Welcome!",
            message="Welcome to Mario's Pizzeria!",
        )
        assert not general_notification.is_order_related()

    def test_string_representation(self):
        """Test string representation of notification"""
        notification = CustomerNotification(
            customer_id="customer-123",
            notification_type=NotificationType.ORDER_READY,
            title="Order Ready",
            message="Your order is ready!",
        )

        str_repr = str(notification)
        assert "Order Ready" in str_repr
        assert "unread" in str_repr.lower()

        notification.mark_as_read()
        str_repr = str(notification)
        assert "read" in str_repr.lower()
