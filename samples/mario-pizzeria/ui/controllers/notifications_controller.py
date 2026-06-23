"""UI controller for customer notifications pages"""

from application.commands import DismissCustomerNotificationCommand
from application.queries import GetCustomerNotificationsQuery
from application.settings import app_settings
from classy_fastapi import Routable, get, post
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from neuroglia.mvc.controller_base import generate_unique_id_function


class UINotificationsController(ControllerBase):
    """UI notifications management controller"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.name = "Notifications"

        # Initialize Routable with /notifications prefix
        Routable.__init__(
            self,
            prefix="/notifications",
            tags=["UI"],
            generate_unique_id_function=generate_unique_id_function,
        )

    @get("/", response_class=HTMLResponse)
    async def notifications_root(self, request: Request):
        """Handle /notifications/ with trailing slash"""
        return await self.view_notifications(request)

    @get("", response_class=HTMLResponse)
    async def view_notifications(self, request: Request):
        """Display customer notifications page"""
        # Check authentication
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/auth/login?next=/notifications", status_code=302)

        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/auth/login?next=/notifications", status_code=302)

        # Get customer notifications
        notifications = []
        unread_count = 0
        error = None

        try:
            notifications_query = GetCustomerNotificationsQuery(user_id=str(user_id))
            notifications_result = await self.mediator.execute_async(notifications_query)
            if notifications_result.is_success:
                notifications = notifications_result.data.notifications
                unread_count = notifications_result.data.unread_count
            else:
                error = notifications_result.error_message
        except Exception as e:
            error = f"Failed to load notifications: {str(e)}"

        return request.app.state.templates.TemplateResponse(
            "notifications/index.html",
            {
                "request": request,
                "title": "My Notifications",
                "active_page": "notifications",
                "authenticated": True,
                "username": request.session.get("username"),
                "name": request.session.get("name"),
                "email": request.session.get("email"),
                "roles": request.session.get("roles", []),
                "notifications": notifications,
                "unread_count": unread_count,
                "error": error,
                "app_version": app_settings.app_version,
            },
        )

    @post("/{notification_id}/dismiss")
    async def dismiss_notification(self, request: Request, notification_id: str):
        """Dismiss a customer notification"""
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/auth/login", status_code=302)

        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/auth/login", status_code=302)

        # Get redirect URL from query parameter or referer header, default to notifications
        redirect_url = request.query_params.get("redirect")
        if not redirect_url:
            referer = request.headers.get("referer", "")
            if "/profile" in referer:
                redirect_url = "/profile"
            else:
                redirect_url = "/notifications"

        # Dismiss the notification
        command = DismissCustomerNotificationCommand(notification_id=notification_id, user_id=str(user_id))
        result = await self.mediator.execute_async(command)

        if result.is_success:
            return RedirectResponse(url=redirect_url, status_code=302)
        else:
            error_url = f"{redirect_url}{'&' if '?' in redirect_url else '?'}error=Failed+to+dismiss+notification"
            return RedirectResponse(url=error_url, status_code=302)
