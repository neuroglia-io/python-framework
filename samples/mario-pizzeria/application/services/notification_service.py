"""Simple in-memory notification service for tracking dismissed notifications"""

from datetime import datetime, timezone

from api.dtos.notification_dtos import CustomerNotificationDto


class NotificationService:
    """Simple in-memory service to manage notifications and dismissals"""

    def __init__(self):
        # Track dismissed notification IDs per user
        self._dismissed_notifications: dict[str, set[str]] = {}

    def dismiss_notification(self, user_id: str, notification_id: str) -> bool:
        """Mark a notification as dismissed for a user"""
        if user_id not in self._dismissed_notifications:
            self._dismissed_notifications[user_id] = set()

        self._dismissed_notifications[user_id].add(notification_id)
        return True

    def is_notification_dismissed(self, user_id: str, notification_id: str) -> bool:
        """Check if a notification is dismissed for a user"""
        return user_id in self._dismissed_notifications and notification_id in self._dismissed_notifications[user_id]

    def get_sample_notifications(self, user_id: str, customer_id: str) -> list[CustomerNotificationDto]:
        """Get sample notifications, filtering out dismissed ones"""
        all_sample_notifications = [
            CustomerNotificationDto(
                id="sample-notification-1",
                customer_id=customer_id,
                notification_type="order_cooking_started",
                title="👨‍🍳 Cooking Started",
                message="Your order is now being prepared!",
                order_id="sample-order-123",
                status="unread",
                created_at=datetime.now(timezone.utc),
                read_at=None,
                dismissed_at=None,
            ),
            CustomerNotificationDto(
                id="sample-notification-2",
                customer_id=customer_id,
                notification_type="order_ready",
                title="🍕 Order Ready",
                message="Your delicious pizza is ready for pickup!",
                order_id="sample-order-124",
                status="unread",
                created_at=datetime.now(timezone.utc),
                read_at=None,
                dismissed_at=None,
            ),
            CustomerNotificationDto(
                id="sample-notification-3",
                customer_id=customer_id,
                notification_type="promotion",
                title="🎉 Special Offer",
                message="Get 20% off your next order with code PIZZA20!",
                order_id=None,
                status="unread",
                created_at=datetime.now(timezone.utc),
                read_at=None,
                dismissed_at=None,
            ),
        ]

        # Filter out dismissed notifications
        active_notifications = []
        for notification in all_sample_notifications:
            if not self.is_notification_dismissed(user_id, notification.id):
                active_notifications.append(notification)
            else:
                # Mark as dismissed in the DTO for completeness
                notification.dismissed_at = datetime.now(timezone.utc)

        return active_notifications


# Global singleton instance (in a real app, this would be properly injected)
notification_service = NotificationService()
