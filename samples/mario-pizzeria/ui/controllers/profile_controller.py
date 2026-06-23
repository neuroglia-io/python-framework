"""UI controller for customer profile pages"""

from typing import Optional

from application.commands import UpdateCustomerProfileCommand
from application.queries import (
    GetCustomerNotificationsQuery,
    GetOrCreateCustomerProfileQuery,
)
from application.settings import app_settings
from classy_fastapi import Routable, get, post
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase
from neuroglia.mvc.controller_base import generate_unique_id_function


class UIProfileController(ControllerBase):
    """UI profile management controller"""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        self.service_provider = service_provider
        self.mapper = mapper
        self.mediator = mediator
        self.name = "Profile"

        # Initialize Routable with /profile prefix
        Routable.__init__(
            self,
            prefix="/profile",
            tags=["UI"],
            generate_unique_id_function=generate_unique_id_function,
        )

    @get("/", response_class=HTMLResponse)
    async def profile_root(self, request: Request):
        """Handle /profile/ with trailing slash"""
        return await self.view_profile(request)

    @get("", response_class=HTMLResponse)
    async def view_profile(self, request: Request):
        """Display user profile page"""
        # Check authentication
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/auth/login?next=/profile", status_code=302)

        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/auth/login?next=/profile", status_code=302)

        # Get or create profile
        query = GetOrCreateCustomerProfileQuery(
            user_id=str(user_id),
            email=request.session.get("email"),
            name=request.session.get("name"),
        )
        result = await self.mediator.execute_async(query)

        profile = result.data if result.is_success else None
        error = None if result.is_success else result.error_message

        # Get customer notifications
        notifications = []
        unread_count = 0
        if user_id:
            notifications_query = GetCustomerNotificationsQuery(user_id=str(user_id))
            notifications_result = await self.mediator.execute_async(notifications_query)
            if notifications_result.is_success:
                notifications = notifications_result.data.notifications
                unread_count = notifications_result.data.unread_count

        return request.app.state.templates.TemplateResponse(
            "profile/view.html",
            {
                "request": request,
                "title": "My Profile",
                "active_page": "profile",
                "authenticated": True,
                "username": request.session.get("username"),
                "name": request.session.get("name"),
                "email": request.session.get("email"),
                "roles": request.session.get("roles", []),
                "profile": profile,
                "error": error,
                "notifications": notifications,
                "unread_count": unread_count,
                "app_version": app_settings.app_version,
            },
        )

    @get("/edit", response_class=HTMLResponse)
    async def edit_profile_page(self, request: Request):
        """Display profile edit form"""
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/auth/login?next=/profile/edit", status_code=302)

        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/auth/login?next=/profile/edit", status_code=302)

        # Get or create current profile
        query = GetOrCreateCustomerProfileQuery(
            user_id=str(user_id),
            email=request.session.get("email"),
            name=request.session.get("name"),
        )
        result = await self.mediator.execute_async(query)

        profile = result.data if result.is_success else None

        return request.app.state.templates.TemplateResponse(
            "profile/edit.html",
            {
                "request": request,
                "title": "Edit Profile",
                "active_page": "profile",
                "authenticated": True,
                "username": request.session.get("username"),
                "name": request.session.get("name"),
                "email": request.session.get("email"),
                "roles": request.session.get("roles", []),
                "profile": profile,
                "app_version": app_settings.app_version,
            },
        )

    @post("/edit")
    async def update_profile(
        self,
        request: Request,
        name: str = Form(...),
        email: str = Form(...),
        phone: Optional[str] = Form(None),
        address: Optional[str] = Form(None),
    ):
        """Handle profile update form submission"""
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/auth/login", status_code=302)

        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/auth/login", status_code=302)

        # Get current profile to get customer_id
        query = GetOrCreateCustomerProfileQuery(user_id=str(user_id), email=email, name=name)
        profile_result = await self.mediator.execute_async(query)

        if not profile_result.is_success or not profile_result.data:
            return request.app.state.templates.TemplateResponse(
                "profile/edit.html",
                {
                    "request": request,
                    "title": "Edit Profile",
                    "error": "Profile not found. Please contact support.",
                    "authenticated": True,
                    "username": request.session.get("username"),
                    "name": name,
                    "email": email,
                    "roles": request.session.get("roles", []),
                    "app_version": app_settings.app_version,
                },
                status_code=404,
            )

        profile = profile_result.data

        # Update profile
        command = UpdateCustomerProfileCommand(
            customer_id=profile.id,
            name=name,
            email=email,
            phone=phone if phone else None,
            address=address if address else None,
        )

        result = await self.mediator.execute_async(command)

        if result.is_success:
            # Update session with new info
            request.session["name"] = name
            request.session["email"] = email
            return RedirectResponse(url="/profile?success=true", status_code=302)
        else:
            # Re-render form with error
            return request.app.state.templates.TemplateResponse(
                "profile/edit.html",
                {
                    "request": request,
                    "title": "Edit Profile",
                    "profile": profile,
                    "error": result.error_message,
                    "authenticated": True,
                    "username": request.session.get("username"),
                    "name": name,
                    "email": email,
                    "roles": request.session.get("roles", []),
                    "app_version": app_settings.app_version,
                },
                status_code=400,
            )
