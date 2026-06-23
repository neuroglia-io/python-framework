"""Command for dismissing customer notifications"""

from dataclasses import dataclass

from application.services.notification_service import notification_service
from domain.repositories import ICustomerRepository

from neuroglia.core import OperationResult
from neuroglia.mediation import Command, CommandHandler


@dataclass
class DismissCustomerNotificationCommand(Command[OperationResult[dict]]):
    """Command to dismiss a customer notification"""

    notification_id: str
    user_id: str


class DismissCustomerNotificationHandler(CommandHandler[DismissCustomerNotificationCommand, OperationResult[dict]]):
    """Handler for dismissing customer notifications"""

    def __init__(self, customer_repository: ICustomerRepository):
        self.customer_repository = customer_repository

    async def handle_async(self, request: DismissCustomerNotificationCommand) -> OperationResult[dict]:
        """Handle notification dismissal"""

        try:
            # Find customer by user_id
            all_customers = await self.customer_repository.get_all_async()
            customer = None
            for c in all_customers:
                if hasattr(c.state, "user_id") and c.state.user_id == request.user_id:
                    customer = c
                    break

            if not customer:
                return self.not_found("Customer", request.user_id)

            # Dismiss the notification using the notification service
            success = notification_service.dismiss_notification(request.user_id, request.notification_id)

            if success:
                return self.ok({"message": "Notification dismissed successfully"})
            else:
                return self.bad_request("Failed to dismiss notification")

        except Exception as e:
            return self.bad_request(f"Failed to dismiss notification: {str(e)}")
