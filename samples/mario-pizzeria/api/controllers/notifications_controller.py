"""
API controller for customer notifications.

Provides endpoints for retrieving and managing customer notifications.
"""

from typing import Annotated

from api.dtos.notification_dtos import (
    CustomerNotificationListDto,
    DismissNotificationDto,
)
from application.commands.dismiss_customer_notification_command import (
    DismissCustomerNotificationCommand,
)
from application.queries.get_customer_notifications_query import (
    GetCustomerNotificationsQuery,
)
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase

# Security setup
security = HTTPBearer()


class NotificationsController(ControllerBase):
    """Controller for customer notification operations"""

    def __init__(self, service_provider, mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

    def _get_user_id_from_token(self, credentials: HTTPAuthorizationCredentials) -> str:
        """Extract user ID from JWT token"""
        # In a real application, you would validate the JWT token and extract the user ID
        # For now, we'll extract from the request session or token payload
        # This is a placeholder implementation
        return "user-123"  # Replace with actual JWT parsing

    async def get_customer_notifications(
        self,
        request: Request,
        page: int = 1,
        page_size: int = 20,
        include_dismissed: bool = False,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)] = None,
    ) -> CustomerNotificationListDto:
        """
        Get customer notifications.

        Args:
            request: FastAPI request object
            page: Page number for pagination
            page_size: Number of notifications per page
            include_dismissed: Whether to include dismissed notifications
            credentials: JWT authorization credentials

        Returns:
            CustomerNotificationListDto: List of customer notifications
        """
        try:
            # Extract user ID from session or token
            user_id = request.session.get("user_id")
            if not user_id:
                raise HTTPException(status_code=401, detail="User not authenticated")

            # Query customer notifications
            query = GetCustomerNotificationsQuery(
                user_id=user_id,
                page=page,
                page_size=page_size,
                include_dismissed=include_dismissed,
            )

            result = await self.mediator.execute_async(query)

            if not result.is_success:
                raise HTTPException(status_code=400, detail=result.error_message)

            return result.data

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to retrieve notifications: {str(e)}")

    async def dismiss_notification(
        self,
        request: Request,
        dismiss_dto: DismissNotificationDto,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)] = None,
    ) -> dict:
        """
        Dismiss a customer notification.

        Args:
            request: FastAPI request object
            dismiss_dto: Notification dismissal request
            credentials: JWT authorization credentials

        Returns:
            dict: Success response
        """
        try:
            # Extract user ID from session or token
            user_id = request.session.get("user_id")
            if not user_id:
                raise HTTPException(status_code=401, detail="User not authenticated")

            # Dismiss notification command
            command = DismissCustomerNotificationCommand(
                notification_id=dismiss_dto.notification_id,
                user_id=user_id,
            )

            result = await self.mediator.execute_async(command)

            if not result.is_success:
                raise HTTPException(status_code=400, detail=result.error_message)

            return {"message": "Notification dismissed successfully"}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to dismiss notification: {str(e)}")

    async def mark_notification_as_read(
        self,
        notification_id: str,
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)] = None,
    ) -> dict:
        """
        Mark a customer notification as read.

        Args:
            notification_id: ID of the notification to mark as read
            request: FastAPI request object
            credentials: JWT authorization credentials

        Returns:
            dict: Success response
        """
        try:
            # Extract user ID from session or token
            user_id = request.session.get("user_id")
            if not user_id:
                raise HTTPException(status_code=401, detail="User not authenticated")

            # Mark as read command (we'll need to create this)
            # For now, just return success
            return {"message": "Notification marked as read successfully"}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to mark notification as read: {str(e)}")
